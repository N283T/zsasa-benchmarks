#!/usr/bin/env python3
"""Generate trajectory/MD performance figures from the benchmark DuckDB database."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

try:
    from scripts.benchlib.reporting import adopted_for_reporting, run_set
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from benchlib.reporting import adopted_for_reporting, run_set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures", "md")
MD_RUN_SET = "v0_9_0_md_128"

DATASET_ORDER = ["5wvo_C_analysis", "6sup_A_analysis", "5vz0_A_protein"]
VARIANT_ORDER = [
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
ZSASA_MD_VARIANTS = [
    "zsasa_cli_f64",
    "zsasa_cli_f32",
    "zsasa_cli_bitmask_f64",
    "zsasa_cli_bitmask_f32",
    "zsasa_mdtraj",
    "zsasa_mdtraj_bitmask",
    "zsasa_mdanalysis",
    "zsasa_mdanalysis_bitmask",
]
MD_COMPARATOR_VARIANTS = ["mdtraj", "mdsasa_bolt"]
COLORS = {
    "zsasa_cli_f64": "#f39c12",
    "zsasa_cli_f32": "#f6c85f",
    "zsasa_cli_bitmask_f64": "#e67e22",
    "zsasa_cli_bitmask_f32": "#ffb347",
    "zsasa_mdtraj": "#d35400",
    "zsasa_mdtraj_bitmask": "#a04000",
    "zsasa_mdanalysis": "#b9770e",
    "zsasa_mdanalysis_bitmask": "#7e5109",
    "mdtraj": "#3498db",
    "mdsasa_bolt": "#2ecc71",
}
MARKERS = {
    "zsasa_cli_f64": "o",
    "zsasa_cli_f32": "o",
    "zsasa_cli_bitmask_f64": "o",
    "zsasa_cli_bitmask_f32": "o",
    "zsasa_mdtraj": "^",
    "zsasa_mdtraj_bitmask": "^",
    "zsasa_mdanalysis": "s",
    "zsasa_mdanalysis_bitmask": "s",
    "mdtraj": "^",
    "mdsasa_bolt": "s",
}
DISPLAY_NAMES = {
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
    "5wvo_C_analysis": "5wvo_C (1,001 frames, 3,858 atoms)",
    "6sup_A_analysis": "6sup_A (1,001 frames, 33,377 atoms)",
    "5vz0_A_protein": "5vz0_A (10,001 frames, 17,910 atoms)",
}
MD_STORY_DATASET_LABELS = {
    "5wvo_C_analysis": "5wvo_C",
    "6sup_A_analysis": "6sup_A",
    "5vz0_A_protein": "5vz0_A",
}
MD_STORY_VARIANTS = [
    "zsasa_cli_f64",
    "zsasa_cli_bitmask_f32",
    "zsasa_mdtraj",
    "zsasa_mdtraj_bitmask",
    "zsasa_mdanalysis",
    "zsasa_mdanalysis_bitmask",
    "mdtraj",
    "mdsasa_bolt",
]
MD_STORY_DISPLAY_NAMES = {
    "zsasa_cli_f64": "zsasa f64",
    "zsasa_cli_bitmask_f32": "zsasa bitmask f32",
}


def md_variant_name(run: dict[str, Any]) -> str:
    tool_id = str(run.get("tool_id") or "")
    precision = str(run.get("precision") or "")
    mode = str(run.get("mode") or "")
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


def milliseconds_per_frame(mean_s: float, frame_count: int) -> float:
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    return mean_s * 1000.0 / frame_count


def atom_frames_per_second(frame_count: int, atom_count: int, mean_s: float) -> float:
    if mean_s <= 0:
        raise ValueError("mean_s must be positive")
    return frame_count * atom_count / mean_s


def frames_per_second(frame_count: int, mean_s: float) -> float:
    if mean_s <= 0:
        raise ValueError("mean_s must be positive")
    return frame_count / mean_s


def display_name(variant: str) -> str:
    return DISPLAY_NAMES.get(variant, variant)


def color_for(variant: str) -> str:
    return COLORS.get(variant, "#7f8c8d")


def marker_for(variant: str) -> str:
    return MARKERS.get(variant, "o")


def md_rss_label_style(dataset_id: str, variant: str) -> dict[str, Any]:
    arrowprops = {"arrowstyle": "-", "color": "0.35", "lw": 0.7}

    if variant == "mdsasa_bolt":
        if dataset_id == "5vz0_A_protein":
            return {
                "xytext": (-10, 9),
                "ha": "right",
                "va": "bottom",
                "arrowprops": arrowprops,
            }
        return {"xytext": (-10, 0), "ha": "right", "va": "center", "arrowprops": arrowprops}

    if dataset_id == "5vz0_A_protein":
        styles = {
            "zsasa_cli_f32": (24, 12, "left", "bottom"),
            "zsasa_cli_f64": (24, -12, "left", "top"),
            "zsasa_cli_bitmask_f32": (24, 4, "left", "bottom"),
            "zsasa_cli_bitmask_f64": (24, -12, "left", "top"),
        }
        if variant in styles:
            x, y, ha, va = styles[variant]
            return {"xytext": (x, y), "ha": ha, "va": va, "arrowprops": arrowprops}

    if dataset_id == "6sup_A_analysis":
        if variant.endswith("_f32"):
            return {"xytext": (8, 7), "ha": "left", "va": "bottom", "arrowprops": arrowprops}
        if variant.endswith("_f64"):
            return {"xytext": (8, -7), "ha": "left", "va": "top", "arrowprops": arrowprops}
        if variant.startswith("zsasa_mdanalysis"):
            return {"xytext": (8, -7), "ha": "left", "va": "top", "arrowprops": arrowprops}
        if variant.startswith("zsasa_mdtraj") or variant == "mdtraj":
            return {"xytext": (8, 7), "ha": "left", "va": "bottom", "arrowprops": arrowprops}

    if variant.endswith("_f32"):
        return {"xytext": (8, 7), "ha": "left", "va": "bottom"}
    if variant.endswith("_f64"):
        return {"xytext": (8, -7), "ha": "left", "va": "top"}

    return {"xytext": (8, 0), "ha": "left", "va": "center"}


def variant_sort_key(variant: str) -> tuple[int, str]:
    try:
        return (VARIANT_ORDER.index(variant), variant)
    except ValueError:
        return (len(VARIANT_ORDER), variant)


def dataset_sort_key(dataset_id: str) -> tuple[int, str]:
    try:
        return (DATASET_ORDER.index(dataset_id), dataset_id)
    except ValueError:
        return (len(DATASET_ORDER), dataset_id)


def dataset_label(dataset_id: str) -> str:
    return DATASET_LABELS.get(dataset_id, dataset_id)


def parse_atom_count(notes: str | None) -> int | None:
    if not notes:
        return None
    match = re.search(r"atoms=(\d+)", notes)
    return int(match.group(1)) if match else None


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 140,
            "savefig.dpi": 200,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(fig: plt.Figure, out_dir: Path, name: str) -> list[Path]:
    written: list[Path] = []
    for ext in ("png", "svg", "pdf"):
        path = out_dir.joinpath(ext, f"{name}.{ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        written.append(path)
    plt.close(fig)
    return written


def add_panel_label(ax: plt.Axes, label: str) -> None:
    """Place a consistent publication-style label above a panel."""
    ax.text(
        -0.12,
        1.04,
        f"({label})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        clip_on=False,
    )


def load_md_rows(db_path: Path, *, include_options: bool = False) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        columns = [
            "run_id",
            "dataset_id",
            "tool_id",
            "precision",
            "mode",
            "bitmask_variant",
            "threads",
            "n_points",
            "frame_count",
            "notes",
            "source_path",
            "status",
        ]
        run_rows = con.execute(
            """
            SELECT r.run_id, r.dataset_id, r.tool_id, r.precision, r.mode, r.variant,
                   r.threads, r.n_points, d.expected_count, d.notes, r.source_path, r.status
            FROM benchmark_runs r
            JOIN datasets d USING (dataset_id)
            WHERE r.benchmark_kind = 'trajectory'
            ORDER BY r.dataset_id, r.tool_id, r.mode, r.precision
            """
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for raw in run_rows:
            run = dict(zip(columns, raw, strict=True))
            if not adopted_for_reporting("trajectory", run["source_path"], run["status"]):
                continue
            source = run_set(run["source_path"])
            if source != MD_RUN_SET:
                continue
            if not include_options:
                if run["threads"] not in {None, 10}:
                    continue
                if run["tool_id"] == "zig_bitmask" and run["bitmask_variant"] != "single_corrected":
                    continue
            stats = {
                (metric, statistic): value
                for metric, statistic, value in con.execute(
                    """
                    SELECT metric, statistic, value
                    FROM performance_results
                    WHERE run_id = ?
                    """,
                    [run["run_id"]],
                ).fetchall()
            }
            mean_s = float(stats[("runtime", "mean")])
            median_s = float(stats.get(("runtime", "median")) or mean_s)
            stddev_s = float(stats.get(("runtime", "stddev")) or 0.0)
            frame_count = int(run["frame_count"])
            atom_count = parse_atom_count(run.get("notes")) or 0
            rss_bytes = float(stats.get(("peak_rss", "mean")) or 0.0)
            rss_stddev_bytes = float(stats.get(("peak_rss", "stddev")) or 0.0)
            variant = md_variant_name(run)
            fps = frames_per_second(frame_count, mean_s)
            rows.append(
                {
                    "dataset_id": run["dataset_id"],
                    "variant": variant,
                    "threads": run["threads"],
                    "bitmask_variant": run["bitmask_variant"],
                    "run_set": source,
                    "n_points": run["n_points"],
                    "mean_s": mean_s,
                    "median_s": median_s,
                    "stddev_s": stddev_s,
                    "frame_count": frame_count,
                    "atom_count": atom_count,
                    "fps": fps,
                    "fps_stddev": frame_count * stddev_s / (mean_s**2),
                    "ms_per_frame": milliseconds_per_frame(mean_s, frame_count),
                    "atom_frames_per_sec": atom_frames_per_second(frame_count, atom_count, mean_s)
                    if atom_count
                    else 0.0,
                    "rss_mib": rss_bytes / (1024 * 1024),
                    "rss_stddev_mib": rss_stddev_bytes / (1024 * 1024),
                    "fps_per_mib": fps / (rss_bytes / (1024 * 1024)) if rss_bytes else 0.0,
                    "user_time_s": float(stats.get(("user_time", "mean")) or 0.0),
                    "system_time_s": float(stats.get(("system_time", "mean")) or 0.0),
                }
            )
        return sorted(
            rows,
            key=lambda row: (dataset_sort_key(row["dataset_id"]), variant_sort_key(row["variant"])),
        )
    finally:
        con.close()


def load_md_correction_accuracy(
    db_path: Path,
    *,
    dataset_id: str = "5wvo_C_analysis",
    n_points: int = 128,
) -> list[dict[str, Any]]:
    """Summarize frame-wise bitmask differences from zsasa f32."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        columns = [
            "run_id",
            "tool_id",
            "precision",
            "variant",
            "source_path",
            "status",
        ]
        raw_runs = con.execute(
            """
            SELECT run_id, tool_id, precision, variant, source_path, status
            FROM benchmark_runs
            WHERE benchmark_kind = 'trajectory_validation'
              AND dataset_id = ?
              AND n_points = ?
              AND (
                  (tool_id = 'zig' AND precision = 'f32')
                  OR (
                      tool_id = 'zig_bitmask'
                      AND precision = 'f32'
                      AND variant IN ('single', 'single_corrected')
                  )
              )
            """,
            [dataset_id, n_points],
        ).fetchall()
        runs = [
            dict(zip(columns, row, strict=True))
            for row in raw_runs
            if adopted_for_reporting("trajectory_validation", row[-2], row[-1])
        ]
        run_ids: dict[str, str] = {}
        for run in runs:
            if run["tool_id"] == "zig":
                run_ids["reference"] = str(run["run_id"])
            else:
                run_ids[str(run["variant"])] = str(run["run_id"])
        if not {"reference", "single", "single_corrected"}.issubset(run_ids):
            return []

        values: dict[str, dict[str, float]] = {}
        for key, run_id in run_ids.items():
            values[key] = {
                str(frame): float(total_sasa)
                for frame, total_sasa in con.execute(
                    """
                    SELECT structure_id, total_sasa
                    FROM validation_results
                    WHERE run_id = ? AND total_sasa IS NOT NULL
                    """,
                    [run_id],
                ).fetchall()
            }
        common_frames = set.intersection(*(set(items) for items in values.values()))
        if not common_frames:
            return []

        summaries = [
            {
                "accuracy_key": "reference",
                "variant": "zsasa_cli_f32",
                "bitmask_variant": None,
                "mean_abs_relative_difference": 0.0,
                "p05_abs_relative_difference": 0.0,
                "p95_abs_relative_difference": 0.0,
                "n_frames": len(common_frames),
            }
        ]
        reference = values["reference"]
        for key in ("single", "single_corrected"):
            differences = np.asarray(
                [
                    abs(100.0 * (values[key][frame] - reference[frame]) / reference[frame])
                    for frame in common_frames
                    if reference[frame] != 0.0
                ],
                dtype=float,
            )
            summaries.append(
                {
                    "accuracy_key": key,
                    "variant": "zsasa_cli_bitmask_f32",
                    "bitmask_variant": key,
                    "mean_abs_relative_difference": float(np.mean(differences)),
                    "p05_abs_relative_difference": float(np.percentile(differences, 5)),
                    "p95_abs_relative_difference": float(np.percentile(differences, 95)),
                    "n_frames": len(differences),
                }
            )
        return summaries
    finally:
        con.close()


