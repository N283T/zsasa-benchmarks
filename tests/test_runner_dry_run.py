from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.benchlib.hyperfine import hyperfine_command, parse_hyperfine_result
from scripts.benchlib.runner import (
    CommandRecord,
    filter_records,
    run_command,
    run_records,
    write_command_log,
    write_config,
)


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


def test_filter_records_applies_only_and_exclude_globs() -> None:
    records = [
        CommandRecord(name="zsasa_sr_f64_standard_100", argv=["zsasa"]),
        CommandRecord(name="rustsasa_sr_100", argv=["rust-sasa"]),
        CommandRecord(name="lahuta_sr_bitmask_100", argv=["lahuta"]),
    ]

    selected = filter_records(records, only=["*_sr_*"], exclude=["*bitmask*"])

    assert [record.name for record in selected] == [
        "zsasa_sr_f64_standard_100",
        "rustsasa_sr_100",
    ]


def test_filter_records_rejects_empty_selection() -> None:
    records = [CommandRecord(name="zsasa_sr_f64_standard_100", argv=["zsasa"])]

    with pytest.raises(ValueError, match="no commands selected"):
        filter_records(records, only=["rustsasa_*"], exclude=[])


def test_run_records_replace_removes_selected_outputs_before_execution(tmp_path: Path) -> None:
    selected_output = tmp_path.joinpath("selected")
    selected_output.mkdir()
    selected_output.joinpath("old.txt").write_text("old", encoding="utf-8")
    unselected_output = tmp_path.joinpath("unselected")
    unselected_output.mkdir()
    unselected_output.joinpath("keep.txt").write_text("keep", encoding="utf-8")
    records = [
        CommandRecord(name="rustsasa_sr_100", argv=["true"], outputs=[selected_output]),
        CommandRecord(name="zsasa_sr_100", argv=["true"], outputs=[unselected_output]),
    ]

    with patch("scripts.benchlib.runner.subprocess.run") as run_mock:
        run_records(records[:1], execute=True, replace=True)

    run_mock.assert_called_once()
    assert not selected_output.exists()
    assert unselected_output.joinpath("keep.txt").is_file()


def test_run_records_replace_dry_run_does_not_remove_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path.joinpath("selected")
    output.mkdir()
    output.joinpath("old.txt").write_text("old", encoding="utf-8")
    records = [CommandRecord(name="rustsasa_sr_100", argv=["true"], outputs=[output])]

    with patch("scripts.benchlib.runner.subprocess.run") as run_mock:
        run_records(records, execute=False, replace=True)

    run_mock.assert_not_called()
    assert output.joinpath("old.txt").is_file()
    assert f"would remove: {output}" in capsys.readouterr().out


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
