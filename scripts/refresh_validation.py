#!/usr/bin/env python3
"""Refresh validation CSVs by rerunning only zsasa and reusing comparator baselines."""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ZSASA_VARIANTS = {
    "zsasa_f64": {"precision": "f64", "bitmask": False},
    "zsasa_f32": {"precision": "f32", "bitmask": False},
    "zsasa_bitmask_f64": {"precision": "f64", "bitmask": True},
    "zsasa_bitmask_f32": {"precision": "f32", "bitmask": True},
}


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--zsasa-bin", type=Path, default=None)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--baseline-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--algorithm", choices=["all", "sr", "lr"], default="all")
    parser.add_argument("--execute", action="store_true", help="actually run zsasa")
    parser.add_argument("--dry-run", action="store_true", help="print planned commands only")
    return parser.parse_args()


def resolve(path: Path, base: Path = ROOT) -> Path:
    return path if path.is_absolute() else base.joinpath(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], columns: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def planned_command(
    zsasa_bin: Path,
    input_dir: Path,
    output_dir: Path,
    algorithm: str,
    precision: str,
    threads: int,
    points_flag: str,
    points: int,
    bitmask: bool,
) -> list[str]:
    command = [
        str(zsasa_bin),
        "batch",
        str(input_dir),
        str(output_dir),
        f"--algorithm={algorithm}",
        f"--precision={precision}",
        f"--threads={threads}",
        f"{points_flag}={points}",
    ]
    if bitmask:
        command.append("--use-bitmask")
    return command


def parse_zsasa_output(output_dir: Path) -> dict[str, tuple[float, int]]:
    results: dict[str, tuple[float, int]] = {}
    for json_file in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            total = float(data["total_area"])
            n_atoms = len(data.get("atom_areas", []))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        results[json_file.stem] = (round(total, 2), n_atoms)
    return results


def run_zsasa_variant(
    zsasa_bin: Path,
    input_dir: Path,
    algorithm: str,
    variant: str,
    threads: int,
    points_flag: str,
    points: int,
) -> dict[str, tuple[float, int]]:
    spec = ZSASA_VARIANTS[variant]
    with tempfile.TemporaryDirectory(prefix=f"zsasa_{variant}_{points}_") as tmp:
        out_dir = Path(tmp)
        command = planned_command(
            zsasa_bin=zsasa_bin,
            input_dir=input_dir,
            output_dir=out_dir,
            algorithm=algorithm,
            precision=str(spec["precision"]),
            threads=threads,
            points_flag=points_flag,
            points=points,
            bitmask=bool(spec["bitmask"]),
        )
        proc = subprocess.run(command, capture_output=True, text=True, timeout=3600, check=False)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(f"zsasa failed for {variant} at {points} ({algorithm})")
        return parse_zsasa_output(out_dir)


def merge_rows(
    baseline_rows: list[dict[str, str]],
    keep_columns: list[str],
    variants: list[str],
    zsasa_results: dict[str, dict[str, tuple[float, int]]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    for baseline in baseline_rows:
        structure = baseline["structure"]
        row: dict[str, object] = {}
        for column in keep_columns:
            if column in baseline:
                row[column] = baseline[column]
        for variant in variants:
            result = zsasa_results.get(variant, {}).get(structure)
            if result is not None:
                row[variant] = result[0]
                row.setdefault("n_atoms", result[1])
        merged.append(row)
    return merged


def main() -> None:
    args = parse_args()
    if args.execute and args.dry_run:
        raise SystemExit("choose either --execute or --dry-run, not both")
    execute = args.execute

    manifest_path = resolve(args.manifest)
    manifest = load_toml(manifest_path)
    dataset = manifest["dataset"]
    baseline = manifest["baseline"]
    output = manifest["output"]

    input_dir = args.input_dir or Path(dataset["historical_path"])
    baseline_dir = args.baseline_dir or Path(baseline["historical_results_dir"])
    output_dir = resolve(args.output_dir or Path(output["default_dir"]))
    zsasa_bin = args.zsasa_bin or Path(os.environ.get("ZSASA_BIN", "zsasa"))
    if not zsasa_bin.is_absolute() and shutil.which(str(zsasa_bin)):
        zsasa_bin = Path(shutil.which(str(zsasa_bin)) or str(zsasa_bin))

    keep_columns = list(baseline["keep_columns"])

    print(f"manifest={manifest_path}")
    print(f"input_dir={input_dir}")
    print(f"baseline_dir={baseline_dir}")
    print(f"output_dir={output_dir}")
    print(f"zsasa_bin={zsasa_bin}")
    print(f"mode={'execute' if execute else 'dry-run'}")

    if execute:
        if not input_dir.exists():
            raise SystemExit(f"input directory does not exist: {input_dir}")
        if not baseline_dir.exists():
            raise SystemExit(f"baseline directory does not exist: {baseline_dir}")
        if not zsasa_bin.exists():
            raise SystemExit(f"zsasa binary does not exist: {zsasa_bin}")

    planned: list[dict[str, object]] = []
    for run in manifest["runs"]:
        algorithm = run["algorithm"]
        if args.algorithm != "all" and args.algorithm != algorithm:
            continue
        points_flag = run["points_flag"]
        variants = list(run["variants"])
        for points, baseline_file in zip(run["points"], run["baseline_files"], strict=True):
            baseline_csv = baseline_dir.joinpath(run["baseline_subdir"], baseline_file)
            out_csv = output_dir.joinpath(algorithm, baseline_file)
            print(f"\n[{algorithm} {points}] baseline={baseline_csv}")
            zsasa_results: dict[str, dict[str, tuple[float, int]]] = {}
            for variant in variants:
                spec = ZSASA_VARIANTS[variant]
                command = planned_command(
                    zsasa_bin=zsasa_bin,
                    input_dir=input_dir,
                    output_dir=Path("<tmp>"),
                    algorithm=algorithm,
                    precision=str(spec["precision"]),
                    threads=args.threads,
                    points_flag=points_flag,
                    points=points,
                    bitmask=bool(spec["bitmask"]),
                )
                print("  plan:", " ".join(command))
                planned.append({"algorithm": algorithm, "points": points, "variant": variant, "command": command})
                if execute:
                    zsasa_results[variant] = run_zsasa_variant(
                        zsasa_bin=zsasa_bin,
                        input_dir=input_dir,
                        algorithm=algorithm,
                        variant=variant,
                        threads=args.threads,
                        points_flag=points_flag,
                        points=points,
                    )
            if execute:
                baseline_rows = read_csv(baseline_csv)
                rows = merge_rows(baseline_rows, keep_columns, variants, zsasa_results)
                columns = [column for column in keep_columns if any(column in row for row in rows)]
                columns.extend(variant for variant in variants if any(variant in row for row in rows))
                write_csv(out_csv, rows, columns)
                print(f"  wrote {out_csv} ({len(rows)} rows)")

    config = {
        "timestamp": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "input_dir": str(input_dir),
        "baseline_dir": str(baseline_dir),
        "output_dir": str(output_dir),
        "threads": args.threads,
        "execute": execute,
        "planned_commands": planned,
    }
    if execute:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_dir.joinpath("refresh_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    else:
        print("\ndry run only; pass --execute to run zsasa and write refreshed CSVs")


if __name__ == "__main__":
    main()
