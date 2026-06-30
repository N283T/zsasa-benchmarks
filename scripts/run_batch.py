#!/usr/bin/env python3
"""Native directory batch throughput dry-run runner."""

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
from scripts.benchlib.hyperfine import hyperfine_command  # noqa: E402
from scripts.benchlib.manifest import expect_dict, load_manifest  # noqa: E402
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    filter_records,
    run_records,
    shell_join,
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
    legacy_refresh = manifest.get("refresh") or manifest.get("planned_refresh") or {}
    if isinstance(legacy_refresh, dict):
        for key in ["n_points", "threads", "runs", "warmup", "precisions", "prepare"]:
            if key in legacy_refresh:
                full_rerun.setdefault(key, legacy_refresh[key])
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault("n_points", 128)
    full_rerun.setdefault("threads", [10])
    full_rerun.setdefault("runs", 3)
    full_rerun.setdefault("warmup", 3)
    full_rerun.setdefault("precisions", ["f64", "f32"])
    full_rerun.setdefault("modes", ["standard", "bitmask"])
    full_rerun.setdefault("prepare", "sync")
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def dataset_name(manifest_path: Path, manifest: dict[str, Any]) -> str:
    dataset = expect_dict(manifest, "dataset")
    dataset_id = str(dataset.get("id", "")).lower()
    manifest_stem = manifest_path.stem.lower()
    if ("ecoli" in dataset_id or "ecoli" in manifest_stem) and (
        dataset_id.endswith("_cif") or "cif" in manifest_stem
    ):
        return "ecoli_cif"
    if ("human" in dataset_id or "human" in manifest_stem) and (
        dataset_id.endswith("_cif") or "cif" in manifest_stem
    ):
        return "human_cif"
    if "ecoli" in dataset_id or "ecoli" in manifest_stem:
        return "ecoli"
    if "human" in dataset_id or "human" in manifest_stem:
        return "human"
    if "swissprot" in dataset_id or "swissprot" in manifest_stem:
        return "swissprot"
    return manifest_stem.removeprefix("batch-")


def is_zsasa_tool(tool_id: str) -> bool:
    return tool_id == "zsasa" or tool_id.startswith("zsasa_")


def zsasa_batch_record_name(
    *, tool_id: str, precision: str, mode: str, threads: int, n_points: int
) -> str:
    suffix = f"batch_{precision}_{mode}_{threads}t_{n_points}p"
    if tool_id == "zsasa":
        return f"zsasa_{suffix}"
    return f"{tool_id}_{suffix}"


def default_batch_tools(settings: dict[str, Any]) -> list[str]:
    tools = [str(tool) for tool in settings.get("tools", [])]
    if tools:
        return tools
    if settings.get("rerun_zsasa", True):
        tools.append("zsasa")
    if settings.get("rerun_comparators", True):
        tools.extend(["freesasa_batch", "rustsasa", "lahuta"])
    return tools


def batch_jobs(settings: dict[str, Any]) -> list[dict[str, Any]]:
    raw_jobs = settings.get("jobs", [])
    if raw_jobs:
        if not isinstance(raw_jobs, list):
            raise ValueError("full_rerun.jobs must be an array of TOML tables")
        jobs: list[dict[str, Any]] = []
        for raw_job in raw_jobs:
            if not isinstance(raw_job, dict):
                raise ValueError("full_rerun.jobs entries must be TOML tables")
            tool = str(raw_job["tool"])
            jobs.append(
                {
                    "tool": tool,
                    "threads": [
                        int(value) for value in raw_job.get("threads", settings["threads"])
                    ],
                    "precisions": [
                        str(value) for value in raw_job.get("precisions", settings["precisions"])
                    ],
                    "modes": [str(value) for value in raw_job.get("modes", settings["modes"])],
                }
            )
        return jobs

    return [
        {
            "tool": tool,
            "threads": [int(value) for value in settings["threads"]],
            "precisions": [str(value) for value in settings["precisions"]],
            "modes": [str(value) for value in settings["modes"]],
        }
        for tool in default_batch_tools(settings)
    ]


