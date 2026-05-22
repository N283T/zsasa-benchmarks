#!/usr/bin/env python3
"""Native static validation dry-run runner for the E. coli full rerun."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.commands import (  # noqa: E402
    batch_command,
    freesasa_batch_command,
    lahuta_batch_command,
)
from scripts.benchlib.datasets import (  # noqa: E402
    DEFAULT_DATASETS_CONFIG,
    dataset_path,
    load_dataset_catalog,
)
from scripts.benchlib.manifest import (  # noqa: E402
    expect_dict,
    expect_list,
    load_manifest,
    require_native_full_rerun_flags,
)
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    filter_records,
    run_records,
    write_command_log,
    write_config,
)
from scripts.benchlib.tools import (  # noqa: E402
    ToolError,
    ToolSpec,
    load_tool_specs,
    resolve_tool_binary,
)

DEFAULT_RUN_ID = "v0_6_0_full"
DEFAULT_TOOL_VERSIONS = Path("config/tool-versions.toml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--tool-versions", type=Path, default=DEFAULT_TOOL_VERSIONS)
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS_CONFIG)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="print and record commands without running them (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_false",
        dest="dry_run",
        help="execute commands instead of only printing the plan",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="GLOB",
        help="run only command records whose names match this glob; repeatable",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip command records whose names match this glob; repeatable",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="remove selected command outputs before running; dry-runs only print removals",
    )
    return parser.parse_args()


def require_binary(specs: dict[str, ToolSpec], tool_id: str) -> Path:
    spec = specs.get(tool_id)
    if spec is None:
        raise ToolError(f"unknown tool: {tool_id}")
    if spec.binary is None:
        raise ToolError(f"missing binary for tool: {tool_id}")
    if tool_id == "zsasa":
        return resolve_tool_binary(tool_id, spec.binary)
    return spec.binary


def full_rerun_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    full_rerun = dict(manifest.get("full_rerun", {}))
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault("threads", 10)
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def validation_dataset_name(manifest: dict[str, Any]) -> str:
    dataset = expect_dict(manifest, "dataset")
    dataset_id = str(dataset.get("id", "")).lower()
    if dataset_id == "ecoli_smoke_pdb":
        return "ecoli_smoke"
    if "ecoli" in dataset_id:
        return "ecoli"
    return dataset_id.replace("-", "_")


def zsasa_lr_batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_jsonl: Path,
    precision: str,
    n_slices: int,
    threads: int,
) -> list[str]:
    return [
        str(binary),
        "batch",
        str(input_dir),
        "--format=jsonl",
        "-o",
        str(output_jsonl),
        f"--threads={threads}",
        f"--precision={precision}",
        "--algorithm=lr",
        f"--n-slices={n_slices}",
    ]


def rustsasa_validation_command(
    *,
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    n_points: int,
    threads: int,
) -> list[str]:
    return [
        str(binary),
        str(input_dir),
        str(output_dir),
        "-n",
        str(n_points),
        "-f",
        "json",
        "-t",
        str(threads),
        "-o",
        "protein",
        "--allow-vdw-fallback",
    ]


def sr_records(
    *,
    zsasa: Path,
    freesasa_batch: Path,
    lahuta: Path,
    rustsasa: Path,
    input_dir: Path,
    output_base: Path,
    points: list[int],
    threads: int,
) -> list[CommandRecord]:
    records: list[CommandRecord] = []
    for n_points in points:
        for precision in ["f64", "f32"]:
            for bitmask in [False, True]:
                suffix = "bitmask" if bitmask else "standard"
                records.append(
                    CommandRecord(
                        name=f"zsasa_sr_{precision}_{suffix}_{n_points}",
                        outputs=[
                            output_base.joinpath(
                                "zsasa", f"sr_{precision}_{suffix}_{n_points}.jsonl"
                            )
                        ],
                        argv=batch_command(
                            binary=zsasa,
                            input_dir=input_dir,
                            output_jsonl=output_base.joinpath(
                                "zsasa", f"sr_{precision}_{suffix}_{n_points}.jsonl"
                            ),
                            precision=precision,
                            n_points=n_points,
                            threads=threads,
                            bitmask=bitmask,
                        ),
                    )
                )

        records.append(
            CommandRecord(
                name=f"freesasa_batch_sr_{n_points}",
                outputs=[output_base.joinpath("freesasa_batch", f"sr_{n_points}")],
                argv=freesasa_batch_command(
                    binary=freesasa_batch,
                    input_dir=input_dir,
                    output_dir=output_base.joinpath("freesasa_batch", f"sr_{n_points}"),
                    n_points=n_points,
                    threads=threads,
                ),
            )
        )
        records.append(
            CommandRecord(
                name=f"rustsasa_sr_{n_points}",
                outputs=[output_base.joinpath("rustsasa", f"sr_{n_points}")],
                argv=rustsasa_validation_command(
                    binary=rustsasa,
                    input_dir=input_dir,
                    output_dir=output_base.joinpath("rustsasa", f"sr_{n_points}"),
                    n_points=n_points,
                    threads=threads,
                ),
            )
        )
        for bitmask in [False, True]:
            suffix = "bitmask" if bitmask else "standard"
            records.append(
                CommandRecord(
                    name=f"lahuta_sr_{suffix}_{n_points}",
                    outputs=[
                        output_base.joinpath("lahuta", f"sr_{suffix}_{n_points}"),
                        output_base.joinpath("lahuta", f"sr_{suffix}_{n_points}.jsonl"),
                    ],
                    argv=lahuta_batch_command(
                        binary=lahuta,
                        input_dir=input_dir,
                        output_dir=output_base.joinpath("lahuta", f"sr_{suffix}_{n_points}"),
                        n_points=n_points,
                        threads=threads,
                        bitmask=bitmask,
                    ),
                )
            )
    return records


def lr_records(
    *,
    zsasa: Path,
    input_dir: Path,
    output_base: Path,
    slices: list[int],
    threads: int,
) -> list[CommandRecord]:
    records: list[CommandRecord] = []
    for n_slices in slices:
        for precision in ["f64", "f32"]:
            records.append(
                CommandRecord(
                    name=f"zsasa_lr_{precision}_{n_slices}",
                    outputs=[output_base.joinpath("zsasa", f"lr_{precision}_{n_slices}.jsonl")],
                    argv=zsasa_lr_batch_command(
                        binary=zsasa,
                        input_dir=input_dir,
                        output_jsonl=output_base.joinpath(
                            "zsasa", f"lr_{precision}_{n_slices}.jsonl"
                        ),
                        precision=precision,
                        n_slices=n_slices,
                        threads=threads,
                    ),
                )
            )
    return records


def build_records(
    *,
    manifest: dict[str, Any],
    specs: dict[str, ToolSpec],
    dataset_catalog: dict[str, dict[str, Any]],
    output_base: Path,
) -> list[CommandRecord]:
    dataset = expect_dict(manifest, "dataset")
    full_rerun = full_rerun_settings(manifest)
    input_dir = dataset_path(dataset_catalog, str(dataset["id"]), "path")
    threads = int(full_rerun["threads"])

    zsasa = require_binary(specs, "zsasa")
    freesasa_batch = require_binary(specs, "freesasa_batch")
    lahuta = require_binary(specs, "lahuta")
    rustsasa = require_binary(specs, "rustsasa")

    records: list[CommandRecord] = []
    for run in expect_list(manifest, "runs"):
        if not isinstance(run, dict):
            continue
        algorithm = str(run.get("algorithm", ""))
        if algorithm == "sr":
            records.extend(
                sr_records(
                    zsasa=zsasa,
                    freesasa_batch=freesasa_batch,
                    lahuta=lahuta,
                    rustsasa=rustsasa,
                    input_dir=input_dir,
                    output_base=output_base,
                    points=[int(point) for point in run.get("points", [])],
                    threads=threads,
                )
            )
        elif algorithm == "lr":
            records.extend(
                lr_records(
                    zsasa=zsasa,
                    input_dir=input_dir,
                    output_base=output_base,
                    slices=[int(point) for point in run.get("points", [])],
                    threads=threads,
                )
            )

    return records


def prepare_output_directories(*, manifest: dict[str, Any], output_base: Path) -> None:
    directories = [output_base, output_base.joinpath("zsasa")]

    for run in expect_list(manifest, "runs"):
        if not isinstance(run, dict):
            continue
        algorithm = str(run.get("algorithm", ""))
        if algorithm != "sr":
            continue
        for n_points in [int(point) for point in run.get("points", [])]:
            directories.extend(
                [
                    output_base.joinpath("freesasa_batch", f"sr_{n_points}"),
                    output_base.joinpath("rustsasa", f"sr_{n_points}"),
                    output_base.joinpath("lahuta", f"sr_standard_{n_points}"),
                    output_base.joinpath("lahuta", f"sr_bitmask_{n_points}"),
                ]
            )

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    specs = load_tool_specs(args.tool_versions)
    dataset_catalog = load_dataset_catalog(args.datasets)
    full_rerun = full_rerun_settings(manifest)
    require_native_full_rerun_flags(full_rerun, runner="scripts/run_validation.py")
    source_kind = str(full_rerun["source_kind"])
    output_base = full_rerun_dir(args.run_id, "validation", validation_dataset_name(manifest))

    records = build_records(
        manifest=manifest,
        specs=specs,
        dataset_catalog=dataset_catalog,
        output_base=output_base,
    )
    prepare_output_directories(manifest=manifest, output_base=output_base)
    selected_records = filter_records(records, only=args.only, exclude=args.exclude)

    write_command_log(output_base.joinpath("commands.log"), selected_records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": source_kind,
            "threads": full_rerun["threads"],
            "tool_versions": str(resolve_repo_path(args.tool_versions)),
            "datasets": str(resolve_repo_path(args.datasets)),
            "only": list(args.only),
            "exclude": list(args.exclude),
            "replace": bool(args.replace),
            "commands": [record.name for record in selected_records],
        },
    )

    print(f"source_kind={source_kind}")
    print(f"run_id={args.run_id}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    print(f"selected_commands={len(selected_records)}/{len(records)}")
    run_records(selected_records, execute=not args.dry_run, replace=bool(args.replace))


if __name__ == "__main__":
    main()