def group_by_dataset(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["dataset_id"]].append(row)
    return {
        key: sorted(value, key=lambda row: variant_sort_key(row["variant"]))
        for key, value in grouped.items()
    }


def plot_bar_grid(
    rows: list[dict[str, Any]],
    *,
    metric: str,
    ylabel: str,
    title: str,
    out_dir: Path,
    name: str,
    lower_is_better: bool = False,
    yscale: str = "linear",
) -> list[Path]:
    grouped = group_by_dataset(rows)
    datasets = sorted(grouped, key=dataset_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(6.4 * len(datasets), 5.8),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle(title)
    for ax, dataset_id in zip(axes[0], datasets, strict=True):
        items = sorted(
            grouped[dataset_id], key=lambda row: row[metric], reverse=not lower_is_better
        )
        ax.bar(
            [display_name(row["variant"]) for row in items],
            [row[metric] for row in items],
            color=[color_for(row["variant"]) for row in items],
        )
        ax.set_title(dataset_label(dataset_id))
        ax.set_ylabel(ylabel)
        if yscale != "linear":
            ax.set_yscale(yscale)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    return save_figure(fig, out_dir, name)


def zsasa_only_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["variant"].startswith("zsasa")]


def md_story_display_name(variant: str) -> str:
    return MD_STORY_DISPLAY_NAMES.get(variant, display_name(variant))


