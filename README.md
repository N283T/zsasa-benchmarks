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

## Benchmark system

The benchmark results were collected on this local machine:

- Model: MacBook Pro (`Mac16,1`)
- Chip: Apple M4
- CPU cores: 10 total (4 performance, 6 efficiency)
- Memory: 32 GB
- Operating system: macOS 26.2 (`25C56`)

Tool and dependency versions are pinned by the Nix development shell, project lock files,
and `config/tool-versions.toml`.

## Hyperfine timing conditions

Wall-clock benchmark timings are collected with `hyperfine` 1.20.0, as pinned in
`config/tool-versions.toml`. Native runners build commands through
`scripts/benchlib/hyperfine.py`, which uses:

```text
hyperfine --warmup <warmup> --runs <runs> --export-json <path> --command-name <name> [--prepare sync] <command>
```

Current full-rerun manifests use these timing settings:

| Benchmark suite | Manifest | Hyperfine settings | Benchmark settings |
| --- | --- | --- | --- |
| E. coli batch throughput | `manifests/batch-ecoli.toml` | 3 warmups, 3 measured runs, `--prepare sync` | 128 points; threads 1, 4, 8, and 10; `f64` and `f32` `zsasa` variants |
| Human batch throughput | `manifests/batch-human.toml` | 3 warmups, 3 measured runs, `--prepare sync` | 128 points; 10 threads; `f64` and `f32` `zsasa` variants |
| Single-file wall-clock throughput | `manifests/single-file-sample.toml` | 1 warmup, 3 measured runs, `--prepare sync` | 100 points; threads 1, 4, 8, and 10; Lahuta excluded |
| Trajectory throughput | `manifests/trajectory.toml` | 1 warmup, 3 measured runs, `--prepare sync` | 100 points; stride 1; 10 threads; `naccess` classifier; explicit hydrogens included |

Validation runs are not Hyperfine timing runs; they record output agreement for the
configured validation datasets. The single-file `timing` phase records tool component
timings directly, while the single-file `wall` phase is the Hyperfine-measured phase.

## Quick start

```bash
nix develop
python scripts/check_scaffold.py
python scripts/check_tools.py --profile minimal
python scripts/check_tools.py --profile single_file
uv run python scripts/check_tools.py --profile full
python scripts/run_validation.py --manifest manifests/validation-ecoli-smoke.toml --datasets config/datasets.toml.example --run-id smoke --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/prepare_single_file_structures.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --dry-run
python scripts/run_single_file.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
```

The native Phase 1 runner examples above are dry-runs. They print the commands and `results/full_rerun/<run_id>/...` layout without running benchmarks; do not remove `--dry-run` until a real rerun is explicitly approved. Trajectory runners now route execution through `scripts.benchlib.trajectory_tools`, including explicit hydrogens and the `naccess` trajectory classifier for `zsasa traj` CLI commands.

The `nix develop` shell provides the pinned `zsasa` CLI from `github:N283T/zsasa/v0.6.0` and exports `ZSASA_CLI` to that Nix-store binary so uv-installed Python console scripts cannot shadow the CLI benchmark target. The same shell also builds and exposes the pinned native comparator CLIs (`freesasa`, `freesasa_batch`, `rust-sasa`, and `lahuta`) from `flake.nix`; `config/tool-versions.toml` intentionally resolves those tools from `PATH` instead of the ignored `external/bin` tree. Python trajectory backends and the `zsasa` Python package are pinned in `pyproject.toml`/`uv.lock`; do not import `zsasa` from a local source checkout for manuscript reruns.

Local dataset paths are centralized in `config/datasets.local.toml` (ignored). Copy `config/datasets.toml.example` and adjust paths before real runs.

Single-file subset source files are tracked under
`datasets/single-file-large-structure-sources/`; prepared benchmark PDB inputs
are regenerated under ignored `datasets/single-file-large-structure/pdb/` and
registered as `single_file_large_structure_subset` in the dataset catalog.
Rebuild them with `scripts/prepare_single_file_structures.py`. The preparation step copies
already-clean AFDB PDB inputs where appropriate and converts NVDA `.cif.zst`
plus PDB mmCIF `.cif.gz` structures to protein-only cleaned PDB files. Ligands,
waters, hydrogens, alternative conformations, and non-L-peptide chains are
excluded from these benchmark inputs so comparator behavior remains aligned.
Run them with `scripts/run_single_file.py`, which records both hyperfine wall-clock
commands and tool `--timing` component commands for parse/SASA timing.

## Remaining benchmark rerun

After validation, run the remaining benchmark suites (E. coli batch, human batch, trajectory throughput, and single-file) with:

```bash
uv run python scripts/run_remaining_benchmarks.py --run-id nix_full_20260524 --execute
```

The script auto-enters `nix develop`, prepares the single-file inputs, and then invokes the existing native runners. Omit `--execute` to dry-run the full command plan first. Add `--import-db --validation-run-id nix_validation_20260524` to import a split validation/benchmark rerun into DuckDB after the remaining benchmarks finish.

## Selective reruns

Native runners accept command-record glob filters for targeted reruns:

```bash
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'rustsasa_*' --replace --execute
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'zsasa_batch_*_10t_*' --dry-run
python scripts/run_single_file.py --manifest manifests/single-file-sample.toml --datasets config/datasets.local.toml --run-id v0_6_0_full --only 'single_wall_zsasa_f64_*_10t_100p' --dry-run
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
