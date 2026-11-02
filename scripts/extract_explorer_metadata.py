"""Extract per-model metadata for the SASA explorer tables.

AFDB dimer models (mmCIF): UniProt accession, entry name, gene, description and
residue count of each chain, and the global pLDDT and ipTM of the model.
SwissProt monomer models (PDB): accession, molecule name, organism, residue
count and mean pLDDT.

    uv run python scripts/extract_explorer_metadata.py dimers \
        --input-dir ~/pdb/afdb/nvda/homodimers/9606_HUMAN/structure \
        --out workflows/sasa-explorer/metadata/homodimers.parquet
    uv run python scripts/extract_explorer_metadata.py swissprot \
        --input-dir ~/pdb/afdb/swissprot_pdb_v6 \
        --out workflows/sasa-explorer/metadata/swissprot.parquet
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterator
from multiprocessing import Pool
from pathlib import Path

import duckdb
import gemmi

MODEL_ID = re.compile(r"^(AF-[0-9A-Za-z]+(?:-F\d+)?)")


def read_text(path: Path) -> str:
    """Read a structure file, decompressing .zst and .gz."""
    data = path.read_bytes()
    if path.suffix == ".zst":
        import zstandard

        data = zstandard.ZstdDecompressor().decompressobj().decompress(data)
    elif path.suffix == ".gz":
        data = gzip.decompress(data)
    return data.decode()


def model_id(filename: str) -> str:
    match = MODEL_ID.match(filename)
    if match is None:
        raise ValueError(f"no AFDB model identifier in {filename}")
    return match.group(1)


def loop_rows(block: gemmi.cif.Block, category: str, tags: list[str]) -> list[list[str]]:
    table = block.find(category, tags)
    return [[gemmi.cif.as_string(row[i]) for i in range(len(tags))] for row in table]


def chain_entities(block: gemmi.cif.Block) -> dict[str, tuple[str, str]]:
    """Entity of each chain, by the sequence of its atoms.

    The header of many restored heterodimer files declares the two entities in
    the other order than the atoms: the atoms of chain A carry the sequence of
    entity 2 although `_atom_site.label_entity_id` says 1. The chain is matched
    to the entity whose `_entity_poly` sequence equals the sequence of its
    atoms, and falls back to the atom-site entity when none does. Returns
    {chain: (entity, "sequence" | "atom_site")}.
    """
    polys = {
        entity: gemmi.cif.as_string(seq).replace("\n", "").replace(" ", "")
        for entity, seq in zip(
            block.find_values("_entity_poly.entity_id"),
            block.find_values("_entity_poly.pdbx_seq_one_letter_code"),
            strict=True,
        )
    }
    structure = gemmi.make_structure_from_block(block)
    chains = {}
    for chain in structure[0]:
        sequence = gemmi.one_letter_code([residue.name for residue in chain])
        labelled = chain[0].entity_id
        matches = [entity for entity, poly in polys.items() if poly == sequence]
        if labelled in matches or not matches:
            chains[chain.name] = (labelled, "atom_site" if not matches else "sequence")
        else:
            chains[chain.name] = (matches[0], "sequence")
    return chains


def dimer_metadata(path: Path) -> dict:
    """Metadata of one dimer model, with the chains in label order (A, B)."""
    block = gemmi.cif.read_string(read_text(path)).sole_block()
    entity_description = dict(loop_rows(block, "_entity.", ["id", "pdbx_description"]))
    targets = {
        entity: (accession, code, gene)
        for entity, accession, code, gene in loop_rows(
            block,
            "_ma_target_ref_db_details.",
            ["target_entity_id", "db_accession", "db_code", "gene_name"],
        )
    }
    polys = dict(loop_rows(block, "_entity_poly.", ["entity_id", "pdbx_seq_one_letter_code"]))
    chains = chain_entities(block)
    if set(chains) != {"A", "B"}:
        raise ValueError(f"{path.name}: expected chains A and B, found {sorted(chains)}")
    metric_name = {
        metric_id: (name, mode)
        for metric_id, name, mode in loop_rows(block, "_ma_qa_metric.", ["id", "name", "mode"])
    }
    global_metrics = {}
    for metric_id, value in loop_rows(
        block, "_ma_qa_metric_global.", ["metric_id", "metric_value"]
    ):
        name, mode = metric_name.get(metric_id, ("", ""))
        if mode == "global":
            global_metrics[name] = float(value)
    row = {"model_id": model_id(path.name), "filename": path.name}
    for label in ("A", "B"):
        entity, source = chains[label]
        accession, code, gene = targets.get(entity, ("", "", ""))
        suffix = label.lower()
        row[f"accession_{suffix}"] = accession
        row[f"entry_name_{suffix}"] = code
        row[f"gene_{suffix}"] = gene
        row[f"description_{suffix}"] = entity_description.get(entity, "")
        row[f"n_residues_{suffix}"] = len(polys.get(entity, "").replace("\n", ""))
        row[f"entity_{suffix}"] = entity
        row[f"entity_source_{suffix}"] = source
    row["plddt_global"] = global_metrics.get("pLDDT")
    row["iptm_model"] = global_metrics.get("ipTM")
    return row


def swissprot_metadata(path: Path) -> dict:
    """Metadata of one SwissProt monomer model in PDB format."""
    molecule: list[str] = []
    organism = ""
    taxid = None
    plddt_sum = 0.0
    n_residues = 0
    for line in read_text(path).splitlines():
        record = line[:6]
        if record == "COMPND":
            text = line[10:].strip()
            if text.startswith("MOLECULE:"):
                molecule.append(text.removeprefix("MOLECULE:").strip().rstrip(";"))
        elif record == "SOURCE":
            text = line[10:].strip()
            if text.startswith("ORGANISM_SCIENTIFIC:"):
                organism = text.removeprefix("ORGANISM_SCIENTIFIC:").strip().rstrip(";")
            elif text.startswith("ORGANISM_TAXID:"):
                taxid = int(text.removeprefix("ORGANISM_TAXID:").strip().rstrip(";"))
        elif record == "ATOM  " and line[12:16] == " CA ":
            plddt_sum += float(line[60:66])
            n_residues += 1
    match = re.match(r"^AF-([0-9A-Za-z]+)-F(\d+)", path.name)
    if match is None:
        raise ValueError(f"no AFDB model identifier in {path.name}")
    return {
        "model_id": model_id(path.name),
        "filename": path.name,
        "accession": match.group(1),
        "fragment": int(match.group(2)),
        "description": " ".join(molecule),
        "organism": organism,
        "taxonomy_id": taxid,
        "n_residues": n_residues,
        "plddt_mean": plddt_sum / n_residues if n_residues else None,
    }


def extract(task: tuple[str, str]) -> dict:
    kind, path = task
    try:
        reader = dimer_metadata if kind == "dimers" else swissprot_metadata
        return {"ok": True, "row": reader(Path(path))}
    except Exception as exc:  # reported per file, the run goes on
        return {"ok": False, "filename": Path(path).name, "error": f"{type(exc).__name__}: {exc}"}


def structure_files(input_dir: Path) -> Iterator[Path]:
    for entry in sorted(os.scandir(input_dir), key=lambda e: e.name):
        if entry.name.startswith("AF-") and (entry.is_file() or entry.is_symlink()):
            yield Path(entry.path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=["dimers", "swissprot"])
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Parquet file to write")
    parser.add_argument("--processes", type=int, default=6)
    args = parser.parse_args(argv)

    tasks = [(args.kind, str(path)) for path in structure_files(args.input_dir.expanduser())]
    failures = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        rows_path = Path(tmp) / "rows.jsonl"
        with rows_path.open("w") as rows, Pool(args.processes) as pool:
            for done, result in enumerate(pool.imap(extract, tasks, chunksize=64), 1):
                if result["ok"]:
                    rows.write(json.dumps(result["row"]) + "\n")
                else:
                    failures.append(result)
                if done % 50000 == 0:
                    print(f"{done:,}/{len(tasks):,}", file=sys.stderr)
        duckdb.sql(
            f"COPY (SELECT * FROM read_json_auto('{rows_path}') ORDER BY model_id) "
            f"TO '{args.out}' (FORMAT parquet, COMPRESSION zstd)"
        )
    print(f"{len(tasks) - len(failures):,} models, {len(failures):,} failed -> {args.out}")
    for failure in failures[:20]:
        print(f"  {failure['filename']}: {failure['error']}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
