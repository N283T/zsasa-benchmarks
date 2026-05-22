from __future__ import annotations

from pathlib import Path

import pytest
from scripts.benchlib.manifest import (
    ManifestError,
    expect_dict,
    expect_int,
    expect_list,
    load_manifest,
)


def test_load_manifest_reads_toml(tmp_path: Path) -> None:
    path = tmp_path.joinpath("manifest.toml")
    path.write_text('id = "example"\n[dataset]\nid = "dataset"\n', encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest["id"] == "example"
    assert manifest["dataset"]["id"] == "dataset"


def test_expect_dict_accepts_dict() -> None:
    assert expect_dict({"a": {"b": 1}}, "a") == {"b": 1}


def test_expect_dict_rejects_missing_key() -> None:
    with pytest.raises(ManifestError, match="missing required table: full_rerun"):
        expect_dict({}, "full_rerun")


def test_expect_list_rejects_string() -> None:
    with pytest.raises(ManifestError, match="must be a list"):
        expect_list({"threads": "10"}, "threads")


def test_expect_int_accepts_integer() -> None:
    assert expect_int({"runs": 3}, "runs") == 3


def test_expect_int_rejects_boolean() -> None:
    with pytest.raises(ManifestError, match="must be an integer"):
        expect_int({"runs": True}, "runs")
