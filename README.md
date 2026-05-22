# zsasa-benchmarks

Release-fixed benchmark and validation harness for the `zsasa` manuscript.

This repository is a clean benchmark workspace for the `zsasa` manuscript. It intentionally keeps generated result files out of git and reruns benchmark evidence from pinned tool versions instead of mixing previous comparator outputs with refreshed `zsasa` runs.

## Benchmark policy

- Build all benchmark tools from pinned versions before collecting manuscript evidence.
- Treat FreeSASA comparator values as `freesasa_batch` wrapper outputs, because upstream FreeSASA has no native directory batch mode.
- Capture RustSASA protein-level outputs as JSON. Do not use protein-level PDB B-factors for totals, because the PDB B-factor field cannot represent large total SASA values reliably.
- Use the fixed `zsasa` `v0.6.0` release for the current manuscript rerun.
- Keep generated results out of git; archive final outputs separately after review.
- Store generated evidence in DuckDB when result import/export is needed.

## Quick start

```bash
nix develop
python scripts/check_scaffold.py
python scripts/check_tools.py --profile minimal --dry-run
python scripts/setup_external_tools.py --dry-run --reset freesasa freesasa_batch rustsasa lahuta verify
python scripts/run_validation.py --manifest manifests/validation-ecoli-smoke.toml --datasets config/datasets.toml.example --run-id smoke --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
```

The native Phase 1 runner examples above are dry-runs. They print the commands and `results/full_rerun/<run_id>/...` layout without running benchmarks; do not remove `--dry-run` until a real rerun is explicitly approved. Trajectory runners now route execution through `scripts.benchlib.trajectory_tools`, including explicit hydrogens and the `naccess` trajectory classifier for `zsasa traj` CLI commands.

The `nix develop` shell provides the pinned `zsasa` CLI from `github:N283T/zsasa/v0.6.0` and exports `ZSASA_CLI` to that Nix-store binary so uv-installed Python console scripts cannot shadow the CLI benchmark target. Python trajectory backends and the `zsasa` Python package are pinned in `pyproject.toml`/`uv.lock`; do not import `zsasa` from a local source checkout for manuscript reruns. External comparator binaries are built under the ignored `external/` tree by `scripts/setup_external_tools.py` from pinned commits, then referenced through `external/bin/*`.

Local dataset paths are centralized in `config/datasets.local.toml` (ignored). Copy `config/datasets.toml.example` and adjust paths before real runs.

## Selective reruns

Native runners accept command-record glob filters for targeted reruns:

```bash
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'rustsasa_*' --replace --execute
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'zsasa_batch_*_10t_*' --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'zig_bitmask_*_1000p' --dry-run
```

Use `--only` and `--exclude` repeatedly to combine conditions. Use `--replace` only when
you want the selected outputs removed before execution; dry-runs print the paths that would
be removed without deleting anything.

## Repository layout

```text
config/      pinned tool/version policy
manifests/   dataset and rerun manifests; no raw data
schemas/     DuckDB schema for benchmark evidence
scripts/     benchmark orchestration, DB import/export, and scaffold checks
docs/        benchmark policy and rerun plans
results/     ignored generated benchmark outputs and local DuckDB files
archives/    ignored final archive staging area
```

## DuckDB workflow

Initialize a local ignored database for newly generated benchmark evidence:

```bash
uv run python scripts/init_db.py \
  --datasets config/datasets.toml.example \
  --manifest manifests/validation-ecoli.toml \
  --manifest manifests/batch-ecoli.toml
```

Export validation summaries from the DB after result import/loading steps are available:

```bash
uv run python scripts/export_validation_summary.py
```
