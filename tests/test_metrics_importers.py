from __future__ import annotations

import math
from pathlib import Path

import pytest
from scripts.benchlib.importers import artifact_path, source_kind_for_full_rerun
from scripts.benchlib.metrics import files_per_second, r2_score, relative_error_percent


def test_files_per_second() -> None:
    assert files_per_second(4370, 4.37) == 1000.0


@pytest.mark.parametrize("seconds", [0.0, -1.0])
def test_files_per_second_rejects_non_positive_seconds(seconds: float) -> None:
    with pytest.raises(ValueError, match="seconds must be positive"):
        files_per_second(1, seconds)


def test_relative_error_percent() -> None:
    assert relative_error_percent(101.0, 100.0) == 1.0


def test_relative_error_percent_handles_zero_reference() -> None:
    assert relative_error_percent(0.0, 0.0) == 0.0
    assert math.isinf(relative_error_percent(1.0, 0.0))


def test_r2_score_perfect() -> None:
    assert r2_score([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_r2_score_constant_reference_is_perfect() -> None:
    assert r2_score([2.0, 2.0, 2.0], [1.0, 2.0, 3.0]) == 1.0


def test_r2_score_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="reference and observed lengths differ"):
        r2_score([1.0, 2.0], [1.0])


def test_source_kind_for_full_rerun() -> None:
    assert source_kind_for_full_rerun() == "full_rerun"


def test_artifact_path_returns_string_path(tmp_path: Path) -> None:
    path = tmp_path.joinpath("artifact.json")
    assert artifact_path(path) == str(path)
