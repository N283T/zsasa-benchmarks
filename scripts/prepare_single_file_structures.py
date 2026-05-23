#!/usr/bin/env python3
"""Prepare cleaned PDB inputs for the single-file benchmark subset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.datasets import (  # noqa: E402
    DEFAULT_DATASETS_CONFIG,
    load_dataset_catalog,
)
from scripts.benchlib.manifest import load_manifest  # noqa: E402
from scripts.benchlib.paths import resolve_repo_path  # noqa: E402
from scripts.benchlib.preprocess import (  # noqa: E402
    PreparedStructure,
    PreprocessError,
    prepare_manifest_structures,
)

DEFAULT_MANIFEST = Path("manifests/single-file-sample.toml")
DEFAULT_OUTPUT_DIR = Path("results/single/subset_inputs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="print planned inputs without preparing files (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_false",
        dest="dry_run",
        help="prepare files instead of only printing the plan",
    )
    return parser.parse_args()


def _planned_rows(
    *,
    manifest: dict[str, Any],
    dataset_catalog: dict[str, dict[str, Any]],
    output_dir: Path,
) -> list[PreparedStructure]:
    """Build dry-run rows without touching output files."""
    rows: list[PreparedStructure] = []
    structures = manifest.get("structures")
    if not isinstance(structures, list) or not structures:
        raise PreprocessError("manifest must define non-empty [[structures]] entries")
    from scripts.benchlib.preprocess import _resolve_source_path  # noqa: PLC0415

    for raw_entry in structures:
        if not isinstance(raw_entry, dict):
            raise PreprocessError("each structure entry must be a table")
        structure_id = str(raw_entry.get("id") or "")
        role = str(raw_entry.get("role") or "")
        source_kind = str(raw_entry.get("source_kind") or "")
        source_dataset = str(raw_entry.get("source_dataset") or "")
        source_file = str(raw_entry.get("source_file") or "")
        if not structure_id or not role or not source_kind or not source_dataset or not source_file:
            raise PreprocessError(
                "structure entries require id, role, source_kind, source_dataset, and source_file"
            )
        source_path = _resolve_source_path(
            dataset_catalog=dataset_catalog,
            source_dataset=source_dataset,
            source_file=source_file,
        )
        rows.append(
            PreparedStructure(
                structure_id=structure_id,
                role=role,
                source_kind=source_kind,
                source_dataset=source_dataset,
                source_path=source_path,
                output_path=output_dir.joinpath("pdb", f"{structure_id}.pdb"),
                n_atoms=int(raw_entry.get("expected_atoms") or 0),
                n_chains=int(raw_entry.get("expected_chains") or 0),
                status="planned",
                notes=str(raw_entry.get("notes") or ""),
            )
        )
    return rows


def _print_rows(rows: list[PreparedStructure]) -> None:
    for row in rows:
        print(
            "\t".join(
                [
                    row.structure_id,
                    row.role,
                    row.source_kind,
                    str(row.n_atoms),
                    str(row.n_chains),
                    str(row.source_path),
                    "->",
                    str(row.output_path),
                ]
            )
        )


def _validate_expected(manifest: dict[str, Any], rows: list[PreparedStructure]) -> None:
    entries = {
        str(entry.get("id")): entry
        for entry in manifest.get("structures", [])
        if isinstance(entry, dict)
    }
    for row in rows:
        entry = entries.get(row.structure_id, {})
        expected_atoms = entry.get("expected_atoms")
        expected_chains = entry.get("expected_chains")
        if isinstance(expected_atoms, int) and expected_atoms != row.n_atoms:
            raise PreprocessError(
                f"{row.structure_id}: expected {expected_atoms} atoms, got {row.n_atoms}"
            )
        if isinstance(expected_chains, int) and expected_chains != row.n_chains:
            raise PreprocessError(
                f"{row.structure_id}: expected {expected_chains} chains, got {row.n_chains}"
            )


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    preprocess = manifest.get("preprocess", {})
    default_output = DEFAULT_OUTPUT_DIR
    if isinstance(preprocess, dict) and isinstance(preprocess.get("output_dir_default"), str):
        default_output = Path(preprocess["output_dir_default"])
    output_dir = resolve_repo_path(args.output_dir or default_output)
    dataset_catalog = load_dataset_catalog(args.datasets)

    print(f"manifest={manifest_path}")
    print(f"datasets={resolve_repo_path(args.datasets)}")
    print(f"output_dir={output_dir}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")

    if args.dry_run:
        rows = _planned_rows(
            manifest=manifest,
            dataset_catalog=dataset_catalog,
            output_dir=output_dir,
        )
    else:
        rows = prepare_manifest_structures(
            manifest=manifest,
            dataset_catalog=dataset_catalog,
            output_dir=output_dir,
        )
        _validate_expected(manifest, rows)

    print(f"structures={len(rows)}")
    _print_rows(rows)


if __name__ == "__main__":
    try:
        main()
    except PreprocessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