def md_performance_story_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep precision extremes, wrappers, and external trajectory comparators."""
    selected = set(MD_STORY_VARIANTS)
    return [row for row in rows if row["variant"] in selected]


def plot_md_performance_memory_story(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show trajectory throughput and memory with native and wrapper paths."""
    selected = md_performance_story_rows(rows)
    grouped = group_by_dataset(selected)
    datasets = sorted(grouped, key=dataset_sort_key)
    if not datasets:
        return []

    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(4.4 * len(datasets), 4.6),
        squeeze=False,
        layout="constrained",
    )
    for index, (ax, dataset_id) in enumerate(zip(axes[0], datasets, strict=True)):
        for row in grouped[dataset_id]:
            ax.errorbar(
                row["rss_mib"],
                row["fps"],
                xerr=row["rss_stddev_mib"],
                yerr=row["fps_stddev"],
                color=color_for(row["variant"]),
                marker=marker_for(row["variant"]),
                markeredgecolor="#333333",
                markeredgewidth=0.4,
                markersize=7,
                capsize=2,
                linestyle="none",
                zorder=3,
            )
            label_style = md_rss_label_style(dataset_id, row["variant"])
            ax.annotate(
                md_story_display_name(row["variant"]),
                (row["rss_mib"], row["fps"]),
                xytext=label_style["xytext"],
                textcoords="offset points",
                ha=label_style["ha"],
                va=label_style["va"],
                arrowprops=label_style.get("arrowprops"),
                fontsize=7.2,
            )
        ax.set_xscale("log")
        xmin = min(row["rss_mib"] for row in grouped[dataset_id])
        xmax = max(row["rss_mib"] for row in grouped[dataset_id])
        ymax = max(row["fps"] + row["fps_stddev"] for row in grouped[dataset_id])
        ax.set_xlim(xmin / 1.4, xmax * 1.4)
        ax.set_ylim(-0.06 * ymax, 1.15 * ymax)
        ax.set_yticks([tick for tick in ax.get_yticks() if tick >= 0])
        ax.set_title(DATASET_LABELS[dataset_id], fontsize=9.5)
        ax.set_xlabel("Peak RSS (MiB)")
        ax.set_ylabel(r"Throughput (frames s$^{-1}$)")
        add_panel_label(ax, chr(ord("a") + index))
    fig.suptitle("Trajectory throughput and peak memory", fontsize=11)
    return save_figure(fig, out_dir, "md_performance_memory_story")


def ratio_with_propagated_sd(
    numerator: dict[str, Any],
    denominator: dict[str, Any],
    *,
    value_key: str,
    sd_key: str,
) -> tuple[float, float]:
    """Return a ratio and independent-error propagation from two SDs."""
    numerator_value = float(numerator[value_key])
    denominator_value = float(denominator[value_key])
    ratio = numerator_value / denominator_value
    uncertainty = ratio * np.hypot(
        float(numerator[sd_key]) / numerator_value,
        float(denominator[sd_key]) / denominator_value,
    )
    return ratio, float(uncertainty)


