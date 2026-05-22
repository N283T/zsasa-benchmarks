"""Hyperfine command helpers."""

from __future__ import annotations

import json
from pathlib import Path


def hyperfine_command(
    *,
    name: str,
    command: str,
    output_json: Path,
    warmup: int,
    runs: int,
    prepare: str | None,
) -> list[str]:
    argv = [
        "hyperfine",
        "--warmup",
        str(warmup),
        "--runs",
        str(runs),
        "--export-json",
        str(output_json),
        "--command-name",
        name,
    ]
    if prepare:
        argv.extend(["--prepare", prepare])
    argv.append(command)
    return argv


def parse_hyperfine_result(path: Path) -> dict[str, float | int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = data["results"][0]
    return {
        "mean_s": float(result["mean"]),
        "stddev_s": float(result.get("stddev", 0.0)),
        "min_s": float(result.get("min", result["mean"])),
        "max_s": float(result.get("max", result["mean"])),
        "median_s": float(result.get("median", result["mean"])),
        "n_runs": len(result.get("times", [])),
    }
