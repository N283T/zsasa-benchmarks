# Native benchmark runners design

Date: 2026-05-22
Repository: `zsasa-benchmarks`
Status: approved design for implementation planning

## Objective

Replace runtime dependence on `/Users/nagaet/freesasa-zig/benchmarks/scripts` with native benchmark runners in this repository. The benchmark workspace should own runner logic, tool setup checks, result layout, DuckDB import/export, figure inputs, and archive staging. The `zsasa` repository remains an input software target pinned by tag/commit, not a provider of benchmark scripts.

This design covers Phase 1 only: static validation, batch throughput, trajectory validation, and trajectory throughput. Single-file benchmarking is a separate Phase 2 design to be started immediately after the Phase 1 foundation is in place.

## Non-goals for Phase 1

- Do not redesign the single-file benchmark runner in this phase.
- Do not weaken or rewrite paper claims here; this repository change is about benchmark infrastructure only.
- Do not delete existing generated results or historical logs as part of the runner replacement.
- Do not run heavy benchmarks from Codex; runners must support dry-run planning and user-executed benchmark sessions.
- Do not build a general workflow engine yet. A later campaign-level wrapper can orchestrate the native runners after they are stable.

## Architecture

Add a shared library under `scripts/benchlib/` and thin category-specific CLIs under `scripts/`.

```text
scripts/
  benchlib/
    __init__.py
    paths.py
    manifest.py
    tools.py
    commands.py
    hyperfine.py
    runner.py
    metrics.py
    importers.py
  check_tools.py
  run_validation.py
  run_batch.py
  run_trajectory_validation.py
  run_trajectory.py
  import_results.py
  export_tables.py
  plot_figures.py
```

### `benchlib.paths`

Responsibilities:

- Resolve repository-root-relative paths.
- Create ignored output directories under `results/full_rerun/<run_id>/`.
- Keep source data paths, tool build paths, raw outputs, exports, figures, and archive staging paths distinct.

### `benchlib.manifest`

Responsibilities:

- Load and validate TOML manifests.
- Normalize run ids, dataset ids, tool ids, thread lists, point counts, and output paths.
- Fail early on missing required keys or invalid combinations.

### `benchlib.tools`

Responsibilities:

- Read `config/tool-versions.toml` as the tool registry.
- Resolve or build tool binaries.
- Capture versions, commits, paths, and environment metadata.
- Support profiles such as `minimal`, `validation`, `batch`, `trajectory`, and `full`.

The initial implementation may use locally available tool paths, but the API should make it possible to build pinned tools later. `check_tools.py` should expose this layer as a preflight command.

### `benchlib.commands`

Responsibilities:

- Build command lines for `zsasa`, `freesasa_batch`, RustSASA, Lahuta, MDTraj, mdsasa-bolt, and Python wrapper benchmarks.
- Keep tool-specific command construction in one place.
- Return structured command objects with tool id, dataset id, run parameters, output paths, and shell-safe argv.

### `benchlib.hyperfine`

Responsibilities:

- Run or dry-run hyperfine commands.
- Preserve per-run hyperfine JSON files.
- Parse timing and memory fields into normalized records.
- Keep command construction separate from execution.

### `benchlib.runner`

Responsibilities:

- Provide shared `--dry-run` and `--execute` behavior.
- Write `commands.log`, `config.json`, `environment.json`, and run summaries.
- Make dry-run the safe default for every heavy benchmark command.

### `benchlib.metrics`

Responsibilities:

- Compute files/s, frames/s, mean, median, standard deviation, peak memory, and validation error summaries.
- Keep units explicit.
- Avoid plotting-specific transformations here.

### `benchlib.importers`

Responsibilities:

- Import validation and performance outputs into DuckDB.
- Set `source_kind = "full_rerun"` for new campaign results.
- Preserve raw artifact paths in the `artifacts` table.

## Runner CLIs

### `run_validation.py`

Static SASA validation runner.

Inputs:

- `manifests/validation-ecoli.toml`
- E. coli AFDB PDB directory
- tool registry

Workloads:

- Shrake--Rupley point counts: 100, 128, 200, 500, 1000
- Lee--Richards slice count: 20
- tools: `zsasa` f64/f32 standard and bitmask variants, `freesasa_batch`, RustSASA where supported, Lahuta bitmask where supported

Outputs:

```text
results/full_rerun/<run_id>/validation/ecoli/
  commands.log
  config.json
  environment.json
  sr/results_<points>.csv
  lr/results_<slices>.csv
```

Validation runner should prioritize deterministic per-structure SASA output. Timing from validation commands is secondary and should not be used for speed figures unless explicitly imported as performance evidence.

### `run_batch.py`

Directory throughput runner.

Inputs:

- `manifests/batch-ecoli.toml`
- `manifests/batch-human.toml`
- tool registry

Workloads:

- E. coli AFDB directory
- human AFDB directory
- 128 points
- selected thread lists from manifests
- repeated hyperfine runs

Tools:

- `zsasa` f64/f32 standard
- `zsasa` f64/f32 bitmask
- `freesasa_batch`
- RustSASA
- Lahuta and Lahuta bitmask when compatible with the dataset and point count

Outputs:

```text
results/full_rerun/<run_id>/batch/<dataset>/
  commands.log
  config.json
  environment.json
  runs/*.json
  summary.csv
```

