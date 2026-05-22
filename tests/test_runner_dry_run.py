from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.benchlib.hyperfine import hyperfine_command, parse_hyperfine_result
from scripts.benchlib.runner import CommandRecord, run_command, write_command_log, write_config


def test_write_command_log(tmp_path: Path) -> None:
    records = [CommandRecord(name="example", argv=["echo", "hello"], cwd=tmp_path)]
    path = tmp_path.joinpath("commands.log")
    write_command_log(path, records)
    assert "echo hello" in path.read_text(encoding="utf-8")


def test_run_command_dry_run_does_not_execute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = CommandRecord(name="example", argv=["echo", "hello"], cwd=tmp_path)
    with patch("scripts.benchlib.runner.subprocess.run") as run_mock:
        run_command(record, execute=False)
    run_mock.assert_not_called()
    assert "echo hello" in capsys.readouterr().out


def test_write_config(tmp_path: Path) -> None:
    path = tmp_path.joinpath("config.json")
    write_config(path, {"run_id": "abc", "threads": [1, 2]})
    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "abc"


def test_hyperfine_command_includes_export_json() -> None:
    cmd = hyperfine_command(
        name="bench_zsasa_10t",
        command="zsasa batch input --threads=10",
        output_json=Path("runs/bench_zsasa_10t.json"),
        warmup=1,
        runs=3,
        prepare="sync",
    )
    assert cmd[:2] == ["hyperfine", "--warmup"]
    assert "--export-json" in cmd
    assert "runs/bench_zsasa_10t.json" in cmd


def test_parse_hyperfine_result(tmp_path: Path) -> None:
    path = tmp_path.joinpath("result.json")
    path.write_text(
        '{"results":[{"mean":1.5,"stddev":0.1,"min":1.4,"max":1.7,'
        '"median":1.5,"times":[1.4,1.5]}]}',
        encoding="utf-8",
    )
    result = parse_hyperfine_result(path)
    assert result["mean_s"] == 1.5
    assert result["median_s"] == 1.5
