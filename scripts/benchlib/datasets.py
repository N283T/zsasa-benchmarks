"""Dataset path catalog loading for benchmark runners."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from scripts.benchlib.paths import resolve_repo_path

DEFAULT_DATASETS_CONFIG = Path("config/datasets.local.toml")


class DatasetConfigError(RuntimeError):
    """Raised when the local dataset path catalog is missing or incomplete."""


def load_dataset_catalog(path: str | Path = DEFAULT_DATASETS_CONFIG) -> dict[str, dict[str, Any]]:
    """Load a dataset path catalog keyed by manifest dataset id."""
    resolved = resolve_repo_path(path)
    if not resolved.exists():
        raise DatasetConfigError(
            f"dataset config not found: {resolved}; copy config/datasets.toml.example "
            "to config/datasets.local.toml or pass --datasets"
        )
    with resolved.open("rb") as handle:
        raw = tomllib.load(handle)
    catalog: dict[str, dict[str, Any]] = {}
    for dataset_id, value in raw.items():
        if not isinstance(value, dict):
            raise DatasetConfigError(f"dataset config for {dataset_id} must be a table")
        catalog[str(dataset_id)] = value
    return catalog


def dataset_path(catalog: dict[str, dict[str, Any]], dataset_id: str, key: str) -> Path:
    """Resolve a path field from a loaded dataset catalog."""
    entry = catalog.get(dataset_id)
    if entry is None:
        raise DatasetConfigError(f"missing dataset config for {dataset_id}")
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise DatasetConfigError(f"missing {key} path for dataset {dataset_id}")
    return resolve_repo_path(value)
