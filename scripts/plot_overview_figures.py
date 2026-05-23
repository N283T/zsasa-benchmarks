#!/usr/bin/env python3
"""Generate overview speedup figures and a top-level figure index."""

# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.plot_batch_figures import (
    ECOLI_DATASET,
    HUMAN_DATASET,
    color_for as batch_color_for,
    display_name as batch_display_name,
    load_batch_rows,
    setup_style as setup_batch_style,
    t10_rows,
    variant_sort_key as batch_variant_sort_key,
)
from scripts.plot_md_figures import (
    color_for as md_color_for,
    dataset_label as md_dataset_label,
    dataset_sort_key as md_dataset_sort_key,
    display_name as md_display_name,
    load_md_rows,
    marker_for as md_marker_for,
    variant_sort_key as md_variant_sort_key,
)

DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_FIGURES_DIR = ROOT.joinpath("results", "figures")

SECTION_LABELS = {
    "validation": "Validation",
    "batch_ecoli": "E. coli batch",
    "batch_human": "Human batch",
    "batch_t10_comparison": "Batch t10 comparison",
    "md": "MD / trajectory",
    "overview": "Overview summaries",
}
SECTION_ORDER = [
    "overview",
    "validation",
    "batch_ecoli",
    "batch_human",
    "batch_t10_comparison",
    "md",
]
REPRESENTATIVE_IMAGES = [
    ("Validation static scatter", "validation/png/static_sr_scatter_grid.png"),
    ("Validation MD scatter", "validation/png/md_scatter_grid.png"),
    ("E. coli throughput", "batch_ecoli/png/ecoli_throughput_vs_threads.png"),
    ("Human t10 throughput", "batch_human/png/human_t10_throughput_bar.png"),
    ("Batch t10 size comparison", "batch_t10_comparison/png/t10_ms_per_structure_ecoli_human.png"),
    ("MD throughput vs RSS", "md/png/md_throughput_vs_peak_rss_logx_grid.png"),
    ("Batch speedup overview", "overview/png/batch_t10_speedup_vs_freesasa.png"),
    ("MD speedup overview", "overview/png/md_speedup_vs_mdtraj_grid.png"),
]


@dataclass(frozen=True)
class FigureSection:
    name: str
    png_count: int
    index_path: Path | None


def section_sort_key(section: FigureSection) -> tuple[int, str]:
    try:
        return (SECTION_ORDER.index(section.name), section.name)
    except ValueError:
        return (len(SECTION_ORDER), section.name)


def figure_sections(figures_dir: Path) -> list[FigureSection]:
    sections: list[FigureSection] = []
    for child in figures_dir.iterdir() if figures_dir.exists() else []:
        if not child.is_dir():
            continue
        png_dir = child.joinpath("png")
        png_count = sum(1 for _path in png_dir.rglob("*.png")) if png_dir.exists() else 0
        if png_count == 0:
            continue
        index_path = child.joinpath("index.md")
        sections.append(
            FigureSection(
                name=child.name,
                png_count=png_count,
                index_path=index_path if index_path.exists() else None,
            )
        )
    return sorted(sections, key=section_sort_key)


def format_markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def speedup_against_baseline(
    rows: list[dict[str, Any]],
    *,
    group_key: str,
    variant_key: str,
    value_key: str,
    baseline_variant: str,
) -> list[dict[str, Any]]:
    baseline_by_group = {
        row[group_key]: float(row[value_key])
        for row in rows
        if row[variant_key] == baseline_variant and float(row[value_key]) > 0.0
    }
    output: list[dict[str, Any]] = []
    for row in rows:
        if row[variant_key] == baseline_variant:
            continue
        baseline = baseline_by_group.get(row[group_key])
        if not baseline:
            continue
        output.append(
            {
                group_key: row[group_key],
                variant_key: row[variant_key],
                "baseline": baseline_variant,
                "speedup": float(row[value_key]) / baseline,
            }
        )
    return output


