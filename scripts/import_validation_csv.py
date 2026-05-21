#!/usr/bin/env python3
"""Import validation CSVs into the DuckDB benchmark database without running tools."""
from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

from db_common import DEFAULT_DB, apply_schema, connect, load_toml, resolve, stable_id
from init_db import seed_dataset_from_manifest, seed_tools

ROOT = Path(__file__).resolve().parents[1]
TOOL_COLUMNS = {
    "freesasa": {"tool_id": "freesasa", "precision": "f64", "mode": "standard"},
    "rustsasa": {"tool_id": "rustsasa", "precision": "f32", "mode": "standard"},
    "lahuta_bitmask": {"tool_id": "lahuta", "precision": "f64", "mode": "bitmask"},
    "zsasa_f64": {"tool_id": "zsasa", "precision": "f64", "mode": "standard"},
    "zsasa_f32": {"tool_id": "zsasa", "precision": "f32", "mode": "standard"},
    "zsasa_bitmask_f64": {"tool_id": "zsasa", "precision": "f64", "mode": "bitmask"},
    "zsasa_bitmask_f32": {"tool_id": "zsasa", "precision": "f32", "mode": "bitmask"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-kind", default="historical_baseline")
    parser.add_argument("--baseline-dir", type=Path, default=None)
    parser.add_argument(
        "--tools",
        default="all",
        help="comma-separated CSV columns to import, or all/comparators/zsasa",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def requested_tools(value: str) -> set[str]:
    if value == "all":
        return set(TOOL_COLUMNS)
    if value == "comparators":
        return {"freesasa", "rustsasa", "lahuta_bitmask"}
    if value == "zsasa":
        return {name for name in TOOL_COLUMNS if name.startswith("zsasa")}
    return {part.strip() for part in value.split(",") if part.strip()}


def run_metadata(run: dict, points: int) -> tuple[int | None, int | None]:
    if run["points_flag"] == "--n-slices":
        return None, points
    return points, None


def import_tool_column(
    conn,
    *,
    manifest: dict,
    run: dict,
    csv_path: Path,
    rows: list[dict[str, str]],
    column: str,
    source_kind: str,
    points: int,
) -> None:
    spec = TOOL_COLUMNS[column]
    n_points, n_slices = run_metadata(run, points)
    run_id = stable_id(
        source_kind,
        manifest["id"],
        run["algorithm"],
        points,
        column,
        csv_path.name,
    )
    conn.execute("DELETE FROM validation_results WHERE run_id = ?", [run_id])
    conn.execute("DELETE FROM benchmark_runs WHERE run_id = ?", [run_id])
    conn.execute(
        """
        INSERT INTO benchmark_runs
        (run_id, benchmark_kind, dataset_id, tool_id, algorithm, precision, mode,
         n_points, n_slices, threads, source_kind, source_path, manifest_id,
         created_at, status, notes)
        VALUES (?, 'validation', ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 'imported', ?)
        """,
        [
            run_id,
            manifest["dataset"]["id"],
            spec["tool_id"],
            run["algorithm"],
            spec["precision"],
            spec["mode"],
            n_points,
            n_slices,
            source_kind,
            str(csv_path),
            manifest["id"],
            datetime.now(UTC),
            f"imported column {column}",
        ],
    )
    payload = []
    for row in rows:
        value = row.get(column)
        if value in (None, ""):
            continue
        payload.append([run_id, row["structure"], int(float(row.get("n_atoms") or 0)), float(value)])
    conn.executemany(
        """
        INSERT INTO validation_results (run_id, structure_id, n_atoms, total_sasa)
        VALUES (?, ?, ?, ?)
        """,
        payload,
    )
    print(f"imported {column}: {len(payload)} rows from {csv_path}")


def main() -> None:
    args = parse_args()
    manifest = load_toml(resolve(args.manifest))
    baseline_dir = args.baseline_dir or Path(manifest["baseline"]["historical_results_dir"])
    tools = requested_tools(args.tools)

    conn = connect(resolve(args.db))
    try:
        apply_schema(conn)
        seed_tools(conn, load_toml(ROOT.joinpath("config/tool-versions.toml")))
        seed_dataset_from_manifest(conn, manifest)
        for run in manifest["runs"]:
            for points, baseline_file in zip(run["points"], run["baseline_files"], strict=True):
                csv_path = baseline_dir.joinpath(run["baseline_subdir"], baseline_file)
                rows = read_csv(csv_path)
                for column in sorted(tools & set(rows[0].keys()) & set(TOOL_COLUMNS)):
                    import_tool_column(
                        conn,
                        manifest=manifest,
                        run=run,
                        csv_path=csv_path,
                        rows=rows,
                        column=column,
                        source_kind=args.source_kind,
                        points=points,
                    )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
