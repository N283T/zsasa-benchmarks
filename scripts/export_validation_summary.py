#!/usr/bin/env python3
"""Export validation summary statistics from the benchmark DuckDB database."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from db_common import DEFAULT_DB, connect, resolve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=Path("results/exports/validation-summary.csv"))
    parser.add_argument("--reference-tool", default="freesasa")
    return parser.parse_args()


def r2_score(reference: list[float], observed: list[float]) -> float:
    mean_ref = sum(reference) / len(reference)
    ss_tot = sum((value - mean_ref) ** 2 for value in reference)
    ss_res = sum((obs - ref) ** 2 for obs, ref in zip(observed, reference, strict=True))
    return 1.0 - (ss_res / ss_tot) if ss_tot else 1.0


def summarize_pair(reference_rows: dict[str, float], observed_rows: dict[str, float]) -> dict[str, float | int]:
    shared = sorted(set(reference_rows) & set(observed_rows))
    reference = [reference_rows[key] for key in shared]
    observed = [observed_rows[key] for key in shared]
    rel_errors = [abs(obs - ref) / ref * 100 for obs, ref in zip(observed, reference, strict=True) if ref > 0]
    return {
        "n": len(shared),
        "r2": r2_score(reference, observed),
        "mean_error_percent": sum(rel_errors) / len(rel_errors) if rel_errors else 0.0,
        "max_error_percent": max(rel_errors) if rel_errors else 0.0,
    }


def load_runs(conn) -> list[dict]:
    columns = [
        "run_id",
        "dataset_id",
        "tool_id",
        "algorithm",
        "precision",
        "mode",
        "n_points",
        "n_slices",
        "source_kind",
    ]
    rows = conn.execute(
        """
        SELECT run_id, dataset_id, tool_id, algorithm, precision, mode,
               n_points, n_slices, source_kind
        FROM benchmark_runs
        WHERE benchmark_kind = 'validation'
        ORDER BY dataset_id, algorithm, COALESCE(n_points, n_slices), tool_id, precision, mode
        """
    ).fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def load_values(conn, run_id: str) -> dict[str, float]:
    return dict(
        conn.execute(
            "SELECT structure_id, total_sasa FROM validation_results WHERE run_id = ?",
            [run_id],
        ).fetchall()
    )


def main() -> None:
    args = parse_args()
    conn = connect(resolve(args.db))
    try:
        runs = load_runs(conn)
        values = {run["run_id"]: load_values(conn, run["run_id"]) for run in runs}
    finally:
        conn.close()

    refs = {
        (run["dataset_id"], run["algorithm"], run["n_points"], run["n_slices"]): run
        for run in runs
        if run["tool_id"] == args.reference_tool
    }
    out_rows = []
    for run in runs:
        key = (run["dataset_id"], run["algorithm"], run["n_points"], run["n_slices"])
        ref = refs.get(key)
        if ref is None or run["run_id"] == ref["run_id"]:
            continue
        stats = summarize_pair(values[ref["run_id"]], values[run["run_id"]])
        out_rows.append({**run, "reference_run_id": ref["run_id"], **stats})

    out_path = resolve(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "run_id",
        "dataset_id",
        "tool_id",
        "algorithm",
        "precision",
        "mode",
        "n_points",
        "n_slices",
        "source_kind",
        "reference_run_id",
        "n",
        "r2",
        "mean_error_percent",
        "max_error_percent",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"wrote {out_path} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
