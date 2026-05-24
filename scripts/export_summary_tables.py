#!/usr/bin/env python3
"""Export CSV summary tables for benchmark reporting from DuckDB."""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "tables")

ECOLI_DATASET = "UP000000625_83333_ECOLI_v6_pdb"
HUMAN_DATASET = "UP000005640_9606_HUMAN_v6_pdb"

BATCH_VARIANT_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "freesasa_batch",
    "rustsasa",
    "lahuta",
    "lahuta_bitmask",
]
SINGLE_VARIANT_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "freesasa",
    "rustsasa",
]
MD_VARIANT_ORDER = [
    "zsasa_cli_f64",
    "zsasa_cli_f32",
    "zsasa_cli_bitmask_f64",
    "zsasa_cli_bitmask_f32",
    "zsasa_mdtraj",
    "zsasa_mdtraj_bitmask",
    "zsasa_mdanalysis",
    "zsasa_mdanalysis_bitmask",
    "mdtraj",
    "mdsasa_bolt",
]

DISPLAY_NAMES = {
    "zsasa_f64": "zsasa f64",
    "zsasa_f32": "zsasa f32",
    "zsasa_bitmask_f64": "zsasa bitmask f64",
    "zsasa_bitmask_f32": "zsasa bitmask f32",
    "freesasa": "FreeSASA",
    "freesasa_batch": "FreeSASA batch",
    "rustsasa": "RustSASA",
    "lahuta": "Lahuta",
    "lahuta_bitmask": "Lahuta bitmask",
    "zsasa_cli_f64": "zsasa CLI f64",
    "zsasa_cli_f32": "zsasa CLI f32",
    "zsasa_cli_bitmask_f64": "zsasa CLI bitmask f64",
    "zsasa_cli_bitmask_f32": "zsasa CLI bitmask f32",
    "zsasa_mdtraj": "zsasa + MDTraj",
    "zsasa_mdtraj_bitmask": "zsasa + MDTraj bitmask",
    "zsasa_mdanalysis": "zsasa + MDAnalysis",
    "zsasa_mdanalysis_bitmask": "zsasa + MDAnalysis bitmask",
    "mdtraj": "MDTraj",
    "mdsasa_bolt": "mdsasa-bolt (Rust)",
}

DATASET_LABELS = {
    ECOLI_DATASET: "E. coli AFDB",
    HUMAN_DATASET: "Human AFDB",
    "5wvo_C_analysis": "5wvo_C",
    "6sup_A_analysis": "6sup_A",
    "5vz0_A_protein": "5vz0_A",
}

