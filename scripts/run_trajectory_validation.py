#!/usr/bin/env python3
"""Native trajectory numerical validation dry-run runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchlib.commands import mdtraj_runner_command  # noqa: E402
from scripts.benchlib.manifest import (  # noqa: E402
    expect_dict,
    load_manifest,
    require_native_full_rerun_flags,
)
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    run_command,
    write_command_log,
    write_config,
)
from scripts.benchlib.tools import load_tool_specs  # noqa: E402

DEFAULT_RUN_ID = "v0_6_0_full"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
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


def full_rerun_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    full_rerun = dict(manifest.get("full_rerun", {}))
    refresh = manifest.get("refresh", {})
    if isinstance(refresh, dict):
        for key in ["tools", "n_points", "stride", "threads"]:
            if key in refresh:
                full_rerun.setdefault(key, refresh[key])
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault(
        "tools", ["mdtraj", "zsasa_mdtraj", "zsasa_mdanalysis", "zig", "zig_bitmask"]
    )
    full_rerun.setdefault("n_points", [100, 200, 500, 1000])
    full_rerun.setdefault("stride", 1)
    full_rerun.setdefault("threads", 10)
    full_rerun.setdefault("cli_precisions", ["f64", "f32"])
    full_rerun.setdefault("classifier", "naccess")
    full_rerun.setdefault("include_hydrogens", True)
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def require_zsasa_binary(tool_versions: Path) -> Path:
    specs = load_tool_specs(tool_versions)
    spec = specs.get("zsasa")
    if spec is None or spec.binary is None:
        return Path("zsasa")
    return spec.binary


def command_variants(*, tool: str, n_points: int, settings: dict[str, Any]) -> list[dict[str, Any]]:
    threads = int(settings["threads"])
    if tool in {"zig", "zig_bitmask"}:
        return [
            {
                "name": f"{tool}_{precision}_{threads}t_{n_points}p",
                "tool": tool,
                "precision": str(precision),
                "threads": threads,
                "raw_parts": [tool, str(precision), f"{n_points}p"],
            }
            for precision in settings["cli_precisions"]
        ]
    return [
        {
            "name": f"{tool}_{threads}t_{n_points}p"
            if tool.startswith("zsasa_")
            else f"{tool}_{n_points}p",
            "tool": tool,
            "precision": None,
            "threads": threads,
            "raw_parts": [tool, f"{n_points}p"],
        }
    ]


def build_records(
    *,
    dataset: dict[str, Any],
    output_base: Path,
    settings: dict[str, Any],
    zsasa_binary: Path,
) -> list[CommandRecord]:
    xtc = resolve_repo_path(str(dataset["xtc"]))
    pdb = resolve_repo_path(str(dataset["pdb"]))
    stride = int(settings["stride"])
    records: list[CommandRecord] = []
    for tool in [str(value) for value in settings["tools"]]:
        for n_points in [int(value) for value in settings["n_points"]]:
            for variant in command_variants(tool=tool, n_points=n_points, settings=settings):
                raw_dir = output_base.joinpath("raw", *variant["raw_parts"])
                raw_dir.mkdir(parents=True, exist_ok=True)
                records.append(
                    CommandRecord(
                        name=str(variant["name"]),
                        argv=mdtraj_runner_command(
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
                        ),
                    )
                )
    return records


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    dataset = expect_dict(manifest, "dataset")
    settings = full_rerun_settings(manifest)
    require_native_full_rerun_flags(settings, runner="scripts/run_trajectory_validation.py")
    zsasa_binary = require_zsasa_binary(resolve_repo_path(args.tool_versions))
    dataset_id = str(dataset["id"])
    output_base = full_rerun_dir(args.run_id, "validation_md", dataset_id)
    output_base.mkdir(parents=True, exist_ok=True)

    records = build_records(
        dataset=dataset, output_base=output_base, settings=settings, zsasa_binary=zsasa_binary
    )
    write_command_log(output_base.joinpath("commands.log"), records)
    write_config(
        output_base.joinpath("config.json"),
        {
            "manifest": str(manifest_path),
            "run_id": args.run_id,
            "source_kind": settings["source_kind"],
            "dataset_id": dataset_id,
            "xtc": str(resolve_repo_path(str(dataset["xtc"]))),
            "pdb": str(resolve_repo_path(str(dataset["pdb"]))),
            "output_base": str(output_base),
            "tools": [str(value) for value in settings["tools"]],
            "n_points": [int(value) for value in settings["n_points"]],
            "stride": int(settings["stride"]),
            "threads": int(settings["threads"]),
            "cli_precisions": [str(value) for value in settings["cli_precisions"]],
            "classifier": str(settings["classifier"]),
            "include_hydrogens": bool(settings["include_hydrogens"]),
            "zsasa_binary": str(zsasa_binary),
            "commands": [record.name for record in records],
        },
    )

    print(f"source_kind={settings['source_kind']}")
    print(f"run_id={args.run_id}")
    print(f"dataset={dataset_id}")
    print(f"output_base={output_base}")
    print(f"mode={'dry-run' if args.dry_run else 'execute'}")
    for record in records:
        print(f"# name: {record.name}")
        run_command(record, execute=not args.dry_run)


if __name__ == "__main__":
    main()
