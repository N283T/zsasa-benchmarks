#!/usr/bin/env python3
"""Generate batch benchmark figures from the benchmark DuckDB database."""

from __future__ import annotations

import argparse
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
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures")
ECOLI_DATASET = "UP000000625_83333_ECOLI_v6_pdb"
HUMAN_DATASET = "UP000005640_9606_HUMAN_v6_pdb"
HUMAN_CIF_DATASET = "UP000005640_9606_HUMAN_v6_cif"
SWISSPROT_DATASET = "swissprot_500k_pdb"

VARIANT_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "zsasa_0_6_0_f32",
    "zsasa_0_6_0_bitmask_f32",
    "zsasa_0_9_0_f32",
    "zsasa_0_9_0_bitmask_f32",
    "zsasa_generic_read",
    "zsasa_generic_mmap",
    "zsasa_af_fast_read",
    "zsasa_af_fast_mmap",
    "freesasa_batch",
    "rustsasa",
    "lahuta",
    "lahuta_bitmask",
]
ZSASA_BATCH_VARIANTS = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
]
BATCH_COMPARATOR_VARIANTS = ["freesasa_batch", "rustsasa", "lahuta_bitmask"]
ECOLI_STORY_VARIANTS = [
    "zsasa_f64",
    "zsasa_bitmask_f32",
    "freesasa_batch",
    "rustsasa",
    "lahuta_bitmask",
]
ECOLI_STORY_STYLES = {
    "zsasa_f64": {"marker": "o", "linestyle": "-", "linewidth": 2.2},
    "zsasa_bitmask_f32": {"marker": "s", "linestyle": "-", "linewidth": 2.6},
    "freesasa_batch": {"marker": "^", "linestyle": "--", "linewidth": 1.8},
    "rustsasa": {"marker": "D", "linestyle": "--", "linewidth": 1.8},
    "lahuta_bitmask": {"marker": "P", "linestyle": ":", "linewidth": 2.0},
}
COLORS = {
    "zsasa_f64": "#f39c12",
    "zsasa_f32": "#f6c85f",
    "zsasa_bitmask_f64": "#e67e22",
    "zsasa_bitmask_f32": "#ffb347",
    "zsasa_0_6_0_f32": "#f6c85f",
    "zsasa_0_6_0_bitmask_f32": "#ffb347",
    "zsasa_0_9_0_f32": "#d99b2b",
    "zsasa_0_9_0_bitmask_f32": "#e67e22",
    "zsasa_generic_read": "#f6c85f",
    "zsasa_generic_mmap": "#d99b2b",
    "zsasa_af_fast_read": "#e67e22",
    "zsasa_af_fast_mmap": "#b95f0b",
    "freesasa_batch": "#3498db",
    "rustsasa": "#e74c3c",
    "lahuta": "#8e44ad",
    "lahuta_bitmask": "#c39bd3",
}
DISPLAY_NAMES = {
    "zsasa_f64": "zsasa f64",
    "zsasa_f32": "zsasa f32",
    "zsasa_bitmask_f64": "zsasa bitmask f64",
    "zsasa_bitmask_f32": "zsasa bitmask f32",
    "zsasa_0_6_0_f32": "zsasa 0.6.0 f32",
    "zsasa_0_6_0_bitmask_f32": "zsasa 0.6.0 bitmask f32",
    "zsasa_0_9_0_f32": "zsasa 0.9.0 f32",
    "zsasa_0_9_0_bitmask_f32": "zsasa 0.9.0 bitmask f32",
    "zsasa_generic_read": "zsasa generic/read",
    "zsasa_generic_mmap": "zsasa generic/mmap",
    "zsasa_af_fast_read": "zsasa AF fast/read",
    "zsasa_af_fast_mmap": "zsasa AF fast/mmap",
    "freesasa_batch": "FreeSASA batch",
    "rustsasa": "RustSASA",
    "lahuta": "Lahuta",
    "lahuta_bitmask": "Lahuta bitmask",
}


def dataset_slug(dataset_id: str) -> str:
    if "ECOLI" in dataset_id:
        return "ecoli"
    if "HUMAN" in dataset_id:
        return "human"
    return dataset_id.lower().replace("/", "_")


def dataset_label(dataset_id: str) -> str:
    if "ECOLI" in dataset_id:
        return "E. coli AFDB"
    if "HUMAN" in dataset_id:
        return "Human AFDB"
    if dataset_id == SWISSPROT_DATASET:
        return "SwissProt AFDB"
    return dataset_id


def batch_column_name(run: dict[str, Any]) -> str:
    tool_id = str(run.get("tool_id") or "")
    run_variant = str(run.get("run_variant") or "")
    if run_variant:
        return f"zsasa_{run_variant}" if tool_id.startswith("zsasa") else run_variant
    precision = str(run.get("precision") or "")
    mode = str(run.get("mode") or "")
    if tool_id == "freesasa_batch":
        return "freesasa_batch"
    if tool_id == "rustsasa":
        return "rustsasa"
    if tool_id == "lahuta":
        return "lahuta_bitmask" if mode == "bitmask" else "lahuta"
    if tool_id.startswith("zsasa"):
        prefix = f"{tool_id}_bitmask" if mode == "bitmask" else tool_id
        return f"{prefix}_{precision}"
    return f"{tool_id}_{precision}" if precision else tool_id


def display_name(variant: str) -> str:
    return DISPLAY_NAMES.get(variant, variant)


def color_for(variant: str) -> str:
    return COLORS.get(variant, "#7f8c8d")


def variant_sort_key(variant: str) -> tuple[int, str]:
    try:
        return (VARIANT_ORDER.index(variant), variant)
    except ValueError:
        return (len(VARIANT_ORDER), variant)


def throughput_per_second(n_structures: int, mean_s: float) -> float:
    if mean_s <= 0:
        raise ValueError("mean_s must be positive")
    return n_structures / mean_s


def milliseconds_per_structure(mean_s: float, n_structures: int) -> float:
    if n_structures <= 0:
        raise ValueError("n_structures must be positive")
    return mean_s * 1000.0 / n_structures


def memory_summary_mb(values: list[int]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mb_values = [value / (1024 * 1024) for value in values]
    mean = sum(mb_values) / len(mb_values)
    if len(mb_values) == 1:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in mb_values) / (len(mb_values) - 1)
    return mean, variance**0.5


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "legend.frameon": False,
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


