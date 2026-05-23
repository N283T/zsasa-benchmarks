# Figure inventory

Exploratory figures are generated from `results/benchmark.duckdb` and written under
`results/figures/`. The top-level entry point is:

- `results/figures/index.md`

## Generation scripts

Run these from the repository root after importing benchmark results into the DuckDB database:

```bash
uv run python scripts/plot_validation_figures.py --db results/benchmark.duckdb --out-dir results/figures/validation
uv run python scripts/plot_batch_figures.py --db results/benchmark.duckdb --out-dir results/figures --dataset-id all
uv run python scripts/plot_md_figures.py --db results/benchmark.duckdb --out-dir results/figures/md
uv run python scripts/plot_overview_figures.py --db results/benchmark.duckdb --figures-dir results/figures
```

## Current sections

- `results/figures/overview/` — cross-cutting speedup summaries.
- `results/figures/validation/` — static and MD SASA agreement figures.
- `results/figures/batch_ecoli/` — E. coli batch throughput, runtime, memory, CPU, and scaling figures.
- `results/figures/batch_human/` — Human batch 10-thread throughput, runtime, memory, and CPU figures.
- `results/figures/batch_t10_comparison/` — E. coli vs Human 10-thread comparison figures.
- `results/figures/md/` — trajectory throughput, runtime, memory, throughput/RSS, and CPU figures.

Each section includes PNG and SVG outputs plus a section-level `index.md`.
MD scatter-style summaries use marker families in addition to color:

- circles: native `zsasa` CLI runs
- triangles: MDTraj-backed runs
- squares: MDAnalysis-backed runs, including `mdsasa-bolt`
