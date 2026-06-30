# PDBTools.jl Single-File Benchmark Design

## Goal

Add PDBTools.jl as a fair single-file SASA competitor for both cleaned PDB inputs and native mmCIF inputs. Do not add it to validation, batch, or trajectory benchmarks in this change.

## Scope

PDBTools.jl is a Julia library, not a native batch CLI. The benchmark harness will therefore use a thin repository-owned Julia wrapper for single-file runs only. The wrapper will be labelled as `pdbtools_jl` so result tables and figure labels can distinguish it from native command-line tools.

## Fairness policy

- **Wall phase:** measure the complete wrapper command with hyperfine. This includes Julia process startup and package loading, matching what users experience when invoking the wrapper as a command.
- **Timing phase:** run inside one Julia process. The wrapper performs one unrecorded warmup before recording repeated parse+SASA measurements, then reports median `parse_time_ms`, `sasa_time_ms`, and `total_time_ms` to stderr in the same format consumed by `scripts/run_single_file.py`.
- **Sampling:** pass manifest `n_points` as PDBTools.jl `n_dots`. Document that this is a Shrake-Rupley sampling-count alignment rather than a proof of identical point sets.
- **Parallelism:** invoke Julia with `--threads=<threads>` and call `sasa_particles(...; parallel=true)` when `threads > 1`.
- **Input formats:** use `read_pdb`, which PDBTools.jl documents as the preferred reader for both PDB and mmCIF auto-detection.

## Exclusions

- No full validation integration. PDBTools.jl is a performance comparator, not a reference oracle for zsasa validation.
- No directory batch wrapper. A hand-written Julia directory loop would benchmark wrapper design as much as PDBTools.jl and is unlikely to be competitive with native batch tools.
- No trajectory integration. PDBTools.jl delegates trajectory workflows to the broader Julia MD ecosystem.

## Files

- `scripts/benchlib/pdbtools_sasa.jl`: Julia wrapper used by wall and timing phases.
- `scripts/run_single_file.py`: recognize `pdbtools_jl`, pass timing repeats, and build wrapper commands.
- `config/tool-versions.toml`: add `pdbtools_jl` with `julia` binary metadata.
- `scripts/benchlib/tools.py`: add optional `single_file_pdbtools` check profile.
- `manifests/single-file-sample.toml` and `manifests/single-file-mmcif-sample.toml`: include `pdbtools_jl`.
- Tests for dry-run command shape and import label parsing.
