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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures", "md")

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
    for ext in ("png", "svg"):
        path = out_dir.joinpath(ext, f"{name}.{ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        written.append(path)
    plt.close(fig)
    return written


def load_md_rows(db_path: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        columns = [
            "run_id",
            "dataset_id",
            "tool_id",
            "precision",
            "mode",
            "threads",
            "n_points",
            "frame_count",
            "notes",
        ]
        run_rows = con.execute(
            """
            SELECT r.run_id, r.dataset_id, r.tool_id, r.precision, r.mode, r.threads,
                   r.n_points, d.expected_count, d.notes
            FROM benchmark_runs r
            JOIN datasets d USING (dataset_id)
            WHERE r.benchmark_kind = 'trajectory'
            ORDER BY r.dataset_id, r.tool_id, r.mode, r.precision
            """
        ).fetchall()
        rows: list[dict[str, Any]] = []
        for raw in run_rows:
            run = dict(zip(columns, raw, strict=True))
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
                    "n_points": run["n_points"],
                    "mean_s": mean_s,
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


def write_index(out_dir: Path, outputs: list[Path]) -> Path:
    index = out_dir.joinpath("index.md")
    pngs = sorted(path for path in outputs if path.suffix == ".png")
    lines = ["# MD performance figures", "", f"Generated {len(pngs)} PNG figures.", ""]
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
    rows = load_md_rows(args.db)
    outputs: list[Path] = []
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
    index = write_index(args.out_dir, outputs)
    png_count = sum(1 for path in outputs if path.suffix == ".png")
    print(f"wrote {png_count} PNG figures under {args.out_dir}")
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
