from __future__ import annotations

import json
from pathlib import Path

import duckdb
from scripts.import_full_rerun import (
    parse_batch_record_name,
    parse_validation_zsasa_name,
    parse_zsasa_jsonl_total,
    reset_database,
)


def test_parse_validation_zsasa_name() -> None:
    assert parse_validation_zsasa_name("sr_f64_bitmask_1000.jsonl") == {
        "algorithm": "sr",
        "precision": "f64",
        "mode": "bitmask",
        "n_points": 1000,
        "n_slices": None,
    }
    assert parse_validation_zsasa_name("lr_f32_20.jsonl") == {
        "algorithm": "lr",
        "precision": "f32",
        "mode": "standard",
        "n_points": None,
        "n_slices": 20,
    }


def test_parse_zsasa_jsonl_total_avoids_atom_area_parsing() -> None:
    assert parse_zsasa_jsonl_total(
        '{"filename":"AF-A.pdb","total_area":123.4,"atom_areas":[1,2,3]}'
    ) == ("AF-A.pdb", 123.4, None)


def test_parse_batch_record_name() -> None:
    assert parse_batch_record_name("zsasa_batch_f64_standard_10t_128p") == {
        "tool_id": "zsasa",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "standard",
        "threads": 10,
        "n_points": 128,
    }
    assert parse_batch_record_name("lahuta_bitmask_4t_128p") == {
        "tool_id": "lahuta",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "bitmask",
        "threads": 4,
        "n_points": 128,
    }
    assert parse_batch_record_name("freesasa_batch_1t_128p")["tool_id"] == "freesasa_batch"


def test_reset_database_removes_existing_rows(tmp_path: Path) -> None:
    db = tmp_path.joinpath("benchmark.duckdb")
    conn = duckdb.connect(str(db))
    conn.execute("CREATE TABLE stale(value INTEGER)")
    conn.close()

    reset_database(db)

    conn = duckdb.connect(str(db), read_only=True)
    try:
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        assert "stale" not in tables
        assert {"benchmark_runs", "validation_results", "performance_results"} <= tables
    finally:
        conn.close()


def test_smoke_import_full_rerun_fixture(tmp_path: Path) -> None:
    from scripts.import_full_rerun import import_validation_static

    root = tmp_path.joinpath("full_rerun", "run")
    validation = root.joinpath("validation", "ecoli")
    validation.joinpath("zsasa").mkdir(parents=True)
    validation.joinpath("freesasa_batch", "sr_100").mkdir(parents=True)
    validation.joinpath("rustsasa", "sr_100").mkdir(parents=True)
    validation.joinpath("lahuta").mkdir(parents=True)
    validation.joinpath("config.json").write_text(
        json.dumps({"manifest": "manifests/validation-ecoli.toml"}),
        encoding="utf-8",
    )
    validation.joinpath("zsasa", "sr_f64_standard_100.jsonl").write_text(
        '{"filename":"a.pdb","total_area":1.5,"atom_areas":[1.0,0.5]}\n',
        encoding="utf-8",
    )
    validation.joinpath("freesasa_batch", "sr_100", "a.txt").write_text("1.5\n", encoding="utf-8")
    validation.joinpath("rustsasa", "sr_100", "a.json").write_text(
        '{"Protein":{"global_total":1.4}}\n', encoding="utf-8"
    )
    validation.joinpath("lahuta", "sr_standard_100.jsonl").write_text(
        '{"model":"/tmp/a.pdb","sasa":[1.0,0.5]}\n', encoding="utf-8"
    )

    db = tmp_path.joinpath("benchmark.duckdb")
    reset_database(db)
    conn = duckdb.connect(str(db))
    try:
        conn.execute(
            """
            INSERT INTO datasets
            (dataset_id, name, role, expected_count)
            VALUES ('UP000000625_83333_ECOLI_v6_pdb', 'ecoli', 'validation', 1)
            """
        )
        for tool_id in ["zsasa", "freesasa_batch", "rustsasa", "lahuta"]:
            conn.execute(
                "INSERT INTO tools (tool_id, name) VALUES (?, ?)",
                [tool_id, tool_id],
            )
        import_validation_static(conn, validation, "run")
        assert conn.execute("SELECT count(*) FROM benchmark_runs").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM validation_results").fetchone()[0] == 4
    finally:
        conn.close()


def test_import_hyperfine_directory_imports_memory_and_cpu_metrics(tmp_path: Path) -> None:
    from scripts.import_full_rerun import import_hyperfine_directory

    db = tmp_path.joinpath("benchmark.duckdb")
    reset_database(db)
    root = tmp_path.joinpath("batch", "ecoli")
    root.joinpath("hyperfine").mkdir(parents=True)
    root.joinpath("hyperfine", "zsasa_batch_f64_standard_1t_128p.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "command": "zsasa_batch_f64_standard_1t_128p",
                        "mean": 10.0,
                        "stddev": 1.0,
                        "median": 9.5,
                        "min": 9.0,
                        "max": 11.0,
                        "times": [9.0, 10.0, 11.0],
                        "user": 20.0,
                        "system": 3.0,
                        "memory_usage_byte": [100, 200, 300],
                        "exit_codes": [0, 0, 0],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    conn = duckdb.connect(str(db))
    try:
        conn.execute(
            """
            INSERT INTO datasets (dataset_id, name, role, expected_count)
            VALUES ('UP000000625_83333_ECOLI_v6_pdb', 'ecoli', 'batch', 1)
            """
        )
        conn.execute("INSERT INTO tools (tool_id, name) VALUES ('zsasa', 'zsasa')")
        import_hyperfine_directory(
            conn,
            base=root,
            run_label="run",
            benchmark_kind="batch",
            dataset_id="UP000000625_83333_ECOLI_v6_pdb",
            manifest_id="batch-ecoli-full-rerun",
            name_parser=parse_batch_record_name,
        )
        metrics = {
            (metric, statistic): (value, unit, n)
            for metric, statistic, value, unit, n in conn.execute(
                """
                SELECT metric, statistic, value, unit, n
                FROM performance_results
                ORDER BY metric, statistic
                """
            ).fetchall()
        }
    finally:
        conn.close()

    assert metrics[("runtime", "run_2")] == (10.0, "s", 3)
    assert metrics[("peak_rss", "mean")] == (200.0, "bytes", 3)
    assert metrics[("peak_rss", "run_3")] == (300.0, "bytes", 3)
    assert metrics[("user_time", "mean")] == (20.0, "s", 3)
    assert metrics[("system_time", "mean")] == (3.0, "s", 3)
