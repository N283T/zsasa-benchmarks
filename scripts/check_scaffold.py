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
    "manifests/batch-ecoli.toml",
    "manifests/single-file-sample.toml",
    "manifests/trajectory.toml",
    "docs/benchmark-policy.md",
    "docs/existing-assets.md",
    "docs/migration-plan.md",
    "docs/zsasa-only-validation-refresh.md",
    "docs/batch-rerun-plan.md",
    "docs/database.md",
    "docs/validation-rerun-log.md",
    "schemas/benchmark.sql",
    "scripts/check_scaffold.py",
    "scripts/db_common.py",
    "scripts/init_db.py",
    "scripts/import_validation_csv.py",
    "scripts/export_validation_summary.py",
    "scripts/report_existing_assets.py",
    "scripts/refresh_validation.py",
    "scripts/smoke_db.py",
    "tests/fixtures/validation/validation-fixture.toml",
    "tests/fixtures/validation/sr/results_100.csv",
    "tests/fixtures/validation/lr/results_20.csv",
    "results/.gitkeep",
    "archives/.gitkeep",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not ROOT.joinpath(path).exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    tools = read_toml(ROOT.joinpath("config/tool-versions.toml"))
    if tools.get("zsasa", {}).get("tag") != "v0.6.0":
        fail("tool-versions.toml must pin zsasa to v0.6.0 for the current refresh")
    for tool in ["freesasa", "rustsasa", "lahuta"]:
        if "reuse existing comparator baseline" not in tools.get(tool, {}).get("policy", ""):
            fail(f"{tool} policy must preserve baseline reuse")

    manifest = read_toml(ROOT.joinpath("manifests/validation-ecoli.toml"))
    dataset = manifest.get("dataset", {})
    if dataset.get("expected_count") != 4370:
        fail("validation manifest must describe the E. coli 4,370-structure dataset")
    if "UP000000625_83333_ECOLI" not in dataset.get("historical_path", ""):
        fail("validation manifest must point to the historical E. coli dataset path")
    if "replace zsasa columns" not in manifest.get("baseline", {}).get("policy", ""):
        fail("validation manifest must state the zsasa-only refresh policy")

    runs = manifest.get("runs", [])
    if not any(run.get("algorithm") == "sr" and 100 in run.get("points", []) for run in runs):
        fail("validation manifest must include SR 100-point refresh")
    if not any(run.get("algorithm") == "lr" and 20 in run.get("points", []) for run in runs):
        fail("validation manifest must include LR 20-slice refresh")

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

    database_doc = ROOT.joinpath("docs/database.md").read_text(encoding="utf-8")
    for phrase in ["historical_baseline", "zsasa_v0.6.0_refresh", "full_rerun"]:
        if phrase not in database_doc:
            fail(f"database docs missing source kind: {phrase}")

    rerun_log = ROOT.joinpath("docs/validation-rerun-log.md").read_text(encoding="utf-8")
    for phrase in ["freesasa_batch", "zsasa 0.6.0", "4,370 PDB files", "Comparator tools were not rerun"]:
        if phrase not in rerun_log:
            fail(f"validation rerun log missing phrase: {phrase}")

    batch_manifest = read_toml(ROOT.joinpath("manifests/batch-ecoli.toml"))
    refresh = batch_manifest.get("planned_refresh", {})
    if refresh.get("source_kind") != "zsasa_v0.6.0_refresh":
        fail("batch manifest must identify the zsasa v0.6.0 refresh source kind")
    if refresh.get("tools") != ["zig", "zig_bitmask"]:
        fail("batch manifest must restrict the first refresh to zsasa tools")
    if refresh.get("threads") != [10] or refresh.get("n_points") != 128:
        fail("batch manifest must match the historical ecoli_t10 settings")

    batch_plan = ROOT.joinpath("docs/batch-rerun-plan.md").read_text(encoding="utf-8")
    for phrase in [
        "do not rerun FreeSASA",
        "zsasa_v0.6.0_refresh",
        "4,370 PDB files",
        "Closing Codex",
        "--tool zig_bitmask",
    ]:
        if phrase not in batch_plan:
            fail(f"batch rerun plan missing phrase: {phrase}")

    print("benchmark scaffold checks passed")


if __name__ == "__main__":
    main()
