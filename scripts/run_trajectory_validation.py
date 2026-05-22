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
from scripts.benchlib.manifest import expect_dict, load_manifest  # noqa: E402
from scripts.benchlib.paths import full_rerun_dir, resolve_repo_path  # noqa: E402
from scripts.benchlib.runner import (  # noqa: E402
    CommandRecord,
    run_command,
    write_command_log,
    write_config,
)

DEFAULT_RUN_ID = "v0_6_0_full"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
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
        for key in ["tools", "n_points", "stride"]:
            if key in refresh:
                full_rerun.setdefault(key, refresh[key])
    full_rerun.setdefault("source_kind", "full_rerun")
    full_rerun.setdefault("run_id_default", DEFAULT_RUN_ID)
    full_rerun.setdefault("tools", ["mdtraj", "zsasa_mdtraj", "zsasa_mdanalysis"])
    full_rerun.setdefault("n_points", [100, 200, 500, 1000])
    full_rerun.setdefault("stride", 1)
    full_rerun.setdefault("rerun_zsasa", True)
    full_rerun.setdefault("rerun_comparators", True)
    return full_rerun


def build_records(
    *, dataset: dict[str, Any], output_base: Path, settings: dict[str, Any]
) -> list[CommandRecord]:
    xtc = resolve_repo_path(str(dataset["xtc"]))
    pdb = resolve_repo_path(str(dataset["pdb"]))
    stride = int(settings["stride"])
    records: list[CommandRecord] = []
    for tool in [str(value) for value in settings["tools"]]:
        for n_points in [int(value) for value in settings["n_points"]]:
            name = f"{tool}_{n_points}p"
            records.append(
                CommandRecord(
                    name=name,
                    argv=mdtraj_runner_command(
                        tool=tool,
                        xtc=xtc,
                        pdb=pdb,
                        n_points=n_points,
                        stride=stride,
                    ),
                )
            )
            output_base.joinpath("raw", tool, f"{n_points}p").mkdir(parents=True, exist_ok=True)
    return records


def main() -> None:
    args = parse_args()
    manifest_path = resolve_repo_path(args.manifest)
    manifest = load_manifest(manifest_path)
    dataset = expect_dict(manifest, "dataset")
    settings = full_rerun_settings(manifest)
    dataset_id = str(dataset["id"])
    output_base = full_rerun_dir(args.run_id, "validation_md", dataset_id)
    output_base.mkdir(parents=True, exist_ok=True)

    records = build_records(dataset=dataset, output_base=output_base, settings=settings)
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
