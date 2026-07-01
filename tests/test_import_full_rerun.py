from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from scripts.import_full_rerun import (
    import_full_rerun,
    manifest_id_from_config,
    parse_batch_record_name,
    parse_validation_zsasa_name,
    parse_zsasa_jsonl_total,
    reset_database,
    single_structure_metadata,
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


def test_parse_zsasa_jsonl_total_accepts_status_ok_rows() -> None:
    assert parse_zsasa_jsonl_total(
        '{"status":"ok","filename":"AF-A.pdb","total_area":123.4,"atom_areas":[1,2,3]}'
    ) == ("AF-A.pdb", 123.4, 3)


def test_parse_zsasa_jsonl_total_rejects_status_err_rows() -> None:
    with pytest.raises(ValueError, match="zsasa JSONL error row"):
        parse_zsasa_jsonl_total(
            '{"status":"err","filename":"AF-B.pdb","error":"parse failed"}'
        )


def test_parse_batch_record_name() -> None:
    assert parse_batch_record_name("zsasa_batch_f64_standard_10t_128p") == {
        "tool_id": "zsasa",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "standard",
        "threads": 10,
        "n_points": 128,
    }
    assert parse_batch_record_name("zsasa_0_7_0_batch_f64_standard_10t_128p") == {
        "tool_id": "zsasa_0_7_0",
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


def test_parse_single_tool_label_accepts_versioned_zsasa() -> None:
    from scripts.import_full_rerun import parse_single_tool_label

    assert parse_single_tool_label("zsasa_0_7_0_f64") == {
        "tool_id": "zsasa_0_7_0",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "standard",
    }
    assert parse_single_tool_label("zsasa_0_7_0_f64_bitmask") == {
        "tool_id": "zsasa_0_7_0",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "bitmask",
    }


def test_parse_single_tool_label_accepts_pdbtools_jl() -> None:
    from scripts.import_full_rerun import parse_single_tool_label

    assert parse_single_tool_label("pdbtools_jl") == {
        "tool_id": "pdbtools_jl",
        "algorithm": "sr",
        "precision": "f64",
        "mode": "standard",
    }


def test_single_structure_metadata_can_read_mmcif_manifest() -> None:
    metadata = single_structure_metadata(Path("manifests/single-file-mmcif-sample.toml"))

    assert metadata["5vyc"]["role"] == "rustsasa-parser-outlier"
    assert metadata["5vyc"]["n_atoms"] > 0


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


def test_import_full_rerun_imports_swissprot_version_refresh_batch(tmp_path: Path) -> None:
    results_root = tmp_path.joinpath("full_rerun", "version_refresh")
    hyperfine_dir = results_root.joinpath("batch", "swissprot", "hyperfine")
    hyperfine_dir.mkdir(parents=True)
    hyperfine_dir.joinpath("zsasa_0_7_0_batch_f32_bitmask_40t_128p.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "command": "zsasa_0_7_0_batch_f32_bitmask_40t_128p",
                        "mean": 495.0,
                        "stddev": 0.0,
                        "median": 495.0,
                        "min": 495.0,
                        "max": 495.0,
                        "times": [495.0],
                        "user": 1728.0,
                        "system": 128.0,
                        "memory_usage_byte": [466 * 1024 * 1024],
                        "exit_codes": [0],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    db = tmp_path.joinpath("benchmark.duckdb")
    import_full_rerun(
        db,
        results_root,
        "version_refresh",
        Path("config/datasets.toml.example"),
    )

    conn = duckdb.connect(str(db), read_only=True)
    try:
        run = conn.execute(
            """
            SELECT benchmark_kind, dataset_id, tool_id, precision, mode, threads, n_points,
                   manifest_id, notes
            FROM benchmark_runs
            WHERE dataset_id = 'swissprot_500k_pdb'
            """
        ).fetchone()
        metrics = {
            (metric, statistic): value
            for metric, statistic, value in conn.execute(
                """
                SELECT metric, statistic, value
                FROM performance_results
                WHERE run_id = (
                  SELECT run_id FROM benchmark_runs WHERE dataset_id = 'swissprot_500k_pdb'
                )
                """
            ).fetchall()
        }
    finally:
        conn.close()

    assert run == (
        "batch",
        "swissprot_500k_pdb",
        "zsasa_0_7_0",
        "f32",
        "bitmask",
        40,
        128,
        "batch-swissprot-version-refresh",
        "zsasa_0_7_0_batch_f32_bitmask_40t_128p",
    )
    assert metrics[("runtime", "mean")] == 495.0
    assert metrics[("peak_rss", "mean")] == 466 * 1024 * 1024


def test_manifest_id_from_config_reads_batch_overcommit_manifest(tmp_path: Path) -> None:
    base = tmp_path.joinpath("full_rerun", "run", "batch", "human")
    base.mkdir(parents=True)
    base.joinpath("config.json").write_text(
        json.dumps({"manifest": "manifests/batch-human-overcommit.toml"}),
        encoding="utf-8",
    )

    assert (
        manifest_id_from_config(base, "batch-human-full-rerun")
        == "batch-human-zsasa-0-7-overcommit"
    )


def test_import_full_rerun_imports_human_cif_overcommit_batch(tmp_path: Path) -> None:
    results_root = tmp_path.joinpath("full_rerun", "cif_overcommit")
    human_cif = results_root.joinpath("batch", "human_cif")
    hyperfine_dir = human_cif.joinpath("hyperfine")
    hyperfine_dir.mkdir(parents=True)
    human_cif.joinpath("config.json").write_text(
        json.dumps({"manifest": "manifests/batch-human-cif-overcommit.toml"}),
        encoding="utf-8",
    )
    hyperfine_dir.joinpath("zsasa_0_7_0_batch_f32_bitmask_40t_128p.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "command": "zsasa_0_7_0_batch_f32_bitmask_40t_128p",
                        "mean": 23.0,
                        "stddev": 0.0,
                        "median": 23.0,
                        "min": 23.0,
                        "max": 23.0,
                        "times": [23.0],
                        "user": 190.0,
                        "system": 10.0,
                        "memory_usage_byte": [520 * 1024 * 1024],
                        "exit_codes": [0],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    db = tmp_path.joinpath("benchmark.duckdb")
    import_full_rerun(
        db,
        results_root,
        "cif_overcommit",
        Path("config/datasets.toml.example"),
    )

    conn = duckdb.connect(str(db), read_only=True)
    try:
        run = conn.execute(
            """
            SELECT benchmark_kind, dataset_id, tool_id, precision, mode, threads, n_points,
                   manifest_id, notes
            FROM benchmark_runs
            WHERE dataset_id = 'UP000005640_9606_HUMAN_v6_cif'
            """
        ).fetchone()
        runtime = conn.execute(
            """
            SELECT value
            FROM performance_results
            WHERE run_id = (
              SELECT run_id
              FROM benchmark_runs
              WHERE dataset_id = 'UP000005640_9606_HUMAN_v6_cif'
            )
              AND metric = 'runtime'
              AND statistic = 'mean'
            """
        ).fetchone()[0]
    finally:
        conn.close()

    assert run == (
        "batch",
        "UP000005640_9606_HUMAN_v6_cif",
        "zsasa_0_7_0",
        "f32",
        "bitmask",
        40,
        128,
        "batch-human-cif-zsasa-0-7-overcommit",
        "zsasa_0_7_0_batch_f32_bitmask_40t_128p",
    )
    assert runtime == 23.0


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
