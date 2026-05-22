from __future__ import annotations

from pathlib import Path

import pytest
from scripts.benchlib.datasets import DatasetConfigError, dataset_path, load_dataset_catalog


def test_dataset_path_expands_home_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path.joinpath("datasets.toml")
    config.write_text(
        '[example]\npath = "$HOME/pdb/example"\nxtc = "~/traj/example.xtc"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    catalog = load_dataset_catalog(config)

    assert dataset_path(catalog, "example", "path") == tmp_path.joinpath("pdb/example")
    assert dataset_path(catalog, "example", "xtc") == tmp_path.joinpath("traj/example.xtc")


def test_dataset_path_requires_dataset_entry(tmp_path: Path) -> None:
    config = tmp_path.joinpath("datasets.toml")
    config.write_text("[known]\npath = 'data/known'\n", encoding="utf-8")

    catalog = load_dataset_catalog(config)

    with pytest.raises(DatasetConfigError, match="missing dataset config for unknown"):
        dataset_path(catalog, "unknown", "path")


def test_load_dataset_catalog_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetConfigError, match="dataset config not found"):
        load_dataset_catalog(tmp_path.joinpath("missing.toml"))
