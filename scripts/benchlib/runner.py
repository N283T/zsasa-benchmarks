"""Shared dry-run and execution utilities."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandRecord:
    name: str
    argv: list[str]
    cwd: Path | None = None
    outputs: Sequence[Path] = ()


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


def filter_records(
    records: Sequence[CommandRecord], *, only: Sequence[str], exclude: Sequence[str]
) -> list[CommandRecord]:
    selected: list[CommandRecord] = []
    for record in records:
        if only and not any(fnmatchcase(record.name, pattern) for pattern in only):
            continue
        if exclude and any(fnmatchcase(record.name, pattern) for pattern in exclude):
            continue
        selected.append(record)
    if not selected:
        raise ValueError(
            "no commands selected; adjust --only/--exclude patterns or check record names"
        )
    return selected


def remove_record_outputs(record: CommandRecord, *, execute: bool) -> None:
    for output in record.outputs:
        if not output.exists() and not output.is_symlink():
            continue
        if not execute:
            print(f"would remove: {output}", flush=True)
            continue
        if output.is_dir() and not output.is_symlink():
            shutil.rmtree(output)
        else:
            output.unlink()


def run_records(records: Sequence[CommandRecord], *, execute: bool, replace: bool) -> None:
    for record in records:
        print(f"# name: {record.name}")
        if replace:
            remove_record_outputs(record, execute=execute)
        run_command(record, execute=execute)
