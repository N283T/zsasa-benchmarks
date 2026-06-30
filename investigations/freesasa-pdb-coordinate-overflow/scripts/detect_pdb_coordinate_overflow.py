#!/usr/bin/env python3
"""Detect PDB coordinate fields that exceed the fixed-width 8.3 range.

This script is intentionally small and dependency-free so it can be used when
preparing an upstream FreeSASA issue. It reads PDB ATOM/HETATM coordinate fields
using fixed columns and reports structures whose coordinates cannot be safely
represented in PDB 8.3 fields.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdbCoordinateSummary:
    path: Path
    n_atoms: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    @property
    def overflows_pdb_8_3(self) -> bool:
        # PDB coordinate fields are 8 columns wide with 3 decimals. Values with
        # absolute magnitude >= 1000 commonly become adjacent to neighboring
        # fields in writer output and are not safely parseable as separated
        # floating-point tokens.
        return any(
            abs(value) >= 1000.0
            for value in (self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max)
        )


def summarize_pdb(path: Path) -> PdbCoordinateSummary:
    n_atoms = 0
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]

    with path.open(errors="replace") as handle:
        for line in handle:
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            try:
                coords = [float(line[30:38]), float(line[38:46]), float(line[46:54])]
            except ValueError as exc:
                msg = f"failed to parse fixed-width coordinates in {path}: {line.rstrip()}"
                raise ValueError(msg) from exc
            n_atoms += 1
            for idx, value in enumerate(coords):
                mins[idx] = min(mins[idx], value)
                maxs[idx] = max(maxs[idx], value)

    if n_atoms == 0:
        return PdbCoordinateSummary(path, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    return PdbCoordinateSummary(
        path=path,
        n_atoms=n_atoms,
        x_min=mins[0],
        x_max=maxs[0],
        y_min=mins[1],
        y_max=maxs[1],
        z_min=mins[2],
        z_max=maxs[2],
    )


def iter_pdb_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.pdb")))
        else:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="PDB files or directories to inspect")
    args = parser.parse_args()

    fieldnames = [
        "path",
        "n_atoms",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "z_min",
        "z_max",
        "overflows_pdb_8_3",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for pdb_path in iter_pdb_files(args.paths):
        summary = summarize_pdb(pdb_path)
        writer.writerow(
            {
                "path": str(summary.path),
                "n_atoms": summary.n_atoms,
                "x_min": f"{summary.x_min:.3f}",
                "x_max": f"{summary.x_max:.3f}",
                "y_min": f"{summary.y_min:.3f}",
                "y_max": f"{summary.y_max:.3f}",
                "z_min": f"{summary.z_min:.3f}",
                "z_max": f"{summary.z_max:.3f}",
                "overflows_pdb_8_3": str(summary.overflows_pdb_8_3).lower(),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
