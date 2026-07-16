#!/usr/bin/env python3
"""Materialize uncompressed native mmCIF inputs for single-file benchmarks."""

from __future__ import annotations

import argparse
import gzip
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.datasets import (  # noqa: E402
    DEFAULT_DATASETS_CONFIG,
    dataset_path,
    load_dataset_catalog,
)
from scripts.benchlib.manifest import load_manifest  # noqa: E402
from scripts.benchlib.paths import resolve_repo_path  # noqa: E402
from scripts.benchlib.preprocess import clean_structure_to_cif  # noqa: E402

DEFAULT_MANIFEST = Path("manifests/single-file-mmcif-sample.toml")


class PreparationError(RuntimeError):
    """Raised when a native mmCIF input cannot be materialized."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execute", action="store_true", help="write outputs instead of planning")
    return parser.parse_args()


def structure_rows(
    manifest: dict[str, Any], catalog: dict[str, dict[str, Any]], output_dir: Path
) -> list[tuple[str, Path, Path, str, int | None, int | None]]:
    structures = manifest.get("structures")
    if not isinstance(structures, list) or not structures:
        raise PreparationError("manifest must define non-empty [[structures]] entries")
    rows: list[tuple[str, Path, Path, str, int | None, int | None]] = []
    for item in structures:
        if not isinstance(item, dict):
            raise PreparationError("each structure entry must be a table")
        source_dataset = str(item.get("source_dataset") or "")
        source_file = str(item.get("source_file") or "")
        input_file = Path(str(item.get("input_file") or ""))
        structure_id = str(item.get("id") or "")
        preprocess = str(item.get("preprocess") or "decompress")
        expected_atoms = int(item["expected_atoms"]) if "expected_atoms" in item else None
        expected_chains = int(item["expected_chains"]) if "expected_chains" in item else None
        if not structure_id or not source_dataset or not source_file or not input_file.name:
            raise PreparationError(
                "mmCIF structures require id, source_dataset, source_file, and input_file"
            )
        if input_file.is_absolute() or ".." in input_file.parts or input_file.suffix != ".cif":
            raise PreparationError(f"unsafe or non-CIF input_file: {input_file}")
        source = dataset_path(catalog, source_dataset, "path").joinpath(source_file)
        if not source.is_file():
            raise PreparationError(f"source file not found: {source}")
        if preprocess not in {"decompress", "protein_only_clean_cif"}:
            raise PreparationError(f"unsupported mmCIF preprocess policy: {preprocess}")
        rows.append(
            (
                structure_id,
                source,
                output_dir.joinpath(input_file),
                preprocess,
                expected_atoms,
                expected_chains,
            )
        )
    return rows


def materialize(
    structure_id: str,
    source: Path,
    output: Path,
    *,
    preprocess: str,
    expected_atoms: int | None,
    expected_chains: int | None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    try:
        if preprocess == "protein_only_clean_cif":
            result = clean_structure_to_cif(source, temporary, structure_id=structure_id)
            if expected_atoms is not None and result.n_atoms != expected_atoms:
                raise PreparationError(
                    f"{structure_id}: expected {expected_atoms} atoms, got {result.n_atoms}"
                )
            if expected_chains is not None and result.n_chains != expected_chains:
                raise PreparationError(
                    f"{structure_id}: expected {expected_chains} chains, got {result.n_chains}"
                )
        elif source.name.endswith(".gz"):
            with gzip.open(source, "rb") as source_handle, temporary.open("wb") as output_handle:
                shutil.copyfileobj(source_handle, output_handle)
        elif source.name.endswith(".zst"):
            zstd = shutil.which("zstd")
            if zstd is None:
                raise PreparationError("zstd is required to decompress .zst sources")
            with temporary.open("wb") as output_handle:
                subprocess.run(
                    [zstd, "-dc", "--", str(source)],
                    check=True,
                    stdout=output_handle,
                )
        else:
            shutil.copyfile(source, temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    preprocess = manifest.get("preprocess", {})
    default_output = "datasets/single-file-large-structure-mmcif"
    if isinstance(preprocess, dict) and isinstance(preprocess.get("output_dir_default"), str):
        default_output = preprocess["output_dir_default"]
    output_dir = resolve_repo_path(args.output_dir or Path(default_output))
    catalog = load_dataset_catalog(args.datasets)
    rows = structure_rows(manifest, catalog, output_dir)

    print(f"manifest={manifest_path}")
    print(f"output_dir={output_dir}")
    print(f"mode={'execute' if args.execute else 'dry-run'}")
    print(f"structures={len(rows)}")
    for structure_id, source, output, preprocess, expected_atoms, expected_chains in rows:
        print(f"{structure_id}\t{preprocess}\t{source}\t->\t{output}")
        if args.execute:
            materialize(
                structure_id,
                source,
                output,
                preprocess=preprocess,
                expected_atoms=expected_atoms,
                expected_chains=expected_chains,
            )


if __name__ == "__main__":
    try:
        main()
    except (PreparationError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
