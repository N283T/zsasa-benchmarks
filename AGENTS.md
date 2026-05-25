# Project Instructions for Codex

This file applies to work in the `zsasa-benchmarks` repository.

## Repository Purpose

- This repository stores benchmark data, plotting scripts, generated figures, and summary tables for `zsasa` benchmark analysis.
- Benchmark data is stored in `results/benchmark.duckdb`.
- Generated figures under `results/figures/` and summary tables under `results/tables/` are intentionally tracked.

## Workflow

- Do not commit directly to `main`.
- Use short-lived branches for changes, for example `chore/regenerate-figures-from-refreshed-data`.
- Keep changes scoped: regenerate only the relevant figure/table groups unless the user asks for all outputs.
- Use `uv run ...` for Python scripts and checks.
- Before committing plotting/script changes, run focused checks such as:

```bash
uv run ruff check scripts/plot_validation_figures.py scripts/plot_batch_figures.py scripts/plot_md_figures.py scripts/plot_single_file_figures.py scripts/plot_overview_figures.py scripts/export_summary_tables.py
```

## Common Commands

Regenerate all figure groups:

```bash
uv run python scripts/plot_validation_figures.py --db results/benchmark.duckdb --out-dir results/figures/validation
uv run python scripts/plot_batch_figures.py --db results/benchmark.duckdb --out-dir results/figures --dataset-id all
uv run python scripts/plot_md_figures.py --db results/benchmark.duckdb --out-dir results/figures/md
uv run python scripts/plot_single_file_figures.py --db results/benchmark.duckdb --out-dir results/figures/single_file
uv run python scripts/plot_overview_figures.py --db results/benchmark.duckdb --figures-dir results/figures
```

Regenerate summary tables:

```bash
uv run python scripts/export_summary_tables.py --db results/benchmark.duckdb --out-dir results/tables
```

## Plotting Conventions

- Use `zsasa`, not `zSASA`.
- Keep colors consistent across figures:
  - `zsasa`: yellow/orange family
  - `RustSASA`: red
  - `FreeSASA` / `MDTraj`: blue
  - `Lahuta`: purple
- Prefer Matplotlib's automatic layout for grids; avoid manual grid tweaks that make panels uneven.
- For point-count comparison grids, keep the point count aligned across each row when possible.
- Avoid title suffixes such as `(log scale)` or `(linear-x)`. Use axis scaling only when it genuinely improves readability.
- For simple `n×` speedup/ratio bar charts, prefer linear y-axes unless there is an extreme dynamic range.
- For thread scaling, prefer median runtime when computing speedup/parallel efficiency to reduce sensitivity to run outliers.
- Use leader lines for moved labels when label placement is not adjacent to the plotted point.

## Labeling Conventions

- Use `mdsasa-bolt (Rust)` in MD figures.
- Keep labels legible even if a legend is present; for dense scatter plots, direct labels with leader lines are often preferred.
- Avoid unnecessary dataset/file suffixes in labels when the figure title or panel title already provides the context.

## Output Expectations

- When regenerating figures after data changes, also consider regenerating `results/tables/` so CSV summaries match the plotted data.
- After large regenerations, report generated artifact counts, for example PNG/SVG/CSV totals.
- When reviewing visual changes, inspect representative images from each affected group rather than relying only on script success.
