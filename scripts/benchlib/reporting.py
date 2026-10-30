"""Helpers for selecting adopted benchmark runs for tracked reports."""

import re

_RUN_SET_RE = re.compile(r"/results/full_rerun/([^/]+)/")

# The zsasa release the reports describe, and its trajectory run set.
CURRENT_ZSASA = "zsasa_0_12_1"
MD_RUN_SET = "v0_12_1_md_128"

_ADOPTED = {
    "validation": {"v0_12_1_validation"},
    "trajectory_validation": {"v0_12_1_validation"},
    "trajectory": {"v0_12_1_md_128", "v0_9_0_md_128"},
    "single_file": {
        "v0_6_0_full",
        "v0_9_0_single_pdb",
        "v0_9_0_single_mmcif",
        "v0_12_1_single_pdb",
        "v0_12_1_single_mmcif",
    },
    "batch": {
        "v0_12_1_batch",
        "v0_12_1_human_cif",
        "v0_12_1_swissprot_default_io",
        "v0_12_1_swissprot_passive_io",
    },
}


def run_set(source_path: str | None) -> str:
    """Return the full-rerun directory name encoded in a run source path."""
    match = _RUN_SET_RE.search(source_path or "")
    return match.group(1) if match else ""


def adopted_for_reporting(benchmark_kind: str, source_path: str | None, status: str) -> bool:
    """Return whether a run belongs to the documented adopted reporting scope."""
    if status == "superseded":
        return False
    return run_set(source_path) in _ADOPTED.get(benchmark_kind, set())


def retained_for_reporting(
    benchmark_kind: str,
    source_path: str | None,
    status: str,
    tool_id: str,
    dataset_id: str,
) -> bool:
    """Return whether an adopted run is reported, keeping only the retained comparator rows.

    Comparators that were not rerun with the current release keep their earlier rows:
    FreeSASA and RustSASA on single-file PDB from 0.6.0, PDBTools.jl on single-file PDB
    and all single-file mmCIF comparators from 0.9.0, and mdsasa-bolt on 5vz0 from 0.9.0.
    """
    if not adopted_for_reporting(benchmark_kind, source_path, status):
        return False
    source = run_set(source_path)
    if benchmark_kind == "single_file":
        if source == "v0_6_0_full":
            return tool_id in {"freesasa", "rustsasa"}
        if source in {"v0_9_0_single_pdb", "v0_9_0_single_mmcif"}:
            return not tool_id.startswith("zsasa")
    if benchmark_kind == "trajectory" and source == "v0_9_0_md_128":
        return tool_id == "mdsasa_bolt" and dataset_id == "5vz0_A_protein"
    return True