def save_figure(fig: plt.Figure, out_dir: Path, name: str) -> list[Path]:
    written: list[Path] = []
    for ext in ("png", "svg"):
        path = out_dir.joinpath(ext, f"{name}.{ext}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        written.append(path)
    plt.close(fig)
    return written


def database_summary_rows(db_path: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT benchmark_kind, COUNT(*) AS runs, COUNT(DISTINCT dataset_id) AS datasets
            FROM benchmark_runs
            GROUP BY benchmark_kind
            ORDER BY benchmark_kind
            """
        ).fetchall()
        return [
            {"benchmark_kind": kind, "runs": int(runs), "datasets": int(datasets)}
            for kind, runs, datasets in rows
        ]
    finally:
        con.close()


def metric_summary_rows(db_path: Path) -> list[dict[str, Any]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT metric, COUNT(*) AS rows, COUNT(DISTINCT run_id) AS runs
            FROM performance_results
            GROUP BY metric
            ORDER BY metric
            """
        ).fetchall()
        return [
            {"metric": metric, "rows": int(rows_), "runs": int(runs)}
            for metric, rows_, runs in rows
        ]
    finally:
        con.close()


def best_batch_t10_rows(db_path: Path) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for dataset_name, dataset_id in [("E. coli", ECOLI_DATASET), ("Human", HUMAN_DATASET)]:
        rows = t10_rows(load_batch_rows(db_path, dataset_id))
        if not rows:
            continue
        best_throughput = max(rows, key=lambda row: row["throughput"])
        best_memory = min(
            [row for row in rows if row.get("memory_mean_mb", 0.0) > 0.0],
            key=lambda row: row["memory_mean_mb"],
            default=None,
        )
        summary.append(
            {
                "dataset": dataset_name,
                "best_throughput": batch_display_name(best_throughput["variant"]),
                "structures_per_sec": f"{best_throughput['throughput']:.1f}",
                "lowest_rss": batch_display_name(best_memory["variant"]) if best_memory else "n/a",
                "rss_mib": f"{best_memory['memory_mean_mb']:.1f}" if best_memory else "n/a",
            }
        )
    return summary


def best_md_rows(db_path: Path) -> list[dict[str, Any]]:
    rows = load_md_rows(db_path)
    summary: list[dict[str, Any]] = []
    for dataset_id in sorted({row["dataset_id"] for row in rows}, key=md_dataset_sort_key):
        dataset_rows = [row for row in rows if row["dataset_id"] == dataset_id]
        best_throughput = max(dataset_rows, key=lambda row: row["fps"])
        lowest_rss = min(
            [row for row in dataset_rows if row.get("rss_mib", 0.0) > 0.0],
            key=lambda row: row["rss_mib"],
        )
        summary.append(
            {
                "dataset": md_dataset_label(dataset_id),
                "best_throughput": md_display_name(best_throughput["variant"]),
                "frames_per_sec": f"{best_throughput['fps']:.1f}",
                "lowest_rss": md_display_name(lowest_rss["variant"]),
                "rss_mib": f"{lowest_rss['rss_mib']:.1f}",
            }
        )
    return summary


def batch_speedup_rows(db_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset_name, dataset_id in [("E. coli", ECOLI_DATASET), ("Human", HUMAN_DATASET)]:
        for row in t10_rows(load_batch_rows(db_path, dataset_id)):
            rows.append(
                {
                    "dataset": dataset_name,
                    "variant": row["variant"],
                    "throughput": row["throughput"],
                }
            )
    return speedup_against_baseline(
        rows,
        group_key="dataset",
        variant_key="variant",
        value_key="throughput",
        baseline_variant="freesasa_batch",
    )


def plot_batch_speedup(rows: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    datasets = ["E. coli", "Human"]
    variants = sorted({row["variant"] for row in rows}, key=batch_variant_sort_key)
    x = np.arange(len(variants))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.5, 5.2), layout="constrained")
    for dataset_idx, dataset in enumerate(datasets):
        by_variant = {row["variant"]: row for row in rows if row["dataset"] == dataset}
        offset = (dataset_idx - 0.5) * width
        ax.bar(
            x + offset,
            [by_variant.get(variant, {"speedup": np.nan})["speedup"] for variant in variants],
            width=width,
            label=dataset,
            color=[batch_color_for(variant) for variant in variants],
            alpha=0.95 if dataset_idx == 0 else 0.62,
        )
    ax.axhline(1.0, linestyle="--", color="0.35", alpha=0.45)
    ax.set_title("Batch throughput speedup at 10 threads vs FreeSASA batch")
    ax.set_ylabel("speedup (higher is better)")
    ax.set_xticks(x, [batch_display_name(variant) for variant in variants], rotation=35, ha="right")
    ax.legend(loc="best")
    return save_figure(fig, out_dir, "batch_t10_speedup_vs_freesasa")


def md_speedup_rows(db_path: Path, baseline_variant: str) -> list[dict[str, Any]]:
    rows = [
        {"dataset": row["dataset_id"], "variant": row["variant"], "fps": row["fps"]}
        for row in load_md_rows(db_path)
    ]
    return speedup_against_baseline(
        rows,
        group_key="dataset",
        variant_key="variant",
        value_key="fps",
        baseline_variant=baseline_variant,
    )


def plot_md_speedup_grid(
    rows: list[dict[str, Any]], out_dir: Path, baseline_variant: str
) -> list[Path]:
    datasets = sorted({row["dataset"] for row in rows}, key=md_dataset_sort_key)
    variants = sorted({row["variant"] for row in rows}, key=md_variant_sort_key)
    fig, axes = plt.subplots(
        1,
        len(datasets),
        figsize=(6.2 * len(datasets), 5.2),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle(f"MD throughput speedup vs {md_display_name(baseline_variant)}")
    for ax, dataset in zip(axes[0], datasets, strict=True):
        by_variant = {row["variant"]: row for row in rows if row["dataset"] == dataset}
        xs = np.arange(len(variants))
        values = [by_variant.get(variant, {"speedup": np.nan})["speedup"] for variant in variants]
        ax.bar(
            xs,
            values,
            color=[md_color_for(variant) for variant in variants],
            edgecolor="0.25",
            linewidth=0.3,
        )
        for idx, variant in enumerate(variants):
            ax.scatter(
                idx,
                values[idx],
                marker=md_marker_for(variant),
                s=34,
                color=md_color_for(variant),
                edgecolor="0.25",
                linewidth=0.4,
                zorder=3,
            )
        ax.axhline(1.0, linestyle="--", color="0.35", alpha=0.45)
        ax.set_title(md_dataset_label(dataset))
        ax.set_ylabel("speedup (higher is better)")
        ax.set_xticks(
            xs, [md_display_name(variant) for variant in variants], rotation=45, ha="right"
        )
    suffix = baseline_variant.replace("_", "-")
    return save_figure(fig, out_dir, f"md_speedup_vs_{suffix}_grid")


def write_overview_index(out_dir: Path, outputs: list[Path]) -> Path:
    pngs = sorted(path for path in outputs if path.suffix == ".png")
    lines = ["# Overview summary figures", "", f"Generated {len(pngs)} PNG figures.", ""]
    for path in pngs:
        lines.append(f"- `{path.relative_to(out_dir)}`")
    index = out_dir.joinpath("index.md")
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def relative_link(from_dir: Path, target: Path) -> str:
    return target.relative_to(from_dir).as_posix()


def write_top_index(figures_dir: Path, db_path: Path) -> Path:
    sections = figure_sections(figures_dir)
    section_rows = [
        {
            "section": (
                f"[{SECTION_LABELS.get(section.name, section.name)}]"
                f"({relative_link(figures_dir, section.index_path)})"
            )
            if section.index_path
            else SECTION_LABELS.get(section.name, section.name),
            "png_figures": section.png_count,
        }
        for section in sections
    ]
    lines = [
        "# Benchmark figure index",
        "",
        "Exploratory figures generated from `results/benchmark.duckdb`.",
        "",
        "## Sections",
        "",
        format_markdown_table(["section", "png_figures"], section_rows),
        "",
        "## Database contents",
        "",
        format_markdown_table(
            ["benchmark_kind", "runs", "datasets"], database_summary_rows(db_path)
        ),
        "",
        "## Performance metrics in DB",
        "",
        format_markdown_table(["metric", "rows", "runs"], metric_summary_rows(db_path)),
        "",
        "## Quick winners",
        "",
        "### Batch at 10 threads",
        "",
        format_markdown_table(
            ["dataset", "best_throughput", "structures_per_sec", "lowest_rss", "rss_mib"],
            best_batch_t10_rows(db_path),
        ),
        "",
        "### MD / trajectory",
        "",
        format_markdown_table(
            ["dataset", "best_throughput", "frames_per_sec", "lowest_rss", "rss_mib"],
            best_md_rows(db_path),
        ),
        "",
        "## Representative figures",
        "",
    ]
    for label, rel_path in REPRESENTATIVE_IMAGES:
        path = figures_dir.joinpath(rel_path)
        if not path.exists():
            continue
        lines.extend([f"### {label}", "", f"![{label}]({rel_path})", ""])
    index = figures_dir.joinpath("index.md")
    index.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_batch_style()
    overview_dir = args.figures_dir.joinpath("overview")
    outputs: list[Path] = []
    outputs.extend(plot_batch_speedup(batch_speedup_rows(args.db), overview_dir))
    outputs.extend(plot_md_speedup_grid(md_speedup_rows(args.db, "mdtraj"), overview_dir, "mdtraj"))
    outputs.extend(
        plot_md_speedup_grid(md_speedup_rows(args.db, "mdsasa_bolt"), overview_dir, "mdsasa_bolt")
    )
    overview_index = write_overview_index(overview_dir, outputs)
    top_index = write_top_index(args.figures_dir, args.db)
    png_count = sum(1 for path in outputs if path.suffix == ".png")
    print(f"wrote {png_count} PNG overview figures under {overview_dir}")
    print(f"wrote {overview_index}")
    print(f"wrote {top_index}")


if __name__ == "__main__":
    main()
