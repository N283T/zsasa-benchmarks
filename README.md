# zsasa-benchmarks

Release-fixed benchmark and validation harness for the `zsasa` manuscript.

Archive DOI: [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561)

This repository is a clean benchmark workspace for the `zsasa` manuscript. It intentionally keeps generated result files out of git and reruns benchmark evidence from pinned tool versions instead of mixing previous comparator outputs with refreshed `zsasa` runs.

## Benchmark policy

- Build all benchmark tools from pinned versions before collecting manuscript evidence.
- Treat FreeSASA comparator values as `freesasa_batch` wrapper outputs, because upstream FreeSASA has no native directory batch mode.
- Include PDBTools.jl only for single-file PDB/mmCIF SASA comparisons through the repository Julia wrapper; do not treat it as a native batch CLI.
- Capture RustSASA protein-level outputs as JSON. Do not use protein-level PDB B-factors for totals, because the PDB B-factor field cannot represent large total SASA values reliably.
- Keep the compatibility `zsasa` tool pinned to `v0.6.0` as the last completed baseline, and use `zsasa_0_9_0` for current release-refresh benchmarks. The incomplete 0.7.0 benchmark attempt is retained only as superseded historical data in the database.
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
python scripts/check_tools.py --profile single_file_pdbtools
uv run python scripts/check_tools.py --profile full
python scripts/run_validation.py --manifest manifests/validation-ecoli-smoke.toml --datasets config/datasets.toml.example --run-id smoke --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/prepare_single_file_structures.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --dry-run
python scripts/run_single_file.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
```

Version-refresh preparation dry-runs:

```bash
uv run python scripts/check_tools.py --profile version_refresh_batch --dry-run
uv run python scripts/check_tools.py --profile version_refresh_single --dry-run
uv run python scripts/run_batch.py --manifest manifests/batch-swissprot-version-refresh.toml --datasets config/datasets.toml.example --run-id version_refresh_20260629 --dry-run
uv run python scripts/run_single_file.py --manifest manifests/single-file-mmcif-sample.toml --datasets config/datasets.toml.example --run-id version_refresh_20260629 --dry-run
```

The native Phase 1 runner examples above are dry-runs. They print the commands and `results/full_rerun/<run_id>/...` layout without running benchmarks; do not remove `--dry-run` until a real rerun is explicitly approved. Trajectory runners now route execution through `scripts.benchlib.trajectory_tools`, including explicit hydrogens and the `naccess` trajectory classifier for `zsasa traj` CLI commands.

The `nix develop` shell provides the pinned `zsasa` CLI from `github:N283T/zsasa/v0.6.0` and exports `ZSASA_CLI` to that Nix-store binary so uv-installed Python console scripts cannot shadow the CLI benchmark target. The same shell also builds and exposes the pinned native comparator CLIs (`freesasa`, `freesasa_batch`, `rust-sasa`, and `lahuta`) from `flake.nix`; `config/tool-versions.toml` intentionally resolves those tools from `PATH` instead of the ignored `external/bin` tree. Python trajectory backends and the `zsasa` Python package are pinned in `pyproject.toml`/`uv.lock`; do not import `zsasa` from a local source checkout for manuscript reruns.

PDBTools.jl is available as the `pdbtools_jl` single-file comparator. The harness invokes `julia --threads <N> --project=scripts/julia/pdbtools_sasa scripts/benchlib/pdbtools_sasa.jl` for PDB and mmCIF inputs. For fair reporting, use Hyperfine `wall` results for full wrapper invocation cost and the Julia wrapper `timing` phase for warmed in-process parse/SASA medians. The Julia dependencies are locked in `scripts/julia/pdbtools_sasa/Manifest.toml`; before a real run in a fresh environment, instantiate/precompile them once with `nix develop -c julia --project=scripts/julia/pdbtools_sasa -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'`.

Version-refresh manifests can compare multiple `zsasa` releases in the same harness. `config/tool-versions.toml` includes versioned tool IDs such as `zsasa_0_6_0` and `zsasa_0_9_0`; their command names are kept separate from the compatibility `ZSASA_CLI` alias so dry-runs, outputs, and DB imports preserve release identity. The Nix development shell exposes the current release as `zsasa-0.9.0`.

Batch `zsasa` commands generated by `scripts/run_batch.py` default to `--classifier=protor` for protein-only benchmark runs. Manifests may override this with `[full_rerun] classifier = "<name>"`. They may also set `[full_rerun] jsonl_decimals = <N>` to pass `--jsonl-decimals=N` when comparing rounded JSONL output behavior; leave it unset when measuring the default writer.

For `zsasa` 0.9.0 AlphaFold mmCIF batch runs, manifests may set `af_model_fast = true` and `input_io = "auto"`, `"mmap"`, or `"read"`. Diagnostic runs may additionally set `timing = true` and `profile_stages = true`; stage profiling is intended for diagnostics rather than primary Hyperfine comparisons.

Batch jobs may override those options and define a lowercase `variant` name. Variant names are included in command names, output directories, and the DuckDB `benchmark_runs.variant` column. The Human CIF manifest uses this to compare generic/read and AF-fast/read at 10, 20, and 40 threads, plus a 20-thread generic/AF-fast mmap control and Lahuta at 10 threads. It uses one warmup, three measured runs, and three-decimal JSONL output.

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
commands and tool `--timing` component commands for parse/SASA timing. The same
runner also supports `manifests/single-file-mmcif-sample.toml`, which mirrors all
eight PDB subset structures and the PDB tool/thread matrix using native
uncompressed mmCIF. Materialize those ignored inputs with `uv run python
scripts/prepare_single_file_mmcif_structures.py --datasets
config/datasets.local.toml --execute`. The mmCIF matrix compares zsasa 0.9.0,
FreeSASA, RustSASA, and PDBTools.jl; Lahuta remains excluded because its file mode
requires AlphaFold-style model metadata and skips general PDB-derived assemblies.
FreeSASA is excluded for the two NVDA structures because it aborts without
producing atomic radii, and for 9fqr because the pinned parser aborts on that
file's valid long assembly text field. Every other structure/tool combination
remains enabled. Interrupted wall-clock runs resume from existing hyperfine JSON
results unless `--replace` is supplied.

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
