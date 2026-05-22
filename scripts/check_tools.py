#!/usr/bin/env python3
"""Check benchmark tool availability by profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.tools import PROFILES, ToolError, load_tool_specs, require_tools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
    parser.add_argument("--profile", choices=sorted(PROFILES), default="minimal")
    parser.add_argument(
        "--dry-run", action="store_true", help="print required tool ids without checking"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tool_ids = PROFILES[args.profile]
    if args.dry_run:
        print("required_tools=" + ",".join(tool_ids))
        return
    specs = load_tool_specs(args.tool_versions)
    try:
        checked = require_tools(specs, tool_ids)
    except ToolError as error:
        raise SystemExit(str(error)) from error
    for tool_id, spec in checked.items():
        location = spec.binary if spec.binary is not None else spec.python_module
        print(f"{tool_id}: OK ({location})")


if __name__ == "__main__":
    main()
