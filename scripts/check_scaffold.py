#!/usr/bin/env python3
"""Check the benchmark repository scaffold without running benchmarks."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "flake.nix",
    "pyproject.toml",
    "config/tool-versions.toml",
    "manifests/validation-ecoli.toml",
    "manifests/validation-md-5wvo.toml",
    "manifests/batch-ecoli.toml",
    "manifests/batch-human.toml",
    "manifests/single-file-sample.toml",
    "manifests/trajectory.toml",
    "docs/benchmark-policy.md",
    "docs/database.md",
    "schemas/benchmark.sql",
    "scripts/check_scaffold.py",
    "scripts/setup_external_tools.py",
    "scripts/db_common.py",
    "scripts/init_db.py",
    "scripts/export_validation_summary.py",
    "scripts/run_validation.py",
    "scripts/run_batch.py",
    "scripts/run_trajectory_validation.py",
    "scripts/run_trajectory.py",
    "scripts/benchlib/commands.py",
    "scripts/benchlib/hyperfine.py",
    "scripts/benchlib/importers.py",
    "scripts/benchlib/manifest.py",
    "scripts/benchlib/metrics.py",
    "scripts/benchlib/paths.py",
    "scripts/benchlib/runner.py",
    "scripts/benchlib/tools.py",
    "scripts/benchlib/trajectory_tools.py",
    "tools/freesasa_batch/freesasa_batch.cc",
    "tools/freesasa_batch/Makefile",
    "results/.gitkeep",
    "archives/.gitkeep",
]

REMOVED_LEGACY_FILES = [
    "scripts/import_validation_csv.py",
    "scripts/refresh_validation.py",
    "scripts/refresh_validation_md.py",
    "scripts/report_existing_assets.py",
    "scripts/smoke_db.py",
    "scripts/run_single_file_subset.py",
    "scripts/export_single_file_subset_summary.py",
    "scripts/plot_figures.py",
    "docs/existing-assets.md",
    "docs/migration-plan.md",
    "docs/zsasa-only-validation-refresh.md",
    "docs/validation-rerun-log.md",
    "docs/trajectory-validation-rerun-log.md",
    "docs/batch-rerun-log.md",
    "docs/batch-human-rerun-log.md",
    "docs/trajectory-rerun-log.md",
    "docs/single-file-rerun-log.md",
    "docs/batch-rerun-plan.md",
    "docs/trajectory-rerun-plan.md",
    "docs/single-file-subset-plan.md",
]


FULL_RERUN_MANIFESTS = [
    "manifests/validation-ecoli.toml",
    "manifests/validation-md-5wvo.toml",
    "manifests/batch-ecoli.toml",
    "manifests/batch-human.toml",
    "manifests/trajectory.toml",
    "manifests/single-file-sample.toml",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def require_no_legacy_markers(path: str) -> None:
    text = ROOT.joinpath(path).read_text(encoding="utf-8")
    for marker in [
        "benchmarks/scripts/",
        "refresh_validation.py",
        "import_validation_csv.py",
        "historical comparator",
        "historical baseline",
        "reuse existing comparator",
    ]:
        if marker in text:
            fail(f"legacy benchmark marker {marker!r} remains in {path}")


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not ROOT.joinpath(path).exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    forbidden_user_path = "/Users/" + "nagaet"
    hardcoded_user_paths = [
        path
        for path in [*REQUIRED_FILES, *FULL_RERUN_MANIFESTS]
        if ROOT.joinpath(path).is_file()
        and forbidden_user_path in ROOT.joinpath(path).read_text(encoding="utf-8")
    ]
    if hardcoded_user_paths:
        fail(f"hard-coded {forbidden_user_path} paths remain: " + ", ".join(hardcoded_user_paths))

    remaining_legacy = [path for path in REMOVED_LEGACY_FILES if ROOT.joinpath(path).exists()]
    if remaining_legacy:
        fail("legacy files should be removed: " + ", ".join(remaining_legacy))

    tools = read_toml(ROOT.joinpath("config/tool-versions.toml"))
    if tools.get("zsasa", {}).get("tag") != "v0.6.0":
        fail("tool-versions.toml must pin zsasa to v0.6.0 for the current rerun")
    expected_external_bins = {
        "freesasa": "external/bin/freesasa",
        "freesasa_batch": "external/bin/freesasa_batch",
        "rustsasa": "external/bin/rust-sasa",
        "lahuta": "external/bin/lahuta",
    }
    for tool, expected_binary in expected_external_bins.items():
        spec = tools.get(tool, {})
        if spec.get("binary") != expected_binary:
            fail(f"{tool} binary must resolve through the benchmark repo external/bin tree")
        if "pinned" not in spec.get("policy", ""):
            fail(f"{tool} policy must require pinned reruns")
    if (
        tools.get("freesasa_batch", {}).get("source_path")
        != "tools/freesasa_batch/freesasa_batch.cc"
    ):
        fail("freesasa_batch source must be tracked in tools/freesasa_batch")

    for manifest_path in FULL_RERUN_MANIFESTS:
        manifest = read_toml(ROOT.joinpath(manifest_path))
        full_rerun = manifest.get("full_rerun", {})
        if full_rerun.get("source_kind") != "full_rerun":
            fail(f"{manifest_path} must define source_kind = full_rerun")
        if full_rerun.get("rerun_zsasa") is not True:
            fail(f"{manifest_path} must rerun zsasa")
        if full_rerun.get("rerun_comparators") is not True:
            fail(f"{manifest_path} must rerun comparators")

    validation = read_toml(ROOT.joinpath("manifests/validation-ecoli.toml"))
    dataset = validation.get("dataset", {})
    if dataset.get("expected_count") != 4370:
        fail("validation manifest must describe the E. coli 4,370-structure dataset")
    if "UP000000625_83333_ECOLI" not in dataset.get("path_or_uri", ""):
        fail("validation manifest must point to the E. coli dataset path")
    runs = validation.get("runs", [])
    if not any(run.get("algorithm") == "sr" and 100 in run.get("points", []) for run in runs):
        fail("validation manifest must include SR 100-point full rerun")
    if not any(run.get("algorithm") == "lr" and 20 in run.get("points", []) for run in runs):
        fail("validation manifest must include LR 20-slice full rerun")

    md_validation = read_toml(ROOT.joinpath("manifests/validation-md-5wvo.toml"))
    md_full = md_validation.get("full_rerun", {})
    if md_full.get("tools") != ["mdtraj", "zsasa_mdtraj", "zsasa_mdanalysis", "zig", "zig_bitmask"]:
        fail("MD validation full_rerun must include mdtraj, zsasa wrappers, and CLI tools")
    if md_full.get("classifier") != "naccess" or md_full.get("include_hydrogens") is not True:
        fail("MD validation full_rerun must use naccess with explicit hydrogens")

    trajectory = read_toml(ROOT.joinpath("manifests/trajectory.toml"))
    trajectory_full = trajectory.get("full_rerun", {})
    if "mdtraj" not in trajectory_full.get("default_tools", []):
        fail("trajectory full_rerun must include native mdtraj")
    if "mdsasa_bolt" not in trajectory_full.get("default_tools", []):
        fail("trajectory full_rerun must include mdsasa_bolt")
    if len(trajectory.get("datasets", [])) != 3:
        fail("trajectory manifest must describe the three benchmark datasets")

    schema = ROOT.joinpath("schemas/benchmark.sql").read_text(encoding="utf-8")
    for table in [
        "datasets",
        "tools",
        "benchmark_runs",
        "validation_results",
        "performance_results",
        "artifacts",
    ]:
        if f"CREATE TABLE IF NOT EXISTS {table}" not in schema:
            fail(f"benchmark schema missing table: {table}")

    for path in [
        "README.md",
        "docs/benchmark-policy.md",
        "docs/database.md",
        "scripts/run_validation.py",
        "scripts/run_batch.py",
        "scripts/run_trajectory_validation.py",
        "scripts/run_trajectory.py",
    ]:
        require_no_legacy_markers(path)

    print("benchmark scaffold checks passed")


if __name__ == "__main__":
    main()