def zsasa_detail_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the two native 5vz0_A thread-overcommit paths."""
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row["dataset_id"] != "5vz0_A_protein":
            continue
        variant = row["variant"]
        keep_native_f64 = (
            variant == "zsasa_cli_f64" and row["threads"] in {10, 20, 40}
        )
        keep_corrected_bitmask = (
            variant == "zsasa_cli_bitmask_f32"
            and row["threads"] in {10, 20, 40}
            and row["bitmask_variant"] == "single_corrected"
        )
        if keep_native_f64 or keep_corrected_bitmask:
            selected.append(row)
    return selected


def plot_md_zsasa_performance_memory_detail(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show native zsasa thread paths for the longest trajectory."""
    selected = zsasa_detail_rows(rows)
    grouped = group_by_dataset(selected)
    datasets = sorted(grouped, key=dataset_sort_key)
    if not datasets:
        return []

    native_styles = {
        "zsasa_cli_f64": {
            "color": color_for("zsasa_cli_f64"),
            "marker": "o",
            "label": "zsasa f64",
        },
        "zsasa_cli_bitmask_f32": {
            "color": "#e67e22",
            "marker": "s",
            "label": "zsasa bitmask f32",
        },
    }
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(6.8, 4.7),
        squeeze=False,
        layout="constrained",
    )
    for index, (ax, dataset_id) in enumerate(zip(axes[0], datasets, strict=True)):
        dataset_rows = grouped[dataset_id]
        for variant, style in native_styles.items():
            path_rows = sorted(
                [
                    row
                    for row in dataset_rows
                    if row["variant"] == variant
                    and (
                        variant != "zsasa_cli_bitmask_f32"
                        or row["bitmask_variant"] == "single_corrected"
                    )
                ],
                key=lambda row: row["threads"],
            )
            if not path_rows:
                continue
            ax.errorbar(
                [row["rss_mib"] for row in path_rows],
                [row["fps"] for row in path_rows],
                xerr=[row["rss_stddev_mib"] for row in path_rows],
                yerr=[row["fps_stddev"] for row in path_rows],
                color=style["color"],
                marker=style["marker"],
                markersize=6.5,
                linewidth=2.0,
                capsize=2,
                zorder=3,
            )
            for row in path_rows:
                above = variant == "zsasa_cli_bitmask_f32"
                ax.annotate(
                    str(row["threads"]),
                    (row["rss_mib"], row["fps"]),
                    xytext=(0, 7 if above else -9),
                    textcoords="offset points",
                    ha="center",
                    va="bottom" if above else "top",
                    color=style["color"],
                    fontsize=7.5,
                    fontweight="bold",
                )

        xmin = min(row["rss_mib"] for row in dataset_rows)
        xmax = max(row["rss_mib"] for row in dataset_rows)
        ymax = max(row["fps"] + row["fps_stddev"] for row in dataset_rows)
        x_padding = 0.12 * (xmax - xmin)
        ax.set_xlim(max(0, xmin - x_padding), xmax + x_padding)
        ax.set_ylim(-0.06 * ymax, 1.17 * ymax)
        ax.set_yticks([tick for tick in ax.get_yticks() if tick >= 0])
        ax.set_title(DATASET_LABELS[dataset_id], fontsize=10)
        ax.set_xlabel("Peak RSS (MiB)")
        ax.set_ylabel(r"Throughput (frames s$^{-1}$)")
        if len(datasets) > 1:
            add_panel_label(ax, chr(ord("a") + index))

    legend_handles = [
        plt.Line2D(
            [0],
            [0],
            color=style["color"],
            marker=style["marker"],
            linewidth=2.0,
            label=style["label"],
        )
        for style in native_styles.values()
    ]
    fig.legend(
        handles=legend_handles,
        loc="outside lower center",
        ncol=2,
        frameon=False,
    )
    fig.suptitle("Native zsasa under thread overcommit", fontsize=11)
    return save_figure(fig, out_dir, "md_zsasa_performance_memory_detail")


def plot_md_correction_accuracy_throughput(
    rows: list[dict[str, Any]],
    accuracy_rows: list[dict[str, Any]],
    out_dir: Path,
) -> list[Path]:
    """Combine matched 128-point validation and throughput measurements."""
    performance = {
        (row["variant"], row["bitmask_variant"]): row
        for row in rows
        if row["dataset_id"] == "5wvo_C_analysis"
        and row["n_points"] == 128
        and row["threads"] == 10
    }
    plotted_rows = [
        {**accuracy, **performance[(accuracy["variant"], accuracy["bitmask_variant"])]}
        for accuracy in accuracy_rows
        if (accuracy["variant"], accuracy["bitmask_variant"]) in performance
    ]
    if len(plotted_rows) != 3:
        return []

    styles = {
        "reference": {
            "color": "#f39c12",
            "marker": "o",
            "label": "zsasa f32",
            "offset": (9, 9),
        },
        "single": {
            "color": "#9f4d00",
            "marker": "s",
            "label": "Raw bitmask f32",
            "offset": (8, -15),
        },
        "single_corrected": {
            "color": "#e67e22",
            "marker": "s",
            "label": "Corrected bitmask f32",
            "offset": (8, -15),
        },
    }
    fig, ax = plt.subplots(figsize=(7.4, 4.8), layout="constrained")
    by_key = {row["accuracy_key"]: row for row in plotted_rows}
    for row in plotted_rows:
        style = styles[row["accuracy_key"]]
        mean_difference = row["mean_abs_relative_difference"]
        ax.errorbar(
            mean_difference,
            row["fps"],
            xerr=np.asarray(
                [
                    [mean_difference - row["p05_abs_relative_difference"]],
                    [row["p95_abs_relative_difference"] - mean_difference],
                ]
            ),
            yerr=row["fps_stddev"],
            color=style["color"],
            marker=style["marker"],
            markerfacecolor=(
                "none" if row["accuracy_key"] == "single" else style["color"]
            ),
            markeredgewidth=1.6,
            markersize=8,
            capsize=3,
            linestyle="none",
            zorder=3,
        )
        ax.annotate(
            style["label"],
            (mean_difference, row["fps"]),
            xytext=style["offset"],
            textcoords="offset points",
            ha="left",
            va="bottom" if style["offset"][1] > 0 else "top",
            color=style["color"],
            fontsize=8.5,
            fontweight="bold",
        )

    raw = by_key["single"]
    corrected = by_key["single_corrected"]
    arrow_y = max(raw["fps"], corrected["fps"]) + 75
    ax.annotate(
        "",
        xy=(corrected["mean_abs_relative_difference"], arrow_y),
        xytext=(raw["mean_abs_relative_difference"], arrow_y),
        arrowprops={"arrowstyle": "->", "color": "0.35", "lw": 1.2},
    )
    ax.text(
        (raw["mean_abs_relative_difference"] + corrected["mean_abs_relative_difference"])
        / 2,
        arrow_y + 25,
        "Correction",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color="0.3",
    )
    ax.set_xlim(-0.12, max(row["p95_abs_relative_difference"] for row in plotted_rows) * 1.08)
    ax.set_ylim(0, arrow_y + 110)
    ax.set_xlabel("Mean absolute relative difference from zsasa f32 (%)")
    ax.set_ylabel(r"Throughput (frames s$^{-1}$)")
    ax.set_title(DATASET_LABELS["5wvo_C_analysis"], fontsize=10)
    fig.suptitle("Bitmask correction improves accuracy at unchanged throughput", fontsize=11)
    ax.grid(linewidth=0.7, alpha=0.3)
    return save_figure(fig, out_dir, "md_correction_accuracy_throughput_story")


