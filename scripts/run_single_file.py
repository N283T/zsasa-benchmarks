#!/usr/bin/env python3
"""Native single-file large-structure benchmark runner."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.commands import (  # noqa: E402
    freesasa_single_command,
    rustsasa_single_command,
    zsasa_calc_command,
)
from scripts.benchlib.datasets import (  # noqa: E402
    DEFAULT_DATASETS_CONFIG,
    dataset_path,
    load_dataset_catalog,
)
from scripts.benchlib.hyperfine import hyperfine_command, parse_hyperfine_result  # noqa: E402
from scripts.benchlib.manifest import expect_dict, expect_list, load_manifest  # noqa: E402
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    filter_records,
    run_command,
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
DEFAULT_MANIFEST = Path("manifests/single-file-sample.toml")
DEFAULT_TOOL_VERSIONS = Path("config/tool-versions.toml")
TIMING_PATTERN = re.compile(r"^([A-Z_]+_TIME_MS):([0-9.]+)$")


@dataclass(frozen=True)
class ToolPlan:
    name: str
    tool_id: str
    precision: str | None = None
    bitmask: bool = False


@dataclass(frozen=True)
class StructurePlan:
    structure_id: str
    role: str
    expected_atoms: int | None
    pdb_path: Path


@dataclass(frozen=True)
class SingleFileRecord(CommandRecord):
    phase: str = ""
    tool: str = ""
    structure_id: str = ""
    role: str = ""
    expected_atoms: int | None = None
    threads: int = 0
    n_points: int = 0
    hyperfine_json: Path | None = None
    results_csv: Path | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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


def require_binary(specs: dict[str, ToolSpec], tool_id: str, *, execute: bool) -> Path:
    spec = specs.get(tool_id)
    if spec is None:
        raise ToolError(f"unknown tool: {tool_id}")
    if spec.binary is None:
        raise ToolError(f"missing binary for tool: {tool_id}")
    if not execute:
        return spec.binary
    return resolve_tool_binary(tool_id, spec.binary)


def full_rerun_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    full_rerun = dict(manifest.get("full_rerun", {}))
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault("n_points", 100)
    full_rerun.setdefault("threads", [1, 4, 8, 10])
    full_rerun.setdefault("runs", 3)
    full_rerun.setdefault("warmup", 1)
    full_rerun.setdefault("prepare", "sync")
    full_rerun.setdefault(
        "tools",
        [
            "zsasa_f64",
            "zsasa_f32",
            "zsasa_f64_bitmask",
            "zsasa_f32_bitmask",
            "freesasa",
            "rustsasa",
        ],
    )
    full_rerun.setdefault("phases", ["wall", "timing"])
    return full_rerun


def parse_tool_plan(tool: str) -> ToolPlan:
    if tool.startswith("zsasa_"):
        suffix = tool.removeprefix("zsasa_")
        precision = suffix.removesuffix("_bitmask")
        if precision not in {"f64", "f32"}:
            raise ValueError(f"unsupported zsasa single-file tool: {tool}")
        return ToolPlan(
            name=tool,
            tool_id="zsasa",
            precision=precision,
            bitmask=suffix.endswith("_bitmask"),
        )
    if tool in {"freesasa", "rustsasa"}:
        return ToolPlan(name=tool, tool_id=tool)
    raise ValueError(f"unsupported single-file tool: {tool}")


def structure_plans(manifest: dict[str, Any], input_dir: Path) -> list[StructurePlan]:
    structures = expect_list(manifest, "structures")
    plans: list[StructurePlan] = []
    for raw_structure in structures:
        if not isinstance(raw_structure, dict):
            raise ValueError("single-file structures must be TOML tables")
        structure_id = str(raw_structure["id"])
        plans.append(
            StructurePlan(
                structure_id=structure_id,
                role=str(raw_structure.get("role", "")),
                expected_atoms=(
                    int(raw_structure["expected_atoms"])
                    if "expected_atoms" in raw_structure
                    else None
                ),
                pdb_path=input_dir.joinpath(f"{structure_id}.pdb"),
            )
        )
    return plans


def build_native_command(
    *,
    tool: ToolPlan,
    binary: Path,
    input_path: Path,
    output_path: Path,
    n_points: int,
    threads: int,
    timing: bool,
) -> list[str]:
    if tool.tool_id == "zsasa":
        if tool.precision is None:
            raise ValueError("zsasa tool plan requires precision")
        return zsasa_calc_command(
            binary=binary,
            input_path=input_path,
            output_path=output_path,
            algorithm="sr",
            precision=tool.precision,
            n_points=n_points,
            threads=threads,
            bitmask=tool.bitmask,
            timing=timing,
        )
    if tool.tool_id == "freesasa":
        return freesasa_single_command(
            binary=binary,
            input_path=input_path,
            n_points=n_points,
            threads=threads,
            timing=timing,
        )
    if tool.tool_id == "rustsasa":
        return rustsasa_single_command(
            binary=binary,
            input_path=input_path,
            output_path=output_path,
            n_points=n_points,
            threads=threads,
            timing=timing,
        )
    raise ValueError(f"unsupported tool id: {tool.tool_id}")


def build_records(
    *,
    manifest: dict[str, Any],
    specs: dict[str, ToolSpec],
    input_dir: Path,
    output_base: Path,
    settings: dict[str, Any],
    execute: bool,
) -> list[SingleFileRecord]:
    records: list[SingleFileRecord] = []
    tools = [parse_tool_plan(str(value)) for value in settings["tools"]]
    phases = [str(value) for value in settings["phases"]]
    structures = structure_plans(manifest, input_dir)
    threads = [int(value) for value in settings["threads"]]
    n_points = int(settings["n_points"])
    runs = int(settings["runs"])
    warmup = int(settings["warmup"])
    prepare = str(settings["prepare"]) if settings.get("prepare") else None

    binaries = {
        tool.tool_id: require_binary(specs, tool.tool_id, execute=execute)
        for tool in tools
    }
    for phase in phases:
        if phase not in {"wall", "timing"}:
            raise ValueError(f"unsupported single-file phase: {phase}")
        for tool in tools:
            binary = binaries[tool.tool_id]
            for structure in structures:
                for thread in threads:
                    stem = f"{structure.structure_id}_{thread}t_{n_points}p"
                    name = f"single_{phase}_{tool.name}_{stem}"
                    output_dir = output_base.joinpath(phase, tool.name, "outputs")
                    output_path = output_dir.joinpath(f"{stem}.json")
                    native = build_native_command(
                        tool=tool,
                        binary=binary,
                        input_path=structure.pdb_path,
                        output_path=output_path,
                        n_points=n_points,
                        threads=thread,
                        timing=phase == "timing",
                    )
                    if phase == "wall":
                        hyperfine_json = output_base.joinpath(
                            "wall", tool.name, "runs", f"{stem}.json"
                        )
                        records.append(
                            SingleFileRecord(
                                name=name,
                                argv=hyperfine_command(
                                    name=name,
                                    command=shell_join(native),
                                    output_json=hyperfine_json,
                                    warmup=warmup,
                                    runs=runs,
                                    prepare=prepare,
                                ),
                                outputs=[hyperfine_json, output_path],
                                phase=phase,
                                tool=tool.name,
                                structure_id=structure.structure_id,
                                role=structure.role,
                                expected_atoms=structure.expected_atoms,
                                threads=thread,
                                n_points=n_points,
                                hyperfine_json=hyperfine_json,
                                results_csv=output_base.joinpath(
                                    "wall", tool.name, "results.csv"
                                ),
                            )
                        )
                    else:
                        records.append(
                            SingleFileRecord(
                                name=name,
                                argv=native,
                                outputs=[output_path],
                                phase=phase,
                                tool=tool.name,
                                structure_id=structure.structure_id,
                                role=structure.role,
                                expected_atoms=structure.expected_atoms,
                                threads=thread,
                                n_points=n_points,
                                results_csv=output_base.joinpath(
                                    "timing", tool.name, "timing.csv"
                                ),
                            )
                        )
    return records


def prepare_output_directories(*, output_base: Path, settings: dict[str, Any]) -> None:
    tools = [str(value) for value in settings["tools"]]
    directories = [output_base]
    for tool in tools:
        directories.extend(
            [
                output_base.joinpath("wall", tool, "runs"),
                output_base.joinpath("wall", tool, "outputs"),
                output_base.joinpath("timing", tool, "outputs"),
            ]
        )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def parse_timing(stderr: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in stderr.splitlines():
        match = TIMING_PATTERN.match(line.strip())
        if match is None:
            continue
        key = match.group(1).lower()
        values[key] = match.group(2)
    return values


def run_timing_records(records: list[SingleFileRecord], *, execute: bool, replace: bool) -> None:
    rows_by_csv: dict[Path, list[dict[str, str | int | None]]] = {}
    for record in records:
        print(f"# name: {record.name}")
        if replace:
            for output in record.outputs:
                if not output.exists() and not output.is_symlink():
                    continue
                if execute:
                    output.unlink()
                else:
                    print(f"would remove: {output}", flush=True)
        print(shell_join(record.argv), flush=True)
        if not execute:
            continue
        proc = subprocess.run(
            record.argv,
            cwd=record.cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        timing = parse_timing(proc.stderr)
        rows_by_csv.setdefault(cast(Path, record.results_csv), []).append(
            {
                "tool": record.tool,
                "structure": record.structure_id,
                "role": record.role,
                "n_atoms": record.expected_atoms,
                "threads": record.threads,
                "n_points": record.n_points,
                "parse_time_ms": timing.get("parse_time_ms", ""),
                "sasa_time_ms": timing.get("sasa_time_ms", ""),
                "total_time_ms": timing.get("total_time_ms", ""),
                "status": "ok" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
            }
        )
    for csv_path, rows in rows_by_csv.items():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def write_wall_results(records: list[SingleFileRecord]) -> None:
    rows_by_csv: dict[Path, list[dict[str, float | int | str | None]]] = {}
    for record in records:
        if record.hyperfine_json is None or not record.hyperfine_json.exists():
            continue
        metrics = parse_hyperfine_result(record.hyperfine_json)
        rows_by_csv.setdefault(cast(Path, record.results_csv), []).append(
            {
                "tool": record.tool,
                "structure": record.structure_id,
                "role": record.role,
                "n_atoms": record.expected_atoms,
                "threads": record.threads,
                "n_points": record.n_points,
                **metrics,
            }
        )
    for csv_path, rows in rows_by_csv.items():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def run_single_file_records(
    records: list[SingleFileRecord], *, execute: bool, replace: bool
) -> None:
    wall_records = [record for record in records if record.phase == "wall"]
    timing_records = [record for record in records if record.phase == "timing"]
    for record in wall_records:
        print(f"# name: {record.name}")
        if replace:
            for output in record.outputs:
                if not output.exists() and not output.is_symlink():
                    continue
                if execute:
                    output.unlink()
                else:
                    print(f"would remove: {output}", flush=True)
        run_command(record, execute=execute)
    if execute:
        write_wall_results(wall_records)
    run_timing_records(timing_records, execute=execute, replace=replace)


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    specs = load_tool_specs(args.tool_versions)
    dataset_catalog = load_dataset_catalog(args.datasets)
    settings = full_rerun_settings(manifest)
    dataset = expect_dict(manifest, "dataset")
    dataset_id = str(dataset["id"])
    input_dir = dataset_path(dataset_catalog, dataset_id, "path")
    output_base = full_rerun_dir(args.run_id, "single", dataset_id)

    records = build_records(
        manifest=manifest,
        specs=specs,
        input_dir=input_dir,
        output_base=output_base,
        settings=settings,
        execute=not args.dry_run,
    )
    prepare_output_directories(output_base=output_base, settings=settings)
    selected_records = cast(
        list[SingleFileRecord],
        filter_records(records, only=args.only, exclude=args.exclude),
    )

    write_command_log(output_base.joinpath("commands.log"), selected_records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "benchmark_kind": "single_file",
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": settings["source_kind"],
            "dataset_id": dataset_id,
            "input_dir": str(input_dir),
            "output_base": str(output_base),
            "n_points": settings["n_points"],
            "threads": settings["threads"],
            "tools": settings["tools"],
            "phases": settings["phases"],
            "tool_versions": str(resolve_repo_path(args.tool_versions)),
            "datasets": str(resolve_repo_path(args.datasets)),
            "only": list(args.only),
            "exclude": list(args.exclude),
            "replace": bool(args.replace),
            "commands": [record.name for record in selected_records],
        },
    )

    print("benchmark_kind=single_file")
    print(f"source_kind={settings['source_kind']}")
    print(f"run_id={args.run_id}")
    print(f"dataset={dataset_id}")
    print(f"input_dir={input_dir}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    print(f"selected_commands={len(selected_records)}/{len(records)}")
    run_single_file_records(
        selected_records,
        execute=not args.dry_run,
        replace=bool(args.replace),
    )


if __name__ == "__main__":
    main()
