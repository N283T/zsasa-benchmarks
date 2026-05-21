#!/usr/bin/env python3
"""Smoke-test DuckDB import/export using tiny tracked fixtures."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MANIFEST = ROOT.joinpath("tests/fixtures/validation/validation-fixture.toml")


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="zsasa_bench_db_") as tmp:
        tmp_path = Path(tmp)
        db = tmp_path.joinpath("benchmark.duckdb")
        out = tmp_path.joinpath("summary.csv")
        run([sys.executable, "scripts/init_db.py", "--db", str(db), "--manifest", str(FIXTURE_MANIFEST)])
        run([
            sys.executable,
            "scripts/import_validation_csv.py",
            "--db",
            str(db),
            "--manifest",
            str(FIXTURE_MANIFEST),
            "--baseline-dir",
            str(ROOT.joinpath("tests/fixtures/validation")),
            "--tools",
            "all",
        ])
        run([sys.executable, "scripts/export_validation_summary.py", "--db", str(db), "--out", str(out)])
        text = out.read_text(encoding="utf-8")
        if "zsasa" not in text or "freesasa" not in text:
            raise SystemExit("summary fixture export is missing expected tool comparisons")
    print("database smoke test passed")


if __name__ == "__main__":
    main()
