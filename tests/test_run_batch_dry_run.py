from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def test_run_batch_dry_run_outputs_native_hyperfine_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli.toml",
            "--run-id",
            "test_run",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "hyperfine" in proc.stdout
    assert "freesasa_batch" in proc.stdout
    assert "results/full_rerun/test_run/batch" in proc.stdout
    assert "scripts/bench_batch.py" not in proc.stdout
    assert "benchmarks/scripts/" not in proc.stdout
    assert "--n-points=128" in proc.stdout
    assert "--threads=1" in proc.stdout
    assert "--threads=10" in proc.stdout
    assert "--precision=f64" in proc.stdout
    assert "--precision=f32" in proc.stdout
    assert "--classifier=protor" in proc.stdout
    assert "--use-bitmask" in proc.stdout
    assert "lahuta" in proc.stdout
    assert "rustsasa" in proc.stdout
    assert " -f json " in proc.stdout
    assert " -f pdb " not in proc.stdout


def test_run_batch_dry_run_accepts_jsonl_decimal_rounding(tmp_path: Path) -> None:
    manifest = tmp_path.joinpath("batch-rounding.toml")
    manifest.write_text(
        """
id = "batch-rounding"
status = "planning"

[dataset]
id = "UP000000625_83333_ECOLI_v6_pdb"
expected_count = 4370
role = ["batch-throughput"]

[full_rerun]
source_kind = "full_rerun"
n_points = 128
threads = [10]
runs = 1
warmup = 0
precisions = ["f32"]
modes = ["standard"]
prepare = "sync"
rerun_comparators = false
jsonl_decimals = 3
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            str(manifest),
            "--run-id",
            "test_rounding",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--jsonl-decimals=3" in proc.stdout


def test_run_batch_dry_run_accepts_zsasa_0_9_profile_options(tmp_path: Path) -> None:
    manifest = tmp_path.joinpath("batch-zsasa-0.9.toml")
    manifest.write_text(
        """
id = "batch-zsasa-0-9"
status = "planning"

[dataset]
id = "UP000000625_83333_ECOLI_v6_cif"
expected_count = 4370
role = ["batch-throughput"]

[full_rerun]
source_kind = "full_rerun"
n_points = 128
threads = [10]
runs = 1
warmup = 0
precisions = ["f32"]
modes = ["bitmask"]
prepare = "sync"
rerun_comparators = false
af_model_fast = true
input_io = "read"
profile_stages = true

[[full_rerun.jobs]]
tool = "zsasa_0_9_0"
threads = [10]
precisions = ["f32"]
modes = ["bitmask"]
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            str(manifest),
            "--run-id",
            "test_zsasa_0_9_options",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "zsasa-0.9.0" in proc.stdout
    assert "--af-model-fast" in proc.stdout
    assert "--input-io=read" in proc.stdout
    assert "--timing" in proc.stdout
    assert "--profile-stages" in proc.stdout


def test_run_batch_dry_run_prepares_output_directories() -> None:
    run_id = "test_run_dirs_task9_fix"
    output_base = Path("results/full_rerun") / run_id / "batch" / "ecoli"
    if output_base.exists():
        shutil.rmtree(output_base)

    subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli.toml",
            "--run-id",
            run_id,
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_base.joinpath("commands.log").is_file()
    assert output_base.joinpath("config.json").is_file()
    for dirname in ["hyperfine", "zsasa", "freesasa_batch", "lahuta", "rustsasa"]:
        assert output_base.joinpath(dirname).is_dir()
    for dirname in [
        "freesasa_batch/1t_128p",
        "rustsasa/10t_128p",
        "lahuta/standard_1t_128p",
        "lahuta/bitmask_10t_128p",
    ]:
        assert output_base.joinpath(dirname).is_dir()


def test_run_batch_dry_run_filters_record_names() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli.toml",
            "--run-id",
            "test_run_filtered",
            "--datasets",
            "config/datasets.toml.example",
            "--only",
            "rustsasa_10t_*",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# name: rustsasa_10t_128p" in proc.stdout
    assert "# name: rustsasa_1t_128p" not in proc.stdout
    assert "# name: zsasa_batch_f64_standard_10t_128p" not in proc.stdout


def test_run_batch_swissprot_version_refresh_targets_0_9_thread_overcommit() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-swissprot-version-refresh.toml",
            "--run-id",
            "test_swissprot_versions",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=swissprot" in proc.stdout
    assert "selected_commands=9/9" in proc.stdout
    assert "# name: zsasa_0_6_0_batch_f32_standard_10t_128p" in proc.stdout
    assert "# name: zsasa_0_6_0_batch_f32_bitmask_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_standard_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_standard_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_standard_40t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_40t_128p" in proc.stdout
    assert "# name: lahuta_bitmask_10t_128p" in proc.stdout
    assert "lahuta_standard" not in proc.stdout
    assert "zsasa_0_6_0_batch_f32_standard_20t_128p" not in proc.stdout
    assert "zsasa_0_6_0_batch_f32_bitmask_40t_128p" not in proc.stdout
    assert "freesasa_batch" not in proc.stdout
    assert "rustsasa" not in proc.stdout
    assert "--warmup 0" in proc.stdout
    assert "--runs 1" in proc.stdout
    assert "--use-bitmask" in proc.stdout


def test_run_batch_ecoli_overcommit_targets_zsasa_0_9_matrix() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli-zsasa-0.9.toml",
            "--run-id",
            "test_ecoli_overcommit",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=ecoli" in proc.stdout
    assert "selected_commands=16/16" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f64_standard_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f64_bitmask_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_standard_40t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_80t_128p" in proc.stdout
    assert "freesasa_batch" not in proc.stdout
    assert "rustsasa" not in proc.stdout
    assert "lahuta" not in proc.stdout
    assert "--warmup 3" in proc.stdout
    assert "--runs 3" in proc.stdout


def test_run_batch_human_overcommit_targets_zsasa_0_9_matrix() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-human-zsasa-0.9.toml",
            "--run-id",
            "test_human_overcommit",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=human" in proc.stdout
    assert "selected_commands=16/16" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f64_standard_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f64_bitmask_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_standard_40t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_80t_128p" in proc.stdout
    assert "freesasa_batch" not in proc.stdout
    assert "rustsasa" not in proc.stdout
    assert "lahuta" not in proc.stdout
    assert "--warmup 3" in proc.stdout
    assert "--runs 3" in proc.stdout


def test_run_batch_human_cif_overcommit_targets_minimal_bitmask_matrix() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-human-cif-zsasa-0.9.toml",
            "--run-id",
            "test_human_cif_overcommit",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=human_cif" in proc.stdout
    assert "selected_commands=5/5" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_40t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_80t_128p" in proc.stdout
    assert "# name: lahuta_bitmask_10t_128p" in proc.stdout
    assert "standard" not in proc.stdout
    assert "f64" not in proc.stdout
    assert "freesasa_batch" not in proc.stdout
    assert "rustsasa" not in proc.stdout
    assert "--use-bitmask" in proc.stdout
    assert "--af-model-fast" in proc.stdout
    assert "--input-io=auto" in proc.stdout
    assert "--warmup 3" in proc.stdout
    assert "--runs 3" in proc.stdout


def test_run_batch_ecoli_cif_overcommit_targets_minimal_bitmask_matrix() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli-cif-zsasa-0.9.toml",
            "--run-id",
            "test_ecoli_cif_overcommit",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=ecoli_cif" in proc.stdout
    assert "selected_commands=5/5" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_10t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_20t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_40t_128p" in proc.stdout
    assert "# name: zsasa_0_9_0_batch_f32_bitmask_80t_128p" in proc.stdout
    assert "# name: lahuta_bitmask_10t_128p" in proc.stdout
    assert "standard" not in proc.stdout
    assert "f64" not in proc.stdout
    assert "freesasa_batch" not in proc.stdout
    assert "rustsasa" not in proc.stdout
    assert "--use-bitmask" in proc.stdout
    assert "--af-model-fast" in proc.stdout
    assert "--input-io=auto" in proc.stdout
