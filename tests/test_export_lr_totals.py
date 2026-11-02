from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.export_lr_totals import build_rows


def write_run(run_dir: Path, reference: dict[str, str], zsasa: dict[str, float]) -> None:
    ref_dir = run_dir / "freesasa_batch" / "lr_20"
    ref_dir.mkdir(parents=True)
    for name, total in reference.items():
        ref_dir.joinpath(f"{name}.txt").write_text(f"{total}\n")
    zsasa_dir = run_dir / "zsasa"
    zsasa_dir.mkdir()
    for precision in ("f64", "f32"):
        lines = [
            json.dumps({"status": "ok", "filename": f"{name}.pdb", "total_area": total})
            for name, total in zsasa.items()
        ]
        zsasa_dir.joinpath(f"lr_{precision}_20.jsonl").write_text("\n".join(lines) + "\n")


def test_build_rows_pairs_reference_and_zsasa(tmp_path: Path) -> None:
    write_run(tmp_path, {"b": "20.25", "a": "10.50"}, {"a": 10.5, "b": 20.25})
    rows = build_rows(tmp_path, 20)
    assert [row["structure_id"] for row in rows] == ["a", "b"]
    assert rows[0] == {
        "structure_id": "a",
        "freesasa_lr": "10.50",
        "zsasa_lr_f64": "10.5",
        "zsasa_lr_f32": "10.5",
    }


def test_build_rows_rejects_mismatched_structures(tmp_path: Path) -> None:
    write_run(tmp_path, {"a": "10.50"}, {"a": 10.5, "b": 20.25})
    with pytest.raises(SystemExit):
        build_rows(tmp_path, 20)
