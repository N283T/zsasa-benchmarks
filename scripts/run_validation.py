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
from scripts.benchlib.manifest import expect_dict, load_manifest  # noqa: E402
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    run_command,
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
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault("threads", 10)
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def build_records(
    *,
    manifest: dict[str, Any],
    specs: dict[str, ToolSpec],
    output_base: Path,
) -> list[CommandRecord]:
    dataset = expect_dict(manifest, "dataset")
    full_rerun = full_rerun_settings(manifest)
    input_dir = resolve_repo_path(str(dataset["historical_path"]))
    threads = int(full_rerun["threads"])

    zsasa = require_binary(specs, "zsasa")
    freesasa_batch = require_binary(specs, "freesasa_batch")
    lahuta = require_binary(specs, "lahuta")

    records: list[CommandRecord] = []
    sr_points = [64, 128, 256]
    for n_points in sr_points:
        for precision in ["f64", "f32"]:
            for bitmask in [False, True]:
                suffix = "bitmask" if bitmask else "standard"
                records.append(
                    CommandRecord(
                        name=f"zsasa_sr_{precision}_{suffix}_{n_points}",
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
                argv=freesasa_batch_command(
                    binary=freesasa_batch,
                    input_dir=input_dir,
                    output_dir=output_base.joinpath("freesasa_batch", f"sr_{n_points}"),
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


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    specs = load_tool_specs(args.tool_versions)
    full_rerun = full_rerun_settings(manifest)
    source_kind = str(full_rerun["source_kind"])
    output_base = full_rerun_dir(args.run_id, "validation", "ecoli")

    records = build_records(
        manifest=manifest,
        specs=specs,
        output_base=output_base,
    )

    write_command_log(output_base.joinpath("commands.log"), records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": source_kind,
            "threads": full_rerun["threads"],
            "tool_versions": str(resolve_repo_path(args.tool_versions)),
            "commands": [record.name for record in records],
        },
    )

    print(f"source_kind={source_kind}")
    print(f"run_id={args.run_id}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    for record in records:
        print(f"# name: {record.name}")
        run_command(record, execute=not args.dry_run)


if __name__ == "__main__":
    main()