def _plot_md_trajectory_comparator_ratios(
    rows: list[dict[str, Any]], out_dir: Path, dataset_id: str, name: str
) -> list[Path]:
    """Show throughput and memory comparisons for one trajectory."""
    zsasa_variants = ("zsasa_cli_f64", "zsasa_cli_bitmask_f32")
    zsasa_labels = ("zsasa f64", "zsasa bitmask f32")
    comparator_styles = {
        "mdtraj": {
            "color": color_for("mdtraj"),
            "edgecolor": "#1f5f8f",
            "label": "vs MDTraj",
        },
        "mdsasa_bolt": {
            "color": color_for("mdsasa_bolt"),
            "edgecolor": "#1e8449",
            "label": "vs mdsasa-bolt (Rust)",
        },
    }
    selected = {
        row["variant"]: row
        for row in rows
        if row["dataset_id"] == dataset_id
        and row["variant"] in {*zsasa_variants, *comparator_styles}
    }
    comparators = [
        comparator for comparator in comparator_styles if comparator in selected
    ]
    if not comparators or any(variant not in selected for variant in zsasa_variants):
        return []

    metrics = (
        {
            "value_key": "fps",
            "sd_key": "fps_stddev",
            "xlabel": "Throughput ratio (zsasa / comparator)",
            "numerator": "zsasa",
            "title": "Throughput",
        },
        {
            "value_key": "rss_mib",
            "sd_key": "rss_stddev_mib",
            "xlabel": "Peak RSS reduction (comparator / zsasa)",
            "numerator": "comparator",
            "title": "Peak RSS reduction",
        },
    )
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), layout="constrained")
    for metric_index, (ax, metric) in enumerate(zip(axes, metrics, strict=True)):
        y_centers = np.arange(len(zsasa_variants))[::-1]
        height = 0.28 if len(comparators) > 1 else 0.38
        offsets = (
            np.linspace(0.18, -0.18, len(comparators))
            if len(comparators) > 1
            else np.asarray([0.0])
        )
        max_ratio = 1.0
        for comparator, offset in zip(comparators, offsets, strict=True):
            style = comparator_styles[comparator]
            ratios: list[float] = []
            uncertainties: list[float] = []
            for variant in zsasa_variants:
                if metric["numerator"] == "zsasa":
                    numerator_row = selected[variant]
                    denominator_row = selected[comparator]
                else:
                    numerator_row = selected[comparator]
                    denominator_row = selected[variant]
                ratio, uncertainty = ratio_with_propagated_sd(
                    numerator_row,
                    denominator_row,
                    value_key=metric["value_key"],
                    sd_key=metric["sd_key"],
                )
                ratios.append(ratio)
                uncertainties.append(uncertainty)
                max_ratio = max(max_ratio, ratio + uncertainty)
            positions = y_centers + offset
            bars = ax.barh(
                positions,
                [ratio - 1.0 for ratio in ratios],
                left=1.0,
                height=height,
                xerr=uncertainties,
                color=style["color"],
                edgecolor=style["edgecolor"],
                linewidth=1.0,
                capsize=2.5,
                alpha=0.86,
                zorder=3,
            )
            for bar, ratio, uncertainty in zip(
                bars, ratios, uncertainties, strict=True
            ):
                ax.annotate(
                    f"{ratio:.1f}×",
                    (ratio + uncertainty, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    color=style["edgecolor"],
                    fontsize=8,
                    fontweight="bold",
                )
        ax.axvline(1.0, color="0.35", linestyle=":", linewidth=1.0, zorder=0)
        ax.set_xscale("log")
        ax.set_xlim(0.9, max_ratio * 1.45)
        ticks = [
            tick
            for tick in (1.0, 10.0, 100.0, 1000.0)
            if tick <= max_ratio * 1.45
        ]
        ax.set_xticks(ticks, [f"{tick:g}×" for tick in ticks])
        ax.set_yticks(y_centers, zsasa_labels)
        ax.set_xlabel(metric["xlabel"])
        ax.set_title(metric["title"], fontsize=9.5)
        ax.grid(axis="y", visible=False)
        if metric_index == 0 and "mdtraj" not in comparators:
            ax.text(
                0.98,
                0.50,
                "MDTraj not measured",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                color="0.35",
            )
        add_panel_label(ax, chr(ord("a") + metric_index))

    legend_handles = [
        Patch(
            facecolor=comparator_styles[variant]["color"],
            edgecolor=comparator_styles[variant]["edgecolor"],
            label=comparator_styles[variant]["label"],
        )
        for variant in comparators
    ]
    fig.legend(
        handles=legend_handles,
        loc="outside lower center",
        ncol=len(legend_handles),
        frameon=False,
    )
    fig.suptitle(f"{DATASET_LABELS[dataset_id]} relative to external tools", fontsize=11)
    return save_figure(fig, out_dir, name)


def plot_md_comparator_ratios_by_trajectory(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Generate one throughput-and-memory figure per selected trajectory."""
    outputs: list[Path] = []
    for dataset_id, name in (
        ("6sup_A_analysis", "md_6sup_comparator_ratios_story"),
        ("5vz0_A_protein", "md_5vz0_comparator_ratios_story"),
    ):
        outputs.extend(
            _plot_md_trajectory_comparator_ratios(rows, out_dir, dataset_id, name)
        )
    return outputs


def native_overcommit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select native precision extremes at the 10- and 40-thread endpoints."""
    variants = {"zsasa_cli_f64", "zsasa_cli_bitmask_f32"}
    return [
        row
        for row in rows
        if row["variant"] in variants
        and row["threads"] in {10, 40}
        and (
            row["variant"] != "zsasa_cli_bitmask_f32"
            or row["bitmask_variant"] == "single_corrected"
        )
    ]


def plot_md_overcommit_tradeoff(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    """Show the 40-thread response relative to the 10-thread baseline."""
    selected = native_overcommit_rows(rows)
    by_key = {
        (row["dataset_id"], row["variant"], row["threads"]): row for row in selected
    }
    datasets = [
        dataset_id
        for dataset_id in DATASET_ORDER
        if all(
            (dataset_id, variant, threads) in by_key
            for variant in ("zsasa_cli_f64", "zsasa_cli_bitmask_f32")
            for threads in (10, 40)
        )
    ]
    if not datasets:
        return []

    variants = ("zsasa_cli_f64", "zsasa_cli_bitmask_f32")
    throughput_40: dict[tuple[str, str], float] = {}
    rss_40: dict[tuple[str, str], float] = {}
    rss_40_uncertainties: dict[tuple[str, str], float] = {}
    for dataset_id in datasets:
        for variant in variants:
            baseline = by_key[(dataset_id, variant, 10)]
            overcommit = by_key[(dataset_id, variant, 40)]
            key = (dataset_id, variant)
            throughput_40[key] = baseline["median_s"] / overcommit["median_s"]
            rss_ratio, rss_uncertainty = ratio_with_propagated_sd(
                overcommit,
                baseline,
                value_key="rss_mib",
                sd_key="rss_stddev_mib",
            )
            rss_40[key] = rss_ratio
            rss_40_uncertainties[key] = rss_uncertainty

    variant_styles = {
        "zsasa_cli_f64": {
            "color": "#f39c12",
            "marker": "o",
            "label": "zsasa f64",
            "offset": 0.13,
        },
        "zsasa_cli_bitmask_f32": {
            "color": "#c4510a",
            "marker": "s",
            "label": "zsasa bitmask f32",
            "offset": -0.13,
        },
    }
    y_centers = np.arange(len(datasets))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), layout="constrained")
    metrics = (
        (axes[0], throughput_40, None, "Throughput"),
        (axes[1], rss_40, rss_40_uncertainties, "Peak RSS"),
    )
    for ax, values, uncertainties, title in metrics:
        plotted_values: list[float] = []
        for variant, style in variant_styles.items():
            x_values = [values[(dataset_id, variant)] for dataset_id in datasets]
            y_values = y_centers + style["offset"]
            x_errors = (
                [uncertainties[(dataset_id, variant)] for dataset_id in datasets]
                if uncertainties is not None
                else None
            )
            for value, y_value in zip(x_values, y_values, strict=True):
                ax.plot(
                    [1.0, value],
                    [y_value, y_value],
                    color=style["color"],
                    linewidth=1.5,
                    alpha=0.45,
                    zorder=1,
                )
                ax.annotate(
                    f"{value:.2f}×",
                    (value, y_value),
                    xytext=(7, 0),
                    textcoords="offset points",
                    ha="left",
                    va="center",
                    color=style["color"],
                    fontsize=7.5,
                    fontweight="bold",
                )
            ax.errorbar(
                x_values,
                y_values,
                xerr=x_errors,
                color=style["color"],
                marker=style["marker"],
                markersize=7,
                capsize=2.5,
                linestyle="none",
                zorder=3,
            )
            plotted_values.extend(x_values)
        ax.axvline(1, color="0.35", linestyle=":", linewidth=1.0, zorder=0)
        ax.set_title(title)
        ax.set_yticks(
            y_centers,
            [MD_STORY_DATASET_LABELS[dataset_id] for dataset_id in datasets],
        )
        ax.set_xlabel("Ratio at 40 threads (10 threads = 1)")
        ax.grid(axis="y", visible=False)
        right = max(plotted_values)
        if title == "Throughput":
            ax.set_xlim(0.99, right + 0.035)
        else:
            ax.set_xlim(0.92, right + 0.38)
    legend_handles = [
        plt.Line2D(
            [0],
            [0],
            color=style["color"],
            marker=style["marker"],
            linewidth=1.5,
            label=style["label"],
        )
        for style in variant_styles.values()
    ]
    fig.legend(
        handles=legend_handles,
        loc="outside lower center",
        ncol=2,
        frameon=False,
    )
    add_panel_label(axes[0], "a")
    add_panel_label(axes[1], "b")
    fig.suptitle("Native zsasa under thread overcommit", fontsize=11)
    return save_figure(fig, out_dir, "md_overcommit_tradeoff_story")


def correction_runtime_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select raw and corrected single-LUT bitmask f32 measurements."""
    return [
        row
        for row in rows
        if row["run_set"] == MD_RUN_SET
        and row["variant"] == "zsasa_cli_bitmask_f32"
        and row["threads"] == 10
        and row["bitmask_variant"] in {"single", "single_corrected"}
    ]


def plot_md_correction_runtime_effect(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show the runtime effect of enabling bitmask quantization correction."""
    selected = correction_runtime_rows(rows)
    by_key = {(row["dataset_id"], row["bitmask_variant"]): row for row in selected}
    datasets = [
        dataset_id
        for dataset_id in DATASET_ORDER
        if (dataset_id, "single") in by_key
        and (dataset_id, "single_corrected") in by_key
    ]
    if not datasets:
        return []

    changes: list[float] = []
    uncertainties: list[float] = []
    for dataset_id in datasets:
        ratio, uncertainty = ratio_with_propagated_sd(
            by_key[(dataset_id, "single_corrected")],
            by_key[(dataset_id, "single")],
            value_key="mean_s",
            sd_key="stddev_s",
        )
        changes.append((ratio - 1.0) * 100)
        uncertainties.append(uncertainty * 100)

    y = np.arange(len(datasets))[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 4.1), layout="constrained")
    ax.axvline(0, color="0.35", linestyle=":", linewidth=1.0, zorder=0)
    ax.errorbar(
        changes,
        y,
        xerr=uncertainties,
        color=color_for("zsasa_cli_bitmask_f32"),
        marker="s",
        markersize=7,
        capsize=3,
        linestyle="none",
        zorder=3,
    )
    for y_value, value in zip(y, changes, strict=True):
        ax.annotate(
            f"{value:+.1f}%",
            (value, y_value),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=color_for("zsasa_cli_bitmask_f32"),
            fontsize=8,
            fontweight="bold",
        )
    ax.set_yticks(y, [MD_STORY_DATASET_LABELS[dataset_id] for dataset_id in datasets])
    ax.set_xlabel("Mean runtime change with correction (%)")
    ax.set_title("Mean runtime changes by less than 1% with bitmask correction")
    ax.grid(axis="y", visible=False)
    return save_figure(fig, out_dir, "md_bitmask_correction_runtime_story")


