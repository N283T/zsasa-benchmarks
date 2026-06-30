# zsasa Version Refresh Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned `zsasa` benchmark dry-run support, a SwissProt-scale version-refresh batch manifest, and a native mmCIF single-file manifest.

**Architecture:** Keep existing runner structure, but let manifests provide selected tools. Add small parsing helpers for versioned `zsasa` labels and input-file overrides instead of introducing a broad tool-matrix framework.

**Tech Stack:** Python 3.12, TOML manifests, pytest, uv, existing benchmark runner helpers.

---

## File Structure

- Modify `config/tool-versions.toml`: add `zsasa_0_6_0` and `zsasa_0_7_0` entries.
- Modify `config/datasets.toml.example`: add SwissProt and mmCIF single-file dataset IDs.
- Modify `scripts/benchlib/tools.py`: prevent `ZSASA_CLI` from overriding versioned `zsasa_*` tool IDs.
- Modify `scripts/run_batch.py`: support `[full_rerun].tools` and versioned `zsasa` command/output labels.
- Modify `scripts/run_single_file.py`: support versioned `zsasa` labels and per-structure `input_file`.
- Modify `scripts/import_full_rerun.py`: parse versioned batch and single-file labels.
- Modify `scripts/check_scaffold.py`: require versioned tool entries and new manifests/datasets instead of only `v0.6.0`.
- Add `manifests/batch-swissprot-version-refresh.toml`.
- Add `manifests/single-file-mmcif-sample.toml`.
- Add/update tests in `tests/test_benchlib_tools.py`, `tests/test_run_batch_dry_run.py`, `tests/test_run_single_file_dry_run.py`, and `tests/test_import_full_rerun.py`.

## Tasks

### Task 1: Versioned tool resolution tests

- [ ] Add tests asserting `zsasa_0_6_0` and `zsasa_0_7_0` exist and that `ZSASA_CLI` only overrides `zsasa`.
- [ ] Run the new tests and confirm they fail because versioned entries and resolution behavior are missing.
- [ ] Add versioned tool entries and adjust `_executable_from_env()` to return `ZSASA_CLI` only for `tool_id == "zsasa"`.
- [ ] Re-run `uv run pytest tests/test_benchlib_tools.py` and confirm it passes.

### Task 2: Versioned batch runner tests

- [ ] Add a dry-run test for `manifests/batch-swissprot-version-refresh.toml` expecting 0.6.0 f32 standard/bitmask at 10 threads, 0.7.0 f32 standard/bitmask at 10/20/40 threads, and Lahuta bitmask at 10 threads.
- [ ] Run the test and confirm it fails because the manifest and tool selection are missing.
- [ ] Add the SwissProt manifest and dataset example entry.
- [ ] Update `scripts/run_batch.py` to build records from manifest `tools`/global matrix or per-tool `jobs`.
- [ ] Re-run `uv run pytest tests/test_run_batch_dry_run.py` and confirm it passes.

### Task 3: Versioned import parser tests

- [ ] Add parser tests for `zsasa_0_7_0_batch_f64_standard_10t_128p` and `zsasa_0_7_0` single-file labels.
- [ ] Run tests and confirm they fail because parsers only know unversioned `zsasa`.
- [ ] Update regex/parsing to preserve `tool_id = "zsasa_0_7_0"`.
- [ ] Re-run `uv run pytest tests/test_import_full_rerun.py` and confirm it passes.

### Task 4: mmCIF single-file tests and manifest

- [ ] Add a dry-run test for `manifests/single-file-mmcif-sample.toml` expecting `.cif.gz` input paths and versioned `zsasa` command names.
- [ ] Run the test and confirm it fails because `input_file` and versioned labels are missing.
- [ ] Add the mmCIF manifest and dataset example entry.
- [ ] Update `scripts/run_single_file.py` to parse versioned `zsasa` labels and use per-structure `input_file` when present.
- [ ] Re-run `uv run pytest tests/test_run_single_file_dry_run.py` and confirm it passes.

### Task 5: Scaffold and docs verification

- [ ] Update scaffold checks to require new manifests and dataset IDs and to accept versioned `zsasa` entries.
- [ ] Update README/docs references that describe `v0.6.0` as the only current target.
- [ ] Run focused pytest, `uv run python scripts/check_scaffold.py`, and both new dry-runs.
- [ ] Commit all scoped changes with `feat: add versioned zsasa benchmark manifests`.
