#!/usr/bin/env python3
"""Export summary CSVs for the curated single-file subset rerun.

This reads refreshed zsasa result CSVs plus historical comparator CSVs. It does
not run benchmarks.
"""
from __future__ import annotations

import argparse
import csv
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT.joinpath("manifests", "single-file-sample.toml")
DEFAULT_REFRESHED = ROOT.joinpath("results", "single", "subset_v0_6_0")
DEFAULT_HISTORICAL = Path("/Users/nagaet/freesasa-zig/benchmarks/results/single/100")
DEFAULT_EXPORT_DIR = ROOT.joinpath("results", "exports")
REFRESHED_TOOLS = ["zig_f64", "zig_f32", "zig_f64_bitmask", "zig_f32_bitmask"]
HISTORICAL_COMPARATORS = ["freesasa", "rustsasa"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--refreshed-dir", type=Path, default=DEFAULT_REFRESHED)
    parser.add_argument("--historical-dir", type=Path, default=DEFAULT_HISTORICAL)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--comparison-thread", type=int, default=10)
    return parser.parse_args()


def load_selection(path: Path) -> list[str]:
    with path.open("rb") as handle:
        manifest = tomllib.load(handle)
    selection = manifest.get("subset", {}).get("selection")
    if not isinstance(selection, list) or not selection:
        raise SystemExit(f"missing subset.selection in {path}")
    return [str(item) for item in selection]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def keep_selection(rows: list[dict[str, str]], selection: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("structure") in selection]


def export_refreshed(
    refreshed_dir: Path,
    selection: list[str],
    export_dir: Path,
) -> list[dict[str, object]]:
    selected = set(selection)
    rows: list[dict[str, object]] = []
    timing_by_key: dict[tuple[str, str, str], dict[str, str]] = {}

    for tool in REFRESHED_TOOLS:
        timing_path = refreshed_dir.joinpath("timing", f"{tool}_sr", "timing.csv")
        for row in keep_selection(read_csv(timing_path), selected):
            timing_by_key[(tool, row["structure"], row["threads"])] = row

    for tool in REFRESHED_TOOLS:
        wall_path = refreshed_dir.joinpath("wall", f"{tool}_sr", "results.csv")
        for row in keep_selection(read_csv(wall_path), selected):
            timing = timing_by_key.get((tool, row["structure"], row["threads"]), {})
            rows.append(
                {
                    "source": "refreshed_v0_6_0",
                    "tool": tool,
                    "structure": row["structure"],
                    "n_atoms": row.get("n_atoms", timing.get("n_atoms", "")),
                    "threads": row["threads"],
                    "mean_s": row.get("mean_s", ""),
                    "stddev_s": row.get("stddev_s", ""),
                    "min_s": row.get("min_s", ""),
                    "max_s": row.get("max_s", ""),
                    "median_s": row.get("median_s", ""),
                    "parse_time_ms": timing.get("parse_time_ms", row.get("parse_time_ms", "")),
                    "sasa_time_ms": timing.get("sasa_time_ms", row.get("sasa_time_ms", "")),
                }
            )

    fieldnames = [
        "source",
        "tool",
        "structure",
        "n_atoms",
        "threads",
        "mean_s",
        "stddev_s",
        "min_s",
        "max_s",
        "median_s",
        "parse_time_ms",
        "sasa_time_ms",
    ]
    write_csv(export_dir.joinpath("single-file-subset-refreshed.csv"), rows, fieldnames)
    return rows


def historical_rows(
    historical_dir: Path,
    selection: set[str],
    thread: int,
) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for tool in HISTORICAL_COMPARATORS:
        path = historical_dir.joinpath(f"{tool}_sr", "results.csv")
        for row in keep_selection(read_csv(path), selection):
            if int(row["threads"]) == thread:
                result[(tool, row["structure"])] = row
    return result


def export_comparison(
    refreshed_rows: list[dict[str, object]],
    historical_dir: Path,
    selection: list[str],
    export_dir: Path,
    thread: int,
) -> None:
    selected = set(selection)
    historical = historical_rows(historical_dir, selected, thread)
    refreshed = {
        (str(row["tool"]), str(row["structure"])): row
        for row in refreshed_rows
        if int(row["threads"]) == thread
    }

    rows: list[dict[str, object]] = []
    for structure in selection:
        # Prefer refreshed n_atoms, fall back to historical comparator rows.
        n_atoms = ""
        for tool in REFRESHED_TOOLS:
            row = refreshed.get((tool, structure))
            if row and row.get("n_atoms"):
                n_atoms = row["n_atoms"]
                break
        if not n_atoms:
            for tool in HISTORICAL_COMPARATORS:
                row = historical.get((tool, structure))
                if row and row.get("n_atoms"):
                    n_atoms = row["n_atoms"]
                    break

        out: dict[str, object] = {"structure": structure, "n_atoms": n_atoms, "threads": thread}
        for tool in REFRESHED_TOOLS:
            row = refreshed.get((tool, structure), {})
            out[f"{tool}_mean_s"] = row.get("mean_s", "")
            out[f"{tool}_parse_ms"] = row.get("parse_time_ms", "")
            out[f"{tool}_sasa_ms"] = row.get("sasa_time_ms", "")
        for tool in HISTORICAL_COMPARATORS:
            row = historical.get((tool, structure), {})
            out[f"historical_{tool}_mean_s"] = row.get("mean_s", "")
            out[f"historical_{tool}_parse_ms"] = row.get("parse_time_ms", "")
            out[f"historical_{tool}_sasa_ms"] = row.get("sasa_time_ms", "")
        rows.append(out)

    fieldnames = ["structure", "n_atoms", "threads"]
    for tool in REFRESHED_TOOLS:
        fieldnames.extend([f"{tool}_mean_s", f"{tool}_parse_ms", f"{tool}_sasa_ms"])
    for tool in HISTORICAL_COMPARATORS:
        fieldnames.extend(
            [
                f"historical_{tool}_mean_s",
                f"historical_{tool}_parse_ms",
                f"historical_{tool}_sasa_ms",
            ]
        )
    write_csv(export_dir.joinpath(f"single-file-subset-comparison-t{thread}.csv"), rows, fieldnames)


def main() -> None:
    args = parse_args()
    selection = load_selection(args.manifest)
    refreshed_rows = export_refreshed(args.refreshed_dir, selection, args.export_dir)
    export_comparison(
        refreshed_rows,
        args.historical_dir,
        selection,
        args.export_dir,
        args.comparison_thread,
    )
    print(f"wrote {args.export_dir.joinpath('single-file-subset-refreshed.csv')}")
    comparison_path = args.export_dir.joinpath(
        f"single-file-subset-comparison-t{args.comparison_thread}.csv"
    )
    print(f"wrote {comparison_path}")


if __name__ == "__main__":
    main()