def plot_comparator_ratio_grid(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    metric: str,
    ylabel: str,
    title: str,
    name: str,
) -> list[Path]:
    grouped = group_by_dataset(rows)
    datasets = sorted(grouped, key=dataset_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(7.0 * len(datasets), 5.8),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle(title)
    comparator_styles = {
        "mdtraj": {
            "color": color_for("mdtraj"),
            "edgecolor": "#1f5f8f",
            "hatch": "",
        },
        "mdsasa_bolt": {
            "color": color_for("mdsasa_bolt"),
            "edgecolor": "#1e8449",
            "hatch": "///",
        },
    }
    for ax, dataset_id in zip(axes[0], datasets, strict=True):
        by_variant = {row["variant"]: row for row in grouped[dataset_id]}
        candidates = [
            variant
            for variant in ZSASA_MD_VARIANTS
            if variant in by_variant
        ]
        if "mdtraj" in by_variant and "mdsasa_bolt" in by_variant:
            candidates.append("mdsasa_bolt")
        comparators = [
            comparator
            for comparator in MD_COMPARATOR_VARIANTS
            if comparator in by_variant
        ]
        x = np.arange(len(candidates))
        width = 0.36 if len(comparators) > 1 else 0.48
        start_offset = (len(comparators) - 1) / 2
        all_values: list[float] = []
        for index, comparator in enumerate(comparators):
            baseline = by_variant[comparator]
            values = []
            for variant in candidates:
                if variant == comparator or by_variant[variant][metric] <= 0:
                    values.append(np.nan)
                else:
                    values.append(baseline[metric] / by_variant[variant][metric])
            all_values.extend(value for value in values if value > 0)
            ax.bar(
                x + (index - start_offset) * width,
                values,
                width=width,
                linewidth=1.2,
                alpha=0.75,
                label=f"vs {display_name(comparator)}",
                **comparator_styles[comparator],
            )
        ax.axhline(1.0, color="0.35", linestyle="--", linewidth=0.8, alpha=0.45)
        if all_values and max(all_values) / min(all_values) > 20:
            ax.set_yscale("log")
        ax.set_title(dataset_label(dataset_id))
        ax.set_ylabel(ylabel)
        ax.set_xticks(x, [display_name(variant) for variant in candidates])
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    handles = [
        Patch(
            facecolor=color_for("mdtraj"),
            edgecolor="#1f5f8f",
            linewidth=1.2,
            label="vs MDTraj",
            alpha=0.75,
        ),
        Patch(
            facecolor=color_for("mdsasa_bolt"),
            edgecolor="#1e8449",
            linewidth=1.2,
            hatch="///",
            label="vs mdsasa-bolt (Rust)",
            alpha=0.75,
        ),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=2)
    return save_figure(fig, out_dir, name)


def plot_throughput_vs_rss_grid(
    rows: list[dict[str, Any]], out_dir: Path, *, log_x: bool = False
) -> list[Path]:
    grouped = group_by_dataset(rows)
    datasets = sorted(grouped, key=dataset_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(6.2 * len(datasets), 5.2),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle("MD throughput vs peak RSS")
    variants = sorted({row["variant"] for row in rows}, key=variant_sort_key)
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker=marker_for(variant),
            markeredgecolor="#333333",
            markeredgewidth=0.4,
            color="w",
            markerfacecolor=color_for(variant),
            label=display_name(variant),
            markersize=7,
        )
        for variant in variants
    ]
    for ax, dataset_id in zip(axes[0], datasets, strict=True):
        for row in grouped[dataset_id]:
            ax.scatter(
                row["rss_mib"],
                row["fps"],
                s=70,
                color=color_for(row["variant"]),
                marker=marker_for(row["variant"]),
                edgecolor="#333333",
                linewidth=0.4,
            )
            if log_x:
                label_style = md_rss_label_style(dataset_id, row["variant"])
                ax.annotate(
                    display_name(row["variant"]),
                    (row["rss_mib"], row["fps"]),
                    xytext=label_style["xytext"],
                    textcoords="offset points",
                    ha=label_style["ha"],
                    va=label_style["va"],
                    arrowprops=label_style.get("arrowprops"),
                    fontsize=7.2,
                )
        if log_x:
            ax.set_xscale("log")
            ymax = max(row["fps"] for row in grouped[dataset_id])
            ax.set_ylim(top=ymax * 1.14)
        ax.set_title(dataset_label(dataset_id))
        ax.set_xlabel("peak RSS (MiB)")
        ax.set_ylabel("frames / sec")
    if not log_x:
        fig.legend(handles=handles, loc="outside lower center", ncol=5)
    name = "md_throughput_vs_peak_rss_logx_grid" if log_x else "md_throughput_vs_peak_rss_grid"
    return save_figure(fig, out_dir, name)


