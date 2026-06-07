from __future__ import annotations

from pathlib import Path

from scripts.build_zenodo_archive import collect_archive_files, format_manifest


def touch(path: Path, data: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_curated_profile_includes_publication_artifacts_and_excludes_raw_runs(
    tmp_path: Path,
) -> None:
    touch(tmp_path.joinpath("README.md"))
    touch(tmp_path.joinpath("pyproject.toml"))
    touch(tmp_path.joinpath("scripts", "run_validation.py"))
    touch(tmp_path.joinpath("manifests", "validation-ecoli.toml"))
    touch(tmp_path.joinpath("config", "datasets.local.toml"))
    touch(tmp_path.joinpath(".env"))
    touch(tmp_path.joinpath("results", "benchmark.duckdb"))
    touch(tmp_path.joinpath("results", "tables", "summary.csv"))
    touch(tmp_path.joinpath("results", "figures", "overview", "plot.png"))
    touch(tmp_path.joinpath("results", "full_rerun", "v0_6_0_full", "raw.json"))
    touch(tmp_path.joinpath("datasets", "single-file-large-structure", "pdb", "9fqr.pdb"))
    touch(tmp_path.joinpath("logs", "single-file-v0_6_0_full.log"))
    touch(tmp_path.joinpath(".git", "HEAD"))
    touch(tmp_path.joinpath("scripts", "__pycache__", "ignored.pyc"))
    touch(tmp_path.joinpath(".DS_Store"))

    files = collect_archive_files(tmp_path, profile="curated")
    relpaths = {item.relative_path for item in files}

    assert "README.md" in relpaths
    assert "pyproject.toml" in relpaths
    assert "scripts/run_validation.py" in relpaths
    assert "manifests/validation-ecoli.toml" in relpaths
    assert "results/benchmark.duckdb" in relpaths
    assert "results/tables/summary.csv" in relpaths
    assert "results/figures/overview/plot.png" in relpaths
    assert "results/full_rerun/v0_6_0_full/raw.json" not in relpaths
    assert "config/datasets.local.toml" not in relpaths
    assert ".env" not in relpaths
    assert "datasets/single-file-large-structure/pdb/9fqr.pdb" not in relpaths
    assert "logs/single-file-v0_6_0_full.log" not in relpaths
    assert ".git/HEAD" not in relpaths
    assert "scripts/__pycache__/ignored.pyc" not in relpaths
    assert ".DS_Store" not in relpaths


def test_full_profile_includes_selected_full_rerun_ids(tmp_path: Path) -> None:
    touch(tmp_path.joinpath("results", "full_rerun", "v0_6_0_full", "raw.json"))
    touch(tmp_path.joinpath("results", "full_rerun", "nix_full_20260524", "raw.json"))
    touch(tmp_path.joinpath("results", "full_rerun", "nix_validation_20260524", "raw.json"))
    touch(tmp_path.joinpath("results", "full_rerun", "smoke_check", "raw.json"))

    files = collect_archive_files(tmp_path, profile="full")
    relpaths = {item.relative_path for item in files}

    assert "results/full_rerun/v0_6_0_full/raw.json" in relpaths
    assert "results/full_rerun/nix_full_20260524/raw.json" in relpaths
    assert "results/full_rerun/nix_validation_20260524/raw.json" in relpaths
    assert "results/full_rerun/smoke_check/raw.json" not in relpaths


def test_format_manifest_records_profile_size_and_checksums(tmp_path: Path) -> None:
    touch(tmp_path.joinpath("README.md"), b"benchmark archive\n")
    files = collect_archive_files(tmp_path, profile="curated")

    manifest = format_manifest(tmp_path, files, profile="curated")

    assert "# zsasa-benchmarks Zenodo archive manifest" in manifest
    assert "Profile: curated" in manifest
    assert "Total files: 1" in manifest
    assert "README.md" in manifest
    assert "sha256:" in manifest
