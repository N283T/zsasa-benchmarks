# zsasa Version Refresh Benchmark Design

## Context

The benchmark harness currently assumes one pinned `zsasa` release, mostly `v0.6.0`, across `flake.nix`, `config/tool-versions.toml`, runner defaults, scaffold checks, and documentation. For `zsasa` `v0.7.0`, the benchmark goal is not just to replace the pinned release. We need a repeatable workflow for testing any future `zsasa` release against previous releases under the same local harness.

`v0.7.0` may improve large batch throughput by removing the CPU cap that caused I/O wait. The most important new workload is a SwissProt-scale directory benchmark of roughly 500k structures. This workload should compare only `zsasa 0.6.0`, `zsasa 0.7.0`, and Lahuta because FreeSASA and RustSASA are too slow for this scale. Runs should be limited to one measured run to keep the experiment practical.

The existing single-file benchmark uses cleaned PDB inputs. Prior investigation found that PDB-format limits can create parser and value problems for non-zsasa tools. A separate mmCIF single-file benchmark should be added so native mmCIF performance can be measured without mixing it with PDB conversion artifacts.

## Goals

1. Allow benchmark manifests to select versioned `zsasa` tool IDs such as `zsasa_0_6_0` and `zsasa_0_7_0`.
2. Keep the existing `zsasa` tool ID as a compatibility alias for old manifests and validation workflows.
3. Add a SwissProt-scale batch manifest for `zsasa_0_6_0`, `zsasa_0_7_0`, and Lahuta only.
4. Add a separate mmCIF single-file manifest and dataset entry.
5. Make dry-runs and imports preserve version identity in command names, output paths, and DB `tool_id` values.
6. Update scaffold checks and docs so the repository no longer hard-requires only `v0.6.0`.

## Non-goals

- Do not run the real SwissProt benchmark in this preparation change.
- Do not regenerate figures or summary tables before new measurements exist.
- Do not generalize every comparator into a fully arbitrary matrix. Keep the abstraction focused on versioned `zsasa` plus the explicitly selected comparators.
- Do not remove existing `v0.6.0` manifests or generated tracked figures/tables.

## Design

### Tool registry

`config/tool-versions.toml` will contain separate entries for `zsasa`, `zsasa_0_6_0`, and `zsasa_0_7_0`. The unversioned `zsasa` entry remains the compatibility default. Versioned `zsasa_*` entries resolve their configured binaries directly and must not be overridden by the `ZSASA_CLI` environment variable. Only the compatibility `zsasa` ID keeps the old `ZSASA_CLI` behavior.

### Batch runner

`manifests/*` may provide `[full_rerun].tools`. `scripts/run_batch.py` will use this list when present. Supported labels are:

- `zsasa` and `zsasa_<version>` labels for native `zsasa batch` commands.
- `freesasa_batch`, `rustsasa`, and `lahuta` comparator labels for existing comparator commands.

For versioned `zsasa`, record names and output paths include the full tool label, for example `zsasa_0_7_0_batch_f64_standard_10t_128p`. Existing unversioned names stay unchanged for compatibility.

### SwissProt manifest

Add `manifests/batch-swissprot-version-refresh.toml` with dataset ID `swissprot_500k_pdb`, expected count `500000`, and:

- `tools = ["zsasa_0_6_0", "zsasa_0_7_0", "lahuta"]`
- `threads = [10]`
- `runs = 1`
- `warmup = 0`
- `n_points = 128`
- `precisions = ["f64"]`
- `modes = ["standard"]`

This manifest prioritizes large-scale feasibility and direct version-refresh evidence over exhaustive parameter coverage.

### Single-file mmCIF runner support

`manifests/single-file-*.toml` structures may specify `input_file`. If absent, the runner keeps the current default of `<id>.pdb`. This avoids breaking the existing PDB benchmark while allowing mmCIF entries such as `3jc8.cif.gz` or `AF-...cif.zst`.

Add `manifests/single-file-mmcif-sample.toml` and dataset entry `single_file_large_structure_mmcif_subset`. The initial tool set is `zsasa_0_6_0` and `zsasa_0_7_0` only, with `runs = 1`, `warmup = 0`, `threads = [10]`, and wall/timing phases.

### Import and summaries

`parse_batch_record_name()` and `parse_single_tool_label()` will recognize versioned `zsasa` labels and return `tool_id` as the exact versioned ID. This preserves identity in DuckDB. Figure/table display-label work can happen after measurements are available.

## Verification

Preparation is complete when these checks pass:

```bash
uv run pytest tests/test_benchlib_tools.py tests/test_run_batch_dry_run.py tests/test_run_single_file_dry_run.py tests/test_import_full_rerun.py
uv run python scripts/check_scaffold.py
uv run python scripts/run_batch.py --manifest manifests/batch-swissprot-version-refresh.toml --datasets config/datasets.toml.example --run-id version_refresh_dry --dry-run
uv run python scripts/run_single_file.py --manifest manifests/single-file-mmcif-sample.toml --datasets config/datasets.toml.example --run-id version_refresh_dry --dry-run
```
