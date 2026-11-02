from __future__ import annotations

import tarfile
from pathlib import Path

from scripts.build_zenodo_archive import (
    collect_archive_files,
    create_part_tarballs,
    format_manifest,
    part_of,
)


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
    touch(tmp_path.joinpath("datasets", "single-file-large-structure-mmcif", "9fqr.cif"))
    touch(tmp_path.joinpath("datasets", "single-file-large-structure-sources", "MANIFEST.csv"))
    touch(tmp_path.joinpath("results", "smoke-clean-cif", "9fqr.json"))
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
    assert "datasets/single-file-large-structure-mmcif/9fqr.cif" not in relpaths
    assert "datasets/single-file-large-structure-sources/MANIFEST.csv" in relpaths
    assert "results/smoke-clean-cif/9fqr.json" not in relpaths
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


def test_part_of_assigns_large_stable_paths_to_their_own_parts() -> None:
    assert part_of("datasets/single-file-large-structure-sources/3jc8.cif.gz") == "inputs"
    assert part_of("results/figures/overview/plot.png") == "figures"
    assert part_of("results/benchmark.duckdb") == "database"
    assert part_of("workflows/afdb-dimers/v0.12.1/homodimers/default/results.parquet") == (
        "afdb-dimers"
    )
    assert part_of("workflows/sasa-explorer/tables/swissprot.parquet") == "sasa-explorer"
    assert part_of("results/full_rerun/v0_6_0_full/raw.json") == "raw-runs"
    assert part_of("results/tables/summary.csv") == "code-and-tables"
    assert part_of("scripts/run_validation.py") == "code-and-tables"


def test_part_tarballs_are_reproducible_and_cover_every_file(tmp_path: Path) -> None:
    repo = tmp_path.joinpath("repo")
    touch(repo.joinpath("README.md"), b"readme\n")
    touch(repo.joinpath("results", "benchmark.duckdb"), b"db")
    touch(repo.joinpath("results", "figures", "a.png"), b"png")
    files = collect_archive_files(repo, profile="curated")

    first = create_part_tarballs(tmp_path.joinpath("one"), files, "gzip")
    for path in repo.rglob("*"):
        path.touch()  # newer mtimes must not change the archives
    second = create_part_tarballs(tmp_path.joinpath("two"), files, "gzip")

    assert [path.name for path in first] == [
        "zsasa-benchmarks-figures.tar.gz",
        "zsasa-benchmarks-database.tar.gz",
        "zsasa-benchmarks-code-and-tables.tar.gz",
    ]
    for a, b in zip(first, second, strict=True):
        assert a.read_bytes() == b.read_bytes()
    members = set()
    for path in first:
        with tarfile.open(path) as archive:
            members |= set(archive.getnames())
    assert members == {f"zsasa-benchmarks/{item.relative_path}" for item in files}


def test_format_manifest_lists_parts(tmp_path: Path) -> None:
    touch(tmp_path.joinpath("README.md"))
    touch(tmp_path.joinpath("results", "benchmark.duckdb"))
    manifest = format_manifest(tmp_path, collect_archive_files(tmp_path), profile="curated")

    assert "| database | `zsasa-benchmarks-database.tar.gz` | 1 |" in manifest
    assert "| `results/benchmark.duckdb` | database |" in manifest
