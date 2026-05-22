from __future__ import annotations

from pathlib import Path

from scripts.benchlib.paths import ROOT, full_rerun_dir, resolve_repo_path


def test_root_is_repository_root() -> None:
    assert ROOT.joinpath("pyproject.toml").exists()
    assert ROOT.name == "zsasa-benchmarks"


def test_resolve_repo_path_keeps_absolute_path() -> None:
    absolute = Path("/tmp/example")
    assert resolve_repo_path(absolute) == absolute


def test_resolve_repo_path_joins_relative_path() -> None:
    assert resolve_repo_path(Path("results/example")).is_absolute()
    assert str(resolve_repo_path(Path("results/example"))).endswith("results/example")


def test_full_rerun_dir_uses_run_id_and_parts() -> None:
    path = full_rerun_dir("v0_6_0_full", "batch", "ecoli")
    assert path == ROOT.joinpath("results", "full_rerun", "v0_6_0_full", "batch", "ecoli")