def load_batch_rows(db_path: Path, dataset_id: str) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        run_cols = [
            "run_id",
            "dataset_id",
            "tool_id",
            "precision",
            "mode",
            "run_variant",
            "threads",
            "expected_count",
            "source_path",
            "status",
        ]
        run_rows = con.execute(
            """
            SELECT r.run_id, r.dataset_id, r.tool_id, r.precision, r.mode, r.variant, r.threads,
                   d.expected_count, r.source_path, r.status
            FROM benchmark_runs r
            LEFT JOIN datasets d USING (dataset_id)
            WHERE r.benchmark_kind = 'batch'
              AND r.dataset_id = ?
              AND r.status <> 'superseded'
            ORDER BY r.tool_id, r.precision, r.mode, r.threads
            """,
            [dataset_id],
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for raw_run in run_rows:
            run = dict(zip(run_cols, raw_run, strict=True))
            if not adopted_for_reporting("batch", run["source_path"], run["status"]):
                continue
            source = run_set(run["source_path"])
            if dataset_id in {ECOLI_DATASET, HUMAN_DATASET}:
                if run["tool_id"] == "zsasa":
                    continue
                if run["tool_id"] == "zsasa_0_9_0":
                    run["tool_id"] = "zsasa"
                    run["run_variant"] = None
                elif source != "v0_6_0_full":
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
            expected_count = int(run["expected_count"])
            memory_mean_bytes = stats.get(("peak_rss", "mean"))
            memory_stddev_bytes = stats.get(("peak_rss", "stddev"))
            memory_mean_mb = float(memory_mean_bytes or 0.0) / (1024 * 1024)
            memory_stddev_mb = float(memory_stddev_bytes or 0.0) / (1024 * 1024)
            row: dict[str, Any] = {
                "variant": batch_column_name(run),
                "threads": int(run["threads"]),
                "mean_s": mean_s,
                "median_s": median_s,
                "stddev_s": stddev_s,
                "throughput": throughput_per_second(expected_count, mean_s),
                "throughput_stddev": expected_count * stddev_s / (mean_s**2),
                "expected_count": expected_count,
                "memory_mean_mb": memory_mean_mb,
                "memory_stddev_mb": memory_stddev_mb,
                "user_time_s": float(stats.get(("user_time", "mean")) or 0.0),
                "system_time_s": float(stats.get(("system_time", "mean")) or 0.0),
            }
            for idx in range(1, 10):
                key = f"run_{idx}"
                if ("runtime", key) in stats:
                    row[key] = float(stats[("runtime", key)])
            rows.append(row)
        return sorted(rows, key=lambda row: (variant_sort_key(row["variant"]), row["threads"]))
    finally:
        con.close()


def cpu_utilization_proxy(row: dict[str, Any]) -> float:
    mean_s = float(row["mean_s"])
    if mean_s <= 0:
        raise ValueError("mean_s must be positive")
    return (float(row.get("user_time_s") or 0.0) + float(row.get("system_time_s") or 0.0)) / mean_s


def thread_scaling_runtime(row: dict[str, Any]) -> float:
    return float(row.get("median_s") or row["mean_s"])


def speedup_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = {
        row["variant"]: thread_scaling_runtime(row)
        for row in rows
        if int(row["threads"]) == 1 and thread_scaling_runtime(row) > 0
    }
    output: list[dict[str, Any]] = []
    for row in rows:
        variant = row["variant"]
        if variant not in baseline:
            continue
        threads = int(row["threads"])
        speedup = baseline[variant] / thread_scaling_runtime(row)
        output.append(
            {
                "variant": variant,
                "threads": threads,
                "speedup": speedup,
                "efficiency": speedup / threads,
            }
        )
    return output


def group_by_variant(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["variant"]].append(row)
    return {
        variant: sorted(items, key=lambda row: row["threads"]) for variant, items in grouped.items()
    }


def plot_throughput(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    for variant, items in sorted(
        group_by_variant(rows).items(), key=lambda item: variant_sort_key(item[0])
    ):
        xs = [item["threads"] for item in items]
        ys = [item["throughput"] for item in items]
        yerr = [item["throughput_stddev"] for item in items]
        ax.errorbar(
            xs,
            ys,
            yerr=yerr,
            marker="o",
            linewidth=1.8,
            capsize=3,
            label=display_name(variant),
            color=color_for(variant),
        )
    ax.set_title("E. coli batch throughput")
    ax.set_xlabel("threads")
    ax.set_ylabel("structures / sec")
    ax.set_xticks(sorted({row["threads"] for row in rows}))
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_throughput_vs_threads")


def plot_runtime(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    for variant, items in sorted(
        group_by_variant(rows).items(), key=lambda item: variant_sort_key(item[0])
    ):
        ax.errorbar(
            [item["threads"] for item in items],
            [item["mean_s"] for item in items],
            yerr=[item["stddev_s"] for item in items],
            marker="o",
            linewidth=1.8,
            capsize=3,
            label=display_name(variant),
            color=color_for(variant),
        )
    ax.set_title("E. coli batch runtime")
    ax.set_xlabel("threads")
    ax.set_ylabel("runtime (s), lower is better")
    ax.set_xticks(sorted({row["threads"] for row in rows}))
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_runtime_vs_threads")


def plot_speedup(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    derived = speedup_rows(rows)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for metric, ax in [("speedup", axes[0]), ("efficiency", axes[1])]:
        grouped = group_by_variant(derived)
        for variant, items in sorted(grouped.items(), key=lambda item: variant_sort_key(item[0])):
            ax.plot(
                [item["threads"] for item in items],
                [item[metric] for item in items],
                marker="o",
                linewidth=1.8,
                label=display_name(variant),
                color=color_for(variant),
            )
        ax.set_xlabel("threads")
        ax.set_xticks(sorted({row["threads"] for row in rows}))
        if metric == "speedup":
            max_thread = max(row["threads"] for row in rows)
            ax.plot([1, max_thread], [1, max_thread], linestyle="--", color="0.3", alpha=0.4)
            ax.set_ylabel("speedup vs 1 thread (median runtime)")
            ax.set_title("Thread speedup")
        else:
            ax.axhline(1.0, linestyle="--", color="0.3", alpha=0.4)
            ax.set_ylabel("parallel efficiency (median runtime)")
            ax.set_title("Thread efficiency")
    axes[1].legend(loc="best", ncol=1)
    return save_figure(fig, out_dir, "ecoli_thread_scaling")


def plot_t10_bar(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    selected = sorted(
        [row for row in rows if row["threads"] == 10],
        key=lambda row: row["throughput"],
        reverse=True,
    )
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    labels = [display_name(row["variant"]) for row in selected]
    values = [row["throughput"] for row in selected]
    yerr = [row["throughput_stddev"] for row in selected]
    colors = [color_for(row["variant"]) for row in selected]
    ax.bar(labels, values, yerr=yerr, capsize=3, color=colors)
    ax.set_title("E. coli batch throughput at 10 threads")
    ax.set_ylabel("structures / sec")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, "ecoli_t10_throughput_bar")


def plot_replicates(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
    offsets = np.linspace(-0.18, 0.18, len(VARIANT_ORDER))
    offset_by_variant = {variant: offsets[idx] for idx, variant in enumerate(VARIANT_ORDER)}
    for row in rows:
        variant = row["variant"]
        x = row["threads"] + float(offset_by_variant.get(variant, 0.0))
        for idx in range(1, 10):
            key = f"run_{idx}"
            if key not in row:
                continue
            ax.scatter(
                x,
                throughput_per_second(row["expected_count"], row[key]),
                s=24,
                alpha=0.55,
                color=color_for(variant),
            )
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color_for(v),
            label=display_name(v),
            markersize=6,
        )
        for v in VARIANT_ORDER
        if any(row["variant"] == v for row in rows)
    ]
    ax.set_title("E. coli batch throughput replicate jitter")
    ax.set_xlabel("threads")
    ax.set_ylabel("structures / sec")
    ax.set_xticks(sorted({row["threads"] for row in rows}))
    ax.legend(handles=handles, loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_throughput_replicates")


def plot_memory(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    memory_rows = [row for row in rows if row.get("memory_mean_mb", 0.0) > 0]
    if not memory_rows:
        return []
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    for variant, items in sorted(
        group_by_variant(memory_rows).items(), key=lambda item: variant_sort_key(item[0])
    ):
        ax.errorbar(
            [item["threads"] for item in items],
            [item["memory_mean_mb"] for item in items],
            yerr=[item["memory_stddev_mb"] for item in items],
            marker="o",
            linewidth=1.8,
            capsize=3,
            label=display_name(variant),
            color=color_for(variant),
        )
    ax.set_title("E. coli batch peak RSS")
    ax.set_xlabel("threads")
    ax.set_ylabel("peak RSS (MiB)")
    ax.set_xticks(sorted({row["threads"] for row in memory_rows}))
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_peak_rss_vs_threads")


def plot_t10_memory_bar(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    selected = sorted(
        [row for row in rows if row["threads"] == 10 and row.get("memory_mean_mb", 0.0) > 0],
        key=lambda row: row["memory_mean_mb"],
    )
    if not selected:
        return []
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [row["memory_mean_mb"] for row in selected],
        yerr=[row["memory_stddev_mb"] for row in selected],
        capsize=3,
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.set_title("E. coli batch peak RSS at 10 threads")
    ax.set_ylabel("peak RSS (MiB)")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, "ecoli_t10_peak_rss_bar")


def plot_t10_throughput_memory(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    selected = [row for row in rows if row["threads"] == 10 and row.get("memory_mean_mb", 0.0) > 0]
    if not selected:
        return []
    fig, ax = plt.subplots(figsize=(7.2, 5.6), layout="constrained")
    for row in selected:
        ax.scatter(
            row["memory_mean_mb"],
            row["throughput"],
            s=70,
            color=color_for(row["variant"]),
            label=display_name(row["variant"]),
        )
        label_style = throughput_memory_label_style(row["variant"])
        ax.annotate(
            display_name(row["variant"]),
            (row["memory_mean_mb"], row["throughput"]),
            xytext=label_style["xytext"],
            textcoords="offset points",
            ha=label_style["ha"],
            va=label_style["va"],
            arrowprops=label_style.get("arrowprops"),
            fontsize=8,
        )
    ax.set_title("E. coli batch throughput vs peak RSS at 10 threads")
    ax.set_xlabel("peak RSS (MiB)")
    ax.set_ylabel("structures / sec")
    return save_figure(fig, out_dir, "ecoli_t10_throughput_vs_peak_rss")


def ecoli_story_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the precision extremes and representative external comparators."""
    selected = set(ECOLI_STORY_VARIANTS)
    return [row for row in ecoli_comparison_rows(rows) if row["variant"] in selected]


def plot_ecoli_throughput_scaling_story(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show throughput scaling for the E. coli story variants."""
    selected = ecoli_story_rows(rows)
    grouped = group_by_variant(selected)
    fig, ax = plt.subplots(figsize=(7.6, 5.2), layout="constrained")
    for variant in ECOLI_STORY_VARIANTS:
        items = grouped.get(variant, [])
        if not items:
            continue
        style = ECOLI_STORY_STYLES[variant]
        ax.errorbar(
            [item["threads"] for item in items],
            [item["throughput"] for item in items],
            yerr=[item["throughput_stddev"] for item in items],
            color=color_for(variant),
            marker=style["marker"],
            linestyle=style["linestyle"],
            linewidth=style["linewidth"],
            markersize=5.5,
            capsize=2.5,
            label=display_name(variant),
        )

    ax.set_title("E. coli AFDB batch throughput scaling")
    ax.set_xlabel("Threads")
    ax.set_ylabel(r"Throughput (structures s$^{-1}$)")
    ax.set_xticks(sorted({row["threads"] for row in selected}))
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", frameon=False)
    return save_figure(fig, out_dir, "ecoli_throughput_scaling_story")


def ecoli_story_label_style(variant: str) -> dict[str, Any]:
    """Position labels around the five E. coli throughput-memory points."""
    if variant == "freesasa_batch":
        return {"xytext": (-8, 0), "ha": "right", "va": "center"}
    if variant in {"rustsasa", "lahuta_bitmask"}:
        return {"xytext": (-8, 0), "ha": "right", "va": "center"}
    return {"xytext": (8, 0), "ha": "left", "va": "center"}


def plot_ecoli_performance_memory_story(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show the E. coli 10-thread throughput-memory trade-off."""
    return plot_selected_t10_performance_memory(
        rows,
        out_dir,
        title="E. coli AFDB batch performance and memory",
        name="ecoli_performance_memory_story",
    )


def plot_selected_t10_performance_memory(
    rows: list[dict[str, Any]], out_dir: Path, *, title: str, name: str
) -> list[Path]:
    """Plot selected zsasa precision extremes and external comparators."""
    t10_by_variant = {row["variant"]: row for row in rows if row["threads"] == 10}
    fig, ax = plt.subplots(figsize=(7.6, 5.2), layout="constrained")
    for variant in ECOLI_STORY_VARIANTS:
        row = t10_by_variant.get(variant)
        if row is None or row.get("memory_mean_mb", 0.0) <= 0:
            continue
        ax.scatter(
            row["memory_mean_mb"],
            row["throughput"],
            color=color_for(variant),
            marker=ECOLI_STORY_STYLES[variant]["marker"],
            s=80,
            zorder=3,
        )
        label_style = ecoli_story_label_style(variant)
        ax.annotate(
            display_name(variant),
            (row["memory_mean_mb"], row["throughput"]),
            xytext=label_style["xytext"],
            textcoords="offset points",
            ha=label_style["ha"],
            va=label_style["va"],
            fontsize=9,
        )

    ax.set_title(title)
    ax.set_xlabel("Peak RSS (MiB)")
    ax.set_ylabel(r"Throughput (structures s$^{-1}$)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return save_figure(fig, out_dir, name)


def plot_human_performance_memory_map(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show the Human PDB 10-thread throughput-memory map."""
    return plot_selected_t10_performance_memory(
        rows,
        out_dir,
        title="Human AFDB PDB batch performance and memory",
        name="human_t10_throughput_vs_peak_rss",
    )


def plot_throughput_per_mib(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    memory_rows = [row for row in rows if row.get("memory_mean_mb", 0.0) > 0]
    if not memory_rows:
        return []
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    for variant, items in sorted(
        group_by_variant(memory_rows).items(), key=lambda item: variant_sort_key(item[0])
    ):
        ax.plot(
            [item["threads"] for item in items],
            [item["throughput"] / item["memory_mean_mb"] for item in items],
            marker="o",
            linewidth=1.8,
            label=display_name(variant),
            color=color_for(variant),
        )
    ax.set_title("E. coli batch throughput per peak RSS")
    ax.set_xlabel("threads")
    ax.set_ylabel("structures / sec / MiB")
    ax.set_xticks(sorted({row["threads"] for row in memory_rows}))
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_throughput_per_mib_vs_threads")


def throughput_memory_label_style(variant: str) -> dict[str, Any]:
    arrowprops = {"arrowstyle": "-", "color": "0.35", "lw": 0.7}
    if variant in {"zsasa_bitmask_f64", "lahuta"}:
        return {"xytext": (14, -10), "ha": "left", "va": "top", "arrowprops": arrowprops}
    if variant == "zsasa_f64":
        return {"xytext": (14, -2), "ha": "left", "va": "center", "arrowprops": arrowprops}
    if variant == "zsasa_f32":
        return {"xytext": (6, 7), "ha": "left", "va": "baseline"}
    return {"xytext": (5, 3), "ha": "left", "va": "baseline"}


def plot_cpu_utilization(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    for variant, items in sorted(
        group_by_variant(rows).items(), key=lambda item: variant_sort_key(item[0])
    ):
        ax.plot(
            [item["threads"] for item in items],
            [cpu_utilization_proxy(item) for item in items],
            marker="o",
            linewidth=1.8,
            label=display_name(variant),
            color=color_for(variant),
        )
    thread_values = sorted({row["threads"] for row in rows})
    ax.plot(thread_values, thread_values, linestyle="--", color="0.3", alpha=0.35, label="ideal")
    ax.set_title("E. coli batch CPU utilization proxy")
    ax.set_xlabel("threads")
    ax.set_ylabel("(user + system) / wall time")
    ax.set_xticks(thread_values)
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, "ecoli_cpu_utilization_vs_threads")


def plot_efficiency_heatmap(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    derived = speedup_rows(rows)
    if not derived:
        return []
    variants = sorted({row["variant"] for row in derived}, key=variant_sort_key)
    threads = sorted({row["threads"] for row in derived})
    values = np.full((len(variants), len(threads)), np.nan)
    for row in derived:
        values[variants.index(row["variant"]), threads.index(row["threads"])] = row["efficiency"]

    fig, ax = plt.subplots(figsize=(8.5, 4.8), layout="constrained")
    image = ax.imshow(
        values, aspect="auto", cmap="viridis", vmin=0, vmax=max(1.0, np.nanmax(values))
    )
    ax.set_title("E. coli batch parallel efficiency heatmap")
    ax.set_xlabel("threads")
    ax.set_ylabel("variant")
    ax.set_xticks(range(len(threads)), [str(thread) for thread in threads])
    ax.set_yticks(range(len(variants)), [display_name(variant) for variant in variants])
    for row_idx, _variant in enumerate(variants):
        for col_idx, _thread in enumerate(threads):
            value = values[row_idx, col_idx]
            if not np.isnan(value):
                ax.text(
                    col_idx,
                    row_idx,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    color="white" if value < 0.65 else "black",
                    fontsize=8,
                )
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("speedup / threads (median runtime)")
    return save_figure(fig, out_dir, "ecoli_parallel_efficiency_heatmap")


def t10_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["threads"] == 10]


def human_cif_t20_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the complete parser-by-I/O matrix at 20 workers."""
    variants = {
        "zsasa_generic_read",
        "zsasa_generic_mmap",
        "zsasa_af_fast_read",
        "zsasa_af_fast_mmap",
    }
    return [row for row in rows if row["threads"] == 20 and row["variant"] in variants]


def row_for(rows: list[dict[str, Any]], variant: str, threads: int) -> dict[str, Any]:
    """Return one reporting row for a variant and worker count."""
    return next(
        row for row in rows if row["variant"] == variant and row["threads"] == threads
    )


def plot_human_format_ranking(
    pdb_rows: list[dict[str, Any]], cif_rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show the format-dependent ranking as a ratio around parity."""
    comparisons = [
        (
            "PDB",
            row_for(pdb_rows, "zsasa_bitmask_f32", 10),
            row_for(pdb_rows, "lahuta_bitmask", 10),
        ),
        (
            "mmCIF",
            row_for(cif_rows, "zsasa_generic_mmap", 10),
            row_for(cif_rows, "lahuta_bitmask", 10),
        ),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 3.8), layout="constrained")
    ax.axvline(1.0, color="0.35", linestyle=":", linewidth=1.2, zorder=0)
    y_positions = [1, 0]
    for y, (_label, zsasa, lahuta) in zip(y_positions, comparisons, strict=True):
        ratio = zsasa["throughput"] / lahuta["throughput"]
        relative_uncertainty = np.hypot(
            zsasa["throughput_stddev"] / zsasa["throughput"],
            lahuta["throughput_stddev"] / lahuta["throughput"],
        )
        ratio_error = ratio * relative_uncertainty
        zsasa_wins = ratio >= 1.0
        color = "#e67e22" if zsasa_wins else color_for("lahuta_bitmask")
        ax.errorbar(
            ratio,
            y,
            xerr=ratio_error,
            color=color,
            marker="o" if zsasa_wins else "P",
            markersize=9,
            capsize=3,
            linewidth=1.5,
            zorder=2,
        )
        winner = "zsasa faster" if zsasa_wins else "Lahuta faster"
        ax.annotate(
            f"{ratio:.2f}×  {winner}",
            (ratio, y),
            xytext=(8, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            color=color,
            fontsize=9,
            fontweight="bold",
        )

    ax.set_title("Human AFDB file format reverses relative throughput")
    ax.set_xlabel("Throughput ratio (zsasa / Lahuta)")
    ax.set_yticks(y_positions, [item[0] for item in comparisons])
    ax.set_xlim(0.90, 1.62)
    ax.set_ylim(-0.55, 1.55)
    ax.grid(axis="y", visible=False)
    ax.text(
        0.99,
        0.04,
        r"10 workers, 128 points, mean $\pm$ SD ($n$ = 3)",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="0.35",
    )
    return save_figure(fig, out_dir, "human_format_zsasa_lahuta_ranking")


def plot_human_cif_recovery(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    """Show categorical parser and I/O configurations without implying a trend."""
    configurations = [
        ("Generic parser / mmap", "zsasa_generic_mmap", "#f6c85f", "s"),
        ("Generic parser / read-all", "zsasa_generic_read", "#f6c85f", "o"),
        ("AF fast path / mmap", "zsasa_af_fast_mmap", "#e67e22", "s"),
        ("AF fast path / read-all", "zsasa_af_fast_read", "#e67e22", "o"),
    ]
    y_positions = np.arange(len(configurations))[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 4.6), layout="constrained")
    ax.axhspan(1.5, 3.5, color="#f6c85f", alpha=0.07, zorder=0)
    ax.axhspan(-0.5, 1.5, color="#e67e22", alpha=0.05, zorder=0)
    for y, (_label, variant, color, marker) in zip(
        y_positions, configurations, strict=True
    ):
        row = row_for(rows, variant, 10)
        ax.errorbar(
            row["throughput"],
            y,
            xerr=row["throughput_stddev"],
            color=color,
            marker=marker,
            markeredgecolor="#9a5708",
            markersize=8,
            capsize=3,
            linewidth=1.5,
            zorder=2,
        )
        ax.annotate(
            f"{row['throughput']:,.0f}",
            (row["throughput"], y),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    lahuta = row_for(rows, "lahuta_bitmask", 10)
    ax.axvline(
        lahuta["throughput"],
        color=color_for("lahuta_bitmask"),
        linestyle=":",
        linewidth=2.0,
        zorder=1,
    )
    ax.text(
        lahuta["throughput"] + 3,
        3.38,
        f"Lahuta bitmask  {lahuta['throughput']:,.0f}",
        color="#75408a",
        ha="left",
        va="top",
        fontsize=8,
        fontweight="bold",
    )
    ax.set_title("Parser and input strategy determine Human AFDB mmCIF throughput")
    ax.set_xlabel(r"Throughput (structures s$^{-1}$)")
    ax.set_yticks(y_positions, [item[0] for item in configurations])
    ax.set_xlim(1380, 1650)
    ax.set_ylim(-0.5, 3.5)
    ax.grid(axis="y", visible=False)
    ax.text(
        0.99,
        0.04,
        r"10 workers, 128 points, mean $\pm$ SD ($n$ = 3)",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="0.35",
    )
    return save_figure(fig, out_dir, "human_cif_parser_recovery")


def plot_human_cif_ranking_recovery_story(
    pdb_rows: list[dict[str, Any]], cif_rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Combine the observed ranking change and categorical recovery steps."""
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.5), layout="constrained")

    comparisons = [
        (
            "PDB",
            row_for(pdb_rows, "zsasa_bitmask_f32", 10),
            row_for(pdb_rows, "lahuta_bitmask", 10),
        ),
        (
            "mmCIF",
            row_for(cif_rows, "zsasa_generic_mmap", 10),
            row_for(cif_rows, "lahuta_bitmask", 10),
        ),
    ]
    ratio_ax = axes[0]
    ratio_ax.axvline(1.0, color="0.35", linestyle=":", linewidth=1.2, zorder=0)
    y_positions = [1, 0]
    for y, (_label, zsasa, lahuta) in zip(y_positions, comparisons, strict=True):
        ratio = zsasa["throughput"] / lahuta["throughput"]
        ratio_error = ratio * np.hypot(
            zsasa["throughput_stddev"] / zsasa["throughput"],
            lahuta["throughput_stddev"] / lahuta["throughput"],
        )
        zsasa_wins = ratio >= 1.0
        color = "#e67e22" if zsasa_wins else color_for("lahuta_bitmask")
        ratio_ax.errorbar(
            ratio,
            y,
            xerr=ratio_error,
            color=color,
            marker="o" if zsasa_wins else "P",
            markersize=9,
            capsize=3,
            linewidth=1.5,
            zorder=2,
        )
        ratio_ax.annotate(
            f"{ratio:.2f}×",
            (ratio, y),
            xytext=(8, 0) if zsasa_wins else (0, -16),
            textcoords="offset points",
            ha="left" if zsasa_wins else "center",
            va="center",
            color=color,
            fontsize=9,
            fontweight="bold",
        )
    ratio_ax.set_title("Observed mean ranking")
    ratio_ax.set_xlabel("Throughput ratio (zsasa / Lahuta)")
    ratio_ax.set_yticks(y_positions, [item[0] for item in comparisons])
    ratio_ax.set_xlim(0.90, 1.62)
    ratio_ax.set_ylim(-0.55, 1.55)
    ratio_ax.grid(axis="y", visible=False)

    configurations = [
        ("Generic, mmap", "zsasa_generic_mmap", "#f6c85f", "s", "white"),
        ("Generic, read-all", "zsasa_generic_read", "#f6c85f", "o", "#f6c85f"),
        ("AF-fast, mmap", "zsasa_af_fast_mmap", "#e67e22", "s", "white"),
        ("AF-fast, read-all", "zsasa_af_fast_read", "#e67e22", "o", "#e67e22"),
    ]
    recovery_ax = axes[1]
    recovery_y = np.arange(len(configurations))[::-1]
    recovery_ax.axhspan(1.5, 3.5, color="#f6c85f", alpha=0.07, zorder=0)
    recovery_ax.axhspan(-0.5, 1.5, color="#e67e22", alpha=0.05, zorder=0)
    for y, (_label, variant, color, marker, facecolor) in zip(
        recovery_y, configurations, strict=True
    ):
        row = row_for(cif_rows, variant, 10)
        recovery_ax.errorbar(
            row["throughput"],
            y,
            xerr=row["throughput_stddev"],
            color=color,
            marker=marker,
            markerfacecolor=facecolor,
            markeredgewidth=1.5,
            markersize=8,
            capsize=3,
            linewidth=1.5,
            zorder=2,
        )
        recovery_ax.annotate(
            f"{row['throughput']:,.0f}",
            (row["throughput"], y),
            xytext=(8, 0) if variant == "zsasa_generic_read" else (0, 9),
            textcoords="offset points",
            ha="left" if variant == "zsasa_generic_read" else "center",
            va="center" if variant == "zsasa_generic_read" else "bottom",
            fontsize=8,
        )
    lahuta = row_for(cif_rows, "lahuta_bitmask", 10)
    recovery_ax.axvline(
        lahuta["throughput"],
        color=color_for("lahuta_bitmask"),
        linestyle=":",
        linewidth=2.0,
        zorder=1,
    )
    recovery_ax.text(
        lahuta["throughput"] + 3,
        3.38,
        f"Lahuta  {lahuta['throughput']:,.0f}",
        color="#75408a",
        ha="left",
        va="top",
        fontsize=8,
        fontweight="bold",
    )
    recovery_ax.set_title("mmCIF recovery")
    recovery_ax.set_xlabel(r"Throughput (structures s$^{-1}$)")
    recovery_ax.set_yticks(recovery_y, [item[0] for item in configurations])
    recovery_ax.set_xlim(1380, 1650)
    recovery_ax.set_ylim(-0.5, 3.5)
    recovery_ax.grid(axis="y", visible=False)

    add_panel_label(ratio_ax, "a")
    add_panel_label(recovery_ax, "b")
    fig.suptitle("Human AFDB ranking and mmCIF performance recovery", fontsize=11)
    return save_figure(fig, out_dir, "human_cif_ranking_recovery_story")


def plot_human_cif_af_fast_overcommit(
    rows: list[dict[str, Any]], out_dir: Path, *, metric: str
) -> list[Path]:
    """Show I/O behavior and memory cost when AF-fast workers are overcommitted."""
    if metric == "throughput":
        value_key = "throughput"
        error_key = "throughput_stddev"
        ylabel = r"Throughput (structures s$^{-1}$)"
        title = "Overcommit narrows the AF-fast mmap throughput gap"
        filename = "human_cif_af_fast_overcommit_throughput"
    elif metric == "memory":
        value_key = "memory_mean_mb"
        error_key = "memory_stddev_mb"
        ylabel = "Peak RSS (MiB)"
        title = "AF-fast overcommit increases peak memory"
        filename = "human_cif_af_fast_overcommit_peak_rss"
    else:
        raise ValueError(f"unsupported AF-fast overcommit metric: {metric}")

    variants = {
        "read-all": "zsasa_af_fast_read",
        "mmap": "zsasa_af_fast_mmap",
    }
    styles = {
        "read-all": {"color": "#e67e22", "marker": "o", "linestyle": "-"},
        "mmap": {"color": "#d99b2b", "marker": "s", "linestyle": "--"},
    }
    fig, ax = plt.subplots(figsize=(7.2, 4.9), layout="constrained")
    ax.axvspan(10, 40, color="0.5", alpha=0.06, zorder=0)
    ax.axvline(10, color="0.4", linestyle=":", linewidth=1.0, alpha=0.7, zorder=0)
    for io_mode, variant in variants.items():
        selected = [row_for(rows, variant, threads) for threads in (10, 20, 40)]
        ax.errorbar(
            [row["threads"] for row in selected],
            [row[value_key] for row in selected],
            yerr=[row[error_key] for row in selected],
            linewidth=2.2,
            markersize=7,
            capsize=3,
            label=io_mode,
            **styles[io_mode],
        )
    ax.text(
        0.98,
        0.96,
        "overcommit",
        transform=ax.transAxes,
        ha="right",
        va="top",
        color="0.35",
        fontsize=8,
    )
    ax.set_title(title)
    ax.set_xlabel("Workers")
    ax.set_ylabel(ylabel)
    ax.set_xticks([10, 20, 40])
    ax.set_xlim(8, 42)
    ax.grid(axis="x", visible=False)
    ax.legend(title=r"10 logical CPUs, mean $\pm$ SD ($n$ = 3)", frameon=False)
    return save_figure(fig, out_dir, filename)


def plot_human_cif_af_fast_overcommit_tradeoff(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Pair the AF-fast throughput response with its memory cost."""
    variants = {
        "read-all": "zsasa_af_fast_read",
        "mmap": "zsasa_af_fast_mmap",
    }
    styles = {
        "read-all": {"color": "#e67e22", "marker": "o", "linestyle": "-"},
        "mmap": {"color": "#d99b2b", "marker": "s", "linestyle": "--"},
    }
    metrics = [
        ("throughput_change", "", "Change from 10 threads (%)", "Throughput response"),
        ("memory_mean_mb", "memory_stddev_mb", "Peak RSS (MiB)", "Memory cost"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), layout="constrained")
    for ax, (value_key, error_key, ylabel, title) in zip(axes, metrics, strict=True):
        ax.axvspan(10, 40, color="0.5", alpha=0.06, zorder=0)
        ax.axvline(10, color="0.4", linestyle=":", linewidth=1.0, alpha=0.7, zorder=0)
        for io_mode, variant in variants.items():
            selected = [row_for(rows, variant, threads) for threads in (10, 20, 40)]
            if value_key == "throughput_change":
                baseline = selected[0]["throughput"]
                values = [(row["throughput"] / baseline - 1.0) * 100 for row in selected]
                errors = [
                    0.0
                    if row is selected[0]
                    else 100
                    * row["throughput"]
                    / baseline
                    * np.hypot(
                        row["throughput_stddev"] / row["throughput"],
                        selected[0]["throughput_stddev"] / baseline,
                    )
                    for row in selected
                ]
            else:
                values = [row[value_key] for row in selected]
                errors = [row[error_key] for row in selected]
            style = dict(styles[io_mode])
            if io_mode == "mmap":
                style.update({"markerfacecolor": "none", "markeredgewidth": 1.5})
            ax.errorbar(
                [row["threads"] for row in selected],
                values,
                yerr=errors,
                linewidth=2.2,
                markersize=7,
                capsize=3,
                label=io_mode,
                **style,
            )
        ax.set_title(title)
        ax.set_xlabel("Threads")
        ax.set_ylabel(ylabel)
        ax.set_xticks([10, 20, 40])
        ax.set_xlim(8, 45)
        ax.grid(axis="x", visible=False)

    read_start = row_for(rows, variants["read-all"], 10)["throughput"]
    read_end = row_for(rows, variants["read-all"], 40)["throughput"]
    mmap_start = row_for(rows, variants["mmap"], 10)["throughput"]
    mmap_end = row_for(rows, variants["mmap"], 40)["throughput"]
    axes[0].axhline(0, color="0.35", linestyle=":", linewidth=0.9, alpha=0.7)
    axes[0].annotate(
        f"read-all  {(read_end / read_start - 1) * 100:+.1f}%",
        (40, (read_end / read_start - 1) * 100),
        xytext=(7, -2),
        textcoords="offset points",
        color=styles["read-all"]["color"],
        fontsize=8,
        fontweight="bold",
    )
    axes[0].annotate(
        f"mmap  {(mmap_end / mmap_start - 1) * 100:+.1f}%",
        (40, (mmap_end / mmap_start - 1) * 100),
        xytext=(7, -2),
        textcoords="offset points",
        color=styles["mmap"]["color"],
        fontsize=8,
        fontweight="bold",
    )
    axes[0].set_ylim(-2.0, 5.5)

    rss_start = row_for(rows, variants["read-all"], 10)["memory_mean_mb"]
    rss_end = row_for(rows, variants["read-all"], 40)["memory_mean_mb"]
    axes[1].text(
        0.96,
        0.13,
        f"read-all and mmap overlap\n{rss_end / rss_start:.1f}× peak RSS",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        color="0.30",
        fontsize=8,
        fontweight="bold",
    )
    axes[1].set_ylim(0, 335)
    axes[1].legend(
        handles=[
            plt.Line2D(
                [0],
                [0],
                color=styles["read-all"]["color"],
                marker=styles["read-all"]["marker"],
                linestyle=styles["read-all"]["linestyle"],
                linewidth=2.0,
                label="read-all",
            ),
            plt.Line2D(
                [0],
                [0],
                color=styles["mmap"]["color"],
                marker=styles["mmap"]["marker"],
                markerfacecolor="none",
                markeredgewidth=1.5,
                linestyle=styles["mmap"]["linestyle"],
                linewidth=2.0,
                label="mmap",
            ),
        ],
        loc="upper center",
        ncol=2,
        frameon=False,
    )
    add_panel_label(axes[0], "a")
    add_panel_label(axes[1], "b")
    fig.suptitle("AF-fast I/O behavior under thread overcommit", fontsize=11)
    return save_figure(fig, out_dir, "human_cif_af_fast_overcommit_tradeoff")


def plot_human_cif_parser_io_metric(
    rows: list[dict[str, Any]], out_dir: Path, *, metric: str
) -> list[Path]:
    """Compare Human mmCIF parser paths and input I/O at 20 workers."""
    selected = {row["variant"]: row for row in human_cif_t20_rows(rows)}
    parser_variants = {
        "read": ["zsasa_generic_read", "zsasa_af_fast_read"],
        "mmap": ["zsasa_generic_mmap", "zsasa_af_fast_mmap"],
    }
    expected_variants = {
        variant for variants in parser_variants.values() for variant in variants
    }
    if not expected_variants.issubset(selected):
        return []

    if metric == "throughput":
        value_key = "throughput"
        error_key = "throughput_stddev"
        ylabel = r"Throughput (structures s$^{-1}$)"
        title_metric = "throughput"
        name_metric = "throughput"
        label_format = ",.0f"
    elif metric == "memory":
        value_key = "memory_mean_mb"
        error_key = "memory_stddev_mb"
        ylabel = "Peak RSS (MiB)"
        title_metric = "peak RSS"
        name_metric = "peak_rss"
        label_format = ".0f"
    else:
        raise ValueError(f"unsupported Human CIF metric: {metric}")

    x = np.arange(2)
    width = 0.34
    fig, ax = plt.subplots(figsize=(7.4, 5.2), layout="constrained")
    io_styles = {
        "read": {"color": "#e67e22", "edgecolor": "#a74f0a", "hatch": ""},
        "mmap": {"color": "#f6c85f", "edgecolor": "#a66f00", "hatch": "//"},
    }
    all_heights: list[float] = []
    for index, (io_mode, variants) in enumerate(parser_variants.items()):
        values = [selected[variant][value_key] for variant in variants]
        errors = [selected[variant][error_key] for variant in variants]
        all_heights.extend(value + error for value, error in zip(values, errors, strict=True))
        bars = ax.bar(
            x + (index - 0.5) * width,
            values,
            width,
            yerr=errors,
            capsize=3,
            linewidth=1.2,
            label=io_mode,
            **io_styles[io_mode],
        )
        ax.bar_label(
            bars,
            labels=[format(value, label_format) for value in values],
            padding=4,
            fontsize=8,
        )

    ax.set_title(
        f"Human AFDB mmCIF parser and input I/O {title_metric}\n"
        "(23,586 structures, 128 points, 20 workers)"
    )
    ax.set_ylabel(ylabel)
    ax.set_xticks(x, ["Generic parser", "AF-model fast path"])
    ax.set_ylim(0, max(all_heights) * 1.18)
    ax.grid(axis="x", visible=False)
    ax.legend(title=r"Mean $\pm$ SD ($n$ = 3)", loc="upper left", frameon=False)
    return save_figure(fig, out_dir, f"human_cif_parser_io_{name_metric}")


def human_cif_t20_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return the complete Human mmCIF 20-worker matrix by variant."""
    return {row["variant"]: row for row in human_cif_t20_rows(rows)}


def plot_human_cif_performance_memory_map(
    rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    """Show parser and input-I/O effects in performance-memory space."""
    selected = human_cif_t20_matrix(rows)
    paths = {
        "read": ("zsasa_generic_read", "zsasa_af_fast_read"),
        "mmap": ("zsasa_generic_mmap", "zsasa_af_fast_mmap"),
    }
    if not {variant for path in paths.values() for variant in path}.issubset(selected):
        return []

    fig, ax = plt.subplots(figsize=(7.4, 5.4), layout="constrained")
    parser_colors = {"generic": "#f6c85f", "af_fast": "#e67e22"}
    io_styles = {
        "read": {"marker": "o", "linestyle": "-"},
        "mmap": {"marker": "X", "linestyle": "--"},
    }
    for io_mode, (generic_variant, fast_variant) in paths.items():
        generic = selected[generic_variant]
        fast = selected[fast_variant]
        ax.plot(
            [generic["memory_mean_mb"], fast["memory_mean_mb"]],
            [generic["throughput"], fast["throughput"]],
            color="0.45",
            linestyle=io_styles[io_mode]["linestyle"],
            linewidth=1.4,
            alpha=0.75,
            zorder=1,
        )
        for parser, row in (("generic", generic), ("af_fast", fast)):
            ax.scatter(
                row["memory_mean_mb"],
                row["throughput"],
                marker=io_styles[io_mode]["marker"],
                s=105 if io_mode == "read" else 75,
                color=parser_colors[parser],
                edgecolor="#7f4a00",
                linewidth=1.2,
                zorder=3 if io_mode == "mmap" else 2,
            )

    generic_rows = [selected[variant] for variant in paths["read"][:1] + paths["mmap"][:1]]
    fast_rows = [selected[variant] for variant in paths["read"][1:] + paths["mmap"][1:]]
    cluster_labels = (
        ("Generic parser", generic_rows, (-10, -12), "right", "top"),
        ("AF-model fast path", fast_rows, (10, -12), "left", "top"),
    )
    for label, cluster, offset, ha, va in cluster_labels:
        x = sum(row["memory_mean_mb"] for row in cluster) / len(cluster)
        y = sum(row["throughput"] for row in cluster) / len(cluster)
        ax.annotate(
            label,
            (x, y),
            xytext=offset,
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=9,
            fontweight="bold",
        )

    handles = [
        plt.Line2D(
            [0],
            [0],
            marker=io_styles[io_mode]["marker"],
            linestyle=io_styles[io_mode]["linestyle"],
            color="0.45",
            markerfacecolor="white",
            markeredgecolor="0.35",
            label=io_mode,
        )
        for io_mode in ("read", "mmap")
    ]
    ax.legend(handles=handles, loc="lower left", frameon=False)
    ax.text(
        0.98,
        0.96,
        "AF fast vs generic\n≈17% higher throughput\n≈25% lower peak RSS",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )
    ax.set_title(
        "Human AFDB mmCIF parser performance and memory\n"
        "(23,586 structures, 128 points, 20 workers, three-run means)"
    )
    ax.set_xlabel("Peak RSS (MiB)")
    ax.set_ylabel(r"Throughput (structures s$^{-1}$)")
    ax.margins(x=0.08, y=0.12)
    return save_figure(fig, out_dir, "human_cif_parser_io_performance_memory")


def plot_human_cif_interaction(
    rows: list[dict[str, Any]], out_dir: Path, *, metric: str
) -> list[Path]:
    """Plot the parser-by-I/O interaction for one Human mmCIF metric."""
    selected = human_cif_t20_matrix(rows)
    variants = {
        "read": ("zsasa_generic_read", "zsasa_af_fast_read"),
        "mmap": ("zsasa_generic_mmap", "zsasa_af_fast_mmap"),
    }
    if not {variant for pair in variants.values() for variant in pair}.issubset(selected):
        return []

    if metric == "throughput":
        value_key = "throughput"
        error_key = "throughput_stddev"
        ylabel = r"Throughput (structures s$^{-1}$)"
        title_metric = "throughput"
        name_metric = "throughput"
        endpoint_labels = ("1,299", "1,514–1,518")
    elif metric == "memory":
        value_key = "memory_mean_mb"
        error_key = "memory_stddev_mb"
        ylabel = "Peak RSS (MiB)"
        title_metric = "peak RSS"
        name_metric = "peak_rss"
        endpoint_labels = ("232–233", "172–175")
    else:
        raise ValueError(f"unsupported Human CIF interaction metric: {metric}")

    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(7.2, 5.2), layout="constrained")
    styles = {
        "read": {"color": "#e67e22", "marker": "o", "linestyle": "-"},
        "mmap": {"color": "#d99b2b", "marker": "s", "linestyle": "--"},
    }
    all_values: list[float] = []
    for io_mode, pair in variants.items():
        values = [selected[variant][value_key] for variant in pair]
        errors = [selected[variant][error_key] for variant in pair]
        all_values.extend(values)
        ax.errorbar(
            x,
            values,
            yerr=errors,
            label=io_mode,
            linewidth=2.0,
            markersize=6,
            capsize=3,
            **styles[io_mode],
        )

    span = max(all_values) - min(all_values)
    ax.set_ylim(min(all_values) - span * 0.22, max(all_values) + span * 0.28)
    ax.set_xticks(x, ["Generic parser", "AF-model fast path"])
    ax.set_ylabel(ylabel)
    ax.set_title(
        f"Human AFDB mmCIF parser and input I/O {title_metric}\n"
        "(23,586 structures, 128 points, 20 workers)"
    )
    ax.grid(axis="x", visible=False)
    ax.legend(title=r"Mean $\pm$ SD ($n$ = 3)", loc="best", frameon=False)
    generic_values = [selected[pair[0]][value_key] for pair in variants.values()]
    fast_values = [selected[pair[1]][value_key] for pair in variants.values()]
    generic_label_y = max(generic_values) + span * 0.08
    ax.text(0, generic_label_y, endpoint_labels[0], ha="center", fontsize=8)
    if metric == "throughput":
        fast_label_y = max(fast_values) + span * 0.08
    else:
        fast_label_y = min(fast_values) - span * 0.10
    ax.text(1, fast_label_y, endpoint_labels[1], ha="center", fontsize=8)
    return save_figure(fig, out_dir, f"human_cif_parser_io_interaction_{name_metric}")


def plot_human_cif_parser_effect(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    """Summarize the AF fast-path effect relative to the generic parser."""
    selected = human_cif_t20_matrix(rows)
    variants = {
        "read": ("zsasa_generic_read", "zsasa_af_fast_read"),
        "mmap": ("zsasa_generic_mmap", "zsasa_af_fast_mmap"),
    }
    if not {variant for pair in variants.values() for variant in pair}.issubset(selected):
        return []

    fig, ax = plt.subplots(figsize=(7.2, 3.7), layout="constrained")
    y_by_metric = {"Throughput": 1.0, "Peak RSS": 0.0}
    styles = {
        "read": {"color": "#e67e22", "marker": "o", "offset": 0.07},
        "mmap": {"color": "#d99b2b", "marker": "s", "offset": -0.07},
    }
    for io_mode, (generic_variant, fast_variant) in variants.items():
        generic = selected[generic_variant]
        fast = selected[fast_variant]
        changes = {
            "Throughput": (fast["throughput"] / generic["throughput"] - 1.0) * 100,
            "Peak RSS": (fast["memory_mean_mb"] / generic["memory_mean_mb"] - 1.0) * 100,
        }
        for metric_name, change in changes.items():
            y = y_by_metric[metric_name] + styles[io_mode]["offset"]
            ax.scatter(
                change,
                y,
                s=65,
                color=styles[io_mode]["color"],
                marker=styles[io_mode]["marker"],
                label=io_mode if metric_name == "Throughput" else None,
                zorder=3,
            )
            ax.annotate(
                f"{change:+.1f}%",
                (change, y),
                xytext=(6, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )

    ax.axvline(0, color="0.35", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_yticks([0, 1], ["Peak RSS", "Throughput"])
    ax.set_xlabel("Change with AF-model fast path relative to generic parser (%)")
    ax.set_title(
        "Human AFDB mmCIF AF-model fast-path effect\n"
        "(23,586 structures, 128 points, 20 workers)"
    )
    ax.grid(axis="y", visible=False)
    ax.legend(loc="center right", frameon=False)
    return save_figure(fig, out_dir, "human_cif_parser_effect_summary")


def plot_human_cif_worker_scaling(
    rows: list[dict[str, Any]], out_dir: Path, *, metric: str
) -> list[Path]:
    """Show parser, I/O, comparator, and worker-overcommit behavior."""
    selected = {row["variant"]: [] for row in rows}
    for row in rows:
        selected[row["variant"]].append(row)
    for variant_rows in selected.values():
        variant_rows.sort(key=lambda row: row["threads"])

    read_variants = {
        "zsasa_generic_read": "zsasa generic/read",
        "zsasa_af_fast_read": "zsasa AF fast/read",
    }
    mmap_variants = {
        "zsasa_generic_mmap": "zsasa generic/mmap (20 workers)",
        "zsasa_af_fast_mmap": "zsasa AF fast/mmap (20 workers)",
    }
    required = {*read_variants, *mmap_variants, "lahuta_bitmask"}
    if not required.issubset(selected):
        return []

    if metric == "throughput":
        value_key = "throughput"
        error_key = "throughput_stddev"
        ylabel = r"Throughput (structures s$^{-1}$)"
        title_metric = "throughput"
        name_metric = "throughput"
    elif metric == "memory":
        value_key = "memory_mean_mb"
        error_key = "memory_stddev_mb"
        ylabel = "Peak RSS (MiB)"
        title_metric = "peak RSS"
        name_metric = "peak_rss"
    else:
        raise ValueError(f"unsupported Human CIF worker-scaling metric: {metric}")

    parser_colors = {
        "zsasa_generic_read": "#f6c85f",
        "zsasa_generic_mmap": "#f6c85f",
        "zsasa_af_fast_read": "#e67e22",
        "zsasa_af_fast_mmap": "#e67e22",
    }
    fig, ax = plt.subplots(figsize=(8.0, 5.3), layout="constrained")
    ax.axvspan(10, 40, color="0.5", alpha=0.06, zorder=0)
    ax.axvline(10, color="0.4", linestyle="--", linewidth=0.9, alpha=0.5, zorder=0)

    for variant, label in read_variants.items():
        variant_rows = selected[variant]
        ax.errorbar(
            [row["threads"] for row in variant_rows],
            [row[value_key] for row in variant_rows],
            yerr=[row[error_key] for row in variant_rows],
            color=parser_colors[variant],
            marker="o",
            linewidth=2.2,
            markersize=6,
            capsize=3,
            label=label,
            zorder=2,
        )

    for variant, label in mmap_variants.items():
        row = selected[variant][0]
        ax.errorbar(
            row["threads"],
            row[value_key],
            yerr=row[error_key],
            color=parser_colors[variant],
            marker="D",
            markerfacecolor="white",
            markeredgewidth=1.4,
            markersize=7,
            capsize=3,
            linestyle="none",
            label=label,
            zorder=4,
        )

    lahuta = next(row for row in selected["lahuta_bitmask"] if row["threads"] == 10)
    ax.errorbar(
        lahuta["threads"],
        lahuta[value_key],
        yerr=lahuta[error_key],
        color=color_for("lahuta_bitmask"),
        marker="P",
        markersize=8,
        capsize=3,
        linestyle="none",
        label="Lahuta bitmask (10 workers)",
        zorder=3,
    )

    ax.set_title(
        f"Human AFDB mmCIF batch {title_metric} by worker count\n"
        "(23,586 structures, 128 points, 10 logical CPUs)"
    )
    ax.set_xlabel("Workers")
    ax.set_ylabel(ylabel)
    ax.set_xticks([10, 20, 40])
    ax.set_xlim(8, 42)
    ax.grid(axis="x", visible=False)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title=r"Mean $\pm$ SD ($n$ = 3)",
        loc="outside lower center",
        ncol=3,
        frameon=False,
    )
    return save_figure(fig, out_dir, f"human_cif_worker_scaling_{name_metric}")


def batch_comparison_label_style(variant: str) -> dict[str, Any]:
    arrowprops = {"arrowstyle": "-", "color": "0.35", "lw": 0.7}
    if variant in {"lahuta", "zsasa_f64"}:
        return {"xytext": (-8, 8), "ha": "right", "va": "bottom", "arrowprops": arrowprops}
    if variant == "zsasa_bitmask_f64":
        return {"xytext": (-10, 0), "ha": "right", "va": "center", "arrowprops": arrowprops}
    return {"xytext": (5, 3), "ha": "left", "va": "baseline"}


def plot_t10_runtime_bar_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = sorted(t10_rows(rows), key=lambda row: row["mean_s"])
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [row["mean_s"] for row in selected],
        yerr=[row["stddev_s"] for row in selected],
        capsize=3,
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.set_title(f"{label} batch runtime at 10 threads")
    ax.set_ylabel("runtime (s), lower is better")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, f"{slug}_t10_runtime_bar")


def plot_t10_throughput_bar_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = sorted(t10_rows(rows), key=lambda row: row["throughput"], reverse=True)
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [row["throughput"] for row in selected],
        yerr=[row["throughput_stddev"] for row in selected],
        capsize=3,
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.set_title(f"{label} batch throughput at 10 threads")
    ax.set_ylabel("structures / sec")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, f"{slug}_t10_throughput_bar")


def plot_t10_memory_bar_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = sorted(
        [row for row in t10_rows(rows) if row.get("memory_mean_mb", 0.0) > 0],
        key=lambda row: row["memory_mean_mb"],
    )
    if not selected:
        return []
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [row["memory_mean_mb"] for row in selected],
        yerr=[row["memory_stddev_mb"] for row in selected],
        capsize=3,
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.set_title(f"{label} batch peak RSS at 10 threads")
    ax.set_ylabel("peak RSS (MiB)")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, f"{slug}_t10_peak_rss_bar")


def plot_t10_throughput_per_mib_bar_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = sorted(
        [row for row in t10_rows(rows) if row.get("memory_mean_mb", 0.0) > 0],
        key=lambda row: row["throughput"] / row["memory_mean_mb"],
        reverse=True,
    )
    if not selected:
        return []
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [row["throughput"] / row["memory_mean_mb"] for row in selected],
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.set_title(f"{label} throughput per peak RSS at 10 threads")
    ax.set_ylabel("structures / sec / MiB")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, f"{slug}_t10_throughput_per_mib_bar")


def plot_t10_cpu_utilization_bar_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = sorted(t10_rows(rows), key=lambda row: cpu_utilization_proxy(row), reverse=True)
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(row["variant"]) for row in selected],
        [cpu_utilization_proxy(row) for row in selected],
        color=[color_for(row["variant"]) for row in selected],
    )
    ax.axhline(10, linestyle="--", color="0.35", alpha=0.4, label="ideal 10")
    ax.set_title(f"{label} CPU utilization proxy at 10 threads")
    ax.set_ylabel("(user + system) / wall time")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(loc="best")
    return save_figure(fig, out_dir, f"{slug}_t10_cpu_utilization_bar")


def plot_t10_throughput_memory_for_dataset(
    rows: list[dict[str, Any]], out_dir: Path, slug: str, label: str
) -> list[Path]:
    selected = [row for row in t10_rows(rows) if row.get("memory_mean_mb", 0.0) > 0]
    if not selected:
        return []
    fig, ax = plt.subplots(figsize=(7.2, 5.6), layout="constrained")
    for row in selected:
        ax.scatter(row["memory_mean_mb"], row["throughput"], s=70, color=color_for(row["variant"]))
        label_style = throughput_memory_label_style(row["variant"])
        ax.annotate(
            display_name(row["variant"]),
            (row["memory_mean_mb"], row["throughput"]),
            xytext=label_style["xytext"],
            textcoords="offset points",
            ha=label_style["ha"],
            va=label_style["va"],
            arrowprops=label_style.get("arrowprops"),
            fontsize=8,
        )
    ax.set_title(f"{label} throughput vs peak RSS at 10 threads")
    ax.set_xlabel("peak RSS (MiB)")
    ax.set_ylabel("structures / sec")
    return save_figure(fig, out_dir, f"{slug}_t10_throughput_vs_peak_rss")


def plot_t10_comparator_ratio_for_dataset(
    rows: list[dict[str, Any]],
    out_dir: Path,
    slug: str,
    label: str,
    *,
    metric: str,
    ylabel: str,
    title_metric: str,
    name_metric: str,
    candidate_variants: list[str] | None = None,
) -> list[Path]:
    selected = {row["variant"]: row for row in t10_rows(rows)}
    requested_candidates = candidate_variants or ZSASA_BATCH_VARIANTS
    candidates = [variant for variant in requested_candidates if variant in selected]
    if not candidates:
        return []
    x = np.arange(len(candidates))
    width = 0.25
    width_inches = 7.8 if len(candidates) <= 2 else 10.5
    fig, ax = plt.subplots(figsize=(width_inches, 5.5), layout="constrained")
    comparator_styles = {
        "freesasa_batch": {
            "color": color_for("freesasa_batch"),
            "edgecolor": "#1f5f8f",
            "hatch": "",
        },
        "rustsasa": {
            "color": color_for("rustsasa"),
            "edgecolor": "#992d22",
            "hatch": "///",
        },
        "lahuta_bitmask": {
            "color": color_for("lahuta_bitmask"),
            "edgecolor": "#7d3c98",
            "hatch": "\\\\\\",
        },
    }
    all_values: list[float] = []
    for index, comparator in enumerate(BATCH_COMPARATOR_VARIANTS):
        baseline = selected.get(comparator)
        if baseline is None:
            continue
        values = []
        for variant in candidates:
            if variant == comparator or selected[variant][metric] <= 0:
                values.append(np.nan)
            else:
                values.append(baseline[metric] / selected[variant][metric])
        all_values.extend(value for value in values if value > 0)
        positions = x + (index - 1) * width
        bars = ax.bar(
            positions,
            values,
            width=width,
            linewidth=1.2,
            label=f"vs {display_name(comparator)}",
            alpha=0.75,
            **comparator_styles[comparator],
        )
        ax.bar_label(
            bars,
            labels=[
                (f"{value:.2f}×" if value < 1 else f"{value:.1f}×")
                if np.isfinite(value)
                else ""
                for value in values
            ],
            padding=3,
            fontsize=8,
        )
    ax.axhline(1.0, color="0.35", linestyle="--", linewidth=0.8, alpha=0.45)
    ymax = max(all_values) * 1.22
    ax.set_ylim(0, ymax)
    if name_metric == "runtime_speedup":
        ratio_ticks = [tick for tick in ax.get_yticks() if 0 <= tick <= ymax]
        ax.set_yticks(sorted({*ratio_ticks, 1.0}))
    ax.set_title(f"{label} batch {title_metric}")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x, [display_name(variant) for variant in candidates])
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")
    handles = [
        Patch(
            facecolor=color_for("freesasa_batch"),
            edgecolor="#1f5f8f",
            linewidth=1.2,
            label="vs FreeSASA batch",
            alpha=0.75,
        ),
        Patch(
            facecolor=color_for("rustsasa"),
            edgecolor="#992d22",
            linewidth=1.2,
            hatch="///",
            label="vs RustSASA",
            alpha=0.75,
        ),
        Patch(
            facecolor=color_for("lahuta_bitmask"),
            edgecolor="#7d3c98",
            linewidth=1.2,
            hatch="\\\\\\",
            label="vs Lahuta bitmask",
            alpha=0.75,
        ),
    ]
    ax.legend(handles=handles, loc="upper right", ncol=3, frameon=False)
    return save_figure(fig, out_dir, f"{slug}_t10_{name_metric}_vs_comparators")


def plot_t10_throughput_dataset_scatter(
    ecoli_rows: list[dict[str, Any]], human_rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    ecoli = {row["variant"]: row for row in t10_rows(ecoli_rows)}
    human = {row["variant"]: row for row in t10_rows(human_rows)}
    variants = sorted(set(ecoli) & set(human), key=variant_sort_key)
    fig, ax = plt.subplots(figsize=(6.8, 5.8), layout="constrained")
    for variant in variants:
        x = ecoli[variant]["throughput"]
        y = human[variant]["throughput"]
        ax.scatter(x, y, s=70, color=color_for(variant))
        label_style = batch_comparison_label_style(variant)
        ax.annotate(
            display_name(variant),
            (x, y),
            xytext=label_style["xytext"],
            textcoords="offset points",
            ha=label_style["ha"],
            va=label_style["va"],
            arrowprops=label_style.get("arrowprops"),
            fontsize=8,
        )
    hi = max(
        [ecoli[v]["throughput"] for v in variants] + [human[v]["throughput"] for v in variants]
    )
    ax.plot([0, hi], [0, hi], linestyle="--", color="0.35", alpha=0.4)
    ax.set_title("10-thread throughput: E. coli vs Human")
    ax.set_xlabel("E. coli structures / sec")
    ax.set_ylabel("Human structures / sec")
    return save_figure(fig, out_dir, "t10_throughput_ecoli_vs_human")


def plot_t10_human_ecoli_retention(
    ecoli_rows: list[dict[str, Any]], human_rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    ecoli = {row["variant"]: row for row in t10_rows(ecoli_rows)}
    human = {row["variant"]: row for row in t10_rows(human_rows)}
    variants = sorted(set(ecoli) & set(human), key=variant_sort_key)
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    ax.bar(
        [display_name(v) for v in variants],
        [human[v]["throughput"] / ecoli[v]["throughput"] for v in variants],
        color=[color_for(v) for v in variants],
    )
    ax.axhline(1.0, linestyle="--", color="0.35", alpha=0.4)
    ax.set_title("Human / E. coli throughput ratio at 10 threads")
    ax.set_ylabel("Human throughput / E. coli throughput")
    ax.tick_params(axis="x", rotation=35)
    return save_figure(fig, out_dir, "t10_human_ecoli_throughput_ratio")


def plot_t10_ms_per_structure_comparison(
    ecoli_rows: list[dict[str, Any]], human_rows: list[dict[str, Any]], out_dir: Path
) -> list[Path]:
    datasets = [("E. coli", ecoli_rows), ("Human", human_rows)]
    variants = sorted(
        {row["variant"] for _, rows in datasets for row in t10_rows(rows)}, key=variant_sort_key
    )
    x = np.arange(len(variants))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.4), layout="constrained")
    for idx, (dataset_name, rows) in enumerate(datasets):
        row_by_variant = {row["variant"]: row for row in t10_rows(rows)}
        offset = (idx - 0.5) * width
        ax.bar(
            x + offset,
            [
                milliseconds_per_structure(
                    row_by_variant[v]["mean_s"], row_by_variant[v]["expected_count"]
                )
                for v in variants
            ],
            width=width,
            label=dataset_name,
            color="#95a5a6" if idx == 0 else "#34495e",
        )
    ax.set_title("10-thread normalized runtime per structure")
    ax.set_ylabel("ms / structure, lower is better")
    ax.set_xticks(x, [display_name(v) for v in variants], rotation=35, ha="right")
    ax.legend(loc="best")
    return save_figure(fig, out_dir, "t10_ms_per_structure_ecoli_human")


def write_index(out_dir: Path, outputs: list[Path], title: str = "E. coli batch figures") -> Path:
    index = out_dir.joinpath("index.md")
    pngs = sorted(path for path in outputs if path.suffix == ".png")
    lines = [f"# {title}", "", f"Generated {len(pngs)} figures in PNG/SVG/PDF.", ""]
    for path in pngs:
        lines.append(f"- `{path.relative_to(out_dir)}`")
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dataset-id", default=ECOLI_DATASET, help="dataset id, or 'all'")
    return parser.parse_args()


def ecoli_comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the release-comparable E. coli thread range in the primary figures."""
    return [row for row in rows if int(row["threads"]) <= 10]


def generate_ecoli(rows: list[dict[str, Any]], out_dir: Path) -> tuple[list[Path], Path]:
    rows = ecoli_comparison_rows(rows)
    outputs: list[Path] = []
    outputs.extend(plot_ecoli_throughput_scaling_story(rows, out_dir))
    outputs.extend(plot_ecoli_performance_memory_story(rows, out_dir))
    outputs.extend(plot_throughput(rows, out_dir))
    outputs.extend(plot_runtime(rows, out_dir))
    outputs.extend(plot_speedup(rows, out_dir))
    outputs.extend(plot_t10_bar(rows, out_dir))
    outputs.extend(plot_replicates(rows, out_dir))
    outputs.extend(plot_memory(rows, out_dir))
    outputs.extend(plot_t10_memory_bar(rows, out_dir))
    outputs.extend(plot_t10_throughput_memory(rows, out_dir))
    outputs.extend(
        plot_t10_comparator_ratio_for_dataset(
            rows,
            out_dir,
            "ecoli",
            "E. coli",
            metric="mean_s",
            ylabel="Throughput ratio (zsasa / comparator)",
            title_metric="throughput ratio",
            name_metric="runtime_speedup",
            candidate_variants=["zsasa_f64", "zsasa_bitmask_f32"],
        )
    )
    outputs.extend(
        plot_t10_comparator_ratio_for_dataset(
            rows,
            out_dir,
            "ecoli",
            "E. coli",
            metric="memory_mean_mb",
            ylabel="Peak RSS ratio (comparator / zsasa)",
            title_metric="peak RSS reduction",
            name_metric="rss_reduction",
            candidate_variants=["zsasa_f64", "zsasa_bitmask_f32"],
        )
    )
    outputs.extend(plot_throughput_per_mib(rows, out_dir))
    outputs.extend(plot_cpu_utilization(rows, out_dir))
    outputs.extend(plot_efficiency_heatmap(rows, out_dir))
    return outputs, write_index(out_dir, outputs, "E. coli batch figures")


def generate_human(rows: list[dict[str, Any]], out_dir: Path) -> tuple[list[Path], Path]:
    outputs: list[Path] = []
    outputs.extend(plot_t10_throughput_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_runtime_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_memory_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_human_performance_memory_map(rows, out_dir))
    outputs.extend(
        plot_t10_comparator_ratio_for_dataset(
            rows,
            out_dir,
            "human",
            "Human",
            metric="mean_s",
            ylabel="Throughput ratio (zsasa / comparator)",
            title_metric="throughput ratio",
            name_metric="runtime_speedup",
            candidate_variants=["zsasa_f64", "zsasa_bitmask_f32"],
        )
    )
    outputs.extend(
        plot_t10_comparator_ratio_for_dataset(
            rows,
            out_dir,
            "human",
            "Human",
            metric="memory_mean_mb",
            ylabel="Peak RSS ratio (comparator / zsasa)",
            title_metric="peak RSS reduction",
            name_metric="rss_reduction",
            candidate_variants=["zsasa_f64", "zsasa_bitmask_f32"],
        )
    )
    outputs.extend(plot_t10_throughput_per_mib_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_cpu_utilization_bar_for_dataset(rows, out_dir, "human", "Human"))
    return outputs, write_index(out_dir, outputs, "Human batch figures")


def generate_human_cif(
    rows: list[dict[str, Any]], pdb_rows: list[dict[str, Any]], out_dir: Path
) -> tuple[list[Path], Path]:
    outputs: list[Path] = []
    outputs.extend(plot_human_cif_ranking_recovery_story(pdb_rows, rows, out_dir))
    outputs.extend(plot_human_cif_af_fast_overcommit_tradeoff(rows, out_dir))
    outputs.extend(plot_human_cif_parser_io_metric(rows, out_dir, metric="throughput"))
    outputs.extend(plot_human_cif_parser_io_metric(rows, out_dir, metric="memory"))
    outputs.extend(plot_human_cif_performance_memory_map(rows, out_dir))
    outputs.extend(plot_human_cif_interaction(rows, out_dir, metric="throughput"))
    outputs.extend(plot_human_cif_interaction(rows, out_dir, metric="memory"))
    outputs.extend(plot_human_cif_parser_effect(rows, out_dir))
    outputs.extend(plot_human_cif_worker_scaling(rows, out_dir, metric="throughput"))
    outputs.extend(plot_human_cif_worker_scaling(rows, out_dir, metric="memory"))
    return outputs, write_index(out_dir, outputs, "Human mmCIF batch figures")


def generate_t10_comparison(
    ecoli_rows: list[dict[str, Any]], human_rows: list[dict[str, Any]], out_dir: Path
) -> tuple[list[Path], Path]:
    outputs: list[Path] = []
    outputs.extend(plot_t10_throughput_dataset_scatter(ecoli_rows, human_rows, out_dir))
    outputs.extend(plot_t10_human_ecoli_retention(ecoli_rows, human_rows, out_dir))
    outputs.extend(plot_t10_ms_per_structure_comparison(ecoli_rows, human_rows, out_dir))
    return outputs, write_index(out_dir, outputs, "Batch 10-thread dataset comparison")


def main() -> None:
    args = parse_args()
    setup_style()
    written_indexes: list[Path] = []
    total_outputs = 0
    if args.dataset_id == "all":
        ecoli_rows = load_batch_rows(args.db, ECOLI_DATASET)
        human_rows = load_batch_rows(args.db, HUMAN_DATASET)
        human_cif_rows = load_batch_rows(args.db, HUMAN_CIF_DATASET)
        for outputs, index in [
            generate_ecoli(ecoli_rows, args.out_dir.joinpath("batch_ecoli")),
            generate_human(human_rows, args.out_dir.joinpath("batch_human")),
            generate_human_cif(
                human_cif_rows, human_rows, args.out_dir.joinpath("batch_human_cif")
            ),
            generate_t10_comparison(
                ecoli_rows, human_rows, args.out_dir.joinpath("batch_t10_comparison")
            ),
        ]:
            total_outputs += sum(1 for path in outputs if path.suffix == ".png")
            written_indexes.append(index)
    elif args.dataset_id == HUMAN_DATASET or args.dataset_id == "human":
        rows = load_batch_rows(args.db, HUMAN_DATASET)
        outputs, index = generate_human(rows, args.out_dir)
        total_outputs = sum(1 for path in outputs if path.suffix == ".png")
        written_indexes.append(index)
    elif args.dataset_id == HUMAN_CIF_DATASET or args.dataset_id == "human_cif":
        rows = load_batch_rows(args.db, HUMAN_CIF_DATASET)
        pdb_rows = load_batch_rows(args.db, HUMAN_DATASET)
        outputs, index = generate_human_cif(rows, pdb_rows, args.out_dir)
        total_outputs = sum(1 for path in outputs if path.suffix == ".png")
        written_indexes.append(index)
    else:
        rows = load_batch_rows(args.db, ECOLI_DATASET)
        outputs, index = generate_ecoli(rows, args.out_dir)
        total_outputs = sum(1 for path in outputs if path.suffix == ".png")
        written_indexes.append(index)
    print(f"wrote {total_outputs} figure sets in PNG/SVG/PDF")
    for index in written_indexes:
        print(f"wrote {index}")


if __name__ == "__main__":
    main()
