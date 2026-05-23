from __future__ import annotations

import csv
import math
from pathlib import Path

from scripts.plot_validation_figures import (
    candidate_columns,
    discover_result_csvs,
    parse_result_points,
    summarize_pair,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_parse_result_points_accepts_regular_and_lahuta_names() -> None:
    assert parse_result_points(Path("results_100.csv")) == 100
    assert parse_result_points(Path("results_lahuta_128.csv")) == 128


def test_discover_result_csvs_sorts_by_points(tmp_path: Path) -> None:
    for name in ["results_500.csv", "results_lahuta_128.csv", "results_100.csv"]:
        tmp_path.joinpath(name).write_text("structure,freesasa,zsasa_f64\n", encoding="utf-8")

    assert [path.name for path in discover_result_csvs(tmp_path)] == [
        "results_100.csv",
        "results_lahuta_128.csv",
        "results_500.csv",
    ]


def test_candidate_columns_excludes_ids_and_reference() -> None:
    rows = [
        {
            "structure": "a",
            "n_atoms": "10",
            "freesasa": "100.0",
            "zsasa_f64": "101.0",
            "rustsasa": "99.0",
        }
    ]

    assert candidate_columns(rows, reference="freesasa") == ["zsasa_f64", "rustsasa"]


def test_summarize_pair_ignores_blank_values_and_reports_errors() -> None:
    rows = [
        {"freesasa": "100", "zsasa_f64": "101"},
        {"freesasa": "200", "zsasa_f64": ""},
        {"freesasa": "300", "zsasa_f64": "303"},
    ]

    summary = summarize_pair(rows, reference="freesasa", candidate="zsasa_f64")

    assert summary.n == 2
    assert summary.r2 == 0.9995
    assert summary.mean_error_percent == 1.0
    assert summary.max_error_percent == 1.0
    assert summary.mean_abs_delta == 2.0


def test_summarize_pair_handles_zero_reference_errors() -> None:
    summary = summarize_pair(
        [{"freesasa": "0", "zsasa_f64": "1"}], reference="freesasa", candidate="zsasa_f64"
    )

    assert summary.n == 1
    assert summary.r2 == 1.0
    assert math.isinf(summary.mean_error_percent)
    assert math.isinf(summary.max_error_percent)


def test_run_column_name_maps_database_runs() -> None:
    from scripts.plot_validation_figures import run_column_name

    assert (
        run_column_name(
            {
                "benchmark_kind": "validation",
                "tool_id": "zsasa",
                "precision": "f64",
                "mode": "bitmask",
            }
        )
        == "zsasa_bitmask_f64"
    )
    assert (
        run_column_name(
            {
                "benchmark_kind": "trajectory_validation",
                "tool_id": "zig",
                "precision": "f32",
                "mode": "standard",
            }
        )
        == "zsasa_cli_f32"
    )
    assert (
        run_column_name(
            {
                "benchmark_kind": "trajectory_validation",
                "tool_id": "zig_bitmask",
                "precision": "f64",
                "mode": "bitmask",
            }
        )
        == "zsasa_cli_bitmask_f64"
    )
    assert (
        run_column_name(
            {
                "benchmark_kind": "trajectory_validation",
                "tool_id": "zsasa_mdtraj",
                "precision": "f64",
                "mode": "standard",
            }
        )
        == "zsasa_mdtraj"
    )


def test_load_validation_tables_from_db_pivots_runs(tmp_path: Path) -> None:
    import duckdb
    from scripts.plot_validation_figures import load_validation_tables_from_db

    db_path = tmp_path.joinpath("validation.duckdb")
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE benchmark_runs (
          run_id VARCHAR,
          benchmark_kind VARCHAR,
          dataset_id VARCHAR,
          tool_id VARCHAR,
          algorithm VARCHAR,
          precision VARCHAR,
          mode VARCHAR,
          n_points INTEGER,
          n_slices INTEGER,
          threads INTEGER,
          source_kind VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE validation_results (
          run_id VARCHAR,
          structure_id VARCHAR,
          n_atoms INTEGER,
          total_sasa DOUBLE
        )
        """
    )
    con.executemany(
        "INSERT INTO benchmark_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "ref",
                "validation",
                "ecoli",
                "freesasa_batch",
                "sr",
                "f64",
                "standard",
                100,
                None,
                None,
                "full_rerun",
            ),
            (
                "obs",
                "validation",
                "ecoli",
                "zsasa",
                "sr",
                "f64",
                "standard",
                100,
                None,
                None,
                "full_rerun",
            ),
            (
                "lr",
                "validation",
                "ecoli",
                "zsasa",
                "lr",
                "f64",
                "standard",
                None,
                20,
                None,
                "full_rerun",
            ),
        ],
    )
    con.executemany(
        "INSERT INTO validation_results VALUES (?, ?, ?, ?)",
        [
            ("ref", "a.pdb", 10, 100.0),
            ("ref", "b.pdb", 20, 200.0),
            ("obs", "a.pdb", None, 101.0),
            ("obs", "b.pdb", None, 202.0),
            ("lr", "a.pdb", None, 99.0),
        ],
    )
    con.close()

    tables = load_validation_tables_from_db(
        db_path,
        benchmark_kind="validation",
        reference_tool_id="freesasa_batch",
        reference_column="freesasa",
    )

    assert len(tables) == 1
    assert tables[0].points == 100
    assert candidate_columns(tables[0].rows, reference="freesasa") == ["zsasa_f64"]
    assert tables[0].rows == [
        {"structure": "a.pdb", "n_atoms": "10", "freesasa": "100.0", "zsasa_f64": "101.0"},
        {"structure": "b.pdb", "n_atoms": "20", "freesasa": "200.0", "zsasa_f64": "202.0"},
    ]
