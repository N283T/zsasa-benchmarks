"""Path helpers for native benchmark runners."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT.joinpath("results")
ARCHIVES_DIR = ROOT.joinpath("archives")


def resolve_repo_path(path: str | Path) -> Path:
    candidate = Path(os.path.expandvars(str(path))).expanduser()
    return candidate if candidate.is_absolute() else ROOT.joinpath(candidate)


def full_rerun_dir(run_id: str, *parts: str) -> Path:
    return RESULTS_DIR.joinpath("full_rerun", run_id, *parts)
