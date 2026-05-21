#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "cffi",
#   "matplotlib>=3.8",
#   "MDAnalysis",
#   "mdtraj",
#   "numpy>=1.26",
#   "polars>=1.0",
#   "rich>=13.0",
#   "typer>=0.9.0",
# ]
# ///
"""Refresh MD trajectory validation by rerunning zsasa while reusing mdtraj reference.

This intentionally does not run native ``mdtraj.shrake_rupley``.  Instead it
reads the historical ``mdtraj`` reference column from existing validation CSVs
and reruns only the zsasa trajectory paths.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZSASA_ROOT = Path("/Users/nagaet/freesasa-zig")
DEFAULT_HISTORICAL = DEFAULT_ZSASA_ROOT.joinpath(
    "benchmarks", "results", "validation_md", "5wvo_C_analysis"
)
DEFAULT_OUTPUT = ROOT.joinpath(
    "results", "validation_md", "zsasa_v0_6_0_5wvo_C_validation"
)
DEFAULT_XTC = DEFAULT_ZSASA_ROOT.joinpath(
    "benchmarks", "md_data", "5wvo_C_analysis", "5wvo_C_R1.xtc"
)
DEFAULT_PDB = DEFAULT_ZSASA_ROOT.joinpath(
    "benchmarks", "md_data", "5wvo_C_analysis", "5wvo_C.pdb"
)


def load_validation_md(zsasa_root: Path) -> Any:
    scripts_dir = zsasa_root.joinpath("benchmarks", "scripts")
    sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir.joinpath("validation_md.py")
    spec = importlib.util.spec_from_file_location("zsasa_validation_md", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_points(value: str) -> list[int]:
    return sorted(int(part.strip()) for part in value.split(",") if part.strip())


def load_historical_mdtraj(csv_path: Path) -> dict[int, float]:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    values: dict[int, float] = {}
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if "frame" not in (reader.fieldnames or []) or "mdtraj" not in (reader.fieldnames or []):
            raise ValueError(f"{csv_path} must contain frame and mdtraj columns")
        for row in reader:
            values[int(row["frame"])] = float(row["mdtraj"])
    if not values:
        raise ValueError(f"{csv_path} contains no mdtraj reference values")
    return values


def run_zsasa_variants(validation_md: Any, xtc: Path, pdb: Path, n_points: int, stride: int, threads: int) -> dict[str, dict[int, float]]:
    zsasa_runs: dict[str, dict[int, float]] = {}
    for col_name, source, precision, use_bitmask in validation_md.ZSASA_MD_VARIANTS:
        validation_md.console.print(f"[bold cyan]Running {col_name} (n_points={n_points})...[/]")
        if source == "mdtraj":
            zsasa_runs[col_name] = validation_md.run_zsasa_mdtraj(
                xtc, pdb, n_points, stride, threads
            )
        elif source == "mdanalysis":
            zsasa_runs[col_name] = validation_md.run_zsasa_mdanalysis(
                xtc, pdb, n_points, stride, threads
            )
        elif source == "cli":
            zsasa_runs[col_name] = validation_md.run_zsasa_cli(
                xtc, pdb, n_points, stride, threads, precision, use_bitmask
            )
        else:
            raise ValueError(f"unknown validation source: {source}")
        validation_md.console.print(f"  Got {len(zsasa_runs[col_name])} frames")
    return zsasa_runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zsasa-root", type=Path, default=DEFAULT_ZSASA_ROOT)
    parser.add_argument("--historical-dir", type=Path, default=DEFAULT_HISTORICAL)
    parser.add_argument("--xtc", type=Path, default=DEFAULT_XTC)
    parser.add_argument("--pdb", type=Path, default=DEFAULT_PDB)
    parser.add_argument("--name", default="zsasa_v0_6_0_5wvo_C_validation")
    parser.add_argument("--n-points", default="100,200,500,1000")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    points = parse_points(args.n_points)
    validation_md = load_validation_md(args.zsasa_root)
    args.output.mkdir(parents=True, exist_ok=True)

    validation_md.console.print("[bold]=== MD SASA Validation Refresh (zsasa-only) ===[/]")
    validation_md.console.print(f"Historical mdtraj reference: {args.historical_dir}")
    validation_md.console.print(f"Output: {args.output}")
    validation_md.console.print("Native mdtraj.shrake_rupley will not be rerun.")

    frame_count: int | None = None
    for n_points in points:
        validation_md.console.print(f"\n[bold]=== n_points = {n_points} ===[/]")
        mdtraj_reference = load_historical_mdtraj(
            args.historical_dir.joinpath(f"results_{n_points}.csv")
        )
        if frame_count is None:
            frame_count = len(mdtraj_reference)
        zsasa_runs = run_zsasa_variants(
            validation_md, args.xtc, args.pdb, n_points, args.stride, args.threads
        )
        validation_md.build_csv(
            mdtraj_reference, zsasa_runs, args.output.joinpath(f"results_{n_points}.csv")
        )

    config = {
        "timestamp": datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        "system": validation_md.get_system_info(),
        "parameters": {
            "name": args.name,
            "xtc": str(args.xtc),
            "pdb": str(args.pdb),
            "tools": ["mdtraj_reference_reused"] + [v[0] for v in validation_md.ZSASA_MD_VARIANTS],
            "mdtraj_reference_source": str(args.historical_dir),
            "native_mdtraj_rerun": False,
            "n_points": points,
            "stride": args.stride,
            "threads": args.threads,
            "frame_count": frame_count,
        },
    }
    args.output.joinpath("config.json").write_text(json.dumps(config, indent=2) + "\n")

    validation_md.print_stats_table(args.output, points)
    validation_md.generate_grid_plot(args.output, points)
    validation_md.generate_per_tool_plots(args.output, points)
    validation_md.generate_xtc_comparison_plot(args.output)
    validation_md.generate_bitmask_comparison_plot(args.output)
    validation_md.console.print(f"\n[bold green]=== Done! Results: {args.output} ===[/]")


if __name__ == "__main__":
    main()
