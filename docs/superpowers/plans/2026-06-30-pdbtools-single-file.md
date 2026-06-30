# PDBTools.jl Single-File Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDBTools.jl as a single-file PDB/mmCIF SASA competitor without adding validation or batch scope.

**Architecture:** `scripts/run_single_file.py` will treat `pdbtools_jl` as a normal single-file tool. A small Julia wrapper will read one structure with PDBTools.jl, compute SASA, write JSON, and emit timing lines compatible with existing CSV collection.

**Tech Stack:** Python runner, Julia wrapper, PDBTools.jl, hyperfine, pytest, ruff, Nix dev shell.

---

### Task 1: Dry-run tests

- [ ] Add tests expecting `pdbtools_jl` in PDB and mmCIF single-file manifests.
- [ ] Confirm tests fail because `pdbtools_jl` is unsupported.
- [ ] Add `pdbtools_jl` parsing and command building.
- [ ] Confirm tests pass.

### Task 2: Wrapper and tool metadata

- [ ] Add `scripts/benchlib/pdbtools_sasa.jl` with CLI arguments for input, output, n-dots, timing, and repeats.
- [ ] Add `pdbtools_jl` to `config/tool-versions.toml` and check profiles.
- [ ] Update Nix dev shell to include Julia.
- [ ] Confirm dry-runs show `julia --threads` commands.

### Task 3: Import/docs/scaffold

- [ ] Update single-file import parsing for `pdbtools_jl`.
- [ ] Update manifests and docs with fairness notes.
- [ ] Run focused ruff, pytest, scaffold, and dry-run checks.
