"""Single-file benchmark input preprocessing utilities."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gemmi
from scripts.benchlib.datasets import DatasetConfigError, dataset_path
from scripts.benchlib.paths import ROOT

_MAX_SERIAL = 99999
_MAX_RESNUM = 9999
_CHAIN_IDS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
_CHAIN_IDS += [chr(c) for c in range(ord("a"), ord("z") + 1)]
_CHAIN_IDS += [chr(c) for c in range(ord("0"), ord("9") + 1)]


class PreprocessError(RuntimeError):
    """Raised when a single-file benchmark input cannot be prepared."""


@dataclass(frozen=True)
class PreparedStructure:
    """Metadata for one prepared single-file benchmark input."""

    structure_id: str
    role: str
    source_kind: str
    source_dataset: str
    source_path: Path
    output_path: Path
    n_atoms: int
    n_chains: int
    status: str
    notes: str = ""


def count_pdb_atoms_and_chains(path: Path) -> tuple[int, int]:
    """Count ATOM records and non-blank chain IDs in a PDB file."""
    atoms = 0
    chains: set[str] = set()
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("ATOM  "):
                continue
            atoms += 1
            chain = line[21].strip() if len(line) > 21 else ""
            chains.add(chain or "?")
    return atoms, len(chains)


def _fix_cryst1_z(output_path: Path) -> None:
    """Ensure the PDB CRYST1 Z field is populated for pdbtbx/RustSASA."""
    lines = output_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.startswith("CRYST1"):
            continue
        z_field = line[66:70] if len(line) > 66 else ""
        if z_field.strip():
            return
        padded = line.rstrip("\n").ljust(80)
        lines[index] = padded[:66] + "   1" + padded[70:] + "\n"
        output_path.write_text("".join(lines), encoding="utf-8")
        return


def _reassign_chain_ids(model: gemmi.Model) -> None:
    """Map long chain IDs onto PDB-compatible single-character IDs."""
    residue_counts: dict[str, int] = {}
    for chain in model:
        chain_residues = len(list(chain))
        for chain_id in _CHAIN_IDS:
            current = residue_counts.get(chain_id, 0)
            if current + chain_residues > _MAX_RESNUM:
                continue
            chain.name = chain_id
            for index, residue in enumerate(chain):
                residue.seqid = gemmi.SeqId(str(current + index + 1))
            residue_counts[chain_id] = current + chain_residues
            break
        else:
            raise PreprocessError("too many residues to fit into PDB chain IDs")


def _wrap_residue_numbers(model: gemmi.Model) -> None:
    """Wrap residue sequence numbers into the PDB 4-digit field."""
    for chain in model:
        for index, residue in enumerate(chain):
            residue.seqid = gemmi.SeqId(str((index % _MAX_RESNUM) + 1))


def _wrap_serial_numbers(model: gemmi.Model) -> None:
    """Wrap atom serial numbers into the PDB 5-digit field."""
    serial = 0
    for chain in model:
        for residue in chain:
            for atom in residue:
                serial = (serial % _MAX_SERIAL) + 1
                atom.serial = serial


def _read_structure(path: Path) -> gemmi.Structure:
    if path.name.endswith(".zst"):
        with tempfile.TemporaryDirectory(prefix="zsasa-bench-cif-") as tmp:
            suffix = "".join(path.suffixes[:-1]) or ".cif"
            decompressed = Path(tmp).joinpath("input" + suffix)
            with decompressed.open("wb") as handle:
                subprocess.run(["zstd", "-dc", str(path)], check=True, stdout=handle)
            return gemmi.read_structure(str(decompressed))
    return gemmi.read_structure(str(path))


def clean_structure_to_pdb(
    source_path: Path, output_path: Path, *, structure_id: str
) -> PreparedStructure:
    """Clean a PDB/mmCIF structure and write a comparator-compatible PDB.

    The cleaning policy removes hydrogens, alternative conformations, ligands,
    waters, empty chains, and non-L-peptide chains. PDB field limits are handled
    explicitly to avoid hybrid36 output that pdbtbx/RustSASA may not parse.
    """
    structure = _read_structure(source_path)
    structure.setup_entities()
    structure.remove_hydrogens()
    structure.remove_alternative_conformations()
    structure.remove_ligands_and_waters()
    structure.remove_empty_chains()
    if len(structure) == 0:
        raise PreprocessError(f"no models after cleaning: {source_path}")

    model = structure[0]
    chains_to_remove: list[str] = []
    for chain in model:
        polymer = chain.get_polymer()
        if not polymer or polymer.check_polymer_type() != gemmi.PolymerType.PeptideL:
            chains_to_remove.append(chain.name)
    for chain_name in chains_to_remove:
        model.remove_chain(chain_name)

    n_atoms = sum(1 for chain in model for residue in chain for _atom in residue)
    if n_atoms == 0:
        raise PreprocessError(f"no protein atoms after cleaning: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    structure.shorten_chain_names()
    has_long_chains = any(len(chain.name) > 1 for chain in model)
    if has_long_chains:
        _reassign_chain_ids(model)

    max_resnum = max((residue.seqid.num for chain in model for residue in chain), default=0)
    has_large_resnum = max_resnum > _MAX_RESNUM
    if has_large_resnum and not has_long_chains:
        _wrap_residue_numbers(model)

    needs_preserve = has_long_chains or has_large_resnum or n_atoms > _MAX_SERIAL
    if needs_preserve:
        _wrap_serial_numbers(model)
        options = gemmi.PdbWriteOptions()
        options.preserve_serial = True
        structure.write_pdb(str(output_path), options)
    else:
        structure.write_pdb(str(output_path))
    _fix_cryst1_z(output_path)

    counted_atoms, counted_chains = count_pdb_atoms_and_chains(output_path)
    return PreparedStructure(
        structure_id=structure_id,
        role="",
        source_kind="cleaned",
        source_dataset="",
        source_path=source_path,
        output_path=output_path,
        n_atoms=counted_atoms,
        n_chains=counted_chains,
        status="cleaned",
    )


def _resolve_source_path(
    *,
    dataset_catalog: dict[str, dict[str, Any]],
    source_dataset: str,
    source_file: str,
) -> Path:
    try:
        base = dataset_path(dataset_catalog, source_dataset, "path")
    except DatasetConfigError as exc:
        raise PreprocessError(str(exc)) from exc
    file_path = Path(source_file)
    if file_path.is_absolute():
        return file_path
    return base.joinpath(file_path)


def _with_entry_metadata(
    result: PreparedStructure,
    *,
    role: str,
    source_kind: str,
    source_dataset: str,
    notes: str,
) -> PreparedStructure:
    return PreparedStructure(
        structure_id=result.structure_id,
        role=role,
        source_kind=source_kind,
        source_dataset=source_dataset,
        source_path=result.source_path,
        output_path=result.output_path,
        n_atoms=result.n_atoms,
        n_chains=result.n_chains,
        status=result.status,
        notes=notes,
    )


def _copy_pdb(source_path: Path, output_path: Path, *, structure_id: str) -> PreparedStructure:
    if not source_path.exists():
        raise PreprocessError(f"source file not found: {source_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)
    n_atoms, n_chains = count_pdb_atoms_and_chains(output_path)
    return PreparedStructure(
        structure_id=structure_id,
        role="",
        source_kind="copied",
        source_dataset="",
        source_path=source_path,
        output_path=output_path,
        n_atoms=n_atoms,
        n_chains=n_chains,
        status="copied",
    )


def prepare_manifest_structures(
    *,
    manifest: dict[str, Any],
    dataset_catalog: dict[str, dict[str, Any]],
    output_dir: Path,
) -> list[PreparedStructure]:
    """Prepare all `[[structures]]` entries from a single-file manifest."""
    structures = manifest.get("structures")
    if not isinstance(structures, list) or not structures:
        raise PreprocessError("manifest must define non-empty [[structures]] entries")

    output_pdb_dir = output_dir.joinpath("pdb")
    rows: list[PreparedStructure] = []
    for raw_entry in structures:
        if not isinstance(raw_entry, dict):
            raise PreprocessError("each structure entry must be a table")
        structure_id = str(raw_entry.get("id") or "")
        role = str(raw_entry.get("role") or "")
        source_kind = str(raw_entry.get("source_kind") or "")
        source_dataset = str(raw_entry.get("source_dataset") or "")
        source_file = str(raw_entry.get("source_file") or "")
        notes = str(raw_entry.get("notes") or "")
        if not structure_id or not role or not source_kind or not source_dataset or not source_file:
            raise PreprocessError(
                "structure entries require id, role, source_kind, source_dataset, and source_file"
            )
        if source_kind not in {"afdb_pdb", "preprocessed_pdb", "pdb", "cif", "cif_zst"}:
            raise PreprocessError(f"unsupported source_kind: {source_kind}")

        source_path = _resolve_source_path(
            dataset_catalog=dataset_catalog,
            source_dataset=source_dataset,
            source_file=source_file,
        )
        output_path = output_pdb_dir.joinpath(f"{structure_id}.pdb")
        if source_kind in {"afdb_pdb", "preprocessed_pdb"}:
            result = _copy_pdb(source_path, output_path, structure_id=structure_id)
        else:
            result = clean_structure_to_pdb(source_path, output_path, structure_id=structure_id)
        rows.append(
            _with_entry_metadata(
                result,
                role=role,
                source_kind=source_kind,
                source_dataset=source_dataset,
                notes=notes,
            )
        )

    _write_metadata(output_dir, rows, manifest_id=str(manifest.get("id", "")))
    return rows


def _write_metadata(output_dir: Path, rows: list[PreparedStructure], *, manifest_id: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "structure_id",
        "role",
        "source_kind",
        "source_dataset",
        "source_path",
        "output_path",
        "n_atoms",
        "n_chains",
        "status",
        "notes",
    ]
    with output_dir.joinpath("metadata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "structure_id": row.structure_id,
                    "role": row.role,
                    "source_kind": row.source_kind,
                    "source_dataset": row.source_dataset,
                    "source_path": _display_path(row.source_path),
                    "output_path": _display_path(row.output_path),
                    "n_atoms": row.n_atoms,
                    "n_chains": row.n_chains,
                    "status": row.status,
                    "notes": row.notes,
                }
            )
    output_dir.joinpath("sample.json").write_text(
        json.dumps({"samples": [row.structure_id for row in rows]}, indent=2) + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath("manifest.json").write_text(
        json.dumps(
            {
                "manifest_id": manifest_id,
                "structures": [
                    {
                        "id": row.structure_id,
                        "role": row.role,
                        "source_kind": row.source_kind,
                        "source_dataset": row.source_dataset,
                        "n_atoms": row.n_atoms,
                        "n_chains": row.n_chains,
                        "status": row.status,
                    }
                    for row in rows
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _display_path(path: Path) -> str:
    """Return repository-relative paths for tracked metadata when possible."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)
