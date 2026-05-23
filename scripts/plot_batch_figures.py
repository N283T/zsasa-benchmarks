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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures")
ECOLI_DATASET = "UP000000625_83333_ECOLI_v6_pdb"
HUMAN_DATASET = "UP000005640_9606_HUMAN_v6_pdb"

VARIANT_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "freesasa_batch",
    "rustsasa",
    "lahuta",
    "lahuta_bitmask",
]
COLORS = {
    "zsasa_f64": "#f39c12",
    "zsasa_f32": "#f6c85f",
    "zsasa_bitmask_f64": "#e67e22",
    "zsasa_bitmask_f32": "#ffb347",
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
    return dataset_id


def batch_column_name(run: dict[str, Any]) -> str:
    tool_id = str(run.get("tool_id") or "")
    precision = str(run.get("precision") or "")
    mode = str(run.get("mode") or "")
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
    for ext in ("png", "svg"):
        path = out_dir.joinpath(ext, f"{name}.{ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        written.append(path)
    plt.close(fig)
    return written


def load_batch_rows(db_path: Path, dataset_id: str) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        run_cols = [
            "run_id",
            "dataset_id",
            "tool_id",
            "precision",
            "mode",
            "threads",
            "expected_count",
            "source_path",
        ]
        run_rows = con.execute(
            """
            SELECT r.run_id, r.dataset_id, r.tool_id, r.precision, r.mode, r.threads,
                   d.expected_count, r.source_path
            FROM benchmark_runs r
            LEFT JOIN datasets d USING (dataset_id)
            WHERE r.benchmark_kind = 'batch'
              AND r.dataset_id = ?
            ORDER BY r.tool_id, r.precision, r.mode, r.threads
            """,
            [dataset_id],
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for raw_run in run_rows:
            run = dict(zip(run_cols, raw_run, strict=True))
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


def speedup_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = {
        row["variant"]: float(row["mean_s"])
        for row in rows
        if int(row["threads"]) == 1 and float(row["mean_s"]) > 0
    }
    output: list[dict[str, Any]] = []
    for row in rows:
        variant = row["variant"]
        if variant not in baseline:
            continue
        threads = int(row["threads"])
        speedup = baseline[variant] / float(row["mean_s"])
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
            ax.set_ylabel("speedup vs 1 thread")
            ax.set_title("Thread speedup")
        else:
            ax.axhline(1.0, linestyle="--", color="0.3", alpha=0.4)
            ax.set_ylabel("parallel efficiency")
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
        label_offsets = {
            "zsasa_f64": (12, 0),
            "zsasa_f32": (6, 7),
        }
        ax.annotate(
            display_name(row["variant"]),
            (row["memory_mean_mb"], row["throughput"]),
            xytext=label_offsets.get(row["variant"], (5, 3)),
            textcoords="offset points",
            va="center" if row["variant"] == "zsasa_f64" else "baseline",
            fontsize=8,
        )
    ax.set_title("E. coli batch throughput vs peak RSS at 10 threads")
    ax.set_xlabel("peak RSS (MiB)")
    ax.set_ylabel("structures / sec")
    return save_figure(fig, out_dir, "ecoli_t10_throughput_vs_peak_rss")


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
    cbar.set_label("speedup / threads")
    return save_figure(fig, out_dir, "ecoli_parallel_efficiency_heatmap")


def t10_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["threads"] == 10]


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
        label_offsets = {"zsasa_f64": (12, 0), "zsasa_f32": (6, 7)}
        ax.annotate(
            display_name(row["variant"]),
            (row["memory_mean_mb"], row["throughput"]),
            xytext=label_offsets.get(row["variant"], (5, 3)),
            textcoords="offset points",
            va="center" if row["variant"] == "zsasa_f64" else "baseline",
            fontsize=8,
        )
    ax.set_title(f"{label} throughput vs peak RSS at 10 threads")
    ax.set_xlabel("peak RSS (MiB)")
    ax.set_ylabel("structures / sec")
    return save_figure(fig, out_dir, f"{slug}_t10_throughput_vs_peak_rss")


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
    lines = [f"# {title}", "", f"Generated {len(pngs)} PNG figures.", ""]
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


def generate_ecoli(rows: list[dict[str, Any]], out_dir: Path) -> tuple[list[Path], Path]:
    outputs: list[Path] = []
    outputs.extend(plot_throughput(rows, out_dir))
    outputs.extend(plot_runtime(rows, out_dir))
    outputs.extend(plot_speedup(rows, out_dir))
    outputs.extend(plot_t10_bar(rows, out_dir))
    outputs.extend(plot_replicates(rows, out_dir))
    outputs.extend(plot_memory(rows, out_dir))
    outputs.extend(plot_t10_memory_bar(rows, out_dir))
    outputs.extend(plot_t10_throughput_memory(rows, out_dir))
    outputs.extend(plot_throughput_per_mib(rows, out_dir))
    outputs.extend(plot_cpu_utilization(rows, out_dir))
    outputs.extend(plot_efficiency_heatmap(rows, out_dir))
    return outputs, write_index(out_dir, outputs, "E. coli batch figures")


def generate_human(rows: list[dict[str, Any]], out_dir: Path) -> tuple[list[Path], Path]:
    outputs: list[Path] = []
    outputs.extend(plot_t10_throughput_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_runtime_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_memory_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_throughput_memory_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_throughput_per_mib_bar_for_dataset(rows, out_dir, "human", "Human"))
    outputs.extend(plot_t10_cpu_utilization_bar_for_dataset(rows, out_dir, "human", "Human"))
    return outputs, write_index(out_dir, outputs, "Human batch figures")


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
        for outputs, index in [
            generate_ecoli(ecoli_rows, args.out_dir.joinpath("batch_ecoli")),
            generate_human(human_rows, args.out_dir.joinpath("batch_human")),
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
    else:
        rows = load_batch_rows(args.db, ECOLI_DATASET)
        outputs, index = generate_ecoli(rows, args.out_dir)
        total_outputs = sum(1 for path in outputs if path.suffix == ".png")
        written_indexes.append(index)
    print(f"wrote {total_outputs} PNG figures")
    for index in written_indexes:
        print(f"wrote {index}")


if __name__ == "__main__":
    main()
