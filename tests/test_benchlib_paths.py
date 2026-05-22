from __future__ import annotations

from pathlib import Path

from scripts.benchlib.paths import ROOT, full_rerun_dir, resolve_repo_path


def test_root_is_repository_root() -> None:
    assert ROOT.joinpath("pyproject.toml").exists()
    assert ROOT.name == "zsasa-benchmarks"


def test_resolve_repo_path_keeps_absolute_path(tmp_path: Path) -> None:
    absolute = tmp_path.joinpath("example")
    assert resolve_repo_path(absolute) == absolute


def test_resolve_repo_path_joins_relative_path() -> None:
    assert resolve_repo_path(Path("results/example")).is_absolute()
    assert resolve_repo_path(Path("results/example")) == ROOT.joinpath("results", "example")


def test_resolve_repo_path_expands_home_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_repo_path("$HOME/data") == tmp_path.joinpath("data")
    assert resolve_repo_path("~/data") == tmp_path.joinpath("data")


def test_full_rerun_dir_uses_run_id_and_parts() -> None:
    path = full_rerun_dir("v0_6_0_full", "batch", "ecoli")
    assert path == ROOT.joinpath("results", "full_rerun", "v0_6_0_full", "batch", "ecoli")
