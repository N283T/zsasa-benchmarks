#!/usr/bin/env python3
"""Generate validation-focused exploratory figures from existing CSV results.

The script intentionally reads the checked benchmark CSV exports directly instead of
reconstructing plots from a database.  That keeps this first validation pass small,
repeatable, and close to the legacy validation scripts in
``/Users/nagaet/freesasa-zig/benchmarks``.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np

try:
    from scripts.benchlib.metrics import r2_score, relative_error_percent
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from benchlib.metrics import r2_score, relative_error_percent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.joinpath("results", "benchmark.duckdb")
DEFAULT_STATIC_DIR = ROOT.joinpath("results", "validation", "zsasa_v0_6_0_ecoli")
DEFAULT_MD_DIR = ROOT.joinpath("results", "validation_md", "zsasa_v0_6_0_5wvo_C_validation")
DEFAULT_OUT_DIR = ROOT.joinpath("results", "figures", "validation")

ID_COLUMNS = {"structure", "n_atoms", "frame"}
TOOL_ORDER = [
    "zsasa_f64",
    "zsasa_f32",
    "zsasa_bitmask_f64",
    "zsasa_bitmask_f32",
    "zsasa_cli_f64",
    "zsasa_cli_f32",
    "zsasa_cli_bitmask_f64",
    "zsasa_cli_bitmask_f32",
    "zsasa_mdtraj",
    "zsasa_mdanalysis",
    "rustsasa",
    "lahuta",
    "lahuta_bitmask",
    "mdtraj",
    "freesasa",
]
COLORS = {
    # References / external tools
    "freesasa": "#3498db",  # blue
    "mdtraj": "#2c7fb8",  # blue
    "rustsasa": "#e74c3c",  # red
    "lahuta": "#8e44ad",  # purple
    "lahuta_bitmask": "#c39bd3",  # light purple
    # zsasa/Zig family: yellow/orange across every figure
    "zsasa_f64": "#f39c12",
    "zsasa_f32": "#f6c85f",
    "zsasa_bitmask_f64": "#e67e22",
    "zsasa_bitmask_f32": "#ffb347",
    "zsasa_cli_f64": "#f39c12",
    "zsasa_cli_f32": "#f6c85f",
    "zsasa_cli_bitmask_f64": "#e67e22",
    "zsasa_cli_bitmask_f32": "#ffb347",
    "zsasa_mdtraj": "#d35400",
    "zsasa_mdanalysis": "#b9770e",
}
DISPLAY_NAMES = {
    "freesasa": "FreeSASA",
    "mdtraj": "MDTraj",
    "rustsasa": "RustSASA",
    "lahuta": "Lahuta",
    "lahuta_bitmask": "Lahuta bitmask",
    "zsasa_f64": "zsasa f64",
    "zsasa_f32": "zsasa f32",
    "zsasa_bitmask_f64": "zsasa bitmask f64",
    "zsasa_bitmask_f32": "zsasa bitmask f32",
    "zsasa_cli_f64": "zsasa CLI f64",
    "zsasa_cli_f32": "zsasa CLI f32",
    "zsasa_cli_bitmask_f64": "zsasa CLI bitmask f64",
    "zsasa_cli_bitmask_f32": "zsasa CLI bitmask f32",
    "zsasa_mdtraj": "zsasa + MDTraj XTC",
    "zsasa_mdanalysis": "zsasa + MDAnalysis XTC",
}


@dataclass(frozen=True)
class PairSummary:
    n: int
    r2: float
    mean_error_percent: float
    max_error_percent: float
    mean_abs_delta: float
    max_abs_delta: float


@dataclass(frozen=True)
class ResultCsv:
    path: Path
    points: int
    label: str
    rows: list[dict[str, str]]


@dataclass(frozen=True)
class SummaryRecord:
    group: str
    points: int
    candidate: str
    summary: PairSummary


@dataclass(frozen=True)
class ScatterSpec:
    csv_data: ResultCsv
    reference: str
    candidate: str


def run_column_name(run: dict[str, object]) -> str:
    """Map benchmark_runs metadata to the plotting column names used in figures."""
    benchmark_kind = str(run.get("benchmark_kind") or "")
    tool_id = str(run.get("tool_id") or "")
    precision = str(run.get("precision") or "")
    mode = str(run.get("mode") or "")

    if tool_id == "freesasa_batch":
        return "freesasa"
    if tool_id == "mdtraj":
        return "mdtraj"
    if tool_id == "rustsasa":
        return "rustsasa"
    if tool_id in {"zsasa_mdtraj", "zsasa_mdanalysis"}:
        return tool_id
    if tool_id == "lahuta":
        return "lahuta_bitmask" if mode == "bitmask" else "lahuta"
    if tool_id == "zsasa":
        prefix = "zsasa_bitmask" if mode == "bitmask" else "zsasa"
        return f"{prefix}_{precision}"
    if tool_id == "zig":
        prefix = "zsasa_cli" if benchmark_kind == "trajectory_validation" else "zsasa"
        return f"{prefix}_{precision}"
    if tool_id == "zig_bitmask":
        prefix = (
            "zsasa_cli_bitmask" if benchmark_kind == "trajectory_validation" else "zsasa_bitmask"
        )
        return f"{prefix}_{precision}"
    if precision and mode == "bitmask":
        return f"{tool_id}_bitmask_{precision}"
    if precision:
        return f"{tool_id}_{precision}"
    return tool_id


def run_points(run: dict[str, object]) -> int | None:
    value = run.get("n_points") if run.get("n_points") is not None else run.get("n_slices")
    return int(value) if value is not None else None


def structure_sort_key(structure_id: str) -> tuple[int, object]:
    match = re.fullmatch(r"frame_(\d+)", structure_id)
    if match:
        return (0, int(match.group(1)))
    return (1, structure_id)


def db_scalar_to_text(value: object) -> str:
    return "" if value is None else str(value)


def load_run_values(
    con: duckdb.DuckDBPyConnection, run_id: str
) -> dict[str, tuple[int | None, float | None]]:
    rows = con.execute(
        """
        SELECT structure_id, n_atoms, total_sasa
        FROM validation_results
        WHERE run_id = ?
        ORDER BY structure_id
        """,
        [run_id],
    ).fetchall()
    return {str(structure_id): (n_atoms, total_sasa) for structure_id, n_atoms, total_sasa in rows}


def load_validation_tables_from_db(
    db_path: Path,
    *,
    benchmark_kind: str,
    reference_tool_id: str,
    reference_column: str,
    algorithm: str | None = "sr",
    dataset_id: str | None = None,
) -> list[ResultCsv]:
    """Load validation results from DuckDB and pivot runs into figure-ready tables."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        query = """
            SELECT run_id, benchmark_kind, dataset_id, tool_id, algorithm, precision, mode,
                   n_points, n_slices, threads, source_kind
            FROM benchmark_runs
            WHERE benchmark_kind = ?
              AND (? IS NULL OR algorithm = ?)
              AND (? IS NULL OR dataset_id = ?)
            ORDER BY dataset_id, algorithm, COALESCE(n_points, n_slices), tool_id,
                     precision, mode, run_id
        """
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
        ]
        run_rows = con.execute(
            query,
            [benchmark_kind, algorithm, algorithm, dataset_id, dataset_id],
        ).fetchall()
        runs = [dict(zip(columns, row, strict=True)) for row in run_rows]

        grouped: dict[tuple[str, str, int], list[dict[str, object]]] = {}
        for run in runs:
            points = run_points(run)
            if points is None:
                continue
            key = (str(run["dataset_id"]), str(run["algorithm"]), points)
            grouped.setdefault(key, []).append(run)

        tables: list[ResultCsv] = []
        for (group_dataset_id, group_algorithm, points), group_runs in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])
        ):
            reference_runs = [run for run in group_runs if run["tool_id"] == reference_tool_id]
            if not reference_runs:
                continue

            rows_by_structure: dict[str, dict[str, str]] = {}
            for run in reference_runs + [
                run for run in group_runs if run["tool_id"] != reference_tool_id
            ]:
                column = run_column_name(run)
                for structure_id, (n_atoms, total_sasa) in load_run_values(
                    con, str(run["run_id"])
                ).items():
                    is_frame = structure_id.startswith("frame_")
                    row = rows_by_structure.setdefault(
                        structure_id,
                        {
                            "frame" if is_frame else "structure": (
                                structure_id.removeprefix("frame_") if is_frame else structure_id
                            )
                        },
                    )
                    if n_atoms is not None:
                        row["n_atoms"] = db_scalar_to_text(n_atoms)
                    elif "n_atoms" not in row and not is_frame:
                        row["n_atoms"] = ""
                    row[column] = db_scalar_to_text(total_sasa)

            sorted_rows = [
                rows_by_structure[key] for key in sorted(rows_by_structure, key=structure_sort_key)
            ]
            label = f"{benchmark_kind} {group_dataset_id} {group_algorithm} {points}p"
            # Keep the reference column name stable even if the raw DB tool maps differently.
            if reference_column != run_column_name(reference_runs[0]):
                for row in sorted_rows:
                    raw_ref = run_column_name(reference_runs[0])
                    if raw_ref in row:
                        row[reference_column] = row.pop(raw_ref)
            tables.append(ResultCsv(path=db_path, points=points, label=label, rows=sorted_rows))
        return tables
    finally:
        con.close()


def parse_result_points(path: Path) -> int:
    """Return the point count encoded in validation result CSV names."""
    match = re.fullmatch(r"results_(?:lahuta_)?(\d+)\.csv", path.name)
    if match is None:
        raise ValueError(f"unrecognized validation results file name: {path.name}")
    return int(match.group(1))


def discover_result_csvs(directory: Path) -> list[Path]:
    """Find validation CSV files sorted by point count and then file name."""
    return sorted(
        directory.glob("results*.csv"), key=lambda path: (parse_result_points(path), path.name)
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_result_csvs(directory: Path, label_prefix: str) -> list[ResultCsv]:
    return [
        ResultCsv(
            path=path,
            points=parse_result_points(path),
            label=f"{label_prefix} {path.stem}",
            rows=read_rows(path),
        )
        for path in discover_result_csvs(directory)
    ]


def tool_sort_key(name: str) -> tuple[int, str]:
    try:
        return (TOOL_ORDER.index(name), name)
    except ValueError:
        return (len(TOOL_ORDER), name)


def display_name(name: str) -> str:
    return DISPLAY_NAMES.get(name, name)


def tool_color(name: str) -> str:
    """Return the globally consistent color for a plotted tool/variant."""
    return COLORS.get(name, "#7f8c8d")


def slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_").lower()


def numeric_value(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def candidate_columns(rows: list[dict[str, str]], reference: str) -> list[str]:
    """Return numeric data columns other than IDs and the reference column."""
    if not rows:
        return []
    columns = rows[0].keys()
    candidates: list[str] = []
    for column in columns:
        if column in ID_COLUMNS or column == reference:
            continue
        if any(numeric_value(row.get(column)) is not None for row in rows):
            candidates.append(column)
    return sorted(candidates, key=tool_sort_key)


def paired_values(
    rows: list[dict[str, str]], reference: str, candidate: str
) -> tuple[list[float], list[float]]:
    reference_values: list[float] = []
    candidate_values: list[float] = []
    for row in rows:
        ref = numeric_value(row.get(reference))
        obs = numeric_value(row.get(candidate))
        if ref is None or obs is None:
            continue
        reference_values.append(ref)
        candidate_values.append(obs)
    return reference_values, candidate_values


def summarize_pair(rows: list[dict[str, str]], reference: str, candidate: str) -> PairSummary:
    reference_values, candidate_values = paired_values(rows, reference, candidate)
    if not reference_values:
        return PairSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    rel_errors = [
        relative_error_percent(obs, ref)
        for ref, obs in zip(reference_values, candidate_values, strict=True)
    ]
    abs_deltas = [
        abs(obs - ref) for ref, obs in zip(reference_values, candidate_values, strict=True)
    ]
    return PairSummary(
        n=len(reference_values),
        r2=r2_score(reference_values, candidate_values),
        mean_error_percent=sum(rel_errors) / len(rel_errors),
        max_error_percent=max(rel_errors),
        mean_abs_delta=sum(abs_deltas) / len(abs_deltas),
        max_abs_delta=max(abs_deltas),
    )


def relative_errors(rows: list[dict[str, str]], reference: str, candidate: str) -> list[float]:
    reference_values, candidate_values = paired_values(rows, reference, candidate)
    errors = [
        relative_error_percent(obs, ref)
        for ref, obs in zip(reference_values, candidate_values, strict=True)
    ]
    return [value for value in errors if math.isfinite(value)]


def abs_deltas(rows: list[dict[str, str]], left: str, right: str) -> list[float]:
    left_values, right_values = paired_values(rows, left, right)
    return [abs(right - left) for left, right in zip(left_values, right_values, strict=True)]


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


def subplot_shape(n_items: int) -> tuple[int, int]:
    n_cols = max(1, math.ceil(math.sqrt(n_items)))
    n_rows = max(1, math.ceil(n_items / n_cols))
    return n_rows, n_cols


def make_grid(
    items: Sequence[object],
    draw: Callable[[plt.Axes, object], None],
    *,
    title: str,
    out_dir: Path,
    name: str,
    cell_width: float = 4.5,
    cell_height: float = 4.2,
) -> list[Path]:
    if not items:
        return []
    n_rows, n_cols = subplot_shape(len(items))
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(cell_width * n_cols, cell_height * n_rows),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle(title)
    flat_axes = list(axes.flat)
    for ax, item in zip(flat_axes, items, strict=False):
        draw(ax, item)
    for ax in flat_axes[len(items) :]:
        ax.set_visible(False)
    return save_figure(fig, out_dir, name)


def make_point_grid(
    specs: Sequence[ScatterSpec],
    draw: Callable[[plt.Axes, ScatterSpec], None],
    *,
    title: str,
    out_dir: Path,
    name: str,
    cell_width: float = 4.2,
    cell_height: float = 3.8,
) -> list[Path]:
    """Grid scatter specs as rows=point counts and columns=tool variants."""
    if not specs:
        return []
    points = sorted({spec.csv_data.points for spec in specs})
    candidates = sorted({spec.candidate for spec in specs}, key=tool_sort_key)
    spec_map = {(spec.csv_data.points, spec.candidate): spec for spec in specs}
    fig, axes = plt.subplots(
        len(points),
        len(candidates),
        figsize=(cell_width * len(candidates), cell_height * len(points)),
        squeeze=False,
        layout="constrained",
    )
    fig.suptitle(title)
    for row_idx, point in enumerate(points):
        for col_idx, candidate in enumerate(candidates):
            ax = axes[row_idx][col_idx]
            spec = spec_map.get((point, candidate))
            if spec is None:
                ax.set_visible(False)
                continue
            draw(ax, spec)
    return save_figure(fig, out_dir, name)


def draw_scatter(ax: plt.Axes, spec: ScatterSpec) -> None:
    reference_values, candidate_values = paired_values(
        spec.csv_data.rows, spec.reference, spec.candidate
    )
    if len(reference_values) < 1:
        ax.set_title(f"{display_name(spec.candidate)}\n{spec.csv_data.points}p: no data")
        return

    ref = np.array(reference_values, dtype=float)
    obs = np.array(candidate_values, dtype=float)
    ax.scatter(
        ref,
        obs,
        s=8,
        alpha=0.35,
        edgecolors="none",
        color=tool_color(spec.candidate),
        rasterized=True,
    )
    low = min(float(ref.min()), float(obs.min()))
    high = max(float(ref.max()), float(obs.max()))
    pad = (high - low) * 0.03 if high > low else 1.0
    low -= pad
    high += pad
    ax.plot([low, high], [low, high], color="black", linestyle="--", linewidth=1, alpha=0.6)
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"{display_name(spec.reference)} SASA")
    ax.set_ylabel(f"{display_name(spec.candidate)} SASA")
    ax.set_title(f"{display_name(spec.candidate)}\n{spec.csv_data.points} points")

    stats = summarize_pair(spec.csv_data.rows, spec.reference, spec.candidate)
    stats_text = "\n".join(
        [
            f"n={stats.n:,}",
            f"R²={stats.r2:.6f}",
            f"mean err={stats.mean_error_percent:.4g}%",
            f"max err={stats.max_error_percent:.4g}%",
        ]
    )
    ax.text(
        0.03,
        0.97,
        stats_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=7,
        bbox={"boxstyle": "round", "facecolor": "white", "edgecolor": "0.75", "alpha": 0.85},
    )


def collect_scatter_specs(csvs: Iterable[ResultCsv], reference: str) -> list[ScatterSpec]:
    specs: list[ScatterSpec] = []
    for csv_data in csvs:
        for candidate in candidate_columns(csv_data.rows, reference):
            specs.append(ScatterSpec(csv_data=csv_data, reference=reference, candidate=candidate))
    return specs


def collect_summary_records(
    csvs: Iterable[ResultCsv], reference: str, group: str
) -> list[SummaryRecord]:
    records: list[SummaryRecord] = []
    for csv_data in csvs:
        for candidate in candidate_columns(csv_data.rows, reference):
            records.append(
                SummaryRecord(
                    group=group,
                    points=csv_data.points,
                    candidate=candidate,
                    summary=summarize_pair(csv_data.rows, reference, candidate),
                )
            )
    return records


def plot_metric_lines(
    records: list[SummaryRecord], out_dir: Path, prefix: str, title_prefix: str
) -> list[Path]:
    outputs: list[Path] = []
    metrics: list[tuple[str, str, Callable[[PairSummary], float]]] = [
        ("r2", "R²", lambda summary: summary.r2),
        (
            "mean_relative_error",
            "mean relative error (%)",
            lambda summary: summary.mean_error_percent,
        ),
        ("max_relative_error", "max relative error (%)", lambda summary: summary.max_error_percent),
        ("mean_abs_delta", "mean absolute SASA delta", lambda summary: summary.mean_abs_delta),
    ]
    candidates = sorted({record.candidate for record in records}, key=tool_sort_key)
    all_points = sorted({record.points for record in records})
    point_positions = {point: idx for idx, point in enumerate(all_points)}
    for metric_name, ylabel, getter in metrics:
        fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
        for candidate in candidates:
            xs: list[int] = []
            values: list[float] = []
            for record in sorted(
                (item for item in records if item.candidate == candidate),
                key=lambda item: item.points,
            ):
                value = getter(record.summary)
                if math.isfinite(value):
                    xs.append(point_positions[record.points])
                    values.append(value)
            if xs:
                ax.plot(
                    xs,
                    values,
                    marker="o",
                    linewidth=1.8,
                    label=display_name(candidate),
                    color=tool_color(candidate),
                )
        ax.set_title(f"{title_prefix}: {ylabel}")
        ax.set_xlabel("point count")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(len(all_points)), [str(point) for point in all_points])
        ax.legend(loc="best")
        outputs.extend(save_figure(fig, out_dir, f"{prefix}_{metric_name}"))
    return outputs


def plot_error_boxplots(
    csvs: list[ResultCsv], reference: str, out_dir: Path, prefix: str, title: str
) -> list[Path]:
    labels: list[str] = []
    data: list[list[float]] = []
    for csv_data in csvs:
        for candidate in candidate_columns(csv_data.rows, reference):
            errors = relative_errors(csv_data.rows, reference, candidate)
            if errors:
                labels.append(f"{display_name(candidate)}\n{csv_data.points}p")
                data.append(errors)
    if not data:
        return []
    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.45), 5.5), layout="constrained")
    ax.boxplot(data, tick_labels=labels, showfliers=False)
    ax.set_title(title)
    ax.set_ylabel("absolute relative error (%)")
    ax.tick_params(axis="x", rotation=70)
    return save_figure(fig, out_dir, f"{prefix}_relative_error_boxplots")


def plot_static_error_vs_atoms(csvs: list[ResultCsv], out_dir: Path, prefix: str) -> list[Path]:
    specs = collect_scatter_specs(csvs, "freesasa")

    def draw(ax: plt.Axes, spec: ScatterSpec) -> None:
        xs: list[float] = []
        ys: list[float] = []
        for row in spec.csv_data.rows:
            atoms = numeric_value(row.get("n_atoms"))
            ref = numeric_value(row.get(spec.reference))
            obs = numeric_value(row.get(spec.candidate))
            if atoms is None or ref is None or obs is None:
                continue
            err = relative_error_percent(obs, ref)
            if math.isfinite(err):
                xs.append(atoms)
                ys.append(err)
        if not xs:
            ax.set_title(f"{display_name(spec.candidate)} {spec.csv_data.points}p: no data")
            return
        ax.scatter(xs, ys, s=7, alpha=0.35, color=tool_color(spec.candidate), edgecolors="none")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("atoms")
        ax.set_ylabel("absolute relative error (%)")
        ax.set_title(f"{display_name(spec.candidate)}\n{spec.csv_data.points} points")

    return make_point_grid(
        specs,
        draw,
        title="Static SR validation: error vs structure size",
        out_dir=out_dir,
        name=f"{prefix}_error_vs_atoms_grid",
        cell_width=4.2,
        cell_height=3.6,
    )


def plot_md_error_vs_frame(csvs: list[ResultCsv], out_dir: Path, prefix: str) -> list[Path]:
    specs = collect_scatter_specs(csvs, "mdtraj")

    def draw(ax: plt.Axes, spec: ScatterSpec) -> None:
        xs: list[float] = []
        ys: list[float] = []
        for row in spec.csv_data.rows:
            frame = numeric_value(row.get("frame"))
            ref = numeric_value(row.get(spec.reference))
            obs = numeric_value(row.get(spec.candidate))
            if frame is None or ref is None or obs is None:
                continue
            err = relative_error_percent(obs, ref)
            if math.isfinite(err):
                xs.append(frame)
                ys.append(err)
        if not xs:
            ax.set_title(f"{display_name(spec.candidate)} {spec.csv_data.points}p: no data")
            return
        ax.scatter(xs, ys, s=7, alpha=0.4, color=tool_color(spec.candidate), edgecolors="none")
        ax.set_xlabel("frame")
        ax.set_ylabel("absolute relative error (%)")
        ax.set_title(f"{display_name(spec.candidate)}\n{spec.csv_data.points} points")

    return make_point_grid(
        specs,
        draw,
        title="MD validation: error vs frame",
        out_dir=out_dir,
        name=f"{prefix}_error_vs_frame_grid",
        cell_width=4.2,
        cell_height=3.6,
    )


def plot_delta_pairs(
    csvs: list[ResultCsv],
    pair_specs: list[tuple[str, str, str]],
    out_dir: Path,
    prefix: str,
    title: str,
) -> list[Path]:
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    plotted = False
    all_points = sorted({csv_data.points for csv_data in csvs})
    point_positions = {point: idx for idx, point in enumerate(all_points)}
    for left, right, label in pair_specs:
        xs: list[int] = []
        ys: list[float] = []
        for csv_data in csvs:
            if not csv_data.rows or left not in csv_data.rows[0] or right not in csv_data.rows[0]:
                continue
            deltas = abs_deltas(csv_data.rows, left, right)
            if deltas:
                xs.append(point_positions[csv_data.points])
                ys.append(sum(deltas) / len(deltas))
        if xs:
            plotted = True
            ax.plot(xs, ys, marker="o", linewidth=1.8, label=label, color=tool_color(right))
    if not plotted:
        plt.close(fig)
        return []
    ax.set_title(title)
    ax.set_xlabel("point count")
    ax.set_ylabel("mean absolute SASA delta")
    ax.set_xticks(range(len(all_points)), [str(point) for point in all_points])
    ax.legend(loc="best")
    return save_figure(fig, out_dir, f"{prefix}_variant_deltas")


def plot_frame_series(md_csvs: list[ResultCsv], out_dir: Path, prefix: str) -> list[Path]:
    outputs: list[Path] = []
    for csv_data in md_csvs:
        if not csv_data.rows or "frame" not in csv_data.rows[0]:
            continue
        fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
        x = [numeric_value(row.get("frame")) for row in csv_data.rows]
        for column in ["mdtraj", *candidate_columns(csv_data.rows, "mdtraj")]:
            values = [numeric_value(row.get(column)) for row in csv_data.rows]
            xs = [
                frame
                for frame, value in zip(x, values, strict=True)
                if frame is not None and value is not None
            ]
            ys = [
                value
                for frame, value in zip(x, values, strict=True)
                if frame is not None and value is not None
            ]
            if xs:
                ax.plot(xs, ys, linewidth=1.2, label=display_name(column), color=tool_color(column))
        ax.set_title(f"MD validation frame series ({csv_data.points} points)")
        ax.set_xlabel("frame")
        ax.set_ylabel("total SASA")
        ax.legend(loc="best", ncol=2)
        outputs.extend(save_figure(fig, out_dir, f"{prefix}_frame_series_{csv_data.points}p"))
    return outputs


def generate_static_validation(db_path: Path, out_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    sr_csvs = load_validation_tables_from_db(
        db_path,
        benchmark_kind="validation",
        reference_tool_id="freesasa_batch",
        reference_column="freesasa",
        algorithm="sr",
    )

    if sr_csvs:
        sr_specs = collect_scatter_specs(sr_csvs, "freesasa")
        outputs.extend(
            make_point_grid(
                sr_specs,
                draw_scatter,
                title="Static SR validation vs FreeSASA",
                out_dir=out_dir,
                name="static_sr_scatter_grid",
            )
        )
        for spec in sr_specs:
            fig, ax = plt.subplots(figsize=(6.5, 6), layout="constrained")
            draw_scatter(ax, spec)
            outputs.extend(
                save_figure(
                    fig,
                    out_dir,
                    f"static_sr/scatter/{spec.csv_data.points}p_{slugify(spec.candidate)}_vs_freesasa",
                )
            )
        records = collect_summary_records(sr_csvs, "freesasa", "static_sr")
        outputs.extend(plot_metric_lines(records, out_dir, "static_sr", "Static SR validation"))
        outputs.extend(
            plot_error_boxplots(
                sr_csvs,
                "freesasa",
                out_dir,
                "static_sr",
                "Static SR validation error distributions",
            )
        )
        outputs.extend(plot_static_error_vs_atoms(sr_csvs, out_dir, "static_sr"))
        outputs.extend(
            plot_delta_pairs(
                sr_csvs,
                [
                    ("zsasa_f64", "zsasa_bitmask_f64", "zsasa f64: standard vs bitmask"),
                    ("zsasa_f32", "zsasa_bitmask_f32", "zsasa f32: standard vs bitmask"),
                    ("zsasa_f64", "zsasa_f32", "zsasa standard: f64 vs f32"),
                    ("zsasa_bitmask_f64", "zsasa_bitmask_f32", "zsasa bitmask: f64 vs f32"),
                    ("freesasa", "rustsasa", "FreeSASA vs RustSASA"),
                    ("freesasa", "lahuta_bitmask", "FreeSASA vs Lahuta bitmask"),
                ],
                out_dir,
                "static_sr",
                "Static SR validation variant deltas",
            )
        )

    return outputs


def generate_md_validation(db_path: Path, out_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    md_csvs = load_validation_tables_from_db(
        db_path,
        benchmark_kind="trajectory_validation",
        reference_tool_id="mdtraj",
        reference_column="mdtraj",
        algorithm="sr",
    )
    if not md_csvs:
        return outputs

    specs = collect_scatter_specs(md_csvs, "mdtraj")
    outputs.extend(
        make_point_grid(
            specs,
            draw_scatter,
            title="MD validation vs MDTraj",
            out_dir=out_dir,
            name="md_scatter_grid",
        )
    )
    for spec in specs:
        fig, ax = plt.subplots(figsize=(6.5, 6), layout="constrained")
        draw_scatter(ax, spec)
        outputs.extend(
            save_figure(
                fig,
                out_dir,
                f"md/scatter/{spec.csv_data.points}p_{slugify(spec.candidate)}_vs_mdtraj",
            )
        )
    records = collect_summary_records(md_csvs, "mdtraj", "md")
    outputs.extend(plot_metric_lines(records, out_dir, "md", "MD validation"))
    outputs.extend(
        plot_error_boxplots(md_csvs, "mdtraj", out_dir, "md", "MD validation error distributions")
    )
    outputs.extend(plot_md_error_vs_frame(md_csvs, out_dir, "md"))
    outputs.extend(
        plot_delta_pairs(
            md_csvs,
            [
                ("zsasa_cli_f64", "zsasa_cli_bitmask_f64", "zsasa CLI f64: standard vs bitmask"),
                ("zsasa_cli_f32", "zsasa_cli_bitmask_f32", "zsasa CLI f32: standard vs bitmask"),
                ("zsasa_cli_f64", "zsasa_cli_f32", "zsasa CLI standard: f64 vs f32"),
                ("zsasa_cli_bitmask_f64", "zsasa_cli_bitmask_f32", "zsasa CLI bitmask: f64 vs f32"),
                ("zsasa_mdtraj", "zsasa_cli_f64", "zsasa MDTraj-XTC vs CLI-XTC"),
                ("mdtraj", "zsasa_mdanalysis", "MDTraj vs zsasa MDAnalysis"),
            ],
            out_dir,
            "md",
            "MD validation variant deltas",
        )
    )
    outputs.extend(plot_frame_series(md_csvs, out_dir, "md"))
    return outputs


def write_index(out_dir: Path, outputs: list[Path]) -> Path:
    index = out_dir.joinpath("index.md")
    png_outputs = sorted(path for path in outputs if path.suffix == ".png")
    lines = ["# Validation figures", "", f"Generated {len(png_outputs)} PNG figures.", ""]
    for path in png_outputs:
        rel = path.relative_to(out_dir)
        lines.append(f"- `{rel}`")
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-static", action="store_true")
    parser.add_argument("--skip-md", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_style()
    outputs: list[Path] = []
    if not args.skip_static:
        outputs.extend(generate_static_validation(args.db, args.out_dir))
    if not args.skip_md:
        outputs.extend(generate_md_validation(args.db, args.out_dir))
    index = write_index(args.out_dir, outputs)
    png_count = sum(1 for path in outputs if path.suffix == ".png")
    svg_count = sum(1 for path in outputs if path.suffix == ".svg")
    print(f"wrote {png_count} PNG and {svg_count} SVG validation figures under {args.out_dir}")
    print(f"wrote {index}")


if __name__ == "__main__":
    main()
