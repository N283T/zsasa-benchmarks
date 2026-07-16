from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_single_file_dry_run_outputs_wall_and_timing_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            "test_single",
            "--only",
            "single_*_zsasa_f64_AF-P49792-F10-model_v6_1t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "benchmark_kind=single_file" in proc.stdout
    assert "dataset=single_file_large_structure_subset" in proc.stdout
    assert "selected_commands=2/" in proc.stdout
    assert "# name: single_wall_zsasa_f64_AF-P49792-F10-model_v6_1t_100p" in proc.stdout
    assert "# name: single_timing_zsasa_f64_AF-P49792-F10-model_v6_1t_100p" in proc.stdout
    assert "hyperfine" in proc.stdout
    assert " calc " in proc.stdout
    assert "--timing" in proc.stdout
    assert "datasets/single-file-large-structure/pdb/AF-P49792-F10-model_v6.pdb" in proc.stdout


def test_run_single_file_dry_run_writes_command_log_and_config() -> None:
    run_id = "test_single_dirs"
    output_base = Path("results/full_rerun").joinpath(
        run_id,
        "single",
        "single_file_large_structure_subset",
    )
    if output_base.exists():
        import shutil

        shutil.rmtree(output_base)

    subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            run_id,
            "--only",
            "single_wall_freesasa_3jc8_1t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_base.joinpath("commands.log").is_file()
    assert output_base.joinpath("config.json").is_file()
    assert output_base.joinpath("wall", "freesasa", "runs").is_dir()


def test_run_single_file_mmcif_dry_run_uses_input_file_and_versioned_tools() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-mmcif-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            "test_single_mmcif",
            "--only",
            "single_wall_zsasa_0_9_0_f64_3jc8_10t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "dataset=single_file_large_structure_mmcif_subset" in proc.stdout
    assert "selected_commands=1/" in proc.stdout
    assert "# name: single_wall_zsasa_0_9_0_f64_3jc8_10t_100p" in proc.stdout
    assert "datasets/single-file-large-structure-mmcif/3jc8.cif" in proc.stdout
    assert "--runs 3" in proc.stdout
    assert "--warmup 1" in proc.stdout


def test_run_single_file_mmcif_applies_manifest_record_exclusions() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-mmcif-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            "test_single_mmcif_exclusions",
            "--only",
            "single_wall_freesasa_8rbs_1t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_commands=1/424" in proc.stdout
    assert "# name: single_wall_freesasa_8rbs_1t_100p" in proc.stdout
    assert "freesasa_9fqr" not in proc.stdout


def test_run_single_file_pdbtools_dry_run_uses_julia_wrapper_for_pdb() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            "test_single_pdbtools",
            "--only",
            "single_wall_pdbtools_jl_AF-P49792-F10-model_v6_10t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_commands=1/" in proc.stdout
    assert "# name: single_wall_pdbtools_jl_AF-P49792-F10-model_v6_10t_100p" in proc.stdout
    assert "julia --threads 10" in proc.stdout
    assert "scripts/benchlib/pdbtools_sasa.jl" in proc.stdout
    assert "--n-dots 100" in proc.stdout
    assert "--timing-repeats 3" in proc.stdout
    assert "datasets/single-file-large-structure/pdb/AF-P49792-F10-model_v6.pdb" in proc.stdout


def test_run_single_file_pdbtools_dry_run_uses_julia_wrapper_for_mmcif() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_single_file.py",
            "--manifest",
            "manifests/single-file-mmcif-sample.toml",
            "--datasets",
            "config/datasets.toml.example",
            "--run-id",
            "test_single_mmcif_pdbtools",
            "--only",
            "single_timing_pdbtools_jl_3jc8_10t_100p",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_commands=1/" in proc.stdout
    assert "# name: single_timing_pdbtools_jl_3jc8_10t_100p" in proc.stdout
    assert "julia --threads 10" in proc.stdout
    assert "scripts/benchlib/pdbtools_sasa.jl" in proc.stdout
    assert "--timing" in proc.stdout
    assert "--timing-repeats 3" in proc.stdout
    assert "datasets/single-file-large-structure-mmcif/3jc8.cif" in proc.stdout