The runner must record skipped tools or unsupported tool/dataset combinations explicitly rather than silently dropping them.

### `run_trajectory_validation.py`

Trajectory numerical validation runner.

Inputs:

- `manifests/validation-md-5wvo.toml`
- trajectory files
- tool registry

Workloads:

- `5wvo_C_analysis`
- point counts: 100, 200, 500, 1000
- stride from manifest

Tools:

- native MDTraj reference rerun
- `zsasa` Python wrappers
- `zsasa` CLI f64/f32 standard and bitmask variants

Outputs:

```text
results/full_rerun/<run_id>/validation_md/5wvo_C_analysis/
  commands.log
  config.json
  environment.json
  results_<points>.csv
```

Python imports for MDTraj, MDAnalysis, and `zsasa` wrappers must happen inside tool-specific execution functions so unrelated dry runs do not fail because optional trajectory dependencies are absent.

### `run_trajectory.py`

Trajectory throughput runner.

Inputs:

- `manifests/trajectory.toml`
- trajectory files
- tool registry

Workloads:

- `5wvo_C_analysis`
- `6sup_A_analysis`
- `5vz0_A_protein`
- 100 points
- selected tool lists per dataset

Tools:

- `zsasa` CLI standard and bitmask variants
- `zsasa` Python wrappers where selected
- MDTraj
- mdsasa-bolt

Outputs:

```text
results/full_rerun/<run_id>/md/<dataset>/
  commands.log
  config.json
  environment.json
  runs/*.json
  summary.csv
```

The larger 5vz0 workload may keep Python wrapper tools disabled by manifest policy, but MDTraj and mdsasa-bolt should be explicit if used for speed comparison.

## Phase 2: single-file benchmark redesign

Single-file benchmarking is intentionally not implemented in Phase 1. It will receive a separate design because it has distinct requirements:

- curated subset versus full 2,013-structure sample
- parser/runtime breakdown as a first-class output
- PDB multi-chain versus AFDB single-chain behavior
- Lahuta AFDB-only applicability and skipped-structure reporting
- outlier selection and reproducible subset manifests

Phase 1 must not remove `manifests/single-file-sample.toml` or existing single-file logs. It should simply avoid treating the old single-file wrapper as part of the native runner replacement.

## Data flow

All Phase 1 runners follow this flow:

```text
manifest TOML
  -> native runner dry-run/execute
  -> raw outputs + commands.log + config.json + environment.json
  -> DuckDB import with source_kind = "full_rerun"
  -> exported CSV tables
  -> plot_figures.py
  -> archive staging
```

Raw outputs are always preserved. Manuscript tables and figures should be generated from DB-backed exports rather than directly from ad hoc historical paths.

## Result layout

Use a single campaign run id such as `v0_6_0_full`:

```text
results/full_rerun/v0_6_0_full/
  validation/ecoli/
  validation_md/5wvo_C_analysis/
  batch/ecoli/
  batch/human/
  md/5wvo_C_analysis/
  md/6sup_A_analysis/
  md/5vz0_A_protein/
  exports/
  figures/
```

Generated results remain ignored by git. Archive-ready copies later go under:

```text
archives/v0_6_0_full/
```

## Tool setup and environment capture

`check_tools.py` should support:

```bash
python scripts/check_tools.py --profile minimal
python scripts/check_tools.py --profile validation
python scripts/check_tools.py --profile batch
python scripts/check_tools.py --profile trajectory
python scripts/check_tools.py --profile full
```

It should verify binary availability, executable permissions, version commands, required Python modules for selected profiles, and the pinned `zsasa` tag/commit or binary version. Environment capture should include OS, CPU, memory, Python version, Zig version, hyperfine version, DuckDB version, and relevant git commits.

## Migration strategy

1. Keep existing historical and `zsasa`-only refresh logs for reference.
2. Add native shared library and dry-run capable runner CLIs.
3. Replace `plan_full_rerun.py` with native runner `--dry-run` output once the new runners cover the same categories.
4. Update import/export scripts to consume native full-rerun outputs.
5. Update plotting defaults to read full-rerun exports.
6. Start the separate Phase 2 single-file benchmark design.

## Verification plan

Before any implementation branch is considered ready:

```bash
python scripts/check_scaffold.py
python scripts/check_tools.py --profile minimal
uv run ruff check scripts/
python -m py_compile scripts/*.py scripts/benchlib/*.py
uv run python scripts/smoke_db.py
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --dry-run
python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --dry-run
python scripts/run_trajectory.py --manifest manifests/trajectory.toml --dry-run
```

Heavy `--execute` benchmark runs are outside the implementation verification gate and should be launched manually in a quiet benchmarking session.

## Acceptance criteria

Phase 1 is complete when:

- No Phase 1 runner command calls `/Users/nagaet/freesasa-zig/benchmarks/scripts/*`.
- Native dry-run commands exist for validation, batch, trajectory validation, and trajectory throughput.
- Tool preflight checks are available by profile.
- Full-rerun outputs have a consistent `results/full_rerun/<run_id>/...` layout.
- DuckDB import/export can consume native full-rerun outputs.
- Plotting can be driven from full-rerun exports.
- Single-file benchmarking remains explicitly reserved for Phase 2 without being deleted or deprecated.
