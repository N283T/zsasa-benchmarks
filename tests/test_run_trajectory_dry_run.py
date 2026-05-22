from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_trajectory_validation_dry_run_outputs_native_commands() -> None:
    run_id = "test_run"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_trajectory_validation.py",
            "--manifest",
            "manifests/validation-md-5wvo.toml",
            "--run-id",
            run_id,
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "scripts/validation_md.py" not in proc.stdout
    assert "benchmarks/scripts/" not in proc.stdout
    assert "mdtraj" in proc.stdout
    assert f"results/full_rerun/{run_id}/validation_md" in proc.stdout
    assert "--n-points 100" in proc.stdout
    assert "--n-points 1000" in proc.stdout
    assert "--output" in proc.stdout
    assert "raw/mdtraj/100p/results.json" in proc.stdout

    output_base = Path("results/full_rerun") / run_id / "validation_md" / "5wvo_C_analysis"
    assert output_base.joinpath("commands.log").is_file()
    config_path = output_base.joinpath("config.json")
    assert config_path.is_file()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["dataset_id"] == "5wvo_C_analysis"
    assert config["n_points"] == [100, 200, 500, 1000]
    assert output_base.joinpath("raw", "mdtraj", "100p").is_dir()
    assert output_base.joinpath("raw", "zsasa_mdtraj", "1000p").is_dir()


def test_run_trajectory_dry_run_outputs_native_hyperfine_commands() -> None:
    run_id = "test_run"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_trajectory.py",
            "--manifest",
            "manifests/trajectory.toml",
            "--run-id",
            run_id,
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "scripts/bench_md.py" not in proc.stdout
    assert "benchmarks/scripts/" not in proc.stdout
    assert "hyperfine" in proc.stdout
    assert "mdsasa_bolt" in proc.stdout
    assert f"results/full_rerun/{run_id}/md" in proc.stdout
    assert "5wvo_C_analysis" in proc.stdout
    assert "5vz0_A_protein" in proc.stdout
    assert "--tool zig" in proc.stdout
    assert "--tool zsasa_mdtraj" in proc.stdout
    assert "--tool mdsasa_bolt" in proc.stdout
    assert "--output" in proc.stdout
    assert "raw/5wvo_C_analysis/mdsasa_bolt/results.json" in proc.stdout

    output_base = Path("results/full_rerun") / run_id / "md"
    assert output_base.joinpath("commands.log").is_file()
    config_path = output_base.joinpath("config.json")
    assert config_path.is_file()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["dataset_ids"] == ["5wvo_C_analysis", "6sup_A_analysis", "5vz0_A_protein"]
    assert output_base.joinpath("hyperfine").is_dir()
    assert output_base.joinpath("raw", "5wvo_C_analysis", "mdsasa_bolt").is_dir()
    assert output_base.joinpath("raw", "5vz0_A_protein", "zig").is_dir()


def test_trajectory_tools_module_help_is_available() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.benchlib.trajectory_tools",
            "--help",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--tool" in proc.stdout
    assert "--output" in proc.stdout
