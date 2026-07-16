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
    ".gitignore",
    "config/datasets.toml.example",
    "config/tool-versions.toml",
    "manifests/validation-ecoli-smoke.toml",
    "manifests/validation-ecoli.toml",
    "manifests/validation-md-5wvo.toml",
    "manifests/batch-ecoli.toml",
    "manifests/batch-ecoli-zsasa-0.9.toml",
    "manifests/batch-ecoli-cif-zsasa-0.9.toml",
    "manifests/batch-human.toml",
    "manifests/batch-human-zsasa-0.9.toml",
    "manifests/batch-human-cif-zsasa-0.9.toml",
    "manifests/batch-swissprot-version-refresh.toml",
    "manifests/single-file-sample.toml",
    "manifests/single-file-mmcif-sample.toml",
    "manifests/trajectory.toml",
    "docs/benchmark-policy.md",
    "docs/database.md",
    "schemas/benchmark.sql",
    "scripts/check_scaffold.py",
    "scripts/setup_external_tools.py",
    "scripts/db_common.py",
    "scripts/init_db.py",
    "scripts/export_validation_summary.py",
    "scripts/import_full_rerun.py",
    "scripts/run_validation.py",
    "scripts/run_batch.py",
    "scripts/run_single_file.py",
    "scripts/prepare_single_file_mmcif_structures.py",
    "scripts/run_trajectory_validation.py",
    "scripts/run_trajectory.py",
    "scripts/run_remaining_benchmarks.py",
    "scripts/benchlib/commands.py",
    "scripts/benchlib/pdbtools_sasa.jl",
    "scripts/benchlib/datasets.py",
    "scripts/benchlib/hyperfine.py",
    "scripts/benchlib/importers.py",
    "scripts/benchlib/manifest.py",
    "scripts/benchlib/metrics.py",
    "scripts/benchlib/paths.py",
    "scripts/benchlib/runner.py",
    "scripts/benchlib/tools.py",
    "scripts/julia/pdbtools_sasa/Project.toml",
    "scripts/julia/pdbtools_sasa/Manifest.toml",
    "scripts/benchlib/trajectory_tools.py",
    "tools/freesasa_batch/freesasa_batch.cc",
    "tools/freesasa_batch/Makefile",
    "datasets/ecoli-smoke/pdb/AF-A0A385XJ53-F1-model_v6.pdb",
    "datasets/ecoli-smoke/pdb/AF-A5A605-F1-model_v6.pdb",
    "datasets/ecoli-smoke/pdb/AF-A5A611-F1-model_v6.pdb",
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
    "manifests/validation-ecoli-smoke.toml",
    "manifests/validation-ecoli.toml",
    "manifests/validation-md-5wvo.toml",
    "manifests/batch-ecoli.toml",
    "manifests/batch-human.toml",
    "manifests/batch-swissprot-version-refresh.toml",
    "manifests/trajectory.toml",
    "manifests/single-file-sample.toml",
    "manifests/single-file-mmcif-sample.toml",
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
    local_path_keys = ["path_or_uri", "historical_path", 'xtc = "', 'pdb = "']
    manifest_local_paths = []
    for path in FULL_RERUN_MANIFESTS:
        text = ROOT.joinpath(path).read_text(encoding="utf-8")
        if any(key in text for key in local_path_keys):
            manifest_local_paths.append(path)
    if manifest_local_paths:
        fail(
            "local data paths must live in config/datasets.local.toml: "
            + ", ".join(manifest_local_paths)
        )

    gitignore = ROOT.joinpath(".gitignore").read_text(encoding="utf-8")
    if "/config/datasets.local.toml" not in gitignore:
        fail(".gitignore must ignore config/datasets.local.toml")

    remaining_legacy = [path for path in REMOVED_LEGACY_FILES if ROOT.joinpath(path).exists()]
    if remaining_legacy:
        fail("legacy files should be removed: " + ", ".join(remaining_legacy))

    tools = read_toml(ROOT.joinpath("config/tool-versions.toml"))
    if tools.get("zsasa", {}).get("tag") != "v0.6.0":
        fail("tool-versions.toml must keep zsasa as the v0.6.0 compatibility alias")
    expected_zsasa_versions = {
        "zsasa_0_6_0": "v0.6.0",
        "zsasa_0_9_0": "v0.9.0",
    }
    for tool, expected_tag in expected_zsasa_versions.items():
        spec = tools.get(tool, {})
        if spec.get("tag") != expected_tag:
            fail(f"tool-versions.toml must define {tool} with tag {expected_tag}")
        expected_binary = f"zsasa-{expected_tag.removeprefix('v')}"
        if spec.get("binary") != expected_binary:
            fail(f"{tool} binary must use a versioned zsasa-* command name")
    expected_nix_path_bins = {
        "freesasa": "freesasa",
        "freesasa_batch": "freesasa_batch",
        "rustsasa": "rust-sasa",
        "lahuta": "lahuta",
    }
    pdbtools_spec = tools.get("pdbtools_jl", {})
    if pdbtools_spec.get("binary") != "julia":
        fail("pdbtools_jl binary must resolve through Julia in the Nix dev shell")
    if "single-file" not in pdbtools_spec.get("policy", ""):
        fail("pdbtools_jl policy must limit it to single-file benchmarks")

    for tool, expected_binary in expected_nix_path_bins.items():
        spec = tools.get(tool, {})
        if spec.get("binary") != expected_binary:
            fail(f"{tool} binary must resolve from the Nix dev shell PATH")
        if "pinned" not in spec.get("policy", ""):
            fail(f"{tool} policy must require pinned reruns")
        if "Nix" not in spec.get("policy", ""):
            fail(f"{tool} policy must require Nix-managed comparator builds")
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
    if dataset.get("id") != "UP000000625_83333_ECOLI_v6_pdb":
        fail("validation manifest must identify the E. coli dataset")
    dataset_catalog = read_toml(ROOT.joinpath("config/datasets.toml.example"))
    for dataset_id in [
        "ecoli_smoke_pdb",
        "UP000000625_83333_ECOLI_v6_pdb",
        "UP000000625_83333_ECOLI_v6_cif",
        "UP000005640_9606_HUMAN_v6_pdb",
        "UP000005640_9606_HUMAN_v6_cif",
        "swissprot_500k_pdb",
        "single_file_large_structure_sources",
        "single_file_large_structure_subset",
        "single_file_large_structure_mmcif_subset",
        "single_file_stratified_sample",
    ]:
        if "path" not in dataset_catalog.get(dataset_id, {}):
            fail(f"datasets example missing path for {dataset_id}")
    for dataset_id in ["5wvo_C_analysis", "6sup_A_analysis", "5vz0_A_protein"]:
        entry = dataset_catalog.get(dataset_id, {})
        if "xtc" not in entry or "pdb" not in entry:
            fail(f"datasets example missing trajectory paths for {dataset_id}")
    runs = validation.get("runs", [])
    expected_validation_points = [64, 128, 256, 512, 1024]
    if not any(
        run.get("algorithm") == "sr" and run.get("points") == expected_validation_points
        for run in runs
    ):
        fail("validation manifest must include power-of-two SR point counts through 1024")
    if not any(run.get("algorithm") == "lr" and 20 in run.get("points", []) for run in runs):
        fail("validation manifest must include LR 20-slice full rerun")

    smoke = read_toml(ROOT.joinpath("manifests/validation-ecoli-smoke.toml"))
    smoke_dataset = smoke.get("dataset", {})
    if smoke_dataset.get("id") != "ecoli_smoke_pdb":
        fail("smoke validation manifest must use the tracked E. coli smoke dataset")
    if smoke_dataset.get("expected_count") != 3:
        fail("smoke validation manifest must describe the three tracked structures")

    md_validation = read_toml(ROOT.joinpath("manifests/validation-md-5wvo.toml"))
    md_full = md_validation.get("full_rerun", {})
    if md_full.get("tools") != ["mdtraj", "zsasa_mdtraj", "zsasa_mdanalysis", "zig", "zig_bitmask"]:
        fail("MD validation full_rerun must include mdtraj, zsasa wrappers, and CLI tools")
    if md_full.get("n_points") != expected_validation_points:
        fail("MD validation must use power-of-two point counts through 1024")
    if md_full.get("classifier") != "naccess" or md_full.get("include_hydrogens") is not True:
        fail("MD validation full_rerun must use naccess with explicit hydrogens")

    trajectory = read_toml(ROOT.joinpath("manifests/trajectory.toml"))
    trajectory_full = trajectory.get("full_rerun", {})
    if any(
        tool in trajectory_full.get("default_tools", [])
        for tool in ["mdtraj", "mdsasa_bolt"]
    ):
        fail("zsasa 0.9 trajectory refresh must reuse unchanged comparator results")
    if trajectory_full.get("zsasa_tool") != "zsasa_0_9_0":
        fail("trajectory full_rerun must use zsasa 0.9.0")
    if trajectory_full.get("cli_bitmask_variants") != [
        "single",
        "single_corrected",
        "per_frame",
        "cycle",
        "cycle_corrected",
    ]:
        fail("trajectory full_rerun must cover bitmask LUT and correction variants")
    if len(trajectory.get("datasets", [])) != 3:
        fail("trajectory manifest must describe the three benchmark datasets")

    swissprot = read_toml(ROOT.joinpath("manifests/batch-swissprot-version-refresh.toml"))
    swissprot_full = swissprot.get("full_rerun", {})
    if swissprot.get("dataset", {}).get("id") != "swissprot_500k_pdb":
        fail("SwissProt version-refresh manifest must use swissprot_500k_pdb")
    if swissprot_full.get("runs") != 1 or swissprot_full.get("threads") != [10]:
        fail("SwissProt version-refresh manifest must use one 10-thread measured run")
    if swissprot_full.get("precisions") != ["f32"]:
        fail("SwissProt version-refresh manifest must use f32 only")
    jobs = swissprot_full.get("jobs", [])
    expected_jobs = [
        {
            "tool": "zsasa_0_6_0",
            "threads": [10],
            "precisions": ["f32"],
            "modes": ["standard", "bitmask"],
        },
        {
            "tool": "zsasa_0_9_0",
            "threads": [10, 20, 40],
            "precisions": ["f32"],
            "modes": ["standard", "bitmask"],
        },
        {"tool": "lahuta", "threads": [10], "modes": ["bitmask"]},
    ]
    if jobs != expected_jobs:
        fail(
            "SwissProt version-refresh jobs must encode 0.6.0 10t, "
            "0.9.0 10/20/40t, and Lahuta bitmask 10t"
        )

    for manifest_name, dataset_id in [
        ("batch-ecoli-zsasa-0.9.toml", "UP000000625_83333_ECOLI_v6_pdb"),
        ("batch-human-zsasa-0.9.toml", "UP000005640_9606_HUMAN_v6_pdb"),
    ]:
        pdb_refresh = read_toml(ROOT.joinpath("manifests", manifest_name))
        pdb_full = pdb_refresh.get("full_rerun", {})
        if pdb_refresh.get("dataset", {}).get("id") != dataset_id:
            fail(f"{manifest_name} must use {dataset_id}")
        expected_threads = (
            [1, 4, 8, 10, 20, 40]
            if manifest_name == "batch-ecoli-zsasa-0.9.toml"
            else [10, 20, 40]
        )
        expected_pdb_jobs = [
            {
                "tool": "zsasa_0_9_0",
                "threads": expected_threads,
                "precisions": ["f64", "f32"],
                "modes": ["standard", "bitmask"],
            }
        ]
        if pdb_full.get("threads") != expected_threads or pdb_full.get("jobs") != expected_pdb_jobs:
            fail(f"{manifest_name} must encode the expected zsasa 0.9.0 thread matrix")

    human_cif = read_toml(ROOT.joinpath("manifests/batch-human-cif-zsasa-0.9.toml"))
    human_cif_full = human_cif.get("full_rerun", {})
    if human_cif_full.get("runs") != 3 or human_cif_full.get("warmup") != 1:
        fail("Human CIF benchmark must use three measured runs and one warmup")
    if human_cif_full.get("jsonl_decimals") != 3:
        fail("Human CIF benchmark must use three-decimal JSONL output")
    human_cif_jobs = human_cif_full.get("jobs", [])
    expected_human_cif_jobs = [
        {
            "tool": "zsasa_0_9_0",
            "variant": "generic_read",
            "threads": [10, 20, 40],
            "precisions": ["f32"],
            "modes": ["bitmask"],
            "af_model_fast": False,
            "input_io": "read",
        },
        {
            "tool": "zsasa_0_9_0",
            "variant": "af_fast_read",
            "threads": [10, 20, 40],
            "precisions": ["f32"],
            "modes": ["bitmask"],
            "af_model_fast": True,
            "input_io": "read",
        },
        {
            "tool": "zsasa_0_9_0",
            "variant": "generic_mmap",
            "threads": [20],
            "precisions": ["f32"],
            "modes": ["bitmask"],
            "af_model_fast": False,
            "input_io": "mmap",
        },
        {
            "tool": "zsasa_0_9_0",
            "variant": "af_fast_mmap",
            "threads": [20],
            "precisions": ["f32"],
            "modes": ["bitmask"],
            "af_model_fast": True,
            "input_io": "mmap",
        },
        {
            "tool": "lahuta",
            "threads": [10],
            "precisions": ["f32"],
            "modes": ["bitmask"],
        },
    ]
    if human_cif_jobs != expected_human_cif_jobs:
        fail("Human CIF jobs must encode the parser/I/O matrix plus Lahuta 10t")

    single_pdb = read_toml(ROOT.joinpath("manifests/single-file-sample.toml"))
    expected_pdb_tools = {
        "zsasa_0_9_0_f64",
        "zsasa_0_9_0_f32",
        "zsasa_0_9_0_f64_bitmask",
        "zsasa_0_9_0_f32_bitmask",
        "pdbtools_jl",
    }
    if set(single_pdb.get("full_rerun", {}).get("tools", [])) != expected_pdb_tools:
        fail("PDB single-file manifest must refresh zsasa 0.9.0 with PDBTools.jl")

    single_mmcif = read_toml(ROOT.joinpath("manifests/single-file-mmcif-sample.toml"))
    if single_mmcif.get("dataset", {}).get("id") != "single_file_large_structure_mmcif_subset":
        fail("mmCIF single-file manifest must use single_file_large_structure_mmcif_subset")
    if not all("input_file" in item for item in single_mmcif.get("structures", [])):
        fail("mmCIF single-file structures must specify input_file")
    if len(single_mmcif.get("structures", [])) != 8:
        fail("mmCIF single-file manifest must mirror all eight PDB subset structures")
    expected_mmcif_tools = {
        "zsasa_0_9_0_f64",
        "zsasa_0_9_0_f32",
        "zsasa_0_9_0_f64_bitmask",
        "zsasa_0_9_0_f32_bitmask",
        "freesasa",
        "rustsasa",
        "pdbtools_jl",
    }
    if set(single_mmcif.get("full_rerun", {}).get("tools", [])) != expected_mmcif_tools:
        fail("mmCIF single-file manifest must mirror the PDB tool matrix using zsasa 0.9.0")

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
    if "variant VARCHAR" not in schema:
        fail("benchmark_runs schema must include the implementation variant")

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