def rustsasa_batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    n_points: int,
    threads: int,
) -> list[str]:
    """Plan the RustSASA directory invocation used by batch benchmarks."""
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


def build_native_records(
    *,
    specs: dict[str, ToolSpec],
    input_dir: Path,
    output_base: Path,
    settings: dict[str, Any],
) -> list[CommandRecord]:
    records: list[CommandRecord] = []
    n_points = int(settings["n_points"])
    runs = int(settings["runs"])
    warmup = int(settings["warmup"])
    prepare = str(settings["prepare"]) if settings.get("prepare") else None

    for job in batch_jobs(settings):
        tool_id = str(job["tool"])
        threads = [int(thread) for thread in job["threads"]]
        modes = [str(mode) for mode in job["modes"]]
        precisions = [str(precision) for precision in job["precisions"]]

        if is_zsasa_tool(tool_id):
            zsasa = require_binary(specs, tool_id)
            for thread in threads:
                for precision in precisions:
                    for mode in modes:
                        if mode not in {"standard", "bitmask"}:
                            raise ValueError(f"unsupported zsasa batch mode: {mode}")
                        bitmask = mode == "bitmask"
                        name = zsasa_batch_record_name(
                            tool_id=tool_id,
                            precision=precision,
                            mode=mode,
                            threads=thread,
                            n_points=n_points,
                        )
                        native = batch_command(
                            binary=zsasa,
                            input_dir=input_dir,
                            output_jsonl=output_base.joinpath(
                                tool_id, f"{precision}_{mode}_{thread}t_{n_points}p.jsonl"
                            ),
                            precision=precision,
                            n_points=n_points,
                            threads=thread,
                            bitmask=bitmask,
                        )
                        records.append(
                            CommandRecord(
                                name=name,
                                outputs=[
                                    output_base.joinpath(
                                        tool_id,
                                        f"{precision}_{mode}_{thread}t_{n_points}p.jsonl",
                                    ),
                                    output_base.joinpath("hyperfine", f"{name}.json"),
                                ],
                                argv=hyperfine_command(
                                    name=name,
                                    command=shell_join(native),
                                    output_json=output_base.joinpath("hyperfine", f"{name}.json"),
                                    warmup=warmup,
                                    runs=runs,
                                    prepare=prepare,
                                ),
                            )
                        )
            continue

        binary = require_binary(specs, tool_id)
        for thread in threads:
            comparator_commands: list[tuple[str, list[str]]] = []
            if tool_id == "freesasa_batch":
                comparator_commands.append(
                    (
                        f"freesasa_batch_{thread}t_{n_points}p",
                        freesasa_batch_command(
                            binary=binary,
                            input_dir=input_dir,
                            output_dir=output_base.joinpath(
                                "freesasa_batch", f"{thread}t_{n_points}p"
                            ),
                            n_points=n_points,
                            threads=thread,
                        ),
                    )
                )
            elif tool_id == "rustsasa":
                comparator_commands.append(
                    (
                        f"rustsasa_{thread}t_{n_points}p",
                        rustsasa_batch_command(
                            binary=binary,
                            input_dir=input_dir,
                            output_dir=output_base.joinpath("rustsasa", f"{thread}t_{n_points}p"),
                            n_points=n_points,
                            threads=thread,
                        ),
                    )
                )
            elif tool_id == "lahuta":
                for mode in modes:
                    if mode not in {"standard", "bitmask"}:
                        raise ValueError(f"unsupported Lahuta batch mode: {mode}")
                    bitmask = mode == "bitmask"
                    comparator_commands.append(
                        (
                            f"lahuta_{mode}_{thread}t_{n_points}p",
                            lahuta_batch_command(
                                binary=binary,
                                input_dir=input_dir,
                                output_dir=output_base.joinpath(
                                    "lahuta", f"{mode}_{thread}t_{n_points}p"
                                ),
                                n_points=n_points,
                                threads=thread,
                                bitmask=bitmask,
                            ),
                        )
                    )
            else:
                raise ValueError(f"unsupported batch tool: {tool_id}")

            for name, native in comparator_commands:
                output_stem = name.removeprefix("lahuta_")
                lahuta_outputs = [
                    output_base.joinpath("lahuta", output_stem),
                    output_base.joinpath("lahuta", f"{output_stem}.jsonl"),
                ]
                native_outputs = {
                    "freesasa_batch": [
                        output_base.joinpath("freesasa_batch", f"{thread}t_{n_points}p")
                    ],
                    "rustsasa": [output_base.joinpath("rustsasa", f"{thread}t_{n_points}p")],
                    "lahuta": lahuta_outputs,
                }
                tool_outputs = next(
                    outputs for prefix, outputs in native_outputs.items() if name.startswith(prefix)
                )
                records.append(
                    CommandRecord(
                        name=name,
                        outputs=[*tool_outputs, output_base.joinpath("hyperfine", f"{name}.json")],
                        argv=hyperfine_command(
                            name=name,
                            command=shell_join(native),
                            output_json=output_base.joinpath("hyperfine", f"{name}.json"),
                            warmup=warmup,
                            runs=runs,
                            prepare=prepare,
                        ),
                    )
                )
    return records


