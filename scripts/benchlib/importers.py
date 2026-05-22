"""Import helpers for native full-rerun outputs."""

from __future__ import annotations

from pathlib import Path


def source_kind_for_full_rerun() -> str:
    return "full_rerun"


def artifact_path(path: Path) -> str:
    return str(path)
