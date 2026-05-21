#!/usr/bin/env python3
"""Shared helpers for DuckDB-backed benchmark scripts."""
from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results/benchmark.duckdb")
SCHEMA_PATH = ROOT.joinpath("schemas/benchmark.sql")


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def resolve(path: Path, base: Path = ROOT) -> Path:
    return path if path.is_absolute() else base.joinpath(path)


def stable_id(*parts: object) -> str:
    raw = "::".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    safe = "_".join(str(part).replace("/", "_").replace(" ", "_") for part in parts if part is not None)
    return f"{safe}_{digest}"[:180]


def connect(db_path: Path):
    import duckdb

    db_path.parent.mkdir(parents=True, exist_ok=True)
    # `mktemp` creates an empty placeholder file, but DuckDB expects either a
    # valid database or a missing path. Treat zero-byte files as placeholders.
    if db_path.exists() and db_path.stat().st_size == 0:
        db_path.unlink()
    return duckdb.connect(str(db_path))


def apply_schema(conn) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
