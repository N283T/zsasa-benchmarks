"""Tool registry and preflight checks."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, replace
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


def _binary_or_none(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    expanded = os.path.expanduser(value)
    path = Path(expanded)
    if path.is_absolute() or path.parent != Path("."):
        return resolve_repo_path(path)
    return path


def _executable_from_env(tool_id: str) -> Path | None:
    env_var = "ZSASA_CLI" if tool_id == "zsasa" else None
    if env_var is None:
        return None
    value = os.environ.get(env_var)
    if not value:
        return None
    return Path(os.path.expanduser(value))


def resolve_tool_binary(tool_id: str, binary: Path) -> Path:
    env_binary = _executable_from_env(tool_id)
    if env_binary is not None:
        if not env_binary.exists() or not os.access(env_binary, os.X_OK):
            raise ToolError(f"missing executable for {tool_id}: {env_binary} from environment")
        return env_binary
    if binary.parent == Path("."):
        found = shutil.which(str(binary))
        if found is None:
            raise ToolError(f"missing executable for {tool_id}: {binary} (not found on PATH)")
        return Path(found)
    if not binary.exists() or not os.access(binary, os.X_OK):
        raise ToolError(f"missing executable for {tool_id}: {binary}")
    return binary


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
            binary=_binary_or_none(data.get("binary")),
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
            resolved_binary = resolve_tool_binary(tool_id, spec.binary)
            spec = replace(spec, binary=resolved_binary)
            if spec.check_args:
                try:
                    proc = subprocess.run(
                        [str(resolved_binary), *spec.check_args],
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
    "trajectory": ["zsasa", "mdtraj", "mdanalysis", "mdsasa_bolt"],
    "full": [
        "zsasa",
        "freesasa_batch",
        "rustsasa",
        "lahuta",
        "mdtraj",
        "mdanalysis",
        "mdsasa_bolt",
    ],
}
