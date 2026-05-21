#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "matplotlib>=3.8",
# ]
# ///
"""Generate draft manuscript-style benchmark figures.

The script reads existing CSV/JSON outputs only. It does not run benchmarks.
By default, figures are written as PNG for quick review and SVG for editing.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_ROOT = Path("/Users/nagaet/freesasa-zig/benchmarks/results")
DEFAULT_OUTPUT = ROOT.joinpath("results", "figures")
DEFAULT_EXPORTS = ROOT.joinpath("results", "exports")
DEFAULT_VALIDATION = ROOT.joinpath("results", "validation", "zsasa_v0_6_0_ecoli")
DEFAULT_VALIDATION_MD = ROOT.joinpath(
    "results", "validation_md", "zsasa_v0_6_0_5wvo_C_validation"
)
DEFAULT_BATCH_ECOLI = ROOT.joinpath("results", "batch", "zsasa_v0_6_0_ecoli_scaling")
DEFAULT_BATCH_HUMAN = ROOT.joinpath("results", "batch", "zsasa_v0_6_0_human_t10")
DEFAULT_MD = ROOT.joinpath("results", "md", "zsasa_v0_6_0_refresh")
DEFAULT_HIST_BATCH = HISTORICAL_ROOT.joinpath("batch", "128")
DEFAULT_HIST_MD = HISTORICAL_ROOT.joinpath("md", "100")

COLORS = {
    "zsasa": "#f39c12",
    "zsasa_std": "#f39c12",
    "zsasa_bitmask": "#d35400",
    "freesasa": "#3498db",
    "rustsasa": "#e74c3c",
    "lahuta": "#8e44ad",
    "lahuta_bitmask": "#c0399f",
    "mdtraj": "#2ca02c",
    "mdsasa_bolt": "#795548",
    "zsasa_mdtraj": "#9467bd",
    "zsasa_mdanalysis": "#8c564b",
}

LABELS = {
    "zsasa_f64": "zsasa f64",
    "zsasa_f32": "zsasa f32",
    "zsasa_f64_bitmask": "zsasa bitmask f64",
    "zsasa_f32_bitmask": "zsasa bitmask f32",
    "zsasa_bitmask_f32": "zsasa bitmask f32",
    "freesasa": "FreeSASA",
    "rustsasa": "RustSASA",
    "lahuta": "Lahuta",
    "lahuta_bitmask": "Lahuta bitmask",
    "mdtraj": "MDTraj",
    "mdsasa_bolt": "mdsasa-bolt",
    "zsasa_mdtraj": "zsasa.mdtraj",
    "zsasa_mdanalysis": "zsasa.MDAnalysis",
    "zsasa_cli_f64": "CLI f64",
    "zsasa_cli_bitmask_f64": "CLI bitmask f64",
}

BATCH_TOOLS = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_f64_bitmask",
    "zsasa_f32_bitmask",
    "lahuta_bitmask",
    "rustsasa",
    "lahuta",
    "freesasa",
]
BATCH_TOOL_COLORS = {
    "zsasa_f64": COLORS["zsasa_std"],
    "zsasa_f32": "#f8c471",
    "zsasa_f64_bitmask": COLORS["zsasa_bitmask"],
    "zsasa_f32_bitmask": "#e67e22",
    "lahuta_bitmask": COLORS["lahuta_bitmask"],
    "rustsasa": COLORS["rustsasa"],
    "lahuta": COLORS["lahuta"],
    "freesasa": COLORS["freesasa"],
}
SINGLE_FILE_TOOLS = [
    ("zig_f64", "zsasa f64", COLORS["zsasa_std"]),
    ("zig_f64_bitmask", "zsasa bitmask f64", COLORS["zsasa_bitmask"]),
    ("historical_freesasa", "FreeSASA", COLORS["freesasa"]),
    ("historical_rustsasa", "RustSASA", COLORS["rustsasa"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--formats", default="png,svg", help="comma-separated formats")
    parser.add_argument("--exports-dir", type=Path, default=DEFAULT_EXPORTS)
    parser.add_argument("--validation-dir", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--validation-md-dir", type=Path, default=DEFAULT_VALIDATION_MD)
    parser.add_argument("--batch-ecoli-dir", type=Path, default=DEFAULT_BATCH_ECOLI)
    parser.add_argument("--batch-human-dir", type=Path, default=DEFAULT_BATCH_HUMAN)
    parser.add_argument("--md-dir", type=Path, default=DEFAULT_MD)
    parser.add_argument("--historical-batch-dir", type=Path, default=DEFAULT_HIST_BATCH)
    parser.add_argument("--historical-md-dir", type=Path, default=DEFAULT_HIST_MD)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def to_float(value: str | float | int | None) -> float:
    if value is None or value == "":
        return math.nan
    return float(value)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 300,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "svg.fonttype": "none",
        }
    )


def figure_path(output_dir: Path, name: str, fmt: str) -> Path:
    return output_dir.joinpath(fmt, f"{name}.{fmt}")


def k_formatter(value: float, _pos: object) -> str:
    if abs(value) >= 1000:
        return f"{value / 1000:g}k"
    return f"{value:g}"


def apply_k_axes(ax: plt.Axes) -> None:
    formatter = FuncFormatter(k_formatter)
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)


def save_figure(fig: plt.Figure, output_dir: Path, name: str, formats: list[str]) -> None:
    for fmt in formats:
        path = figure_path(output_dir, name, fmt)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def result_mean(path: Path) -> float:
    data = read_json(path)
    if data is None:
        return math.nan
    return float(data["results"][0]["mean"])


def result_stddev(path: Path) -> float:
    data = read_json(path)
    if data is None:
        return math.nan
    return float(data["results"][0].get("stddev", 0.0))


def result_memory_mib(path: Path) -> float:
    data = read_json(path)
    if data is None:
        return math.nan
    values = data["results"][0].get("memory_usage_byte") or []
    return max(values) / (1024 * 1024) if values else math.nan


def result_n_files(result_dir: Path) -> int:
    data = read_json(result_dir.joinpath("config.json"))
    if data is None:
        raise FileNotFoundError(result_dir.joinpath("config.json"))
    return int(data["parameters"]["n_files"])


def correlation_r2(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return math.nan
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    if vx == 0 or vy == 0:
        return math.nan
    return (cov / math.sqrt(vx * vy)) ** 2


def mean_error_percent(ref: list[float], obs: list[float]) -> float:
    vals = [abs(o - r) / r * 100.0 for r, o in zip(ref, obs, strict=True) if r != 0]
    return sum(vals) / len(vals)


def plot_agreement_panel(
    ax: plt.Axes,
    rows: list[dict[str, str]],
    column: str,
    title: str,
    color: str,
    reference_col: str = "freesasa",
    log_scale: bool = True,
) -> None:
    ref = [to_float(row[reference_col]) for row in rows]
    obs = [to_float(row[column]) for row in rows]
    pairs = [(r, o) for r, o in zip(ref, obs, strict=True) if not math.isnan(r + o)]
    ref = [p[0] for p in pairs]
    obs = [p[1] for p in pairs]
    ax.scatter(ref, obs, s=8, alpha=0.28, color=color, edgecolors="none")
    lo = min(min(ref), min(obs))
    hi = max(max(ref), max(obs))
    ax.plot([lo, hi], [lo, hi], color="#555555", linestyle="--", linewidth=1)
    ax.set_title(title)
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
    else:
        margin = (hi - lo) * 0.05
        ax.set_xlim(lo - margin, hi + margin)
        ax.set_ylim(lo - margin, hi + margin)
        apply_k_axes(ax)
    ax.set_aspect("equal", adjustable="box")
    stats = f"R²={correlation_r2(ref, obs):.5f}\nMAE={mean_error_percent(ref, obs):.3f}%"
    ax.text(
        0.04,
        0.96,
        stats,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "lw": 0},
    )


def plot_validation_sr_scatter(validation_dir: Path, output_dir: Path, formats: list[str]) -> None:
    rows128 = read_csv(validation_dir.joinpath("sr", "results_lahuta_128.csv"))
    panels = [
        (rows128, "zsasa_f64", "zsasa f64 (128 pts)", COLORS["zsasa_std"]),
        (rows128, "zsasa_bitmask_f64", "zsasa bitmask f64 (128 pts)", COLORS["zsasa_bitmask"]),
        (rows128, "rustsasa", "RustSASA (128 pts)", COLORS["rustsasa"]),
        (rows128, "lahuta_bitmask", "Lahuta bitmask (128 pts)", COLORS["lahuta_bitmask"]),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.4), constrained_layout=True)
    for ax, (rows, col, title, color) in zip(axes.flat, panels, strict=True):
        plot_agreement_panel(ax, rows, col, title, color)
    fig.supxlabel("FreeSASA total SASA")
    fig.supylabel("Tool total SASA")
    fig.suptitle("SASA agreement on the E. coli AFDB proteome", y=1.02)
    save_figure(fig, output_dir, "validation_sr_scatter_grid", formats)


def plot_validation_md_scatter(
    validation_md_dir: Path,
    output_dir: Path,
    formats: list[str],
) -> None:
    rows = read_csv(validation_md_dir.joinpath("results_500.csv"))
    panels = [
        ("zsasa_cli_f64", "CLI f64", COLORS["zsasa_std"]),
        ("zsasa_cli_bitmask_f64", "CLI bitmask f64", COLORS["zsasa_bitmask"]),
        ("zsasa_mdtraj", "zsasa.mdtraj", COLORS["zsasa_mdtraj"]),
        ("zsasa_mdanalysis", "zsasa.MDAnalysis", COLORS["zsasa_mdanalysis"]),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.4), constrained_layout=True)
    for ax, (col, title, color) in zip(axes.flat, panels, strict=True):
        plot_agreement_panel(
            ax,
            rows,
            col,
            title,
            color,
            reference_col="mdtraj",
            log_scale=False,
        )
    fig.supxlabel("MDTraj total SASA")
    fig.supylabel("Tool total SASA")
    fig.suptitle("Trajectory SASA agreement on 5wvo (500 points)", y=1.02)
    save_figure(fig, output_dir, "validation_md_scatter_grid", formats)


def batch_json_path(result_dir: Path, tool: str, thread: int = 10) -> Path:
    return result_dir.joinpath(f"bench_{tool}_{thread}t.json")


def refreshed_batch_path(result_dir: Path, tool: str) -> Path:
    suffix = tool.removeprefix("zsasa_")
    return result_dir.joinpath(f"bench_zsasa_{suffix}_10t.json")


def plot_batch_t10_competitors(
    refreshed_dir: Path,
    historical_dir: Path,
    output_dir: Path,
    formats: list[str],
    name: str,
    title: str,
) -> None:
    n_files = result_n_files(refreshed_dir)
    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}
    for tool in BATCH_TOOLS:
        if tool.startswith("zsasa_"):
            path = refreshed_batch_path(refreshed_dir, tool)
        else:
            path = batch_json_path(historical_dir, tool)
        means[tool] = result_mean(path)
        stddevs[tool] = result_stddev(path)

    tools = [tool for tool in BATCH_TOOLS if not math.isnan(means[tool])]
    tools.sort(key=lambda t: means[t])
    x = list(range(len(tools)))
    throughput = [n_files / means[tool] for tool in tools]
    errors = [n_files * stddevs[tool] / (means[tool] * means[tool]) for tool in tools]

    fig, ax = plt.subplots(figsize=(7.4, 4.2), constrained_layout=True)
    ax.bar(
        x,
        throughput,
        yerr=errors,
        capsize=3,
        color=[BATCH_TOOL_COLORS[tool] for tool in tools],
    )
    ax.set_title(title)
    ax.set_ylabel("Structures / second")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[tool] for tool in tools], rotation=35, ha="right")
    save_figure(fig, output_dir, name, formats)


def md_frame_count(dataset: str) -> int:
    if dataset == "5vz0_A_protein":
        return 10001
    return 1001


def refreshed_md_path(md_dir: Path, dataset: str, tool: str) -> Path:
    return md_dir.joinpath(dataset, f"bench_{tool}_10t.json")


def historical_md_path(hist_md_dir: Path, dataset: str, tool: str) -> Path:
    if tool == "mdtraj":
        return hist_md_dir.joinpath(dataset, "bench_mdtraj_1t.json")
    if tool == "mdsasa_bolt":
        return hist_md_dir.joinpath(dataset, "bench_mdsasa_bolt_all.json")
    return hist_md_dir.joinpath(dataset, f"bench_{tool}_10t.json")


def plot_trajectory_competitors(
    md_dir: Path,
    historical_md_dir: Path,
    output_dir: Path,
    formats: list[str],
) -> None:
    datasets = ["5wvo_C_analysis", "6sup_A_analysis"]
    tools = ["zig_f64_bitmask", "zig_f64", "mdsasa_bolt", "mdtraj"]
    labels = {
        "zig_f64_bitmask": "zsasa CLI bitmask f64",
        "zig_f64": "zsasa CLI f64",
        "mdsasa_bolt": "mdsasa-bolt",
        "mdtraj": "MDTraj",
    }
    colors = {
        "zig_f64_bitmask": COLORS["zsasa_bitmask"],
        "zig_f64": COLORS["zsasa_std"],
        "mdsasa_bolt": COLORS["mdsasa_bolt"],
        "mdtraj": COLORS["mdtraj"],
    }
    width = 0.18
    x_base = list(range(len(datasets)))

    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    for i, tool in enumerate(tools):
        values = []
        for dataset in datasets:
            path = (
                refreshed_md_path(md_dir, dataset, tool)
                if tool.startswith("zig_")
                else historical_md_path(historical_md_dir, dataset, tool)
            )
            mean = result_mean(path)
            values.append(md_frame_count(dataset) / mean)
        x = [base + (i - 1.5) * width for base in x_base]
        ax.bar(x, values, width=width, label=labels[tool], color=colors[tool])

    ax.set_title("Trajectory throughput against Python/Rust baselines")
    ax.set_ylabel("Frames / second")
    ax.set_yscale("log")
    ax.set_xticks(x_base)
    ax.set_xticklabels(["5wvo", "6sup"])
    ax.legend(ncol=2)
    save_figure(fig, output_dir, "trajectory_competitor_fps", formats)


def plot_trajectory_memory(
    md_dir: Path,
    historical_md_dir: Path,
    output_dir: Path,
    formats: list[str],
) -> None:
    datasets = ["5wvo_C_analysis", "6sup_A_analysis"]
    tools = ["zig_f64_bitmask", "zig_f64", "mdsasa_bolt", "mdtraj"]
    labels = ["zsasa bitmask", "zsasa", "mdsasa-bolt", "MDTraj"]
    colors = [COLORS["zsasa_bitmask"], COLORS["zsasa_std"], COLORS["mdsasa_bolt"], COLORS["mdtraj"]]
    width = 0.18
    x_base = list(range(len(datasets)))

    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    for i, tool in enumerate(tools):
        values = []
        for dataset in datasets:
            path = (
                refreshed_md_path(md_dir, dataset, tool)
                if tool.startswith("zig_")
                else historical_md_path(historical_md_dir, dataset, tool)
            )
            values.append(result_memory_mib(path))
        x = [base + (i - 1.5) * width for base in x_base]
        ax.bar(x, values, width=width, label=labels[i], color=colors[i])

    ax.set_title("Trajectory peak RSS")
    ax.set_ylabel("Memory (MiB)")
    ax.set_yscale("log")
    ax.set_xticks(x_base)
    ax.set_xticklabels(["5wvo", "6sup"])
    ax.legend(ncol=2)
    save_figure(fig, output_dir, "trajectory_memory", formats)


def plot_single_file_runtime(exports_dir: Path, output_dir: Path, formats: list[str]) -> None:
    rows = read_csv(exports_dir.joinpath("single-file-subset-comparison-t10.csv"))
    fig, ax = plt.subplots(figsize=(6.8, 4.5), constrained_layout=True)
    for prefix, label, color in SINGLE_FILE_TOOLS:
        mean_col = f"{prefix}_mean_s"
        points = [
            (to_float(row["n_atoms"]), to_float(row[mean_col]), row["structure"].startswith("af-"))
            for row in rows
            if row.get(mean_col)
        ]
        points.sort(key=lambda item: item[0])
        ax.plot(
            [p[0] for p in points],
            [p[1] for p in points],
            color=color,
            alpha=0.35,
            linewidth=1.4,
        )
        for is_afdb, marker in [
            (True, "o"),
            (False, "s"),
        ]:
            subset = [p for p in points if p[2] is is_afdb]
            if not subset:
                continue
            ax.scatter(
                [p[0] for p in subset],
                [p[1] for p in subset],
                s=42,
                marker=marker,
                alpha=0.82,
                color=color,
                edgecolors="white",
                linewidths=0.4,
                label=label if is_afdb else None,
            )

    # Separate legend for source marker shape.
    source_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#777",
            label="AFDB single-chain",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="#777",
            label="PDB multi-chain",
        ),
    ]
    tool_legend = ax.legend(ncol=2, loc="upper left", title="Tool")
    ax.add_artist(tool_legend)
    ax.legend(handles=source_handles, loc="lower right", title="Input type")
    ax.set_title("Single-file subset runtime (10 threads)")
    ax.set_xlabel("Atoms")
    ax.set_ylabel("Wall time (s)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    save_figure(fig, output_dir, "single_file_runtime_vs_atoms", formats)


def plot_single_file_outlier_runtime(
    exports_dir: Path,
    output_dir: Path,
    formats: list[str],
) -> None:
    rows = read_csv(exports_dir.joinpath("single-file-subset-comparison-t10.csv"))
    outliers = ["8fon", "8rbs", "5vyc", "9fqr"]
    tools = [
        ("zig_f64_mean_s", "zsasa f64", COLORS["zsasa_std"]),
        ("zig_f64_bitmask_mean_s", "zsasa bitmask f64", COLORS["zsasa_bitmask"]),
        ("historical_freesasa_mean_s", "FreeSASA", COLORS["freesasa"]),
        ("historical_rustsasa_mean_s", "RustSASA", COLORS["rustsasa"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.3), constrained_layout=True)
    width = 0.18
    x_base = list(range(len(outliers)))
    for i, (col, label, color) in enumerate(tools):
        values = []
        for structure in outliers:
            row = next(r for r in rows if r["structure"] == structure)
            values.append(to_float(row[col]))
        x = [base + (i - 1.5) * width for base in x_base]
        ax.bar(x, values, width=width, label=label, color=color)
    ax.set_title("Runtime on selected parser/runtime outlier structures")
    ax.set_ylabel("Wall time (s)")
    ax.set_yscale("log")
    ax.set_xticks(x_base)
    ax.set_xticklabels(outliers)
    ax.legend(ncol=2)
    save_figure(fig, output_dir, "single_file_outlier_runtime", formats)


def plot_single_file_breakdown(exports_dir: Path, output_dir: Path, formats: list[str]) -> None:
    rows = read_csv(exports_dir.joinpath("single-file-subset-comparison-t10.csv"))
    outliers = ["8fon", "8rbs", "5vyc", "9fqr"]
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.8), constrained_layout=False)
    tools = [
        ("zig_f64", "zsasa f64"),
        ("zig_f64_bitmask", "zsasa bitmask"),
        ("historical_freesasa", "FreeSASA"),
        ("historical_rustsasa", "RustSASA"),
    ]
    for ax, structure in zip(axes.flat, outliers, strict=True):
        row = next(r for r in rows if r["structure"] == structure)
        labels = [label for _, label in tools]
        parse = [to_float(row[f"{prefix}_parse_ms"]) / 1000.0 for prefix, _ in tools]
        sasa = [to_float(row[f"{prefix}_sasa_ms"]) / 1000.0 for prefix, _ in tools]
        y = list(range(len(tools)))
        ax.barh(y, parse, color="#9ecae1", label="parse")
        ax.barh(y, sasa, left=parse, color="#fdae6b", label="SASA")
        ax.set_title(f"{structure} ({int(to_float(row['n_atoms'])):,} atoms)")
        ax.set_xlabel("Internal timing (s)")
        ax.set_xscale("log")
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.suptitle("Parser and SASA timing breakdown for selected structures", y=0.98)
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.005),
        ncol=2,
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    save_figure(fig, output_dir, "single_file_timing_breakdown", formats)


def write_inventory(output_dir: Path, formats: list[str]) -> None:
    names = [
        ("validation_sr_scatter_grid", "E. coli SASA agreement scatter plots"),
        ("validation_md_scatter_grid", "5wvo trajectory agreement scatter plots"),
        ("batch_ecoli_t10_competitors", "E. coli AFDB batch throughput comparison"),
        ("batch_human_t10_competitors", "Human AFDB batch throughput comparison"),
        ("trajectory_competitor_fps", "Trajectory throughput versus MDTraj and mdsasa-bolt"),
        ("trajectory_memory", "Trajectory peak memory usage"),
        ("single_file_runtime_vs_atoms", "Single-file subset runtime versus atom count"),
        ("single_file_outlier_runtime", "Runtime on selected parser/runtime outlier structures"),
        ("single_file_timing_breakdown", "Parser/SASA breakdown for selected structures"),
    ]
    lines = ["# Draft figure inventory", ""]
    lines.append("Generated by `scripts/plot_figures.py`. Overview/schematic figures are deferred.")
    lines.append("")
    for name, description in names:
        lines.append(f"## `{name}`")
        lines.append("")
        lines.append(description)
        lines.append("")
        for fmt in formats:
            lines.append(f"- `{figure_path(output_dir, name, fmt)}`")
        lines.append("")
    ROOT.joinpath("docs", "figure-inventory.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {ROOT.joinpath('docs', 'figure-inventory.md')}")


def main() -> None:
    args = parse_args()
    formats = [fmt.strip().lstrip(".") for fmt in args.formats.split(",") if fmt.strip()]
    setup_style()
    plot_validation_sr_scatter(args.validation_dir, args.output_dir, formats)
    plot_validation_md_scatter(args.validation_md_dir, args.output_dir, formats)
    plot_batch_t10_competitors(
        args.batch_ecoli_dir,
        args.historical_batch_dir.joinpath("ecoli_t10"),
        args.output_dir,
        formats,
        "batch_ecoli_t10_competitors",
        "Batch throughput on E. coli AFDB (10 threads)",
    )
    plot_batch_t10_competitors(
        args.batch_human_dir,
        args.historical_batch_dir.joinpath("human_t10"),
        args.output_dir,
        formats,
        "batch_human_t10_competitors",
        "Batch throughput on human AFDB (10 threads)",
    )
    plot_trajectory_competitors(args.md_dir, args.historical_md_dir, args.output_dir, formats)
    plot_trajectory_memory(args.md_dir, args.historical_md_dir, args.output_dir, formats)
    plot_single_file_runtime(args.exports_dir, args.output_dir, formats)
    plot_single_file_outlier_runtime(args.exports_dir, args.output_dir, formats)
    plot_single_file_breakdown(args.exports_dir, args.output_dir, formats)
    write_inventory(args.output_dir, formats)


if __name__ == "__main__":
    main()
