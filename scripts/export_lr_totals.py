#!/usr/bin/env python3
"""Export per-structure Lee-Richards totals of zsasa and the FreeSASA reference.

The DuckDB import keeps only the zsasa Lee-Richards rows, and the raw outputs under
`results/full_rerun/` are not tracked or archived. This table keeps the FreeSASA
reference next to the zsasa totals so the Lee-Richards check can be recomputed.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

DEFAULT_RUN_DIR = Path("results/full_rerun/v0_12_1_validation/validation/ecoli")
DEFAULT_OUT = Path("results/tables/validation_lr_totals.csv")
PRECISIONS = ("f64", "f32")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--slices", type=int, default=20)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def freesasa_totals(directory: Path) -> dict[str, float]:
    """Read one `<structure>.txt` total per input file written by freesasa_batch."""
    return {path.stem: float(path.read_text().strip()) for path in sorted(directory.glob("*.txt"))}


def zsasa_totals(path: Path) -> dict[str, float]:
    totals: dict[str, float] = {}
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") != "ok":
                raise SystemExit(f"{path}: {row.get('filename')} has status {row.get('status')}")
            totals[Path(row["filename"]).stem] = float(row["total_area"])
    return totals


def build_rows(run_dir: Path, slices: int) -> list[dict[str, str]]:
    reference = freesasa_totals(run_dir / "freesasa_batch" / f"lr_{slices}")
    observed = {
        precision: zsasa_totals(run_dir / "zsasa" / f"lr_{precision}_{slices}.jsonl")
        for precision in PRECISIONS
    }
    if not reference:
        raise SystemExit(f"no FreeSASA Lee-Richards outputs in {run_dir}")
    for precision, totals in observed.items():
        if set(totals) != set(reference):
            raise SystemExit(
                f"zsasa {precision} and FreeSASA cover different structures "
                f"({len(totals)} against {len(reference)})"
            )
    return [
        {
            "structure_id": structure,
            "freesasa_lr": f"{reference[structure]:.2f}",
            **{f"zsasa_lr_{p}": repr(observed[p][structure]) for p in PRECISIONS},
        }
        for structure in sorted(reference)
    ]


def write_rows(rows: list[dict[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rows = build_rows(args.run_dir, args.slices)
    write_rows(rows, args.out)
    print(f"wrote {len(rows)} structures to {args.out}")


if __name__ == "__main__":
    main()
