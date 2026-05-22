"""CLI entrypoint for trajectory benchmark command plans.

The native dry-run runners emit commands through this module so every planned
trajectory invocation has one importable entrypoint and a required output path.
Real trajectory calculation backends are intentionally not implemented here yet;
this module validates command shape and fails clearly if accidentally executed
for benchmarking before a backend is wired in.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NoReturn

SUPPORTED_TOOLS = {
    "zig",
    "zig_bitmask",
    "mdtraj",
    "mdsasa_bolt",
    "zsasa_mdtraj",
    "zsasa_mdtraj_bitmask",
    "zsasa_mdanalysis",
    "zsasa_mdanalysis_bitmask",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=sorted(SUPPORTED_TOOLS))
    parser.add_argument("--xtc", required=True, type=Path)
    parser.add_argument("--pdb", required=True, type=Path)
    parser.add_argument("--n-points", required=True, type=int)
    parser.add_argument("--stride", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--write-command-stub",
        action="store_true",
        help="write a deterministic command-shape stub instead of running a benchmark",
    )
    return parser.parse_args()


def write_command_stub(args: argparse.Namespace) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "tool": args.tool,
                "xtc": str(args.xtc),
                "pdb": str(args.pdb),
                "n_points": args.n_points,
                "stride": args.stride,
                "status": "command_stub_only",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def fail_not_implemented(tool: str) -> NoReturn:
    raise SystemExit(
        "trajectory benchmark execution is not implemented in "
        f"scripts.benchlib.trajectory_tools for tool '{tool}'. "
        "Use the native runners with --dry-run until a real backend is added."
    )


def main() -> None:
    args = parse_args()
    if args.write_command_stub:
        write_command_stub(args)
        return
    fail_not_implemented(str(args.tool))


if __name__ == "__main__":
    main()
