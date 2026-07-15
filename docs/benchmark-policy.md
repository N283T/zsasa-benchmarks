# Benchmark policy

The benchmark repository now targets a same-harness rerun from pinned tool versions.
Do not mix refreshed `zsasa` timings with previous comparator timings for manuscript
claims. Generated evidence should be created under this repository's runners and
ignored `results/` tree.

## Rerun principles

1. Build comparator tools under `external/` from pinned commits with `scripts/setup_external_tools.py`.
2. Resolve the compatibility `zsasa` CLI from the Nix dev shell (`github:N283T/zsasa/v0.6.0`) for the completed baseline, and use `zsasa_0_9_0` for current release-refresh comparisons. Treat 0.7.0 results as superseded historical data.
3. Resolve Python trajectory backends from the uv environment pinned by `pyproject.toml` and `uv.lock`.
4. Write generated outputs under `results/full_rerun/<run_id>/...`; review before staging archives.
5. Keep raw generated results, local DB files, and external source/build trees out of git.
6. Keep local data paths out of manifests. Put them in ignored `config/datasets.local.toml`; use `config/datasets.toml.example` as the tracked template.
7. Use RustSASA JSON output for protein-level totals. Protein-level PDB output writes the total into atom B-factors, which can truncate large SASA values in fixed-width PDB fields.
8. Include PDBTools.jl only in single-file PDB/mmCIF benchmarks through `scripts/benchlib/pdbtools_sasa.jl`; it is a Julia library wrapper, not a batch CLI.

## Setup and dry-run checks

```bash
python scripts/check_tools.py --profile minimal --dry-run
python scripts/check_tools.py --profile single_file --dry-run
python scripts/check_tools.py --profile single_file_pdbtools --dry-run
python scripts/setup_external_tools.py --dry-run --reset freesasa freesasa_batch rustsasa lahuta verify
python scripts/run_validation.py --manifest manifests/validation-ecoli-smoke.toml --datasets config/datasets.toml.example --run-id smoke --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/prepare_single_file_structures.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --dry-run
python scripts/run_single_file.py --manifest manifests/single-file-sample.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/check_tools.py --profile version_refresh_batch --dry-run
uv run python scripts/check_tools.py --profile version_refresh_single --dry-run
uv run python scripts/run_batch.py --manifest manifests/batch-swissprot-version-refresh.toml --datasets config/datasets.toml.example --run-id version_refresh_20260629 --dry-run
uv run python scripts/run_single_file.py --manifest manifests/single-file-mmcif-sample.toml --datasets config/datasets.toml.example --run-id version_refresh_20260629 --dry-run
```

Remove `--dry-run` / use `--execute` only when a real benchmark run is explicitly approved.

## Version-refresh benchmarks

Release-refresh manifests compare multiple `zsasa` versions without replacing the
compatibility `zsasa` tool used by the manuscript rerun. Keep versioned tool IDs
in command names and output directories so `0.6.0` and `0.9.0` results cannot be
accidentally mixed. The SwissProt-scale manifest intentionally keeps the matrix
small because the full 500k-structure workload is expensive: `zsasa_0_6_0` runs
f32 standard/bitmask at 10 threads, `zsasa_0_9_0` runs f32 standard/bitmask at
10, 20, and 40 threads, and Lahuta runs only the 10-thread bitmask comparator.
The earlier 0.7.0 attempt is excluded from active benchmark manifests.

The native mmCIF single-file manifest is separate from the cleaned-PDB
single-file manifest. It currently compares versioned `zsasa` with PDBTools.jl
only, because FreeSASA/RustSASA/Lahuta mmCIF compatibility needs separate
verification. Do not merge those result sets unless the analysis clearly labels
the input format.

## Selective rerun policy

The native runners support repeatable glob filters over command record names:

```bash
python scripts/run_validation.py ... --only 'rustsasa_*' --execute
python scripts/run_validation.py ... --only '*_sr_1000' --exclude '*bitmask*' --dry-run
python scripts/run_batch.py ... --only 'rustsasa_10t_*' --replace --execute
python scripts/run_single_file.py ... --only 'single_timing_freesasa_*_1t_100p' --dry-run
```

Run filtered jobs with `--dry-run` first and inspect `selected_commands=N/M`. Use
`--replace` for reruns that write directory outputs or when output formats changed, because
it removes only the selected command outputs before execution and avoids stale-file mixing.

## FreeSASA batch wrapper provenance

FreeSASA has no native directory batch mode. This repository therefore tracks
`tools/freesasa_batch/`, a small wrapper around the FreeSASA C API, and builds it
against the pinned FreeSASA fork during external setup.

## Single-file input preprocessing

Single-file benchmark subsets use protein-only cleaned PDB inputs prepared by
`scripts/prepare_single_file_structures.py` from tracked source files under
`datasets/single-file-large-structure-sources/`. The prepared PDB payloads are
regenerated locally under ignored `datasets/single-file-large-structure/pdb/`,
and that path is registered as `single_file_large_structure_subset` in the
dataset catalog. The preprocessing policy removes
hydrogens, alternative conformations, ligands, waters, empty chains, and
non-L-peptide chains. It also keeps generated PDB files compatible with
comparator parsers by wrapping residue numbers and atom serials into PDB field
limits and filling the `CRYST1` Z field when needed.

Ligand support is intentionally outside the single-file benchmark scope. This
keeps the benchmark focused on parser and SASA throughput for large protein
structures and avoids mixing tool-specific ligand/classifier support into the
throughput comparison.

Single-file benchmark execution is split into two phases in
`scripts/run_single_file.py`: `wall` records wrap each tool invocation in
hyperfine for headline throughput, while `timing` records invoke the same native
tool command with `--timing` where supported so parser and SASA component times
can be inspected separately. PDBTools.jl timing records run multiple measurements
inside one Julia process after an unrecorded warmup and report median parse/SASA
times, while wall records include Julia startup and package loading. Results are
planned under `results/full_rerun/<run_id>/single/<dataset_id>/`. Lahuta is
intentionally excluded from this benchmark because it targets AlphaFold-style
inputs and is not expected to cover the mixed preprocessed AFDB/NVDA/PDB subset
consistently.
