from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_validation_dry_run_outputs_native_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_validation.py",
            "--manifest",
            "manifests/validation-ecoli.toml",
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

    assert "source_kind=full_rerun" in proc.stdout
    assert "zsasa" in proc.stdout
    assert "freesasa_batch" in proc.stdout
    assert "rustsasa" in proc.stdout
    assert " -f json " in proc.stdout
    assert " -f pdb " not in proc.stdout
    assert "--n-points=100" in proc.stdout
    assert "--n-points=1000" in proc.stdout
    assert "--n-slices=20" in proc.stdout
    assert "scripts/validation.py" not in proc.stdout

    output_base = Path("results/full_rerun") / "test_run" / "validation" / "ecoli"
    assert output_base.joinpath("commands.log").is_file()
    assert output_base.joinpath("config.json").is_file()
    assert output_base.joinpath("zsasa").is_dir()
    assert output_base.joinpath("freesasa_batch", "sr_100").is_dir()
    assert output_base.joinpath("rustsasa", "sr_1000").is_dir()
    assert output_base.joinpath("lahuta", "sr_standard_100").is_dir()
    assert output_base.joinpath("lahuta", "sr_bitmask_128").is_dir()


def test_run_validation_rejects_disabled_full_rerun_flags(tmp_path: Path) -> None:
    manifest = Path("manifests/validation-ecoli.toml").read_text(encoding="utf-8")
    manifest = manifest.replace("rerun_comparators = true", "rerun_comparators = false")
    manifest_path = tmp_path / "validation-ecoli.toml"
    manifest_path.write_text(manifest, encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_validation.py",
            "--manifest",
            str(manifest_path),
            "--run-id",
            "test_run_disabled_flags",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0
    assert "rerun_comparators must be true" in proc.stderr


def test_run_validation_smoke_manifest_uses_smoke_output_dir() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_validation.py",
            "--manifest",
            "manifests/validation-ecoli-smoke.toml",
            "--run-id",
            "test_smoke",
            "--datasets",
            "config/datasets.toml.example",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "datasets/ecoli-smoke/pdb" in proc.stdout
    assert "results/full_rerun/test_smoke/validation/ecoli_smoke" in proc.stdout
