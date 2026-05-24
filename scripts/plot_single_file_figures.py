#!/usr/bin/env python3
"""Generate exploratory single-file benchmark figures from the DuckDB database."""

from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures", "single_file")

VARIANT_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "freesasa",
    "rustsasa",
]
ZSASA_VARIANTS = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
]
COMPARATOR_VARIANTS = ["freesasa", "rustsasa"]
COLORS = {
    "zsasa_f64": "#f39c12",
    "zsasa_f32": "#f6c85f",
    "zsasa_bitmask_f64": "#e67e22",
    "zsasa_bitmask_f32": "#ffb347",
    "freesasa": "#3498db",
    "rustsasa": "#e74c3c",
}
DISPLAY_NAMES = {
    "zsasa_f64": "zsasa f64",
    "zsasa_f32": "zsasa f32",
    "zsasa_bitmask_f64": "zsasa bitmask f64",
    "zsasa_bitmask_f32": "zsasa bitmask f32",
    "freesasa": "FreeSASA",
    "rustsasa": "RustSASA",
}
MARKERS = {
    "zsasa_f64": "o",
    "zsasa_f32": "o",
    "zsasa_bitmask_f64": "o",
    "zsasa_bitmask_f32": "o",
    "freesasa": "^",
    "rustsasa": "s",
}


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
    for ext in ("png", "svg"):
        path = out_dir.joinpath(ext, f"{name}.{ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        written.append(path)
    plt.close(fig)
    return written


def parse_note(notes: str | None, key: str) -> str | None:
    if not notes:
        return None
    match = re.search(rf"{re.escape(key)}=([^;]+)", notes)
    return match.group(1).strip() if match else None


def single_variant_name(run: dict[str, Any]) -> str:
    tool_id = str(run.get("tool_id") or "")
    precision = str(run.get("precision") or "")
    mode = str(run.get("mode") or "")
    if tool_id == "zsasa":
        prefix = "zsasa_bitmask" if mode == "bitmask" else "zsasa"
        return f"{prefix}_{precision}"
    if tool_id == "freesasa":
        return "freesasa"
    if tool_id == "rustsasa":
        return "rustsasa"
    return f"{tool_id}_{precision}" if precision else tool_id


def display_name(variant: str) -> str:
    return DISPLAY_NAMES.get(variant, variant)


def color_for(variant: str) -> str:
    return COLORS.get(variant, "#7f8c8d")


def marker_for(variant: str) -> str:
    return MARKERS.get(variant, "o")


def variant_sort_key(variant: str) -> tuple[int, str]:
    try:
        return (VARIANT_ORDER.index(variant), variant)
    except ValueError:
        return (len(VARIANT_ORDER), variant)


def structure_sort_key(
    row_or_id: dict[str, Any] | str,
    rows: list[dict[str, Any]] | None = None,
) -> tuple[int, str]:
    if isinstance(row_or_id, dict):
        return (int(row_or_id.get("n_atoms") or 0), str(row_or_id.get("structure_id") or ""))
    if rows is None:
        return (0, row_or_id)
    atoms = next((int(row["n_atoms"]) for row in rows if row["structure_id"] == row_or_id), 0)
    return (atoms, row_or_id)


def structure_label(row: dict[str, Any]) -> str:
    chain_label = "chain" if row["expected_chains"] == 1 else "chains"
    return (
        f"{row['structure_id']}\n"
        f"{row['n_atoms']:,} atoms, {row['expected_chains']} {chain_label}"
    )


def load_single_rows(db_path: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        run_cols = [
            "run_id",
            "tool_id",
            "algorithm",
            "precision",
            "mode",
            "threads",
            "n_points",
            "notes",
        ]
        run_rows = con.execute(
            """
            SELECT run_id, tool_id, algorithm, precision, mode, threads, n_points, notes
            FROM benchmark_runs
            WHERE benchmark_kind = 'single_file'
            ORDER BY notes, tool_id, mode, precision, threads
            """
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for raw in run_rows:
            run = dict(zip(run_cols, raw, strict=True))
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
            rss_bytes = float(stats.get(("peak_rss", "mean")) or 0.0)
            rss_stddev_bytes = float(stats.get(("peak_rss", "stddev")) or 0.0)
            notes = str(run.get("notes") or "")
            structure_id = parse_note(notes, "structure_id") or "unknown"
            n_atoms = int(parse_note(notes, "n_atoms") or 0)
            rows.append(
                {
                    "run_id": run["run_id"],
                    "variant": single_variant_name(run),
                    "threads": int(run["threads"]),
                    "n_points": int(run["n_points"] or 0),
                    "structure_id": structure_id,
                    "role": parse_note(notes, "role") or "",
                    "n_atoms": n_atoms,
                    "expected_chains": int(parse_note(notes, "expected_chains") or 0),
                    "mean_s": mean_s,
                    "stddev_s": stddev_s,
                    "throughput": 1.0 / mean_s if mean_s > 0 else 0.0,
                    "atoms_per_sec": n_atoms / mean_s if mean_s > 0 else 0.0,
                    "rss_mib": rss_bytes / (1024 * 1024),
                    "rss_stddev_mib": rss_stddev_bytes / (1024 * 1024),
                    "parse_ms": float(stats.get(("parse_time", "single")) or 0.0),
                    "sasa_ms": float(stats.get(("sasa_time", "single")) or 0.0),
                    "total_ms": float(stats.get(("total_time", "single")) or 0.0),
                    "user_time_s": float(stats.get(("user_time", "mean")) or 0.0),
                    "system_time_s": float(stats.get(("system_time", "mean")) or 0.0),
                }
            )
        return sorted(
            rows,
            key=lambda row: (
                structure_sort_key(row),
                variant_sort_key(row["variant"]),
                row["threads"],
            ),
        )
    finally:
        con.close()


def t10_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["threads"] == 10]


def group_by_structure(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["structure_id"]].append(row)
    return {
        key: sorted(value, key=lambda row: (variant_sort_key(row["variant"]), row["threads"]))
        for key, value in grouped.items()
    }


def legend_handles(variants: list[str]) -> list[plt.Line2D]:
    return [
        plt.Line2D(
            [0],
            [0],
            marker=marker_for(variant),
            color="w",
            markerfacecolor=color_for(variant),
            markeredgecolor="#333333",
            markeredgewidth=0.4,
            label=display_name(variant),
            markersize=7,
        )
        for variant in variants
    ]


def plot_metric_vs_atoms(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    metric: str,
    ylabel: str,
    title: str,
    name: str,
    yscale: str = "log",
) -> list[Path]:
    selected = t10_rows(rows)
    variants = sorted({row["variant"] for row in selected}, key=variant_sort_key)
    fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
    for variant in variants:
        items = sorted(
            [row for row in selected if row["variant"] == variant],
            key=structure_sort_key,
        )
        ax.plot(
            [row["n_atoms"] for row in items],
            [row[metric] for row in items],
            marker=marker_for(variant),
            linewidth=1.4,
            markersize=5.5,
            label=display_name(variant),
            color=color_for(variant),
        )
    ax.set_xscale("log")
    ax.set_yscale(yscale)
    ax.set_title(title)
    ax.set_xlabel("atoms")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", ncol=2)
    return save_figure(fig, out_dir, name)


def plot_t10_bar_grid(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    metric: str,
    ylabel: str,
    title: str,
    name: str,
    yscale: str = "log",
    lower_is_better: bool = True,
) -> list[Path]:
    grouped = group_by_structure(t10_rows(rows))
    structures = sorted(grouped, key=lambda sid: structure_sort_key(sid, rows))
    ncols = 4
    nrows = math.ceil(len(structures) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.7 * ncols, 4.2 * nrows), layout="constrained")
    fig.suptitle(title)
    flat_axes = list(np.ravel(axes))
    for ax, structure_id in zip(flat_axes, structures, strict=False):
        items = sorted(
            grouped[structure_id],
            key=lambda row: row[metric],
            reverse=not lower_is_better,
        )
        ax.bar(
            [display_name(row["variant"]) for row in items],
            [row[metric] for row in items],
            color=[color_for(row["variant"]) for row in items],
        )
        ax.set_title(structure_label(items[0]))
        ax.set_ylabel(ylabel)
        if yscale != "linear":
            ax.set_yscale(yscale)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    for ax in flat_axes[len(structures) :]:
        ax.set_visible(False)
    return save_figure(fig, out_dir, name)


def plot_comparator_ratio_grid(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    metric: str,
    title: str,
    ylabel: str,
    name: str,
) -> list[Path]:
    grouped = group_by_structure(t10_rows(rows))
    structures = sorted(grouped, key=lambda sid: structure_sort_key(sid, rows))
    ncols = 4
    nrows = math.ceil(len(structures) / ncols)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(4.9 * ncols, 4.1 * nrows),
        layout="constrained",
    )
    fig.suptitle(title)
    flat_axes = list(np.ravel(axes))
    comparator_styles = {
        "freesasa": {
            "color": color_for("freesasa"),
            "edgecolor": "#1f5f8f",
            "hatch": "",
        },
        "rustsasa": {
            "color": color_for("rustsasa"),
            "edgecolor": "#992d22",
            "hatch": "///",
        },
    }
    for ax, structure_id in zip(flat_axes, structures, strict=False):
        items = grouped[structure_id]
        by_variant = {row["variant"]: row for row in items}
        zsasa_items = [
            by_variant[variant]
            for variant in ZSASA_VARIANTS
            if variant in by_variant
        ]
        x = np.arange(len(zsasa_items))
        width = 0.36
        all_values: list[float] = []
        for index, comparator in enumerate(COMPARATOR_VARIANTS):
            baseline = by_variant.get(comparator)
            if baseline is None:
                continue
            values = [
                baseline[metric] / row[metric]
                if row[metric] > 0
                else np.nan
                for row in zsasa_items
            ]
            all_values.extend(value for value in values if value > 0)
            positions = x + (index - 0.5) * width
            style = comparator_styles[comparator]
            ax.bar(
                positions,
                values,
                width=width,
                linewidth=1.2,
                label=f"vs {display_name(comparator)}",
                alpha=0.75,
                **style,
            )
        freesasa = by_variant.get("freesasa")
        rustsasa = by_variant.get("rustsasa")
        if freesasa is not None and rustsasa is not None and rustsasa[metric] > 0:
            rust_vs_freesasa = freesasa[metric] / rustsasa[metric]
            all_values.append(rust_vs_freesasa)
            ax.axhline(
                rust_vs_freesasa,
                color="#9b59b6",
                linestyle=":",
                linewidth=2.0,
                alpha=0.95,
            )
        ax.axhline(1.0, color="0.35", linestyle="--", linewidth=0.8, alpha=0.45)
        ax.set_title(structure_label(items[0]))
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels([display_name(row["variant"]) for row in zsasa_items])
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        if all_values and max(all_values) / min(all_values) > 20:
            ax.set_yscale("log")
    for ax in flat_axes[len(structures) :]:
        ax.set_visible(False)
    handles = [
        Patch(
            facecolor=color_for("freesasa"),
            edgecolor="#1f5f8f",
            linewidth=1.2,
            label="vs FreeSASA",
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
        plt.Line2D(
            [0],
            [0],
            color="#9b59b6",
            linestyle=":",
            linewidth=2.0,
            label="RustSASA vs FreeSASA",
        ),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=3)
    return save_figure(fig, out_dir, name)


def plot_parse_sasa_breakdown(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    grouped = group_by_structure(t10_rows(rows))
    structures = sorted(grouped, key=lambda sid: structure_sort_key(sid, rows))
    ncols = 4
    nrows = math.ceil(len(structures) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.7 * ncols, 4.3 * nrows), layout="constrained")
    fig.suptitle("Single-file parse + SASA timing at 10 threads")
    flat_axes = list(np.ravel(axes))
    for ax, structure_id in zip(flat_axes, structures, strict=False):
        items = sorted(grouped[structure_id], key=lambda row: variant_sort_key(row["variant"]))
        labels = [display_name(row["variant"]) for row in items]
        parse = [row["parse_ms"] for row in items]
        sasa = [row["sasa_ms"] for row in items]
        ax.bar(labels, parse, color="#95a5a6", label="parse")
        ax.bar(
            labels,
            sasa,
            bottom=parse,
            color=[color_for(row["variant"]) for row in items],
            label="SASA",
        )
        ax.set_title(structure_label(items[0]))
        ax.set_ylabel("time (ms)")
        if max([p + s for p, s in zip(parse, sasa, strict=True)] or [0]) > 1000:
            ax.set_yscale("log")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    for ax in flat_axes[len(structures) :]:
        ax.set_visible(False)
    handles = [
        plt.Line2D([0], [0], color="#95a5a6", linewidth=8, label="parse"),
        plt.Line2D([0], [0], color="#f39c12", linewidth=8, label="SASA"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=2)
    return save_figure(fig, out_dir, "single_t10_parse_sasa_breakdown_grid")


def plot_thread_runtime_grid(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    grouped = group_by_structure(rows)
    structures = sorted(grouped, key=lambda sid: structure_sort_key(sid, rows))
    variants = sorted({row["variant"] for row in rows}, key=variant_sort_key)
    ncols = 4
    nrows = math.ceil(len(structures) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.7 * ncols, 4.0 * nrows), layout="constrained")
    fig.suptitle("Single-file runtime vs threads")
    flat_axes = list(np.ravel(axes))
    for ax, structure_id in zip(flat_axes, structures, strict=False):
        items = grouped[structure_id]
        for variant in variants:
            variant_items = sorted(
                [row for row in items if row["variant"] == variant],
                key=lambda r: r["threads"],
            )
            if not variant_items:
                continue
            ax.plot(
                [row["threads"] for row in variant_items],
                [row["mean_s"] for row in variant_items],
                marker=marker_for(variant),
                linewidth=1.2,
                color=color_for(variant),
                label=display_name(variant),
            )
        ax.set_title(structure_label(items[0]))
        ax.set_xlabel("threads")
        ax.set_ylabel("runtime (s)")
        ax.set_yscale("log")
        ax.set_xticks(sorted({row["threads"] for row in items}))
    for ax in flat_axes[len(structures) :]:
        ax.set_visible(False)
    fig.legend(handles=legend_handles(variants), loc="outside lower center", ncol=3)
    return save_figure(fig, out_dir, "single_runtime_vs_threads_grid")


def plot_cpu_utilization_grid(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    for row in rows:
        row["cpu_utilization"] = (row["user_time_s"] + row["system_time_s"]) / row["mean_s"]
    return plot_t10_bar_grid(
        rows,
        out_dir,
        metric="cpu_utilization",
        ylabel="(user + system) / wall time",
        title="Single-file CPU utilization proxy at 10 threads",
        name="single_t10_cpu_utilization_grid",
        yscale="linear",
        lower_is_better=False,
    )


def write_index(out_dir: Path, outputs: list[Path]) -> Path:
    index = out_dir.joinpath("index.md")
    pngs = sorted(path for path in outputs if path.suffix == ".png")
    lines = [
        "# Single-file performance figures",
        "",
        f"Generated {len(pngs)} PNG figures.",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_style()
    rows = load_single_rows(args.db)
    outputs: list[Path] = []
    outputs.extend(
        plot_metric_vs_atoms(
            rows,
            args.out_dir,
            metric="mean_s",
            ylabel="runtime (s), lower is better",
            title="Single-file runtime vs atoms at 10 threads",
            name="single_t10_runtime_vs_atoms",
        )
    )
    outputs.extend(
        plot_metric_vs_atoms(
            rows,
            args.out_dir,
            metric="rss_mib",
            ylabel="peak RSS (MiB), lower is better",
            title="Single-file peak RSS vs atoms at 10 threads",
            name="single_t10_peak_rss_vs_atoms",
        )
    )
    outputs.extend(
        plot_metric_vs_atoms(
            rows,
            args.out_dir,
            metric="atoms_per_sec",
            ylabel="atoms / sec, higher is better",
            title="Single-file atoms/sec vs atoms at 10 threads",
            name="single_t10_atoms_per_sec_vs_atoms",
        )
    )
    outputs.extend(
        plot_t10_bar_grid(
            rows,
            args.out_dir,
            metric="mean_s",
            ylabel="runtime (s), lower is better",
            title="Single-file runtime at 10 threads",
            name="single_t10_runtime_bar_grid",
        )
    )
    outputs.extend(
        plot_t10_bar_grid(
            rows,
            args.out_dir,
            metric="rss_mib",
            ylabel="peak RSS (MiB), lower is better",
            title="Single-file peak RSS at 10 threads",
            name="single_t10_peak_rss_bar_grid",
        )
    )
    outputs.extend(
        plot_comparator_ratio_grid(
            rows,
            args.out_dir,
            metric="mean_s",
            ylabel="runtime speedup, higher is better",
            title="Single-file runtime speedup: zsasa vs FreeSASA/RustSASA at 10 threads",
            name="single_t10_runtime_speedup_vs_comparators_grid",
        )
    )
    outputs.extend(
        plot_comparator_ratio_grid(
            rows,
            args.out_dir,
            metric="rss_mib",
            ylabel="RSS reduction, higher is better",
            title="Single-file RSS reduction: zsasa vs FreeSASA/RustSASA at 10 threads",
            name="single_t10_rss_reduction_vs_comparators_grid",
        )
    )
    outputs.extend(plot_parse_sasa_breakdown(rows, args.out_dir))
    outputs.extend(plot_thread_runtime_grid(rows, args.out_dir))
    outputs.extend(plot_cpu_utilization_grid(rows, args.out_dir))
    index = write_index(args.out_dir, outputs)
    png_count = sum(1 for path in outputs if path.suffix == ".png")
    print(f"wrote {png_count} PNG figures under {args.out_dir}")
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