def prepare_output_directories(*, output_base: Path, settings: dict[str, Any]) -> None:
    n_points = int(settings["n_points"])
    directories = [output_base, output_base.joinpath("hyperfine")]

    for job in batch_jobs(settings):
        tool_id = str(job["tool"])
        threads = [int(thread) for thread in job["threads"]]
        modes = [str(mode) for mode in job["modes"]]
        if is_zsasa_tool(tool_id):
            directories.append(output_base.joinpath(tool_id))
        elif tool_id in {"freesasa_batch", "rustsasa"}:
            for thread in threads:
                directories.append(output_base.joinpath(tool_id, f"{thread}t_{n_points}p"))
        elif tool_id == "lahuta":
            for thread in threads:
                for mode in modes:
                    directories.append(
                        output_base.joinpath("lahuta", f"{mode}_{thread}t_{n_points}p")
                    )
        else:
            raise ValueError(f"unsupported batch tool: {tool_id}")

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    specs = load_tool_specs(args.tool_versions)
    dataset_catalog = load_dataset_catalog(args.datasets)
    settings = full_rerun_settings(manifest)
    dataset = expect_dict(manifest, "dataset")
    name = dataset_name(manifest_path, manifest)
    input_dir = dataset_path(dataset_catalog, str(dataset["id"]), "path")
    output_base = full_rerun_dir(args.run_id, "batch", name)

    records = build_native_records(
        specs=specs,
        input_dir=input_dir,
        output_base=output_base,
        settings=settings,
    )
    prepare_output_directories(output_base=output_base, settings=settings)
    selected_records = filter_records(records, only=args.only, exclude=args.exclude)

    write_command_log(output_base.joinpath("commands.log"), selected_records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": settings["source_kind"],
            "dataset_name": name,
            "input_dir": str(input_dir),
            "output_base": str(output_base),
            "n_points": settings["n_points"],
            "threads": settings["threads"],
            "precisions": settings["precisions"],
            "modes": settings["modes"],
            "jobs": settings.get("jobs", []),
            "tool_versions": str(resolve_repo_path(args.tool_versions)),
            "datasets": str(resolve_repo_path(args.datasets)),
            "only": list(args.only),
            "exclude": list(args.exclude),
            "replace": bool(args.replace),
            "commands": [record.name for record in selected_records],
            "rustsasa_note": (
                "RustSASA batch command is a dry-run plan for the pinned comparator invocation."
            ),
        },
    )

    print(f"source_kind={settings['source_kind']}")
    print(f"run_id={args.run_id}")
    print(f"dataset={name}")
    print(f"input_dir={input_dir}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    print(f"selected_commands={len(selected_records)}/{len(records)}")
    run_records(selected_records, execute=not args.dry_run, replace=bool(args.replace))


if __name__ == "__main__":
    main()