def plot_cpu_utilization_grid(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    for row in rows:
        row["cpu_utilization"] = (row["user_time_s"] + row["system_time_s"]) / row["mean_s"]
    return plot_bar_grid(
        rows,
        metric="cpu_utilization",
        ylabel="(user + system) / wall time",
        title="MD CPU utilization proxy",
        out_dir=out_dir,
        name="md_cpu_utilization_bar_grid",
    )


def native_condition_label(row: dict[str, Any]) -> str:
    """Return a compact label that keeps native trajectory options distinct."""
    precision = row["variant"].rsplit("_", 1)[-1]
    option = row.get("bitmask_variant")
    if not option:
        return f"standard {precision}"
    labels = {
        "single": "single",
        "single_corrected": "single + corrected",
        "per_frame": "per-frame",
        "cycle": "cycle",
        "cycle_corrected": "cycle + corrected",
    }
    return f"{labels.get(option, option)} {precision}"


def plot_native_worker_speedup_grid(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    native = [
        row
        for row in rows
        if row["run_set"] == MD_RUN_SET
        and row["variant"].startswith("zsasa_cli")
    ]
    grouped = group_by_dataset(native)
    datasets = sorted(grouped, key=dataset_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(7.2 * len(datasets), 5.8),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle("Native trajectory worker scaling vs 10 workers")
    for dataset_index, (ax, dataset_id) in enumerate(
        zip(axes[0], datasets, strict=True)
    ):
        items = grouped[dataset_id]
        by_condition: dict[tuple[str, str | None], dict[int, dict[str, Any]]] = defaultdict(dict)
        for row in items:
            key = (row["variant"], row.get("bitmask_variant"))
            by_condition[key][int(row["threads"])] = row
        conditions = sorted(
            by_condition,
            key=lambda key: (key[1] is not None, key[1] or "", key[0]),
        )
        x = np.arange(len(conditions))
        width = 0.38
        for index, threads in enumerate((20, 40)):
            values = []
            for condition in conditions:
                runs = by_condition[condition]
                baseline = runs.get(10)
                candidate = runs.get(threads)
                values.append(
                    baseline["median_s"] / candidate["median_s"]
                    if baseline and candidate
                    else np.nan
                )
            ax.bar(
                x + (index - 0.5) * width,
                values,
                width=width,
                label=f"{threads} workers" if dataset_index == 0 else None,
            )
        ax.axhline(1.0, color="0.35", linestyle="--", linewidth=0.8, alpha=0.55)
        ax.set_title(dataset_label(dataset_id))
        ax.set_ylabel("median runtime speedup")
        ax.set_xticks(
            x,
            [native_condition_label(by_condition[key][10]) for key in conditions],
            rotation=50,
            ha="right",
        )
    fig.legend(loc="outside lower center", ncol=2)
    return save_figure(fig, out_dir, "md_native_worker_speedup_grid")


def plot_bitmask_lut_runtime_grid(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    selected = [
        row
        for row in rows
        if row["run_set"] == MD_RUN_SET
        and row["variant"].startswith("zsasa_cli_bitmask")
        and row["threads"] == 10
    ]
    grouped = group_by_dataset(selected)
    datasets = sorted(grouped, key=dataset_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(6.8 * len(datasets), 5.5),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle("Native bitmask LUT runtime at 10 workers")
    for ax, dataset_id in zip(axes[0], datasets, strict=True):
        items = sorted(grouped[dataset_id], key=lambda row: native_condition_label(row))
        ax.bar(
            [native_condition_label(row) for row in items],
            [row["mean_s"] for row in items],
            color=[color_for(row["variant"]) for row in items],
        )
        ax.set_title(dataset_label(dataset_id))
        ax.set_ylabel("runtime (s), lower is better")
        plt.setp(ax.get_xticklabels(), rotation=50, ha="right", rotation_mode="anchor")
    return save_figure(fig, out_dir, "md_bitmask_lut_runtime_grid")


def write_index(out_dir: Path, outputs: list[Path]) -> Path:
    index = out_dir.joinpath("index.md")
    pngs = sorted(path for path in outputs if path.suffix == ".png")
    lines = [
        "# MD performance figures",
        "",
        f"Generated {len(pngs)} figures in PNG/SVG/PDF.",
        "",
    ]
    for path in pngs:
        lines.append(f"- `{path.relative_to(out_dir)}`")
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--story-only",
        action="store_true",
        help="generate only the curated MD performance figures",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_style()
    rows = load_md_rows(args.db)
    try:
        option_rows = load_md_rows(args.db, include_options=True)
    except TypeError:  # pragma: no cover - compatibility for injected test loaders
        option_rows = rows
    accuracy_rows = load_md_correction_accuracy(args.db)
    outputs: list[Path] = []
    outputs.extend(plot_md_performance_memory_story(rows, args.out_dir))
    outputs.extend(plot_md_zsasa_performance_memory_detail(option_rows, args.out_dir))
    outputs.extend(
        plot_md_correction_accuracy_throughput(
            option_rows, accuracy_rows, args.out_dir
        )
    )
    outputs.extend(plot_md_comparator_ratios_by_trajectory(rows, args.out_dir))
    if getattr(args, "story_only", False):
        index = write_index(args.out_dir, outputs)
        png_count = sum(1 for path in outputs if path.suffix == ".png")
        print(f"wrote {png_count} figure sets in PNG/SVG/PDF under {args.out_dir}")
        print(f"wrote {index}")
        return
    outputs.extend(plot_md_overcommit_tradeoff(option_rows, args.out_dir))
    outputs.extend(
        plot_bar_grid(
            rows,
            metric="fps",
            ylabel="frames / sec",
            title="MD throughput",
            out_dir=args.out_dir,
            name="md_frames_per_sec_bar_grid",
        )
    )
    outputs.extend(
        plot_bar_grid(
            rows,
            metric="mean_s",
            ylabel="runtime (s, log scale), lower is better",
            title="MD runtime",
            out_dir=args.out_dir,
            name="md_runtime_bar_grid",
            lower_is_better=True,
            yscale="log",
        )
    )
    outputs.extend(
        plot_bar_grid(
            rows,
            metric="rss_mib",
            ylabel="peak RSS (MiB, log scale), lower is better",
            title="MD peak RSS",
            out_dir=args.out_dir,
            name="md_peak_rss_bar_grid",
            lower_is_better=True,
            yscale="log",
        )
    )
    outputs.extend(
        plot_bar_grid(
            zsasa_only_rows(rows),
            metric="mean_s",
            ylabel="runtime (s), lower is better",
            title="MD runtime (zsasa variants)",
            out_dir=args.out_dir,
            name="md_zsasa_runtime_bar_grid",
            lower_is_better=True,
        )
    )
    outputs.extend(
        plot_bar_grid(
            zsasa_only_rows(rows),
            metric="rss_mib",
            ylabel="peak RSS (MiB), lower is better",
            title="MD peak RSS (zsasa variants)",
            out_dir=args.out_dir,
            name="md_zsasa_peak_rss_bar_grid",
            lower_is_better=True,
        )
    )
    outputs.extend(
        plot_comparator_ratio_grid(
            rows,
            args.out_dir,
            metric="mean_s",
            ylabel="runtime speedup, higher is better",
            title="MD runtime speedup: zsasa vs MDTraj/mdsasa-bolt (Rust)",
            name="md_runtime_speedup_vs_comparators_grid",
        )
    )
    outputs.extend(
        plot_comparator_ratio_grid(
            rows,
            args.out_dir,
            metric="rss_mib",
            ylabel="RSS reduction, higher is better",
            title="MD RSS reduction: zsasa vs MDTraj/mdsasa-bolt (Rust)",
            name="md_rss_reduction_vs_comparators_grid",
        )
    )
    outputs.extend(plot_throughput_vs_rss_grid(rows, args.out_dir, log_x=True))
    outputs.extend(
        plot_bar_grid(
            rows,
            metric="fps_per_mib",
            ylabel="frames / sec / MiB",
            title="MD throughput per peak RSS",
            out_dir=args.out_dir,
            name="md_frames_per_sec_per_mib_bar_grid",
        )
    )
    outputs.extend(
        plot_bar_grid(
            rows,
            metric="atom_frames_per_sec",
            ylabel="atom-frames / sec",
            title="MD atom-frame throughput",
            out_dir=args.out_dir,
            name="md_atom_frames_per_sec_bar_grid",
        )
    )
    outputs.extend(plot_cpu_utilization_grid(rows, args.out_dir))
    if option_rows and all("run_set" in row for row in option_rows):
        outputs.extend(plot_bitmask_lut_runtime_grid(option_rows, args.out_dir))
        outputs.extend(plot_native_worker_speedup_grid(option_rows, args.out_dir))
    index = write_index(args.out_dir, outputs)
    png_count = sum(1 for path in outputs if path.suffix == ".png")
    print(f"wrote {png_count} figure sets in PNG/SVG/PDF under {args.out_dir}")
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
