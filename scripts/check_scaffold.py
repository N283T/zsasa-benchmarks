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
    "scripts/check_scaffold.py",
    "scripts/report_existing_assets.py",
    "scripts/refresh_validation.py",
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

    print("benchmark scaffold checks passed")


if __name__ == "__main__":
    main()
