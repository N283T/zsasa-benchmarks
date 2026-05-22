"""Shared dry-run and execution utilities."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandRecord:
    name: str
    argv: list[str]
    cwd: Path | None = None


def shell_join(argv: list[str]) -> str:
    return shlex.join(argv)


def write_command_log(path: Path, records: list[CommandRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for record in records:
        if record.cwd is not None:
            lines.append(f"# cwd: {record.cwd}")
        lines.append(f"# name: {record.name}")
        lines.append(shell_join(record.argv))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(record: CommandRecord, *, execute: bool) -> None:
    print(shell_join(record.argv), flush=True)
    if not execute:
        return
    subprocess.run(record.argv, cwd=record.cwd, check=True)