CSV_DESCRIPTIONS = {
    "runs_long.csv": (
        "One row per benchmark run with raw hyperfine-style statistics and common "
        "derived metrics."
    ),
    "datasets.csv": "Dataset metadata copied from the benchmark database.",
    "tools.csv": "Tool metadata copied from the benchmark database.",
    "batch_t10_summary.csv": (
        "10-thread batch performance table, including runtime/RSS ratios versus "
        "comparators."
    ),
    "batch_thread_scaling.csv": (
        "Batch runtime, throughput, RSS, speedup, and efficiency across thread "
        "counts."
    ),
    "single_file_t10_summary.csv": "10-thread single-file performance by structure and variant.",
    "single_file_thread_scaling.csv": (
        "Single-file runtime, RSS, speedup, and efficiency across thread counts."
    ),
    "md_summary.csv": (
        "Trajectory/MD performance summary with runtime/RSS ratios versus "
        "available comparators."
    ),
    "validation_pairwise_summary.csv": (
        "Pairwise SASA agreement against FreeSASA/MDTraj references."
    ),
    "comparator_ratios.csv": (
        "Long-format runtime and RSS ratios used by the comparator-ratio figures."
    ),
    "best_by_context.csv": "Fastest/highest-throughput/lowest-RSS winners by benchmark context.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def parse_note(notes: str | None, key: str) -> str | None:
    if not notes:
        return None
    match = re.search(rf"{re.escape(key)}=([^;]+)", notes)
    return match.group(1).strip() if match else None


def dataset_label(dataset_id: str) -> str:
    return DATASET_LABELS.get(dataset_id, dataset_id)


def display_name(variant: str) -> str:
    return DISPLAY_NAMES.get(variant, variant)


def batch_variant_name(row: dict[str, Any]) -> str:
    tool_id = str(row.get("tool_id") or "")
    precision = str(row.get("precision") or "")
    mode = str(row.get("mode") or "")
    if tool_id == "freesasa_batch":
        return "freesasa_batch"
    if tool_id == "rustsasa":
        return "rustsasa"
    if tool_id == "lahuta":
        return "lahuta_bitmask" if mode == "bitmask" else "lahuta"
    if tool_id == "zsasa":
        prefix = "zsasa_bitmask" if mode == "bitmask" else "zsasa"
        return f"{prefix}_{precision}"
    return f"{tool_id}_{precision}" if precision else tool_id


def single_variant_name(row: dict[str, Any]) -> str:
    tool_id = str(row.get("tool_id") or "")
    precision = str(row.get("precision") or "")
    mode = str(row.get("mode") or "")
    if tool_id == "zsasa":
        prefix = "zsasa_bitmask" if mode == "bitmask" else "zsasa"
        return f"{prefix}_{precision}"
    if tool_id == "freesasa":
        return "freesasa"
    if tool_id == "rustsasa":
        return "rustsasa"
    return f"{tool_id}_{precision}" if precision else tool_id


def md_variant_name(row: dict[str, Any]) -> str:
    tool_id = str(row.get("tool_id") or "")
    precision = str(row.get("precision") or "")
    mode = str(row.get("mode") or "")
    if tool_id == "zig":
        return f"zsasa_cli_{precision}"
    if tool_id == "zig_bitmask":
        return f"zsasa_cli_bitmask_{precision}"
    if tool_id in {
        "zsasa_mdtraj",
        "zsasa_mdtraj_bitmask",
        "zsasa_mdanalysis",
        "zsasa_mdanalysis_bitmask",
        "mdtraj",
        "mdsasa_bolt",
    }:
        return tool_id
    if mode == "bitmask":
        return f"{tool_id}_bitmask"
    return tool_id


def variant_name(row: dict[str, Any]) -> str:
    kind = row["benchmark_kind"]
    if kind == "batch":
        return batch_variant_name(row)
    if kind == "single_file":
        return single_variant_name(row)
    if kind in {"trajectory", "trajectory_validation"}:
        return md_variant_name(row)
    if kind == "validation" and row["tool_id"] == "freesasa_batch":
        return "freesasa_batch"
    if kind == "validation" and row["tool_id"] == "lahuta":
        return "lahuta_bitmask" if row.get("mode") == "bitmask" else "lahuta"
    if kind == "validation" and row["tool_id"] == "zsasa":
        return batch_variant_name(row)
    return str(row.get("tool_id") or "")


def variant_sort_key(variant: str, order: list[str]) -> tuple[int, str]:
    try:
        return (order.index(variant), variant)
    except ValueError:
        return (len(order), variant)


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def stddev(values: list[float]) -> float | None:
    clean = [value for value in values if not math.isnan(value)]
    if len(clean) < 2:
        return 0.0 if clean else None
    avg = sum(clean) / len(clean)
    return (sum((value - avg) ** 2 for value in clean) / (len(clean) - 1)) ** 0.5


def r2_score(reference: list[float], observed: list[float]) -> float | None:
    if len(reference) != len(observed) or not reference:
        return None
    avg = sum(reference) / len(reference)
    ss_tot = sum((value - avg) ** 2 for value in reference)
    if ss_tot == 0:
        return 1.0 if reference == observed else None
    ss_res = sum((obs - ref) ** 2 for ref, obs in zip(reference, observed, strict=True))
    return 1.0 - (ss_res / ss_tot)


def load_metric_map(con: duckdb.DuckDBPyConnection) -> dict[str, dict[tuple[str, str], float]]:
    metric_map: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for run_id, metric, statistic, value in con.execute(
        "SELECT run_id, metric, statistic, value FROM performance_results"
    ).fetchall():
        metric_map[run_id][(metric, statistic)] = float(value)
    return metric_map


def load_runs(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [
        "run_id",
        "benchmark_kind",
        "dataset_id",
        "tool_id",
        "algorithm",
        "precision",
        "mode",
        "n_points",
        "n_slices",
        "threads",
        "source_kind",
        "source_path",
        "manifest_id",
        "created_at",
        "status",
        "notes",
        "dataset_name",
        "dataset_role",
        "expected_count",
        "dataset_notes",
    ]
    rows = con.execute(
        """
        SELECT r.run_id, r.benchmark_kind, r.dataset_id, r.tool_id, r.algorithm,
               r.precision, r.mode, r.n_points, r.n_slices, r.threads,
               r.source_kind, r.source_path, r.manifest_id, r.created_at,
               r.status, r.notes, d.name, d.role, d.expected_count, d.notes
        FROM benchmark_runs r
        LEFT JOIN datasets d USING (dataset_id)
        ORDER BY r.benchmark_kind, r.dataset_id, r.tool_id, r.mode, r.precision,
                 r.threads, r.n_points, r.n_slices, r.run_id
        """
    ).fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def enrich_runs(
    runs: list[dict[str, Any]], metric_map: dict[str, dict[tuple[str, str], float]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for run in runs:
        stats = metric_map.get(run["run_id"], {})
        variant = variant_name(run)
        runtime_mean = stats.get(("runtime", "mean"))
        runtime_stddev = stats.get(("runtime", "stddev"))
        rss_mean_bytes = stats.get(("peak_rss", "mean"))
        rss_stddev_bytes = stats.get(("peak_rss", "stddev"))
        expected_count = run.get("expected_count")
        frame_count = expected_count if run["benchmark_kind"] == "trajectory" else None
        atom_count = parse_note(run.get("dataset_notes"), "atoms")
        structure_atoms = parse_note(run.get("notes"), "n_atoms")
        if atom_count is not None:
            atom_count_int = int(atom_count)
        else:
            atom_count_int = int(structure_atoms) if structure_atoms else None
        throughput_items_per_sec: float | None = None
        item_count: int | None = None
        item_unit = ""
        if runtime_mean and runtime_mean > 0:
            if run["benchmark_kind"] == "batch" and expected_count:
                item_count = int(expected_count)
                item_unit = "structures"
                throughput_items_per_sec = item_count / runtime_mean
            elif run["benchmark_kind"] == "trajectory" and frame_count:
                item_count = int(frame_count)
                item_unit = "frames"
                throughput_items_per_sec = item_count / runtime_mean
            elif run["benchmark_kind"] == "single_file":
                item_count = 1
                item_unit = "structure"
                throughput_items_per_sec = 1.0 / runtime_mean
        rss_mib = rss_mean_bytes / (1024 * 1024) if rss_mean_bytes is not None else None
        row = {
            "run_id": run["run_id"],
            "benchmark_kind": run["benchmark_kind"],
            "dataset_id": run["dataset_id"],
            "dataset_label": dataset_label(run["dataset_id"]),
            "dataset_role": run.get("dataset_role"),
            "variant": variant,
            "display_name": display_name(variant),
            "tool_id": run["tool_id"],
            "algorithm": run.get("algorithm"),
            "precision": run.get("precision"),
            "mode": run.get("mode"),
            "threads": run.get("threads"),
            "n_points": run.get("n_points"),
            "n_slices": run.get("n_slices"),
            "source_kind": run.get("source_kind"),
            "source_path": run.get("source_path"),
            "manifest_id": run.get("manifest_id"),
            "status": run.get("status"),
            "expected_count": expected_count,
            "structure_id": parse_note(run.get("notes"), "structure_id"),
            "structure_role": parse_note(run.get("notes"), "role"),
            "n_atoms": atom_count_int,
            "expected_chains": parse_note(run.get("notes"), "expected_chains"),
            "frame_count": frame_count,
            "runtime_mean_s": runtime_mean,
            "runtime_stddev_s": runtime_stddev,
            "runtime_min_s": stats.get(("runtime", "min")),
            "runtime_median_s": stats.get(("runtime", "median")),
            "runtime_max_s": stats.get(("runtime", "max")),
            "runtime_run_1_s": stats.get(("runtime", "run_1")),
            "runtime_run_2_s": stats.get(("runtime", "run_2")),
            "runtime_run_3_s": stats.get(("runtime", "run_3")),
            "peak_rss_mean_mib": rss_mib,
            "peak_rss_stddev_mib": rss_stddev_bytes / (1024 * 1024)
            if rss_stddev_bytes is not None
            else None,
            "peak_rss_min_mib": stats.get(("peak_rss", "min")) / (1024 * 1024)
            if stats.get(("peak_rss", "min")) is not None
            else None,
            "peak_rss_median_mib": stats.get(("peak_rss", "median")) / (1024 * 1024)
            if stats.get(("peak_rss", "median")) is not None
            else None,
            "peak_rss_max_mib": stats.get(("peak_rss", "max")) / (1024 * 1024)
            if stats.get(("peak_rss", "max")) is not None
            else None,
            "user_time_mean_s": stats.get(("user_time", "mean")),
            "system_time_mean_s": stats.get(("system_time", "mean")),
            "parse_time_ms": stats.get(("parse_time", "single")),
            "sasa_time_ms": stats.get(("sasa_time", "single")),
            "total_time_ms": stats.get(("total_time", "single")),
            "item_count": item_count,
            "item_unit": item_unit,
            "items_per_sec": throughput_items_per_sec,
            "ms_per_item": (runtime_mean * 1000 / item_count)
            if runtime_mean and item_count
            else None,
            "atoms_per_sec": (atom_count_int / runtime_mean)
            if runtime_mean and atom_count_int
            else None,
            "atom_frames_per_sec": (int(frame_count) * atom_count_int / runtime_mean)
            if runtime_mean and frame_count and atom_count_int
            else None,
            "items_per_sec_per_mib": throughput_items_per_sec / rss_mib
            if throughput_items_per_sec and rss_mib
            else None,
            "cpu_utilization_proxy": safe_div(
                (stats.get(("user_time", "mean")) or 0.0)
                + (stats.get(("system_time", "mean")) or 0.0),
                runtime_mean,
            )
            if runtime_mean
            else None,
        }
        output.append(row)
    return output


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_metadata(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    for table in ["datasets", "tools"]:
        result = con.execute(f"SELECT * FROM {table} ORDER BY 1")
        columns = [column[0] for column in result.description]
        rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        path = out_dir.joinpath(f"{table}.csv")
        write_csv(path, rows, columns)
        outputs.append(path)
    return outputs


def export_runs_long(rows: list[dict[str, Any]], out_dir: Path) -> Path:
    path = out_dir.joinpath("runs_long.csv")
    write_csv(path, rows)
    return path


def add_ratio_columns(
    row: dict[str, Any],
    baselines: dict[str, dict[str, Any]],
    comparators: list[str],
    runtime_key: str = "runtime_mean_s",
    rss_key: str = "peak_rss_mean_mib",
) -> None:
    for comparator in comparators:
        base = baselines.get(comparator)
        label = comparator.replace("_batch", "").replace("_", "_")
        row[f"runtime_speedup_vs_{label}"] = safe_div(
            base.get(runtime_key) if base else None,
            row.get(runtime_key),
        )
        row[f"rss_reduction_vs_{label}"] = safe_div(
            base.get(rss_key) if base else None,
            row.get(rss_key),
        )


def export_batch_tables(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    batch = [row for row in rows if row["benchmark_kind"] == "batch"]
    t10_output: list[dict[str, Any]] = []
    scaling_output: list[dict[str, Any]] = []
    for dataset_id in sorted({row["dataset_id"] for row in batch}):
        dataset_rows = [row for row in batch if row["dataset_id"] == dataset_id]
        t1 = {row["variant"]: row for row in dataset_rows if row["threads"] == 1}
        t10 = {row["variant"]: row for row in dataset_rows if row["threads"] == 10}
        for row in sorted(
            dataset_rows,
            key=lambda item: (
                variant_sort_key(item["variant"], BATCH_VARIANT_ORDER),
                item["threads"],
            ),
        ):
            baseline = t1.get(row["variant"])
            speedup = safe_div(
                baseline.get("runtime_mean_s") if baseline else None,
                row.get("runtime_mean_s"),
            )
            scaling_output.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_label": row["dataset_label"],
                    "variant": row["variant"],
                    "display_name": row["display_name"],
                    "threads": row["threads"],
                    "expected_count": row["expected_count"],
                    "runtime_mean_s": row["runtime_mean_s"],
                    "runtime_stddev_s": row["runtime_stddev_s"],
                    "throughput_structures_per_sec": row["items_per_sec"],
                    "ms_per_structure": row["ms_per_item"],
                    "peak_rss_mean_mib": row["peak_rss_mean_mib"],
                    "peak_rss_stddev_mib": row["peak_rss_stddev_mib"],
                    "throughput_per_mib": row["items_per_sec_per_mib"],
                    "cpu_utilization_proxy": row["cpu_utilization_proxy"],
                    "speedup_vs_1_thread": speedup,
                    "parallel_efficiency": safe_div(speedup, row["threads"]),
                }
            )
        for row in sorted(
            t10.values(),
            key=lambda item: variant_sort_key(item["variant"], BATCH_VARIANT_ORDER),
        ):
            out = {
                "dataset_id": dataset_id,
                "dataset_label": row["dataset_label"],
                "variant": row["variant"],
                "display_name": row["display_name"],
                "expected_count": row["expected_count"],
                "threads": row["threads"],
                "runtime_mean_s": row["runtime_mean_s"],
                "runtime_stddev_s": row["runtime_stddev_s"],
                "throughput_structures_per_sec": row["items_per_sec"],
                "ms_per_structure": row["ms_per_item"],
                "peak_rss_mean_mib": row["peak_rss_mean_mib"],
                "peak_rss_stddev_mib": row["peak_rss_stddev_mib"],
                "throughput_per_mib": row["items_per_sec_per_mib"],
                "cpu_utilization_proxy": row["cpu_utilization_proxy"],
            }
            add_ratio_columns(out, t10, ["freesasa_batch", "rustsasa", "lahuta_bitmask"])
            t10_output.append(out)
    outputs = [
        out_dir.joinpath("batch_t10_summary.csv"),
        out_dir.joinpath("batch_thread_scaling.csv"),
    ]
    write_csv(outputs[0], t10_output)
    write_csv(outputs[1], scaling_output)
    return outputs


def export_single_file_tables(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    single = [row for row in rows if row["benchmark_kind"] == "single_file"]
    by_structure: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in single:
        by_structure[str(row["structure_id"])].append(row)
    t10_output: list[dict[str, Any]] = []
    scaling_output: list[dict[str, Any]] = []
    for structure_id, structure_rows in sorted(
        by_structure.items(), key=lambda item: min(row["n_atoms"] or 0 for row in item[1])
    ):
        t1 = {row["variant"]: row for row in structure_rows if row["threads"] == 1}
        t10 = {row["variant"]: row for row in structure_rows if row["threads"] == 10}
        for row in sorted(
            structure_rows,
            key=lambda item: (
                variant_sort_key(item["variant"], SINGLE_VARIANT_ORDER),
                item["threads"],
            ),
        ):
            baseline = t1.get(row["variant"])
            speedup = safe_div(
                baseline.get("runtime_mean_s") if baseline else None,
                row.get("runtime_mean_s"),
            )
            scaling_output.append(
                {
                    "structure_id": structure_id,
                    "structure_role": row["structure_role"],
                    "n_atoms": row["n_atoms"],
                    "expected_chains": row["expected_chains"],
                    "variant": row["variant"],
                    "display_name": row["display_name"],
                    "threads": row["threads"],
                    "runtime_mean_s": row["runtime_mean_s"],
                    "runtime_stddev_s": row["runtime_stddev_s"],
                    "peak_rss_mean_mib": row["peak_rss_mean_mib"],
                    "peak_rss_stddev_mib": row["peak_rss_stddev_mib"],
                    "atoms_per_sec": row["atoms_per_sec"],
                    "cpu_utilization_proxy": row["cpu_utilization_proxy"],
                    "speedup_vs_1_thread": speedup,
                    "parallel_efficiency": safe_div(speedup, row["threads"]),
                }
            )
        for row in sorted(
            t10.values(),
            key=lambda item: variant_sort_key(item["variant"], SINGLE_VARIANT_ORDER),
        ):
            out = {
                "structure_id": structure_id,
                "structure_role": row["structure_role"],
                "n_atoms": row["n_atoms"],
                "expected_chains": row["expected_chains"],
                "variant": row["variant"],
                "display_name": row["display_name"],
                "threads": row["threads"],
                "runtime_mean_s": row["runtime_mean_s"],
                "runtime_stddev_s": row["runtime_stddev_s"],
                "structures_per_sec": row["items_per_sec"],
                "atoms_per_sec": row["atoms_per_sec"],
                "peak_rss_mean_mib": row["peak_rss_mean_mib"],
                "peak_rss_stddev_mib": row["peak_rss_stddev_mib"],
                "parse_time_ms": row["parse_time_ms"],
                "sasa_time_ms": row["sasa_time_ms"],
                "total_time_ms": row["total_time_ms"],
                "cpu_utilization_proxy": row["cpu_utilization_proxy"],
            }
            add_ratio_columns(out, t10, ["freesasa", "rustsasa"])
            t10_output.append(out)
    outputs = [
        out_dir.joinpath("single_file_t10_summary.csv"),
        out_dir.joinpath("single_file_thread_scaling.csv"),
    ]
    write_csv(outputs[0], t10_output)
    write_csv(outputs[1], scaling_output)
    return outputs


def export_md_summary(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    md_rows = [row for row in rows if row["benchmark_kind"] == "trajectory"]
    output: list[dict[str, Any]] = []
    for dataset_id in sorted({row["dataset_id"] for row in md_rows}):
        dataset_rows = [row for row in md_rows if row["dataset_id"] == dataset_id]
        by_variant = {row["variant"]: row for row in dataset_rows}
        for row in sorted(
            dataset_rows,
            key=lambda item: variant_sort_key(item["variant"], MD_VARIANT_ORDER),
        ):
            out = {
                "dataset_id": dataset_id,
                "dataset_label": row["dataset_label"],
                "frame_count": row["frame_count"],
                "atom_count": row["n_atoms"],
                "variant": row["variant"],
                "display_name": row["display_name"],
                "threads": row["threads"],
                "n_points": row["n_points"],
                "runtime_mean_s": row["runtime_mean_s"],
                "runtime_stddev_s": row["runtime_stddev_s"],
                "frames_per_sec": row["items_per_sec"],
                "ms_per_frame": row["ms_per_item"],
                "atom_frames_per_sec": row["atom_frames_per_sec"],
                "peak_rss_mean_mib": row["peak_rss_mean_mib"],
                "peak_rss_stddev_mib": row["peak_rss_stddev_mib"],
                "frames_per_sec_per_mib": row["items_per_sec_per_mib"],
                "cpu_utilization_proxy": row["cpu_utilization_proxy"],
            }
            add_ratio_columns(out, by_variant, ["mdtraj", "mdsasa_bolt"])
            output.append(out)
    path = out_dir.joinpath("md_summary.csv")
    write_csv(path, output)
    return [path]


def validation_values(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = defaultdict(dict)
    for run_id, structure_id, total_sasa in con.execute(
        "SELECT run_id, structure_id, total_sasa FROM validation_results WHERE status = 'ok'"
    ).fetchall():
        if total_sasa is not None:
            values[run_id][structure_id] = float(total_sasa)
    return values


def validation_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["benchmark_kind"],
        row["dataset_id"],
        row["algorithm"],
        row["n_points"],
        row["n_slices"],
    )


def export_validation_summary(
    con: duckdb.DuckDBPyConnection,
    rows: list[dict[str, Any]],
    out_dir: Path,
) -> list[Path]:
    validation_runs = [
        row
        for row in rows
        if row["benchmark_kind"] in {"validation", "trajectory_validation"}
    ]
    values = validation_values(con)
    refs: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in validation_runs:
        is_static_reference = (
            row["benchmark_kind"] == "validation"
            and row["tool_id"] == "freesasa_batch"
        )
        is_trajectory_reference = (
            row["benchmark_kind"] == "trajectory_validation"
            and row["tool_id"] == "mdtraj"
        )
        if is_static_reference or is_trajectory_reference:
            refs[validation_key(row)] = row
    output: list[dict[str, Any]] = []
    for row in validation_runs:
        ref = refs.get(validation_key(row))
        if ref is None or row["run_id"] == ref["run_id"]:
            continue
        ref_values = values.get(ref["run_id"], {})
        obs_values = values.get(row["run_id"], {})
        shared = sorted(set(ref_values) & set(obs_values))
        ref_list = [ref_values[key] for key in shared]
        obs_list = [obs_values[key] for key in shared]
        abs_errors = [abs(obs - ref) for ref, obs in zip(ref_list, obs_list, strict=True)]
        rel_errors = [
            abs(obs - ref) / abs(ref) * 100.0
            for ref, obs in zip(ref_list, obs_list, strict=True)
            if ref != 0
        ]
        output.append(
            {
                "benchmark_kind": row["benchmark_kind"],
                "dataset_id": row["dataset_id"],
                "dataset_label": row["dataset_label"],
                "variant": row["variant"],
                "display_name": row["display_name"],
                "tool_id": row["tool_id"],
                "algorithm": row["algorithm"],
                "precision": row["precision"],
                "mode": row["mode"],
                "n_points": row["n_points"],
                "n_slices": row["n_slices"],
                "threads": row["threads"],
                "reference_run_id": ref["run_id"],
                "reference_variant": ref["variant"],
                "n_shared": len(shared),
                "r2": r2_score(ref_list, obs_list),
                "mean_abs_error": mean(abs_errors),
                "max_abs_error": max(abs_errors) if abs_errors else None,
                "mean_relative_error_percent": mean(rel_errors),
                "max_relative_error_percent": max(rel_errors) if rel_errors else None,
                "stddev_relative_error_percent": stddev(rel_errors),
            }
        )
    path = out_dir.joinpath("validation_pairwise_summary.csv")
    write_csv(path, output)
    return [path]


def export_best_by_context(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    output: list[dict[str, Any]] = []

    def add_winner(
        context: str,
        rows_in_context: list[dict[str, Any]],
        metric: str,
        objective: str,
    ) -> None:
        usable = [row for row in rows_in_context if row.get(metric) is not None]
        if not usable:
            return
        reverse = objective == "max"
        winner = sorted(usable, key=lambda row: row[metric], reverse=reverse)[0]
        output.append(
            {
                "context": context,
                "metric": metric,
                "objective": objective,
                "winner_variant": winner["variant"],
                "winner_display_name": winner["display_name"],
                "winner_value": winner[metric],
                "dataset_id": winner["dataset_id"],
                "dataset_label": winner["dataset_label"],
                "structure_id": winner.get("structure_id"),
                "threads": winner.get("threads"),
            }
        )

    batch_t10 = [row for row in rows if row["benchmark_kind"] == "batch" and row["threads"] == 10]
    for dataset_id in sorted({row["dataset_id"] for row in batch_t10}):
        context_rows = [row for row in batch_t10 if row["dataset_id"] == dataset_id]
        add_winner(f"batch:{dataset_id}:t10", context_rows, "runtime_mean_s", "min")
        add_winner(f"batch:{dataset_id}:t10", context_rows, "items_per_sec", "max")
        add_winner(f"batch:{dataset_id}:t10", context_rows, "peak_rss_mean_mib", "min")
    single_t10 = [
        row for row in rows if row["benchmark_kind"] == "single_file" and row["threads"] == 10
    ]
    for structure_id in sorted({row["structure_id"] for row in single_t10}):
        context_rows = [row for row in single_t10 if row["structure_id"] == structure_id]
        add_winner(f"single_file:{structure_id}:t10", context_rows, "runtime_mean_s", "min")
        add_winner(f"single_file:{structure_id}:t10", context_rows, "atoms_per_sec", "max")
        add_winner(f"single_file:{structure_id}:t10", context_rows, "peak_rss_mean_mib", "min")
    md = [row for row in rows if row["benchmark_kind"] == "trajectory"]
    for dataset_id in sorted({row["dataset_id"] for row in md}):
        context_rows = [row for row in md if row["dataset_id"] == dataset_id]
        add_winner(f"trajectory:{dataset_id}", context_rows, "runtime_mean_s", "min")
        add_winner(f"trajectory:{dataset_id}", context_rows, "items_per_sec", "max")
        add_winner(f"trajectory:{dataset_id}", context_rows, "peak_rss_mean_mib", "min")
    path = out_dir.joinpath("best_by_context.csv")
    write_csv(path, output)
    return [path]


def add_ratio_rows(
    output: list[dict[str, Any]],
    *,
    context: str,
    benchmark_kind: str,
    dataset_id: str,
    dataset_label_value: str,
    target: dict[str, Any],
    comparator: dict[str, Any],
) -> None:
    ratio_specs = [
        ("runtime_speedup", "runtime_mean_s", "higher means target is faster"),
        ("rss_reduction", "peak_rss_mean_mib", "higher means target uses less memory"),
    ]
    for metric_name, value_key, interpretation in ratio_specs:
        ratio = safe_div(comparator.get(value_key), target.get(value_key))
        if ratio is None:
            continue
        output.append(
            {
                "context": context,
                "benchmark_kind": benchmark_kind,
                "dataset_id": dataset_id,
                "dataset_label": dataset_label_value,
                "structure_id": target.get("structure_id"),
                "target_variant": target["variant"],
                "target_display_name": target["display_name"],
                "comparator_variant": comparator["variant"],
                "comparator_display_name": comparator["display_name"],
                "metric": metric_name,
                "ratio": ratio,
                "target_value": target.get(value_key),
                "comparator_value": comparator.get(value_key),
                "interpretation": interpretation,
            }
        )


def export_comparator_ratios(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    output: list[dict[str, Any]] = []
    batch_t10 = [row for row in rows if row["benchmark_kind"] == "batch" and row["threads"] == 10]
    for dataset_id in sorted({row["dataset_id"] for row in batch_t10}):
        context_rows = [row for row in batch_t10 if row["dataset_id"] == dataset_id]
        by_variant = {row["variant"]: row for row in context_rows}
        targets = [variant for variant in BATCH_VARIANT_ORDER if variant.startswith("zsasa")]
        comparators = ["freesasa_batch", "rustsasa", "lahuta_bitmask"]
        for target_variant in targets:
            target = by_variant.get(target_variant)
            if target is None:
                continue
            for comparator_variant in comparators:
                comparator = by_variant.get(comparator_variant)
                if comparator is None:
                    continue
                add_ratio_rows(
                    output,
                    context=f"batch:{dataset_id}:t10",
                    benchmark_kind="batch",
                    dataset_id=dataset_id,
                    dataset_label_value=target["dataset_label"],
                    target=target,
                    comparator=comparator,
                )

    single_t10 = [
        row for row in rows if row["benchmark_kind"] == "single_file" and row["threads"] == 10
    ]
    for structure_id in sorted({row["structure_id"] for row in single_t10}):
        context_rows = [row for row in single_t10 if row["structure_id"] == structure_id]
        by_variant = {row["variant"]: row for row in context_rows}
        targets = [variant for variant in SINGLE_VARIANT_ORDER if variant.startswith("zsasa")]
        for target_variant in targets:
            target = by_variant.get(target_variant)
            if target is None:
                continue
            for comparator_variant in ["freesasa", "rustsasa"]:
                comparator = by_variant.get(comparator_variant)
                if comparator is None:
                    continue
                add_ratio_rows(
                    output,
                    context=f"single_file:{structure_id}:t10",
                    benchmark_kind="single_file",
                    dataset_id=target["dataset_id"],
                    dataset_label_value=target["dataset_label"],
                    target=target,
                    comparator=comparator,
                )

    md_rows = [row for row in rows if row["benchmark_kind"] == "trajectory"]
    for dataset_id in sorted({row["dataset_id"] for row in md_rows}):
        context_rows = [row for row in md_rows if row["dataset_id"] == dataset_id]
        by_variant = {row["variant"]: row for row in context_rows}
        targets = [variant for variant in MD_VARIANT_ORDER if variant.startswith("zsasa")]
        if "mdtraj" in by_variant and "mdsasa_bolt" in by_variant:
            targets.append("mdsasa_bolt")
        for target_variant in targets:
            target = by_variant.get(target_variant)
            if target is None:
                continue
            for comparator_variant in ["mdtraj", "mdsasa_bolt"]:
                comparator = by_variant.get(comparator_variant)
                if comparator is None or comparator_variant == target_variant:
                    continue
                add_ratio_rows(
                    output,
                    context=f"trajectory:{dataset_id}",
                    benchmark_kind="trajectory",
                    dataset_id=dataset_id,
                    dataset_label_value=target["dataset_label"],
                    target=target,
                    comparator=comparator,
                )
    path = out_dir.joinpath("comparator_ratios.csv")
    write_csv(path, output)
    return [path]


def write_index(out_dir: Path, outputs: list[Path]) -> Path:
    rows = []
    for path in sorted(outputs):
        with path.open(newline="", encoding="utf-8") as handle:
            row_count = max(sum(1 for _line in handle) - 1, 0)
        rows.append((path.name, row_count, CSV_DESCRIPTIONS.get(path.name, "")))
    lines = [
        "# Benchmark summary tables",
        "",
        "CSV tables generated from `results/benchmark.duckdb` for reporting "
        "and manuscript/table drafting.",
        "",
        "| file | rows | description |",
        "| --- | ---: | --- |",
    ]
    for name, row_count, description in rows:
        lines.append(f"| `{name}` | {row_count} | {description} |")
    lines.extend(
        [
            "",
            "Notes:",
            "- Runtime ratios are `comparator runtime / variant runtime`; "
            "higher is faster than the comparator.",
            "- RSS ratios are `comparator peak RSS / variant peak RSS`; "
            "higher uses less memory than the comparator.",
            "- CPU utilization proxy is `(user_time + system_time) / wall_time`.",
        ]
    )
    path = out_dir.joinpath("index.md")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        metric_map = load_metric_map(con)
        rows = enrich_runs(load_runs(con), metric_map)
        outputs: list[Path] = []
        outputs.extend(export_metadata(con, out_dir))
        outputs.append(export_runs_long(rows, out_dir))
        outputs.extend(export_batch_tables(rows, out_dir))
        outputs.extend(export_single_file_tables(rows, out_dir))
        outputs.extend(export_md_summary(rows, out_dir))
        outputs.extend(export_validation_summary(con, rows, out_dir))
        outputs.extend(export_comparator_ratios(rows, out_dir))
        outputs.extend(export_best_by_context(rows, out_dir))
        index = write_index(out_dir, outputs)
    finally:
        con.close()
    print(f"wrote {len(outputs)} CSV tables under {out_dir}")
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
