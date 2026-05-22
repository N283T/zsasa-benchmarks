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
