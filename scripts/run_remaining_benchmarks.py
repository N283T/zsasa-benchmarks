#!/usr/bin/env python3
"""Run the remaining non-validation benchmark suites in sequence."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "nix_full_20260524"
DEFAULT_DATASETS = (
    Path("config/datasets.local.toml")
    if ROOT.joinpath("config/datasets.local.toml").exists()
    else Path("config/datasets.toml.example")
)


@dataclass(frozen=True)
class Step:
    name: str
    argv: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS)
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
    parser.add_argument("--db", type=Path, default=Path("results/benchmark.duckdb"))
    parser.add_argument(
        "--import-db",
        action="store_true",
        help="import validation plus remaining benchmark outputs into DuckDB after running stages",
    )
    parser.add_argument(
        "--validation-run-id",
        default=None,
        help="run-id containing validation outputs for --import-db; defaults to --run-id",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="pass --reset to scripts/import_full_rerun.py when --import-db is set",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute benchmarks; default is to dry-run each underlying runner",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="pass --replace to benchmark runners before execution",
    )
    parser.add_argument(
        "--stage",
        action="append",
        choices=["prepare-single-file", "batch-ecoli", "batch-human", "md", "single-file"],
        help="run only selected stage(s); repeatable. Default: all stages.",
    )
    parser.add_argument(
        "--skip-prepare-single-file",
        action="store_true",
        help="skip preparing single-file PDB inputs before the single-file benchmark",
    )
    parser.add_argument("--no-nix", action="store_true", help="do not auto-enter nix develop")
    return parser.parse_args()


def maybe_reexec_in_nix(args: argparse.Namespace) -> None:
    if args.no_nix or os.environ.get("IN_NIX_SHELL"):
        return
    if shutil.which("nix") is None:
        print("WARNING: nix not found; continuing in the current environment", file=sys.stderr)
        return
    os.execvp(
        "nix",
        [
            "nix",
            "develop",
            str(ROOT),
            "--command",
            "uv",
            "run",
            "python",
            str(Path(__file__).resolve()),
            *sys.argv[1:],
            "--no-nix",
        ],
    )


def runner_mode_args(args: argparse.Namespace) -> list[str]:
    mode = ["--execute"] if args.execute else ["--dry-run"]
    if args.replace:
        mode.append("--replace")
    return mode


def build_steps(args: argparse.Namespace) -> list[Step]:
    datasets = str(args.datasets)
    tool_versions = str(args.tool_versions)
    run_id = args.run_id
    mode = runner_mode_args(args)
    selected = set(args.stage or [])
    run_all = not selected

    steps = [
        Step(
            "prepare-single-file",
            [
                "uv",
                "run",
                "python",
                "scripts/prepare_single_file_structures.py",
                "--manifest",
                "manifests/single-file-sample.toml",
                "--datasets",
                datasets,
                *(["--execute"] if args.execute else ["--dry-run"]),
            ],
        ),
        Step(
            "batch-ecoli",
            [
                "uv",
                "run",
                "python",
                "scripts/run_batch.py",
                "--manifest",
                "manifests/batch-ecoli.toml",
                "--datasets",
                datasets,
                "--tool-versions",
                tool_versions,
                "--run-id",
                run_id,
                *mode,
            ],
        ),
        Step(
            "batch-human",
            [
                "uv",
                "run",
                "python",
                "scripts/run_batch.py",
                "--manifest",
                "manifests/batch-human.toml",
                "--datasets",
                datasets,
                "--tool-versions",
                tool_versions,
                "--run-id",
                run_id,
                *mode,
            ],
        ),
        Step(
            "md",
            [
                "uv",
                "run",
                "python",
                "scripts/run_trajectory.py",
                "--manifest",
                "manifests/trajectory.toml",
                "--datasets",
                datasets,
                "--tool-versions",
                tool_versions,
                "--run-id",
                run_id,
                *mode,
            ],
        ),
        Step(
            "single-file",
            [
                "uv",
                "run",
                "python",
                "scripts/run_single_file.py",
                "--manifest",
                "manifests/single-file-sample.toml",
                "--datasets",
                datasets,
                "--tool-versions",
                tool_versions,
                "--run-id",
                run_id,
                *mode,
            ],
        ),
    ]

    filtered: list[Step] = []
    for step in steps:
        if step.name == "prepare-single-file" and args.skip_prepare_single_file:
            continue
        if run_all or step.name in selected:
            filtered.append(step)
    return filtered


def run_step(step: Step) -> None:
    print(f"\n==> {step.name}", flush=True)
    print("+ " + subprocess.list2cmdline(step.argv), flush=True)
    subprocess.run(step.argv, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    maybe_reexec_in_nix(args)
    steps = build_steps(args)
    if not steps:
        raise SystemExit("no stages selected")
    print(f"run_id={args.run_id}")
    print(f"datasets={args.datasets}")
    print(f"mode={'execute' if args.execute else 'dry-run'}")
    print("stages=" + ",".join(step.name for step in steps))
    for step in steps:
        run_step(step)
    if args.import_db:
        validation_run_id = args.validation_run_id or args.run_id
        import_argv = [
            "uv",
            "run",
            "python",
            "scripts/import_full_rerun.py",
            "--db",
            str(args.db),
            "--run-id",
            args.run_id,
            "--validation-run-id",
            validation_run_id,
            "--datasets",
            str(args.datasets),
        ]
        if args.reset_db:
            import_argv.append("--reset")
        run_step(Step("import-db", import_argv))


if __name__ == "__main__":
    main()
