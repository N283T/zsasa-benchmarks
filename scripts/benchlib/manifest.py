"""TOML manifest loading and validation helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from scripts.benchlib.paths import resolve_repo_path


class ManifestError(ValueError):
    """Raised when a benchmark manifest is malformed."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    resolved = resolve_repo_path(path)
    with resolved.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data.get("id"), str):
        raise ManifestError(f"{resolved} missing required string key: id")
    return data


def expect_dict(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ManifestError(f"missing required table: {key}")
    return value


def expect_list(mapping: dict[str, Any], key: str) -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ManifestError(f"{key} must be a list")
    return value


def expect_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{key} must be a non-empty string")
    return value


def expect_int(mapping: dict[str, Any], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"{key} must be an integer")
    return value


def require_native_full_rerun_flags(settings: dict[str, Any], *, runner: str) -> None:
    """Reject partial full-rerun manifests for native runners."""
    for key in ["rerun_zsasa", "rerun_comparators"]:
        if settings.get(key) is not True:
            raise SystemExit(
                f"{key} must be true for {runner}; "
                "native full-rerun runners do not support partial reruns"
            )
