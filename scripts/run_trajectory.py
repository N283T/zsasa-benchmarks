#!/usr/bin/env python3
"""Native trajectory throughput dry-run runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.commands import mdtraj_runner_command  # noqa: E402
from scripts.benchlib.datasets import (  # noqa: E402
    DEFAULT_DATASETS_CONFIG,
    dataset_path,
    load_dataset_catalog,
)
from scripts.benchlib.hyperfine import hyperfine_command  # noqa: E402
from scripts.benchlib.manifest import (  # noqa: E402
    expect_list,
    load_manifest,
    require_native_full_rerun_flags,
)
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    filter_records,
    run_records,
    shell_join,
    write_command_log,
    write_config,
)
from scripts.benchlib.tools import load_tool_specs, resolve_tool_binary  # noqa: E402

DEFAULT_RUN_ID = "v0_6_0_full"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
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


def full_rerun_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    full_rerun = dict(manifest.get("full_rerun", {}))
    refresh = manifest.get("refresh", {})
    if isinstance(refresh, dict):
        inherited_keys = [
            "default_tools",
            "large_trajectory_tools",
            "n_points",
            "stride",
            "runs",
            "warmup",
            "prepare",
            "cli_precisions",
        ]
        for key in inherited_keys:
            if key in refresh:
                full_rerun.setdefault(key, refresh[key])
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault(
        "default_tools",
        [
            "zig",
            "zig_bitmask",
            "zsasa_mdtraj",
            "zsasa_mdtraj_bitmask",
            "zsasa_mdanalysis",
            "zsasa_mdanalysis_bitmask",
            "mdtraj",
            "mdsasa_bolt",
        ],
    )
    full_rerun.setdefault("large_trajectory_tools", ["zig", "zig_bitmask", "mdsasa_bolt"])
    full_rerun.setdefault("n_points", 100)
    full_rerun.setdefault("stride", 1)
    full_rerun.setdefault("threads", [10])
    full_rerun.setdefault("cli_precisions", ["f64", "f32"])
    full_rerun.setdefault("classifier", "naccess")
    full_rerun.setdefault("include_hydrogens", True)
    full_rerun.setdefault("runs", 3)
    full_rerun.setdefault("warmup", 1)
    full_rerun.setdefault("prepare", "sync")
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def require_zsasa_binary(tool_versions: Path) -> Path:
    specs = load_tool_specs(tool_versions)
    spec = specs.get("zsasa")
    if spec is None or spec.binary is None:
        return resolve_tool_binary("zsasa", Path("zsasa"))
    return resolve_tool_binary("zsasa", spec.binary)


def tools_for_dataset(dataset: dict[str, Any], settings: dict[str, Any]) -> list[str]:
    dataset_id = str(dataset.get("id", ""))
    frames = int(dataset.get("frames", 0))
    if dataset_id == "5vz0_A_protein" or frames > 5000:
        return [str(value) for value in settings["large_trajectory_tools"]]
    return [str(value) for value in settings["default_tools"]]


def threads_for_dataset(dataset: dict[str, Any], settings: dict[str, Any]) -> list[int]:
    raw_threads = settings.get("threads", dataset.get("refresh_threads", [10]))
    if isinstance(raw_threads, int):
        return [raw_threads]
    return [int(value) for value in raw_threads]


def command_variants(
    *, tool: str, dataset: dict[str, Any], n_points: int, settings: dict[str, Any]
) -> list[dict[str, Any]]:
    threads = threads_for_dataset(dataset, settings)
    if tool in {"zig", "zig_bitmask"}:
        return [
            {
                "name_parts": [tool, str(precision), f"{thread}t", f"{n_points}p"],
                "tool": tool,
                "precision": str(precision),
                "threads": thread,
                "raw_parts": [str(dataset["id"]), tool, str(precision)],
            }
            for thread in threads
            for precision in settings["cli_precisions"]
        ]
    if tool.startswith("zsasa_"):
        return [
            {
                "name_parts": [tool, f"{thread}t", f"{n_points}p"],
                "tool": tool,
                "precision": None,
                "threads": thread,
                "raw_parts": [str(dataset["id"]), tool],
            }
            for thread in threads
        ]
    return [
        {
            "name_parts": [tool, f"{n_points}p"],
            "tool": tool,
            "precision": None,
            "threads": threads[0],
            "raw_parts": [str(dataset["id"]), tool],
        }
    ]


def build_records(
    *,
    datasets: list[Any],
    dataset_catalog: dict[str, dict[str, Any]],
    output_base: Path,
    settings: dict[str, Any],
    zsasa_binary: Path,
) -> list[CommandRecord]:
    records: list[CommandRecord] = []
    n_points = int(settings["n_points"])
    stride = int(settings["stride"])
    runs = int(settings["runs"])
    warmup = int(settings["warmup"])
    prepare = str(settings["prepare"]) if settings.get("prepare") else None

    output_base.joinpath("hyperfine").mkdir(parents=True, exist_ok=True)
    for raw_dataset in datasets:
        if not isinstance(raw_dataset, dict):
            continue
        dataset_id = str(raw_dataset["id"])
        xtc = dataset_path(dataset_catalog, dataset_id, "xtc")
        pdb = dataset_path(dataset_catalog, dataset_id, "pdb")
        for tool in tools_for_dataset(raw_dataset, settings):
            for variant in command_variants(
                tool=tool, dataset=raw_dataset, n_points=n_points, settings=settings
            ):
                raw_dir = output_base.joinpath("raw", *variant["raw_parts"])
                raw_dir.mkdir(parents=True, exist_ok=True)
                native = mdtraj_runner_command(
                    tool=str(variant["tool"]),
                    xtc=xtc,
                    pdb=pdb,
                    n_points=n_points,
                    stride=stride,
                    output=raw_dir.joinpath("results.json"),
                    threads=int(variant["threads"]),
                    precision=variant["precision"],
                    classifier=str(settings["classifier"]),
                    include_hydrogens=bool(settings["include_hydrogens"]),
                    zsasa_binary=zsasa_binary,
                )
                name = "_".join([dataset_id, *[str(part) for part in variant["name_parts"]]])
                records.append(
                    CommandRecord(
                        name=name,
                        outputs=[
                            raw_dir.joinpath("results.json"),
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
    return records


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    datasets = expect_list(manifest, "datasets")
    dataset_catalog = load_dataset_catalog(args.datasets)
    settings = full_rerun_settings(manifest)
    require_native_full_rerun_flags(settings, runner="scripts/run_trajectory.py")
    zsasa_binary = require_zsasa_binary(resolve_repo_path(args.tool_versions))
    output_base = full_rerun_dir(args.run_id, "md")
    output_base.mkdir(parents=True, exist_ok=True)

    records = build_records(
        datasets=datasets,
        dataset_catalog=dataset_catalog,
        output_base=output_base,
        settings=settings,
        zsasa_binary=zsasa_binary,
    )
    selected_records = filter_records(records, only=args.only, exclude=args.exclude)
    dataset_ids = [str(dataset["id"]) for dataset in datasets if isinstance(dataset, dict)]
    write_command_log(output_base.joinpath("commands.log"), selected_records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": settings["source_kind"],
            "dataset_ids": dataset_ids,
            "output_base": str(output_base),
            "datasets": str(resolve_repo_path(args.datasets)),
            "default_tools": [str(value) for value in settings["default_tools"]],
            "large_trajectory_tools": [str(value) for value in settings["large_trajectory_tools"]],
            "n_points": int(settings["n_points"]),
            "stride": int(settings["stride"]),
            "threads": [int(value) for value in settings["threads"]],
            "cli_precisions": [str(value) for value in settings["cli_precisions"]],
            "classifier": str(settings["classifier"]),
            "include_hydrogens": bool(settings["include_hydrogens"]),
            "runs": int(settings["runs"]),
            "warmup": int(settings["warmup"]),
            "prepare": settings.get("prepare"),
            "zsasa_binary": str(zsasa_binary),
            "only": list(args.only),
            "exclude": list(args.exclude),
            "replace": bool(args.replace),
            "commands": [record.name for record in selected_records],
        },
    )

    print(f"source_kind={settings['source_kind']}")
    print(f"run_id={args.run_id}")
    print(f"datasets={','.join(dataset_ids)}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    print(f"selected_commands={len(selected_records)}/{len(records)}")
    run_records(selected_records, execute=not args.dry_run, replace=bool(args.replace))


if __name__ == "__main__":
    main()
