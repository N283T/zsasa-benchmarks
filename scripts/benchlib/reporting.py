"""Helpers for selecting adopted benchmark runs for tracked reports."""

import re

_RUN_SET_RE = re.compile(r"/results/full_rerun/([^/]+)/")


def run_set(source_path: str | None) -> str:
    """Return the full-rerun directory name encoded in a run source path."""
    match = _RUN_SET_RE.search(source_path or "")
    return match.group(1) if match else ""


def adopted_for_reporting(benchmark_kind: str, source_path: str | None, status: str) -> bool:
    """Return whether a run belongs to the documented adopted reporting scope."""
    if status == "superseded":
        return False
    source = run_set(source_path)
    adopted = {
        "validation": {"v0_9_0_validation"},
        "trajectory_validation": {"v0_9_0_validation"},
        "trajectory": {"v0_9_0_md_128"},
        "single_file": {
            "v0_6_0_full",
            "v0_9_0_single_pdb",
            "v0_9_0_single_mmcif",
        },
        "batch": {
            "v0_6_0_full",
            "version_refresh_20260630",
            "v0_9_0_overcommit",
            "v0_9_0_swissprot",
            "v0_9_0_swissprot_read_t10",
            "v0_9_0_human_cif",
        },
    }
    return source in adopted.get(benchmark_kind, set())
