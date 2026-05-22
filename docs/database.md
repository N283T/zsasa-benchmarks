# DuckDB result store

`schemas/benchmark.sql` defines the local benchmark evidence database. Generated DB files are ignored and should live under `results/` during local work or `archives/` when preparing a release bundle.

## Core tables

- `datasets`: dataset identity, role, expected count, provenance, redistribution status.
- `tools`: tool versions, commits, repositories, and reuse/rerun policy.
- `benchmark_runs`: one row per imported or executed tool/configuration.
- `validation_results`: per-structure SASA values keyed by `run_id` and `structure_id`.
- `performance_results`: aggregate timing or memory metrics.
- `artifacts`: raw outputs, exported tables, figures, and archive links.

## Source kinds

Use `source_kind` to keep generated evidence provenance explicit. The current
manuscript rerun uses `full_rerun` for same-harness comparator and `zsasa` data.

## Typical commands

```bash
uv run python scripts/init_db.py --datasets config/datasets.toml.example --manifest manifests/validation-ecoli.toml
uv run python scripts/export_validation_summary.py
```
