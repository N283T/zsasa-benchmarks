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
from scripts.benchlib.hyperfine import hyperfine_command  # noqa: E402
from scripts.benchlib.manifest import expect_dict, load_manifest  # noqa: E402
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    run_command,
    shell_join,
    write_command_log,
    write_config,
)
from scripts.benchlib.tools import ToolError, ToolSpec, load_tool_specs  # noqa: E402

DEFAULT_RUN_ID = "v0_6_0_full"
DEFAULT_TOOL_VERSIONS = Path("config/tool-versions.toml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--tool-versions", type=Path, default=DEFAULT_TOOL_VERSIONS)
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
    return parser.parse_args()


def require_binary(specs: dict[str, ToolSpec], tool_id: str) -> Path:
    spec = specs.get(tool_id)
    if spec is None:
        raise ToolError(f"unknown tool: {tool_id}")
    if spec.binary is None:
        raise ToolError(f"missing binary for tool: {tool_id}")
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
    full_rerun.setdefault("prepare", "sync")
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def dataset_name(manifest_path: Path, manifest: dict[str, Any]) -> str:
    dataset = expect_dict(manifest, "dataset")
    dataset_id = str(dataset.get("id", "")).lower()
    manifest_stem = manifest_path.stem.lower()
    if "ecoli" in dataset_id or "ecoli" in manifest_stem:
        return "ecoli"
    if "human" in dataset_id or "human" in manifest_stem:
        return "human"
    return manifest_stem.removeprefix("batch-")


def rustsasa_batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    n_points: int,
    threads: int,
) -> list[str]:
    """Plan the historical RustSASA directory invocation used by batch baselines."""
    return [
        str(binary),
        str(input_dir),
        str(output_dir),
        "-n",
        str(n_points),
        "-f",
        "pdb",
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
    threads = [int(thread) for thread in settings["threads"]]
    n_points = int(settings["n_points"])
    runs = int(settings["runs"])
    warmup = int(settings["warmup"])
    prepare = str(settings["prepare"]) if settings.get("prepare") else None

    if settings.get("rerun_zsasa", True):
        zsasa = require_binary(specs, "zsasa")
        for thread in threads:
            for precision in [str(value) for value in settings["precisions"]]:
                for bitmask in [False, True]:
                    suffix = "bitmask" if bitmask else "standard"
                    name = f"zsasa_batch_{precision}_{suffix}_{thread}t_{n_points}p"
                    native = batch_command(
                        binary=zsasa,
                        input_dir=input_dir,
                        output_jsonl=output_base.joinpath(
                            "zsasa", f"{precision}_{suffix}_{thread}t_{n_points}p.jsonl"
                        ),
                        precision=precision,
                        n_points=n_points,
                        threads=thread,
                        bitmask=bitmask,
                    )
                    records.append(
                        CommandRecord(
                            name=name,
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

    if settings.get("rerun_comparators", True):
        freesasa_batch = require_binary(specs, "freesasa_batch")
        lahuta = require_binary(specs, "lahuta")
        rustsasa = require_binary(specs, "rustsasa")
        for thread in threads:
            comparator_commands = [
                (
                    f"freesasa_batch_{thread}t_{n_points}p",
                    freesasa_batch_command(
                        binary=freesasa_batch,
                        input_dir=input_dir,
                        output_dir=output_base.joinpath("freesasa_batch", f"{thread}t_{n_points}p"),
                        n_points=n_points,
                        threads=thread,
                    ),
                ),
                (
                    f"rustsasa_{thread}t_{n_points}p",
                    rustsasa_batch_command(
                        binary=rustsasa,
                        input_dir=input_dir,
                        output_dir=output_base.joinpath("rustsasa", f"{thread}t_{n_points}p"),
                        n_points=n_points,
                        threads=thread,
                    ),
                ),
            ]
            for bitmask in [False, True]:
                suffix = "bitmask" if bitmask else "standard"
                comparator_commands.append(
                    (
                        f"lahuta_{suffix}_{thread}t_{n_points}p",
                        lahuta_batch_command(
                            binary=lahuta,
                            input_dir=input_dir,
                            output_dir=output_base.joinpath(
                                "lahuta", f"{suffix}_{thread}t_{n_points}p"
                            ),
                            n_points=n_points,
                            threads=thread,
                            bitmask=bitmask,
                        ),
                    )
                )
            for name, native in comparator_commands:
                records.append(
                    CommandRecord(
                        name=name,
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
    threads = [int(thread) for thread in settings["threads"]]
    n_points = int(settings["n_points"])
    directories = [output_base, output_base.joinpath("hyperfine")]

    if settings.get("rerun_zsasa", True):
        directories.append(output_base.joinpath("zsasa"))

    if settings.get("rerun_comparators", True):
        for thread in threads:
            directories.extend(
                [
                    output_base.joinpath("freesasa_batch", f"{thread}t_{n_points}p"),
                    output_base.joinpath("rustsasa", f"{thread}t_{n_points}p"),
                ]
            )
            for suffix in ["standard", "bitmask"]:
                directories.append(
                    output_base.joinpath("lahuta", f"{suffix}_{thread}t_{n_points}p")
                )

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    specs = load_tool_specs(args.tool_versions)
    settings = full_rerun_settings(manifest)
    dataset = expect_dict(manifest, "dataset")
    name = dataset_name(manifest_path, manifest)
    input_dir = resolve_repo_path(str(dataset["historical_path"]))
    output_base = full_rerun_dir(args.run_id, "batch", name)

    records = build_native_records(
        specs=specs,
        input_dir=input_dir,
        output_base=output_base,
        settings=settings,
    )
    prepare_output_directories(output_base=output_base, settings=settings)

    write_command_log(output_base.joinpath("commands.log"), records)
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
            "tool_versions": str(resolve_repo_path(args.tool_versions)),
            "commands": [record.name for record in records],
            "rustsasa_note": (
                "RustSASA batch command is a dry-run plan for the historical "
                "directory invocation."
            ),
        },
    )

    print(f"source_kind={settings['source_kind']}")
    print(f"run_id={args.run_id}")
    print(f"dataset={name}")
    print(f"input_dir={input_dir}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    for record in records:
        print(f"# name: {record.name}")
        run_command(record, execute=not args.dry_run)


if __name__ == "__main__":
    main()
