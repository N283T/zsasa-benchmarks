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
    "docs/existing-assets.md",
    "docs/migration-plan.md",
    "docs/zsasa-only-validation-refresh.md",
    "docs/batch-rerun-plan.md",
    "docs/batch-rerun-log.md",
    "docs/batch-human-rerun-log.md",
    "docs/trajectory-rerun-plan.md",
    "docs/trajectory-rerun-log.md",
    "docs/trajectory-validation-rerun-log.md",
    "docs/single-file-subset-plan.md",
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
    "scripts/refresh_validation_md.py",
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

    md_validation_manifest = read_toml(ROOT.joinpath("manifests/validation-md-5wvo.toml"))
    if md_validation_manifest.get("status") != "completed":
        fail("MD validation manifest must record the completed refresh")
    md_validation_dataset = md_validation_manifest.get("dataset", {})
    if md_validation_dataset.get("frames") != 1001 or md_validation_dataset.get("atoms") != 3858:
        fail("MD validation manifest must describe the 5wvo_C_analysis dataset")
    md_validation_refresh = md_validation_manifest.get("refresh", {})
    if md_validation_refresh.get("native_mdtraj_rerun") is not False:
        fail("MD validation refresh must reuse the historical mdtraj reference")

    batch_manifest = read_toml(ROOT.joinpath("manifests/batch-ecoli.toml"))
    refresh = batch_manifest.get("planned_refresh", {})
    if refresh.get("source_kind") != "zsasa_v0.6.0_refresh":
        fail("batch manifest must identify the zsasa v0.6.0 refresh source kind")
    if refresh.get("tools") != ["zig", "zig_bitmask"]:
        fail("batch manifest must restrict the first refresh to zsasa tools")
    if refresh.get("threads") != [1, 2, 4, 8, 10] or refresh.get("n_points") != 128:
        fail("batch manifest must describe the refreshed E. coli scaling settings")

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

    batch_log = ROOT.joinpath("docs/batch-rerun-log.md").read_text(encoding="utf-8")
    for phrase in [
        "bench_zsasa_f64_2t.json",
        "normalized by hand",
        "2,984",
        "Comparator tools were not rerun",
    ]:
        if phrase not in batch_log:
            fail(f"batch rerun log missing phrase: {phrase}")

    human_manifest = read_toml(ROOT.joinpath("manifests/batch-human.toml"))
    human_dataset = human_manifest.get("dataset", {})
    if human_dataset.get("expected_count") != 23586:
        fail("human batch manifest must describe the 23,586-structure dataset")
    human_refresh = human_manifest.get("refresh", {})
    if human_refresh.get("threads") != [10] or human_refresh.get("runs") != 10:
        fail("human batch manifest must describe the completed t10 refresh")
    if human_refresh.get("tools") != ["zig", "zig_bitmask"]:
        fail("human batch manifest must restrict the refresh to zsasa tools")

    human_log = ROOT.joinpath("docs/batch-human-rerun-log.md").read_text(encoding="utf-8")
    for phrase in [
        "23,586 PDB files",
        "Comparator tools were not rerun",
        "1,667",
        "thermal or background-state effects",
    ]:
        if phrase not in human_log:
            fail(f"human batch rerun log missing phrase: {phrase}")

    single_manifest = read_toml(ROOT.joinpath("manifests/single-file-sample.toml"))
    if single_manifest.get("status") != "planning":
        fail("single-file manifest must record the curated subset planning status")
    single_subset = single_manifest.get("subset", {}).get("selection", [])
    if len(single_subset) != 12:
        fail("single-file subset must contain 12 representative structures")
    for required_structure in ["9fqr", "5vyc", "8fon", "8rbs", "af-q6zs30-f1-model_v6"]:
        if required_structure not in single_subset:
            fail(f"single-file subset missing required structure: {required_structure}")

    single_plan = ROOT.joinpath("docs/single-file-subset-plan.md").read_text(encoding="utf-8")
    for phrase in [
        "maximum structure",
        "RustSASA parse-time outlier maximum",
        "FreeSASA total-runtime outlier",
        "Lahuta is not part of this single-file historical set",
    ]:
        if phrase not in single_plan:
            fail(f"single-file subset plan missing phrase: {phrase}")

    trajectory_manifest = read_toml(ROOT.joinpath("manifests/trajectory.toml"))
    if trajectory_manifest.get("status") != "completed":
        fail("trajectory manifest must record the completed rerun")
    trajectory_datasets = trajectory_manifest.get("datasets", [])
    if len(trajectory_datasets) != 3:
        fail("trajectory manifest must describe the three benchmark datasets")
    if {dataset.get("id") for dataset in trajectory_datasets} != {
        "5wvo_C_analysis",
        "6sup_A_analysis",
        "5vz0_A_protein",
    }:
        fail("trajectory manifest has unexpected dataset ids")
    if any(dataset.get("refresh_threads") != [10] for dataset in trajectory_datasets):
        fail("trajectory manifest must describe t10-only refresh threads for all datasets")
    dataset_tools = {dataset.get("id"): dataset.get("refresh_tools") for dataset in trajectory_datasets}
    expected_cli_and_wrappers = [
        "zig",
        "zig_bitmask",
        "zsasa_mdtraj",
        "zsasa_mdtraj_bitmask",
        "zsasa_mdanalysis",
        "zsasa_mdanalysis_bitmask",
    ]
    if dataset_tools.get("5wvo_C_analysis") != expected_cli_and_wrappers:
        fail("5wvo trajectory refresh must include zsasa CLI and Python wrappers")
    if dataset_tools.get("6sup_A_analysis") != expected_cli_and_wrappers:
        fail("6sup trajectory refresh must include zsasa CLI and Python wrappers")
    if dataset_tools.get("5vz0_A_protein") != ["zig", "zig_bitmask"]:
        fail("5vz0 trajectory refresh must be CLI-only")
    trajectory_refresh = trajectory_manifest.get("refresh", {})
    if trajectory_refresh.get("default_tools") != expected_cli_and_wrappers:
        fail("trajectory refresh default tools must include zsasa CLI and Python wrappers")
    if trajectory_refresh.get("large_trajectory_tools") != ["zig", "zig_bitmask"]:
        fail("trajectory refresh must define CLI-only tools for 5vz0")
    if trajectory_refresh.get("external_comparators_not_rerun") != ["mdtraj", "mdsasa_bolt"]:
        fail("trajectory refresh must leave external comparators as historical baselines")
    if trajectory_refresh.get("n_points") != 100:
        fail("trajectory refresh must describe the t10 100-point rerun")

    trajectory_plan = ROOT.joinpath("docs/trajectory-rerun-plan.md").read_text(encoding="utf-8")
    for phrase in [
        "Do not rerun",
        "zsasa_mdtraj_bitmask",
        "5vz0_A_protein` dataset is CLI only",
        "5vz0_A_protein",
        "--tool zig_bitmask",
        "Remove `--dry-run`",
    ]:
        if phrase not in trajectory_plan:
            fail(f"trajectory rerun plan missing phrase: {phrase}")

    trajectory_log = ROOT.joinpath("docs/trajectory-rerun-log.md").read_text(encoding="utf-8")
    for phrase in [
        "External comparators were not rerun",
        "5vz0_A_protein` | 17,910 | 10,001 | CLI only",
        "CLI bitmask f32 | 37.388",
        "zsasa Python wrapper paths for the two 1K-frame datasets",
    ]:
        if phrase not in trajectory_log:
            fail(f"trajectory rerun log missing phrase: {phrase}")

    md_validation_log = ROOT.joinpath("docs/trajectory-validation-rerun-log.md").read_text(encoding="utf-8")
    for phrase in [
        "Native MDTraj rerun: no",
        "0.999539",
        "mdtraj.shrake_rupley` was not rerun",
        "zsasa_cli_bitmask_f32",
    ]:
        if phrase not in md_validation_log:
            fail(f"trajectory validation rerun log missing phrase: {phrase}")

    print("benchmark scaffold checks passed")


if __name__ == "__main__":
    main()
