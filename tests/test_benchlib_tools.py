from __future__ import annotations

from pathlib import Path

import pytest
from scripts.benchlib.tools import (
    ToolError,
    ToolSpec,
    load_tool_specs,
    require_tools,
)


def test_load_tool_specs_reads_known_tools() -> None:
    specs = load_tool_specs(Path("config/tool-versions.toml"))
    assert "zsasa" in specs
    assert specs["zsasa"].repository == "https://github.com/N283T/zsasa"
    assert specs["zsasa"].binary == Path("zsasa")


def test_require_tools_reports_missing_binary(tmp_path: Path) -> None:
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version=None,
            tag=None,
            commit=None,
            binary=tmp_path.joinpath("missing"),
            check_args=["--version"],
            policy="test",
        )
    }
    with pytest.raises(ToolError, match="missing executable for fake"):
        require_tools(specs, ["fake"])


def test_require_tools_accepts_executable(tmp_path: Path) -> None:
    binary = tmp_path.joinpath("fake-tool")
    binary.write_text("#!/bin/sh\necho fake 1.0\n", encoding="utf-8")
    binary.chmod(0o755)
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version="1.0",
            tag=None,
            commit=None,
            binary=binary,
            check_args=["--version"],
            policy="test",
        )
    }
    checked = require_tools(specs, ["fake"])
    assert checked["fake"].binary == binary


def test_require_tools_rejects_failing_check_command(tmp_path: Path) -> None:
    binary = tmp_path.joinpath("fake-tool")
    binary.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    binary.chmod(0o755)
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version="1.0",
            tag=None,
            commit=None,
            binary=binary,
            check_args=["--version"],
            policy="test",
        )
    }
    with pytest.raises(ToolError, match="check command failed for fake"):
        require_tools(specs, ["fake"])


def test_require_tools_accepts_path_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path.joinpath("fake-tool")
    binary.write_text("#!/bin/sh\necho fake 1.0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version="1.0",
            tag=None,
            commit=None,
            binary=Path("fake-tool"),
            check_args=["--version"],
            policy="test",
        )
    }
    checked = require_tools(specs, ["fake"])
    assert checked["fake"].binary == binary


def test_require_tools_prefers_zsasa_cli_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_binary = tmp_path.joinpath("path-bin", "zsasa")
    path_binary.parent.mkdir()
    path_binary.write_text("#!/bin/sh\necho path zsasa\n", encoding="utf-8")
    path_binary.chmod(0o755)
    env_binary = tmp_path.joinpath("nix-zsasa")
    env_binary.write_text("#!/bin/sh\necho zsasa 0.6.0\n", encoding="utf-8")
    env_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(path_binary.parent))
    monkeypatch.setenv("ZSASA_CLI", str(env_binary))
    specs = {
        "zsasa": ToolSpec(
            tool_id="zsasa",
            repository=None,
            version="0.6.0",
            tag="v0.6.0",
            commit=None,
            binary=Path("zsasa"),
            check_args=["--version"],
            policy="test",
        )
    }
    checked = require_tools(specs, ["zsasa"])
    assert checked["zsasa"].binary == env_binary
