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
    assert "--use-bitmask" in proc.stdout
    assert "lahuta" in proc.stdout
    assert "rustsasa" in proc.stdout
    assert " -f json " in proc.stdout
    assert " -f pdb " not in proc.stdout


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
