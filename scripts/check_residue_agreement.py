#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Check per-atom and per-residue agreement between zsasa and FreeSASA.

Compares the per-atom areas stored by the static validation run of
`zsasa-benchmarks` (zsasa f64, Shrake-Rupley, 128 points) with the pinned
FreeSASA command-line build on the E. coli AlphaFold Database collection.
FreeSASA text output carries two decimals, so agreement is judged after
rounding to that precision.

Usage:
    uv run scripts/check_residue_agreement.py --pdb-dir /path/to/ecoli/pdb
"""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ZSASA_OUTPUT = (
    "results/full_rerun/v0_9_0_validation/validation/ecoli/zsasa/sr_f64_standard_128.jsonl"
)


def freesasa_lines(binary: Path, path: Path, fmt: str) -> list[str]:
    result = subprocess.run(
        [binary, "--shrake-rupley", "-n", "128", f"--format={fmt}", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def freesasa_areas(binary: Path, path: Path):
    """Per-atom areas, residue key of each atom, and per-residue areas."""
    atoms, keys = [], []
    for line in freesasa_lines(binary, path, "pdb"):
        if line.startswith("ATOM"):
            atoms.append(float(line[60:66]))
            keys.append(line[21:27])
    residues = [
        float(line.split(":")[1])
        for line in freesasa_lines(binary, path, "seq")
        if line.startswith("SEQ")
    ]
    return atoms, keys, residues


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--benchmarks-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pdb-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    binary = args.benchmarks_dir / "external/bin/freesasa"

    with open(args.benchmarks_dir / ZSASA_OUTPUT) as handle:
        rows = [json.loads(line) for line in handle]
    rows = sorted((r for r in rows if r["status"] == "ok"), key=lambda r: r["filename"])
    with ThreadPoolExecutor(args.workers) as pool:
        reference = list(
            pool.map(lambda r: freesasa_areas(binary, args.pdb_dir / r["filename"]), rows)
        )

    z_atom, f_atom, z_res, f_res, skipped = [], [], [], [], 0
    for row, (atoms, keys, residues) in zip(rows, reference, strict=True):
        z = np.array(row["atom_areas"])
        k = np.array(keys)
        starts = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
        if len(z) != len(atoms) or len(starts) != len(residues):
            skipped += 1
            continue
        z_atom.append(z)
        f_atom.append(np.array(atoms))
        z_res.append(np.add.reduceat(z, starts))
        f_res.append(np.array(residues))
    print(f"structures compared: {len(rows) - skipped:,} of {len(rows):,}")
    for label, z, f in (
        ("atom", np.concatenate(z_atom), np.concatenate(f_atom)),
        ("residue", np.concatenate(z_res), np.concatenate(f_res)),
    ):
        differ = int((np.round(z, 2) != np.round(f, 2)).sum())
        print(
            f"{label}: n={len(z):,} differing at two decimals={differ:,} "
            f"max abs difference={np.abs(z - f).max():.4f} A^2"
        )


if __name__ == "__main__":
    main()
