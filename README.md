# zsasa-benchmarks

Release-fixed benchmark and validation harness for the `zsasa` manuscript.

This repository is a clean benchmark workspace split out from the historical benchmark tree in `/Users/nagaet/freesasa-zig`. It intentionally starts without copied result files. Existing comparator results can be reused as baselines for the first archive/preprint, while `zsasa` itself is refreshed from a fixed release.

## Policy for the first archive/preprint

- Reuse existing FreeSASA/RustSASA/Lahuta comparator outputs where they are already present and documented.
- Treat FreeSASA comparator values as `freesasa_batch` wrapper outputs, because upstream FreeSASA has no native directory batch mode.
- Rerun `zsasa` from the fixed `v0.6.0` release for validation refreshes.
- Do not rerun heavy speed benchmarks or comparator tools until the benchmark scope is explicitly approved.
- Keep generated results out of git; archive final outputs separately after review.
- Store generated/imported evidence in DuckDB, with explicit source provenance for historical baselines versus refreshed runs.

## Quick start

```bash
nix develop
python scripts/check_scaffold.py
uv run python scripts/smoke_db.py
python scripts/report_existing_assets.py --zsasa-repo /Users/nagaet/freesasa-zig
uv run python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --dry-run
```

`refresh_validation.py` defaults to dry-run behavior. It prints the `zsasa` commands that would be run and does not execute benchmarks unless `--execute` is passed.

## Repository layout

```text
config/      pinned tool/version policy
manifests/   dataset and baseline manifests; no raw data
schemas/     DuckDB schema for benchmark evidence
scripts/     benchmark orchestration, DB import/export, and scaffold checks
docs/        migration notes and benchmark policy
results/     ignored generated benchmark outputs and local DuckDB files
archives/    ignored final archive staging area
```

## DuckDB workflow

Initialize a local ignored database:

```bash
uv run python scripts/init_db.py \
  --manifest manifests/validation-ecoli.toml \
  --manifest manifests/batch-ecoli.toml
```

Import historical validation CSVs without running tools:

```bash
uv run python scripts/import_validation_csv.py \
  --manifest manifests/validation-ecoli.toml \
  --tools comparators
```

Export validation summaries from the DB:

```bash
uv run python scripts/export_validation_summary.py
```

These commands read existing CSVs and write ignored DB/export artifacts; they do not run benchmarks.

## Historical source tree

The historical benchmark assets currently live in:

```text
/Users/nagaet/freesasa-zig/benchmarks
```

Result migration is intentionally deferred. See `docs/migration-plan.md`.
