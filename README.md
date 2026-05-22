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
python scripts/check_tools.py --profile minimal --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --run-id v0_6_0_full --dry-run
python scripts/run_single_file_subset.py
python scripts/export_single_file_subset_summary.py
scripts/plot_figures.py
```

The native Phase 1 runner examples above are dry-runs. They print the commands and `results/full_rerun/<run_id>/...` layout without running benchmarks; do not remove `--dry-run` until a real rerun is explicitly approved. Trajectory runners now route execution through `scripts.benchlib.trajectory_tools`, including explicit hydrogens and the `naccess` trajectory classifier for `zsasa traj` CLI commands.

The `nix develop` shell provides the pinned `zsasa` CLI from `github:N283T/zsasa/v0.6.0` and exports `ZSASA_CLI` to that Nix-store binary so uv-installed Python console scripts cannot shadow the CLI benchmark target. Python trajectory backends and the `zsasa` Python package are pinned in `pyproject.toml`/`uv.lock`; do not import `zsasa` from a local source checkout for manuscript reruns.

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
