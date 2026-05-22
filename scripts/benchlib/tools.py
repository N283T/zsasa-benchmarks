"""Tool registry and preflight checks."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import resolve_repo_path


class ToolError(RuntimeError):
    """Raised when a required benchmark tool is unavailable."""


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    repository: str | None
    version: str | None
    tag: str | None
    commit: str | None
    binary: Path | None
    check_args: list[str]
    policy: str | None
    python_module: str | None = None


def _path_or_none(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return resolve_repo_path(Path(os.path.expanduser(value)))


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def load_tool_specs(path: str | Path) -> dict[str, ToolSpec]:
    resolved = resolve_repo_path(path)
    with resolved.open("rb") as handle:
        raw: dict[str, dict[str, Any]] = tomllib.load(handle)
    specs: dict[str, ToolSpec] = {}
    for tool_id, data in raw.items():
        if tool_id == "runner":
            continue
        specs[tool_id] = ToolSpec(
            tool_id=tool_id,
            repository=data.get("repository"),
            version=data.get("version"),
            tag=data.get("tag"),
            commit=data.get("commit") or data.get("commit_sha"),
            binary=_path_or_none(data.get("binary")),
            check_args=_list_of_strings(data.get("check_args")),
            policy=data.get("policy"),
            python_module=data.get("python_module"),
        )
    return specs


def require_tools(specs: dict[str, ToolSpec], tool_ids: list[str]) -> dict[str, ToolSpec]:
    checked: dict[str, ToolSpec] = {}
    for tool_id in tool_ids:
        if tool_id not in specs:
            raise ToolError(f"unknown tool: {tool_id}")
        spec = specs[tool_id]
        if spec.python_module and importlib.util.find_spec(spec.python_module) is None:
            raise ToolError(f"missing Python module for {tool_id}: {spec.python_module}")
        if spec.binary is not None:
            if not spec.binary.exists() or not os.access(spec.binary, os.X_OK):
                raise ToolError(f"missing executable for {tool_id}: {spec.binary}")
            if spec.check_args:
                try:
                    proc = subprocess.run(
                        [str(spec.binary), *spec.check_args],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=20,
                    )
                except (subprocess.TimeoutExpired, OSError) as error:
                    raise ToolError(f"check command failed for {tool_id}: {error}") from error
                if proc.returncode != 0:
                    raise ToolError(f"check command failed for {tool_id}: exit {proc.returncode}")
        checked[tool_id] = spec
    return checked


PROFILES: dict[str, list[str]] = {
    "minimal": ["zsasa"],
    "validation": ["zsasa", "freesasa_batch", "rustsasa", "lahuta"],
    "batch": ["zsasa", "freesasa_batch", "rustsasa", "lahuta"],
    "trajectory": ["zsasa", "mdtraj", "mdsasa_bolt"],
    "full": ["zsasa", "freesasa_batch", "rustsasa", "lahuta", "mdtraj", "mdsasa_bolt"],
}
