# Native Benchmark Runners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build native Phase 1 benchmark runners in `zsasa-benchmarks` for validation, batch, trajectory validation, and trajectory throughput without calling `/Users/nagaet/freesasa-zig/benchmarks/scripts/*`.

**Architecture:** Add a small shared Python library under `scripts/benchlib/` and replace the temporary command planner with dry-run-capable native runner CLIs. Runners read TOML manifests, resolve tools from `config/tool-versions.toml`, write raw outputs under `results/full_rerun/<run_id>/...`, and prepare outputs for DuckDB import/export.

**Tech Stack:** Python 3.12, uv, Ruff, TOML via `tomllib`, DuckDB, hyperfine JSON, subprocess argv execution, existing `zsasa` CLI, FreeSASA/freesasa_batch, RustSASA, Lahuta, MDTraj, mdsasa-bolt.

---

## Scope and ordering

Phase 1 covers only these native runners:

1. static validation,
2. batch throughput,
3. trajectory numerical validation,
4. trajectory throughput,
5. tool preflight,
6. DuckDB import/export hooks for Phase 1 outputs,
7. plotting input path switch to full-rerun exports.

Single-file benchmarking remains a Phase 2 design and implementation. Do not remove `manifests/single-file-sample.toml`; do not wire it into the Phase 1 native runners.

## Files to create or modify

### Create

- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/__init__.py` — package marker.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/paths.py` — root/path helpers and full-rerun output paths.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/manifest.py` — TOML loader and small validation helpers.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/tools.py` — tool registry, binary resolution, version capture, profile checks.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/commands.py` — command builders for Phase 1 tools.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/runner.py` — dry-run/execute runner, command logs, JSON config writing.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/hyperfine.py` — hyperfine argv builder and JSON parsing.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/metrics.py` — normalized metrics helpers.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/importers.py` — full-rerun import helpers.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_tools.py` — profile preflight CLI.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_validation.py` — static validation native runner.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_batch.py` — batch throughput native runner.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory_validation.py` — trajectory validation native runner.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory.py` — trajectory throughput native runner.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_paths.py` — path helper tests.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_commands.py` — command builder tests.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_tools.py` — tool registry tests with temporary fake binaries.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_runner_dry_run.py` — runner dry-run tests.

### Modify

- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/pyproject.toml` — add test dependencies and Ruff package settings.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/README.md` — document native runner commands after implementation.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/config/tool-versions.toml` — add explicit local binary keys and check commands.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/validation-ecoli.toml` — ensure full-rerun keys match native runner inputs.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/batch-ecoli.toml` — ensure full-rerun keys match native runner inputs.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/batch-human.toml` — ensure full-rerun keys match native runner inputs.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/validation-md-5wvo.toml` — ensure full-rerun keys match native runner inputs.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/trajectory.toml` — ensure full-rerun keys match native runner inputs.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py` — check native runner files and forbid Phase 1 runner references to old scripts.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/init_db.py` — seed new tool registry fields if schema remains compatible.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/import_validation_csv.py` — preserve historical import behavior and add full-rerun validation import mode.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/export_validation_summary.py` — support selecting `source_kind=full_rerun`.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/plot_figures.py` — make full-rerun exports the preferred input path once exports exist.

### Remove or retire after replacement

- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/plan_full_rerun.py` — remove after native runner dry-runs cover all Phase 1 categories.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/refresh_validation.py` — keep for history or move to legacy docs only after native validation import works.
- `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/refresh_validation_md.py` — keep for history or move to legacy docs only after native trajectory validation works.

---

### Task 1: Reconcile the current scratch state

**Files:**
- Inspect: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/git status`
- Modify: no source file required unless a conflict is found

- [ ] **Step 1: Inspect uncommitted changes**

Run:

```bash
cd /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks
git status --short --branch
git diff --stat
```

Expected: the committed design spec exists in history, and older scratch changes may still be unstaged.

- [ ] **Step 2: Save a patch of the scratch changes before editing**

Run:

```bash
cd /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks
mkdir -p /tmp/zsasa-benchmarks-safety
git diff > /tmp/zsasa-benchmarks-safety/pre-native-runner-scratch.diff
git status --short > /tmp/zsasa-benchmarks-safety/pre-native-runner-status.txt
```

Expected: both files are written under `/tmp/zsasa-benchmarks-safety/`.

- [ ] **Step 3: Decide whether to keep or revert scratch changes**

If the working tree contains temporary full-rerun planner changes that conflict with this plan, revert only those temporary files with:

```bash
git restore README.md config/tool-versions.toml docs/benchmark-policy.md docs/database.md docs/migration-plan.md manifests/batch-ecoli.toml manifests/batch-human.toml manifests/single-file-sample.toml manifests/trajectory.toml manifests/validation-ecoli.toml manifests/validation-md-5wvo.toml scripts/check_scaffold.py scripts/run_single_file_subset.py
git clean -f -- docs/full-rerun-plan.md scripts/plan_full_rerun.py
```

If any of those files contain edits that should be reused, leave the file and explicitly record the decision in the task notes before continuing.

Expected: the implementation starts from a known state, either clean except the plan file or with intentionally retained edits.

- [ ] **Step 4: Commit only the state-reconciliation decision if files changed**

Run if files were restored or retained with documentation edits:

```bash
git status --short
git add README.md config/tool-versions.toml docs/benchmark-policy.md docs/database.md docs/migration-plan.md manifests/batch-ecoli.toml manifests/batch-human.toml manifests/single-file-sample.toml manifests/trajectory.toml manifests/validation-ecoli.toml manifests/validation-md-5wvo.toml scripts/check_scaffold.py scripts/run_single_file_subset.py
git commit -m "chore: reconcile benchmark runner scaffold"
```

Expected: a commit is created only if there are intentional file changes.

---

### Task 2: Add test tooling and package layout

**Files:**
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/pyproject.toml`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/__init__.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_import_benchlib.py`

- [ ] **Step 1: Add a failing import test**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_import_benchlib.py`:

```python
from __future__ import annotations


def test_benchlib_imports() -> None:
    import scripts.benchlib as benchlib

    assert benchlib.__all__ == []
```

Run:

```bash
uv run pytest tests/test_import_benchlib.py -q
```

Expected: FAIL because `pytest` or `scripts.benchlib` is not available yet.

- [ ] **Step 2: Add test dependency and package marker**

Modify `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/pyproject.toml` so the dependencies list includes pytest:

```toml
[project]
name = "zsasa-benchmarks"
version = "0.1.0"
description = "Benchmark harness for release-fixed zsasa manuscript evidence"
requires-python = ">=3.12"
dependencies = [
  "duckdb==1.5.3",
  "pytest>=8.0",
]
```

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/__init__.py`:

```python
"""Shared helpers for native zsasa benchmark runners."""

from __future__ import annotations

__all__: list[str] = []
```

- [ ] **Step 3: Verify import test passes**

Run:

```bash
uv run pytest tests/test_import_benchlib.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add pyproject.toml scripts/benchlib/__init__.py tests/test_import_benchlib.py
git commit -m "test: add native runner package scaffold"
```

---

### Task 3: Implement path helpers

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/paths.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_paths.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_paths.py`:

```python
from __future__ import annotations

from pathlib import Path

from scripts.benchlib.paths import ROOT, full_rerun_dir, resolve_repo_path


def test_root_is_repository_root() -> None:
    assert ROOT.joinpath("pyproject.toml").exists()
    assert ROOT.name == "zsasa-benchmarks"


def test_resolve_repo_path_keeps_absolute_path() -> None:
    absolute = Path("/tmp/example")
    assert resolve_repo_path(absolute) == absolute


def test_resolve_repo_path_joins_relative_path() -> None:
    assert resolve_repo_path(Path("results/example")).is_absolute()
    assert str(resolve_repo_path(Path("results/example"))).endswith("results/example")


def test_full_rerun_dir_uses_run_id_and_parts() -> None:
    path = full_rerun_dir("v0_6_0_full", "batch", "ecoli")
    assert path == ROOT.joinpath("results", "full_rerun", "v0_6_0_full", "batch", "ecoli")
```

Run:

```bash
uv run pytest tests/test_benchlib_paths.py -q
```

Expected: FAIL because `scripts.benchlib.paths` does not exist.

- [ ] **Step 2: Implement path helpers**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/paths.py`:

```python
"""Path helpers for native benchmark runners."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT.joinpath("results")
ARCHIVES_DIR = ROOT.joinpath("archives")


def resolve_repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT.joinpath(candidate)


def full_rerun_dir(run_id: str, *parts: str) -> Path:
    return RESULTS_DIR.joinpath("full_rerun", run_id, *parts)
```

- [ ] **Step 3: Verify path tests pass**

Run:

```bash
uv run pytest tests/test_benchlib_paths.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/benchlib/paths.py tests/test_benchlib_paths.py
git commit -m "feat: add benchmark path helpers"
```

---

### Task 4: Implement manifest loading and validation helpers

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/manifest.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_manifest.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_manifest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.benchlib.manifest import ManifestError, expect_dict, expect_list, load_manifest


def test_load_manifest_reads_toml(tmp_path: Path) -> None:
    path = tmp_path.joinpath("manifest.toml")
    path.write_text('id = "example"\n[dataset]\nid = "dataset"\n', encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest["id"] == "example"
    assert manifest["dataset"]["id"] == "dataset"


def test_expect_dict_accepts_dict() -> None:
    assert expect_dict({"a": {"b": 1}}, "a") == {"b": 1}


def test_expect_dict_rejects_missing_key() -> None:
    with pytest.raises(ManifestError, match="missing required table: full_rerun"):
        expect_dict({}, "full_rerun")


def test_expect_list_rejects_string() -> None:
    with pytest.raises(ManifestError, match="must be a list"):
        expect_list({"threads": "10"}, "threads")
```

Run:

```bash
uv run pytest tests/test_benchlib_manifest.py -q
```

Expected: FAIL because module does not exist.

- [ ] **Step 2: Implement manifest helpers**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/manifest.py`:

```python
"""TOML manifest loading and validation helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from scripts.benchlib.paths import resolve_repo_path


class ManifestError(ValueError):
    """Raised when a benchmark manifest is malformed."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    resolved = resolve_repo_path(path)
    with resolved.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data.get("id"), str):
        raise ManifestError(f"{resolved} missing required string key: id")
    return data


def expect_dict(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ManifestError(f"missing required table: {key}")
    return value


def expect_list(mapping: dict[str, Any], key: str) -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ManifestError(f"{key} must be a list")
    return value


def expect_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{key} must be a non-empty string")
    return value


def expect_int(mapping: dict[str, Any], key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int):
        raise ManifestError(f"{key} must be an integer")
    return value
```

- [ ] **Step 3: Verify manifest tests pass**

Run:

```bash
uv run pytest tests/test_benchlib_manifest.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/benchlib/manifest.py tests/test_benchlib_manifest.py
git commit -m "feat: add manifest validation helpers"
```

---

### Task 5: Implement tool registry and preflight checks

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/tools.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_tools.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_tools.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/config/tool-versions.toml`

- [ ] **Step 1: Write failing tool registry tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_tools.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.benchlib.tools import ToolError, ToolSpec, load_tool_specs, require_tools


def test_load_tool_specs_reads_known_tools() -> None:
    specs = load_tool_specs(Path("config/tool-versions.toml"))
    assert "zsasa" in specs
    assert specs["zsasa"].repository == "https://github.com/N283T/zsasa"


def test_require_tools_reports_missing_binary(tmp_path: Path) -> None:
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version=None,
            tag=None,
            commit=None,
            binary=tmp_path.joinpath("missing"),
            check_args=["--version"],
            policy="test",
        )
    }
    with pytest.raises(ToolError, match="missing executable for fake"):
        require_tools(specs, ["fake"])


def test_require_tools_accepts_executable(tmp_path: Path) -> None:
    binary = tmp_path.joinpath("fake-tool")
    binary.write_text("#!/bin/sh\necho fake 1.0\n", encoding="utf-8")
    binary.chmod(0o755)
    specs = {
        "fake": ToolSpec(
            tool_id="fake",
            repository=None,
            version="1.0",
            tag=None,
            commit=None,
            binary=binary,
            check_args=["--version"],
            policy="test",
        )
    }
    checked = require_tools(specs, ["fake"])
    assert checked["fake"].binary == binary
```

Run:

```bash
uv run pytest tests/test_benchlib_tools.py -q
```

Expected: FAIL because `scripts.benchlib.tools` does not exist.

- [ ] **Step 2: Add binary/check keys to tool config**

Modify `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/config/tool-versions.toml` by adding these keys where absent:

```toml
[zsasa]
binary = "/Users/nagaet/freesasa-zig/zig-out/bin/zsasa"
check_args = ["--version"]

[freesasa]
binary = "/Users/nagaet/freesasa-zig/benchmarks/external/bin/freesasa"
check_args = ["--version"]

[freesasa_batch]
binary = "/Users/nagaet/freesasa-zig/benchmarks/external/bin/freesasa_batch"
check_args = ["--help"]

[rustsasa]
binary = "/Users/nagaet/freesasa-zig/benchmarks/external/bin/rust-sasa"
check_args = ["--help"]

[lahuta]
binary = "/Users/nagaet/freesasa-zig/benchmarks/external/bin/lahuta"
check_args = ["--version"]

[mdtraj]
python_module = "mdtraj"
check_args = []

[mdsasa_bolt]
python_module = "mdsasa_bolt"
check_args = []
```

Keep existing repository, version, commit, and policy keys.

- [ ] **Step 3: Implement tools module**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/tools.py`:

```python
"""Tool registry and preflight checks."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.benchlib.paths import resolve_repo_path


class ToolError(RuntimeError):
    """Raised when a required benchmark tool is unavailable."""


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    repository: str | None
    version: str | None
    tag: str | None
    commit: str | None
    binary: Path | None
    check_args: list[str]
    policy: str | None
    python_module: str | None = None


def _path_or_none(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return resolve_repo_path(Path(os.path.expanduser(value)))


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def load_tool_specs(path: str | Path) -> dict[str, ToolSpec]:
    resolved = resolve_repo_path(path)
    with resolved.open("rb") as handle:
        raw: dict[str, dict[str, Any]] = tomllib.load(handle)
    specs: dict[str, ToolSpec] = {}
    for tool_id, data in raw.items():
        if tool_id == "runner":
            continue
        specs[tool_id] = ToolSpec(
            tool_id=tool_id,
            repository=data.get("repository"),
            version=data.get("version"),
            tag=data.get("tag"),
            commit=data.get("commit") or data.get("commit_sha"),
            binary=_path_or_none(data.get("binary")),
            check_args=_list_of_strings(data.get("check_args")),
            policy=data.get("policy"),
            python_module=data.get("python_module"),
        )
    return specs


def require_tools(specs: dict[str, ToolSpec], tool_ids: list[str]) -> dict[str, ToolSpec]:
    checked: dict[str, ToolSpec] = {}
    for tool_id in tool_ids:
        if tool_id not in specs:
            raise ToolError(f"unknown tool: {tool_id}")
        spec = specs[tool_id]
        if spec.python_module and importlib.util.find_spec(spec.python_module) is None:
            raise ToolError(f"missing Python module for {tool_id}: {spec.python_module}")
        if spec.binary is not None:
            if not spec.binary.exists() or not os.access(spec.binary, os.X_OK):
                raise ToolError(f"missing executable for {tool_id}: {spec.binary}")
            if spec.check_args:
                subprocess.run(
                    [str(spec.binary), *spec.check_args],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )
        checked[tool_id] = spec
    return checked


PROFILES: dict[str, list[str]] = {
    "minimal": ["zsasa"],
    "validation": ["zsasa", "freesasa_batch", "rustsasa", "lahuta"],
    "batch": ["zsasa", "freesasa_batch", "rustsasa", "lahuta"],
    "trajectory": ["zsasa", "mdtraj", "mdsasa_bolt"],
    "full": ["zsasa", "freesasa_batch", "rustsasa", "lahuta", "mdtraj", "mdsasa_bolt"],
}
```

- [ ] **Step 4: Implement preflight CLI**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_tools.py`:

```python
#!/usr/bin/env python3
"""Check benchmark tool availability by profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.tools import PROFILES, ToolError, load_tool_specs, require_tools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
    parser.add_argument("--profile", choices=sorted(PROFILES), default="minimal")
    parser.add_argument("--dry-run", action="store_true", help="print required tool ids without checking")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tool_ids = PROFILES[args.profile]
    if args.dry_run:
        print("required_tools=" + ",".join(tool_ids))
        return
    specs = load_tool_specs(args.tool_versions)
    try:
        checked = require_tools(specs, tool_ids)
    except ToolError as error:
        raise SystemExit(str(error)) from error
    for tool_id, spec in checked.items():
        location = spec.binary if spec.binary is not None else spec.python_module
        print(f"{tool_id}: OK ({location})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify tests and minimal dry-run pass**

Run:

```bash
uv run pytest tests/test_benchlib_tools.py -q
python scripts/check_tools.py --profile minimal --dry-run
```

Expected: tests PASS and dry-run prints `required_tools=zsasa`.

- [ ] **Step 6: Commit**

Run:

```bash
git add config/tool-versions.toml scripts/benchlib/tools.py scripts/check_tools.py tests/test_benchlib_tools.py
git commit -m "feat: add benchmark tool preflight checks"
```

---

### Task 6: Implement command builders

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/commands.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_commands.py`

- [ ] **Step 1: Write failing command tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_benchlib_commands.py`:

```python
from __future__ import annotations

from pathlib import Path

from scripts.benchlib.commands import (
    batch_command,
    freesasa_batch_command,
    lahuta_batch_command,
    mdtraj_runner_command,
    rustsasa_single_command,
    zsasa_calc_command,
)


def test_zsasa_calc_command_includes_precision_and_bitmask() -> None:
    cmd = zsasa_calc_command(
        binary=Path("/bin/zsasa"),
        input_path=Path("input.pdb"),
        output_path=Path("out.json"),
        algorithm="sr",
        precision="f32",
        n_points=128,
        threads=10,
        bitmask=True,
        timing=True,
    )
    assert cmd == [
        "/bin/zsasa",
        "calc",
        "--algorithm=sr",
        "--threads=10",
        "--precision=f32",
        "--n-points=128",
        "--use-bitmask",
        "--timing",
        "input.pdb",
        "out.json",
    ]


def test_batch_command_writes_jsonl() -> None:
    cmd = batch_command(
        binary=Path("/bin/zsasa"),
        input_dir=Path("pdbs"),
        output_jsonl=Path("out.jsonl"),
        precision="f64",
        n_points=128,
        threads=4,
        bitmask=False,
    )
    assert "--format=jsonl" in cmd
    assert "--precision=f64" in cmd
    assert "--threads=4" in cmd


def test_freesasa_batch_command() -> None:
    cmd = freesasa_batch_command(Path("/bin/freesasa_batch"), Path("pdbs"), Path("out"), 128, 10)
    assert cmd == ["/bin/freesasa_batch", "pdbs", "out", "--n-threads=10", "--n-points=128"]


def test_rustsasa_single_command() -> None:
    cmd = rustsasa_single_command(Path("/bin/rust-sasa"), Path("input.pdb"), Path("out.json"), 100, 2)
    assert "--allow-vdw-fallback" in cmd
    assert "-n" in cmd
    assert "100" in cmd


def test_lahuta_batch_command() -> None:
    cmd = lahuta_batch_command(Path("/bin/lahuta"), Path("pdbs"), Path("out"), 128, 10, True)
    assert "sasa-sr" in cmd
    assert "--use-bitmask" in cmd
    assert "--points" in cmd


def test_mdtraj_runner_command() -> None:
    cmd = mdtraj_runner_command("mdtraj", Path("traj.xtc"), Path("top.pdb"), 100, 1)
    assert cmd[:3] == ["python", "-m", "scripts.benchlib.trajectory_tools"]
    assert "--tool" in cmd
    assert "mdtraj" in cmd
```

Run:

```bash
uv run pytest tests/test_benchlib_commands.py -q
```

Expected: FAIL because command module does not exist.

- [ ] **Step 2: Implement command builders**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/commands.py`:

```python
"""Command builders for native benchmark runners."""

from __future__ import annotations

from pathlib import Path


def zsasa_calc_command(
    *,
    binary: Path,
    input_path: Path,
    output_path: Path,
    algorithm: str,
    precision: str,
    n_points: int | None,
    threads: int,
    bitmask: bool,
    timing: bool = False,
    n_slices: int | None = None,
) -> list[str]:
    cmd = [
        str(binary),
        "calc",
        f"--algorithm={algorithm}",
        f"--threads={threads}",
        f"--precision={precision}",
    ]
    if n_points is not None:
        cmd.append(f"--n-points={n_points}")
    if n_slices is not None:
        cmd.append(f"--n-slices={n_slices}")
    if bitmask:
        cmd.append("--use-bitmask")
    if timing:
        cmd.append("--timing")
    cmd.extend([str(input_path), str(output_path)])
    return cmd


def batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_jsonl: Path,
    precision: str,
    n_points: int,
    threads: int,
    bitmask: bool,
) -> list[str]:
    cmd = [
        str(binary),
        "batch",
        str(input_dir),
        "--format=jsonl",
        "-o",
        str(output_jsonl),
        f"--threads={threads}",
        f"--precision={precision}",
        f"--n-points={n_points}",
    ]
    if bitmask:
        cmd.append("--use-bitmask")
    return cmd


def freesasa_batch_command(binary: Path, input_dir: Path, output_dir: Path, n_points: int, threads: int) -> list[str]:
    return [str(binary), str(input_dir), str(output_dir), f"--n-threads={threads}", f"--n-points={n_points}"]


def rustsasa_single_command(binary: Path, input_path: Path, output_path: Path, n_points: int, threads: int) -> list[str]:
    return [str(binary), str(input_path), str(output_path), "-n", str(n_points), "-t", str(threads), "-o", "protein", "--allow-vdw-fallback"]


def lahuta_batch_command(binary: Path, input_dir: Path, output_dir: Path, n_points: int, threads: int, bitmask: bool) -> list[str]:
    cmd = [str(binary), "sasa-sr", "-f", str(input_dir), "--is_af2_model", "--points", str(n_points), "-t", str(threads), "--output", str(output_dir), "--progress", "0"]
    if bitmask:
        cmd.append("--use-bitmask")
    return cmd


def mdtraj_runner_command(tool: str, xtc: Path, pdb: Path, n_points: int, stride: int) -> list[str]:
    return [
        "python",
        "-m",
        "scripts.benchlib.trajectory_tools",
        "--tool",
        tool,
        "--xtc",
        str(xtc),
        "--pdb",
        str(pdb),
        "--n-points",
        str(n_points),
        "--stride",
        str(stride),
    ]
```

- [ ] **Step 3: Verify command tests pass**

Run:

```bash
uv run pytest tests/test_benchlib_commands.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/benchlib/commands.py tests/test_benchlib_commands.py
git commit -m "feat: add benchmark command builders"
```

---

### Task 7: Implement runner and hyperfine utilities

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/runner.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/hyperfine.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_runner_dry_run.py`

- [ ] **Step 1: Write failing dry-run tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_runner_dry_run.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.benchlib.hyperfine import hyperfine_command, parse_hyperfine_result
from scripts.benchlib.runner import CommandRecord, write_command_log, write_config


def test_write_command_log(tmp_path: Path) -> None:
    records = [CommandRecord(name="example", argv=["echo", "hello"], cwd=tmp_path)]
    path = tmp_path.joinpath("commands.log")
    write_command_log(path, records)
    assert "echo hello" in path.read_text(encoding="utf-8")


def test_write_config(tmp_path: Path) -> None:
    path = tmp_path.joinpath("config.json")
    write_config(path, {"run_id": "abc", "threads": [1, 2]})
    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "abc"


def test_hyperfine_command_includes_export_json() -> None:
    cmd = hyperfine_command(
        name="bench_zsasa_10t",
        command="zsasa batch input --threads=10",
        output_json=Path("runs/bench_zsasa_10t.json"),
        warmup=1,
        runs=3,
        prepare="sync",
    )
    assert cmd[:2] == ["hyperfine", "--warmup"]
    assert "--export-json" in cmd
    assert "runs/bench_zsasa_10t.json" in cmd


def test_parse_hyperfine_result(tmp_path: Path) -> None:
    path = tmp_path.joinpath("result.json")
    path.write_text('{"results":[{"mean":1.5,"stddev":0.1,"min":1.4,"max":1.7,"median":1.5,"times":[1.4,1.5]}]}', encoding="utf-8")
    result = parse_hyperfine_result(path)
    assert result["mean_s"] == 1.5
    assert result["median_s"] == 1.5
```

Run:

```bash
uv run pytest tests/test_runner_dry_run.py -q
```

Expected: FAIL because modules do not exist.

- [ ] **Step 2: Implement runner utilities**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/runner.py`:

```python
"""Shared dry-run and execution utilities."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandRecord:
    name: str
    argv: list[str]
    cwd: Path | None = None


def shell_join(argv: list[str]) -> str:
    return shlex.join(argv)


def write_command_log(path: Path, records: list[CommandRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for record in records:
        if record.cwd is not None:
            lines.append(f"# cwd: {record.cwd}")
        lines.append(f"# name: {record.name}")
        lines.append(shell_join(record.argv))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(record: CommandRecord, *, execute: bool) -> None:
    print(shell_join(record.argv), flush=True)
    if not execute:
        return
    subprocess.run(record.argv, cwd=record.cwd, check=True)
```

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/hyperfine.py`:

```python
"""Hyperfine command helpers."""

from __future__ import annotations

import json
from pathlib import Path


def hyperfine_command(
    *,
    name: str,
    command: str,
    output_json: Path,
    warmup: int,
    runs: int,
    prepare: str | None,
) -> list[str]:
    argv = ["hyperfine", "--warmup", str(warmup), "--runs", str(runs), "--export-json", str(output_json), "--command-name", name]
    if prepare:
        argv.extend(["--prepare", prepare])
    argv.append(command)
    return argv


def parse_hyperfine_result(path: Path) -> dict[str, float | int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = data["results"][0]
    return {
        "mean_s": float(result["mean"]),
        "stddev_s": float(result.get("stddev", 0.0)),
        "min_s": float(result.get("min", result["mean"])),
        "max_s": float(result.get("max", result["mean"])),
        "median_s": float(result.get("median", result["mean"])),
        "n_runs": len(result.get("times", [])),
    }
```

- [ ] **Step 3: Verify runner tests pass**

Run:

```bash
uv run pytest tests/test_runner_dry_run.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/benchlib/runner.py scripts/benchlib/hyperfine.py tests/test_runner_dry_run.py
git commit -m "feat: add native runner execution helpers"
```

---

### Task 8: Implement static validation dry-run runner

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_validation.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_validation_dry_run.py`

- [ ] **Step 1: Write failing dry-run test**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_validation_dry_run.py`:

```python
from __future__ import annotations

import subprocess
import sys


def test_run_validation_dry_run_outputs_native_commands() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_validation.py", "--manifest", "manifests/validation-ecoli.toml", "--run-id", "test_run", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "scripts/validation.py" not in proc.stdout
    assert "source_kind=full_rerun" in proc.stdout
    assert "zsasa" in proc.stdout
    assert "freesasa_batch" in proc.stdout
```

Run:

```bash
uv run pytest tests/test_run_validation_dry_run.py -q
```

Expected: FAIL because `scripts/run_validation.py` does not exist.

- [ ] **Step 2: Implement validation dry-run runner**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_validation.py`:

```python
#!/usr/bin/env python3
"""Native static validation runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.commands import freesasa_batch_command, lahuta_batch_command, batch_command
from benchlib.manifest import expect_dict, load_manifest
from benchlib.paths import full_rerun_dir, resolve_repo_path
from benchlib.runner import CommandRecord, run_command, write_command_log, write_config
from benchlib.tools import load_tool_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", default="v0_6_0_full")
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def build_records(manifest: dict, tool_specs: dict, run_id: str) -> tuple[Path, list[CommandRecord]]:
    dataset = expect_dict(manifest, "dataset")
    input_dir = resolve_repo_path(dataset["historical_path"])
    out_dir = full_rerun_dir(run_id, "validation", "ecoli")
    threads = int(expect_dict(manifest, "full_rerun").get("threads", 10))
    records: list[CommandRecord] = []
    zsasa = tool_specs["zsasa"].binary or Path("zsasa")
    freesasa_batch = tool_specs["freesasa_batch"].binary or Path("freesasa_batch")
    lahuta = tool_specs["lahuta"].binary or Path("lahuta")
    for run in manifest["runs"]:
        algorithm = run["algorithm"]
        for points in run["points"]:
            if algorithm == "sr":
                for precision in ["f64", "f32"]:
                    records.append(CommandRecord(f"zsasa_{precision}_sr_{points}", batch_command(binary=zsasa, input_dir=input_dir, output_jsonl=out_dir.joinpath("sr", f"zsasa_{precision}_{points}.jsonl"), precision=precision, n_points=int(points), threads=threads, bitmask=False)))
                    records.append(CommandRecord(f"zsasa_{precision}_bitmask_sr_{points}", batch_command(binary=zsasa, input_dir=input_dir, output_jsonl=out_dir.joinpath("sr", f"zsasa_{precision}_bitmask_{points}.jsonl"), precision=precision, n_points=int(points), threads=threads, bitmask=True)))
                records.append(CommandRecord(f"freesasa_batch_sr_{points}", freesasa_batch_command(freesasa_batch, input_dir, out_dir.joinpath("sr", f"freesasa_{points}"), int(points), threads)))
                if int(points) in {64, 128, 256}:
                    records.append(CommandRecord(f"lahuta_bitmask_sr_{points}", lahuta_batch_command(lahuta, input_dir, out_dir.joinpath("sr", f"lahuta_bitmask_{points}"), int(points), threads, True)))
            if algorithm == "lr":
                records.append(CommandRecord(f"zsasa_f64_lr_{points}", [str(zsasa), "batch", str(input_dir), out_dir.joinpath("lr", f"zsasa_f64_lr_{points}").as_posix(), "--algorithm=lr", "--precision=f64", f"--n-slices={points}", f"--threads={threads}"]))
                records.append(CommandRecord(f"freesasa_lr_{points}", freesasa_batch_command(freesasa_batch, input_dir, out_dir.joinpath("lr", f"freesasa_lr_{points}"), int(points), threads)))
    return out_dir, records


def main() -> None:
    args = parse_args()
    execute = args.execute and not args.dry_run
    manifest = load_manifest(args.manifest)
    tool_specs = load_tool_specs(args.tool_versions)
    out_dir, records = build_records(manifest, tool_specs, args.run_id)
    print("source_kind=full_rerun")
    write_command_log(out_dir.joinpath("commands.log"), records)
    write_config(out_dir.joinpath("config.json"), {"run_id": args.run_id, "source_kind": "full_rerun", "category": "validation"})
    for record in records:
        run_command(record, execute=execute)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify validation dry-run test passes**

Run:

```bash
uv run pytest tests/test_run_validation_dry_run.py -q
```

Expected: PASS.

- [ ] **Step 4: Update scaffold check**

Modify `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py` so `REQUIRED_FILES` includes:

```python
"scripts/run_validation.py",
"scripts/benchlib/commands.py",
"scripts/benchlib/manifest.py",
"scripts/benchlib/paths.py",
"scripts/benchlib/runner.py",
"scripts/benchlib/tools.py",
```

Add a check that Phase 1 runner files do not contain old runner references:

```python
for runner in ["scripts/run_validation.py"]:
    text = ROOT.joinpath(runner).read_text(encoding="utf-8")
    if "benchmarks/scripts/" in text:
        fail(f"{runner} must not call old benchmark scripts")
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
python scripts/check_scaffold.py
uv run pytest tests/test_run_validation_dry_run.py -q
git add scripts/run_validation.py scripts/check_scaffold.py tests/test_run_validation_dry_run.py
git commit -m "feat: add native validation dry-run runner"
```

---

### Task 9: Implement batch dry-run runner

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_batch.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_batch_dry_run.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py`

- [ ] **Step 1: Write failing batch dry-run test**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_batch_dry_run.py`:

```python
from __future__ import annotations

import subprocess
import sys


def test_run_batch_dry_run_outputs_hyperfine_commands() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_batch.py", "--manifest", "manifests/batch-ecoli.toml", "--run-id", "test_run", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "scripts/bench_batch.py" not in proc.stdout
    assert "hyperfine" in proc.stdout
    assert "freesasa_batch" in proc.stdout
    assert "results/full_rerun/test_run/batch" in proc.stdout
```

Run:

```bash
uv run pytest tests/test_run_batch_dry_run.py -q
```

Expected: FAIL because `scripts/run_batch.py` does not exist.

- [ ] **Step 2: Implement batch dry-run runner**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_batch.py`:

```python
#!/usr/bin/env python3
"""Native directory batch throughput runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.commands import batch_command, freesasa_batch_command, lahuta_batch_command
from benchlib.hyperfine import hyperfine_command
from benchlib.manifest import expect_dict, load_manifest
from benchlib.paths import full_rerun_dir, resolve_repo_path
from benchlib.runner import CommandRecord, run_command, shell_join, write_command_log, write_config
from benchlib.tools import load_tool_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", default="v0_6_0_full")
    parser.add_argument("--tool-versions", type=Path, default=Path("config/tool-versions.toml"))
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def dataset_name(manifest: dict) -> str:
    raw = manifest["dataset"]["id"]
    if "ECOLI" in raw:
        return "ecoli"
    if "HUMAN" in raw:
        return "human"
    return raw.lower()


def build_records(manifest: dict, tool_specs: dict, run_id: str) -> tuple[Path, list[CommandRecord]]:
    dataset = expect_dict(manifest, "dataset")
    full = expect_dict(manifest, "full_rerun")
    name = dataset_name(manifest)
    out_dir = full_rerun_dir(run_id, "batch", name)
    input_dir = resolve_repo_path(dataset["historical_path"])
    runs_dir = out_dir.joinpath("runs")
    n_points = int(full["n_points"])
    warmup = int(full["warmup"])
    runs = int(full["runs"])
    prepare = full.get("prepare")
    zsasa = tool_specs["zsasa"].binary or Path("zsasa")
    freesasa_batch = tool_specs["freesasa_batch"].binary or Path("freesasa_batch")
    lahuta = tool_specs["lahuta"].binary or Path("lahuta")
    records: list[CommandRecord] = []
    for threads in full["threads"]:
        for precision in full.get("precisions", ["f64", "f32"]):
            for bitmask in [False, True]:
                label = f"zsasa_{precision}{'_bitmask' if bitmask else ''}_{threads}t"
                raw = batch_command(binary=zsasa, input_dir=input_dir, output_jsonl=out_dir.joinpath("raw", f"{label}.jsonl"), precision=precision, n_points=n_points, threads=int(threads), bitmask=bitmask)
                records.append(CommandRecord(label, hyperfine_command(name=label, command=shell_join(raw), output_json=runs_dir.joinpath(f"bench_{label}.json"), warmup=warmup, runs=runs, prepare=prepare)))
        label = f"freesasa_{threads}t"
        raw = freesasa_batch_command(freesasa_batch, input_dir, out_dir.joinpath("raw", label), n_points, int(threads))
        records.append(CommandRecord(label, hyperfine_command(name=label, command=shell_join(raw), output_json=runs_dir.joinpath(f"bench_{label}.json"), warmup=warmup, runs=runs, prepare=prepare)))
        for bitmask in [False, True]:
            label = f"lahuta{'_bitmask' if bitmask else ''}_{threads}t"
            raw = lahuta_batch_command(lahuta, input_dir, out_dir.joinpath("raw", label), n_points, int(threads), bitmask)
            records.append(CommandRecord(label, hyperfine_command(name=label, command=shell_join(raw), output_json=runs_dir.joinpath(f"bench_{label}.json"), warmup=warmup, runs=runs, prepare=prepare)))
    return out_dir, records


def main() -> None:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    tool_specs = load_tool_specs(args.tool_versions)
    out_dir, records = build_records(manifest, tool_specs, args.run_id)
    write_command_log(out_dir.joinpath("commands.log"), records)
    write_config(out_dir.joinpath("config.json"), {"run_id": args.run_id, "source_kind": "full_rerun", "category": "batch"})
    execute = args.execute and not args.dry_run
    for record in records:
        run_command(record, execute=execute)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify batch dry-run test passes**

Run:

```bash
uv run pytest tests/test_run_batch_dry_run.py -q
```

Expected: PASS.

- [ ] **Step 4: Update scaffold check**

Add `scripts/run_batch.py` to required files and old-script reference scan.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python scripts/check_scaffold.py
uv run pytest tests/test_run_batch_dry_run.py -q
git add scripts/run_batch.py scripts/check_scaffold.py tests/test_run_batch_dry_run.py
git commit -m "feat: add native batch dry-run runner"
```

---

### Task 10: Implement trajectory validation and throughput dry-run runners

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory_validation.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_trajectory_dry_run.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py`

- [ ] **Step 1: Write failing trajectory dry-run tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_run_trajectory_dry_run.py`:

```python
from __future__ import annotations

import subprocess
import sys


def test_trajectory_validation_dry_run_is_native() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_trajectory_validation.py", "--manifest", "manifests/validation-md-5wvo.toml", "--run-id", "test_run", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "scripts/validation_md.py" not in proc.stdout
    assert "mdtraj" in proc.stdout
    assert "results/full_rerun/test_run/validation_md" in proc.stdout


def test_trajectory_throughput_dry_run_is_native() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_trajectory.py", "--manifest", "manifests/trajectory.toml", "--run-id", "test_run", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "scripts/bench_md.py" not in proc.stdout
    assert "hyperfine" in proc.stdout
    assert "mdsasa_bolt" in proc.stdout
    assert "results/full_rerun/test_run/md" in proc.stdout
```

Run:

```bash
uv run pytest tests/test_run_trajectory_dry_run.py -q
```

Expected: FAIL because scripts do not exist.

- [ ] **Step 2: Implement trajectory validation dry-run runner**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory_validation.py`:

```python
#!/usr/bin/env python3
"""Native trajectory validation runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.commands import mdtraj_runner_command
from benchlib.manifest import expect_dict, load_manifest
from benchlib.paths import full_rerun_dir, resolve_repo_path
from benchlib.runner import CommandRecord, run_command, shell_join, write_command_log, write_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", default="v0_6_0_full")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    dataset = expect_dict(manifest, "dataset")
    full = expect_dict(manifest, "full_rerun")
    out_dir = full_rerun_dir(args.run_id, "validation_md", dataset["id"])
    xtc = resolve_repo_path(dataset["xtc"])
    pdb = resolve_repo_path(dataset["pdb"])
    records: list[CommandRecord] = []
    for points in full["n_points"]:
        for tool in full["tools"]:
            records.append(CommandRecord(f"{tool}_{points}", [*mdtraj_runner_command(tool, xtc, pdb, int(points), int(full["stride"])), "--output", str(out_dir.joinpath(f"{tool}_{points}.csv"))]))
    write_command_log(out_dir.joinpath("commands.log"), records)
    write_config(out_dir.joinpath("config.json"), {"run_id": args.run_id, "source_kind": "full_rerun", "category": "trajectory_validation"})
    execute = args.execute and not args.dry_run
    for record in records:
        run_command(record, execute=execute)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Implement trajectory throughput dry-run runner**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_trajectory.py`:

```python
#!/usr/bin/env python3
"""Native trajectory throughput runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.commands import mdtraj_runner_command
from benchlib.hyperfine import hyperfine_command
from benchlib.manifest import expect_dict, load_manifest
from benchlib.paths import full_rerun_dir, resolve_repo_path
from benchlib.runner import CommandRecord, run_command, shell_join, write_command_log, write_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", default="v0_6_0_full")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    full = expect_dict(manifest, "full_rerun")
    records: list[CommandRecord] = []
    for dataset in manifest["datasets"]:
        out_dir = full_rerun_dir(args.run_id, "md", dataset["id"])
        xtc = resolve_repo_path(dataset["xtc"])
        pdb = resolve_repo_path(dataset["pdb"])
        for tool in dataset["tools"]:
            raw = mdtraj_runner_command(tool, xtc, pdb, int(full["n_points"]), int(full["stride"]))
            raw.extend(["--output", str(out_dir.joinpath("raw", f"{tool}.csv"))])
            label = f"{dataset['id']}_{tool}"
            records.append(CommandRecord(label, hyperfine_command(name=label, command=shell_join(raw), output_json=out_dir.joinpath("runs", f"bench_{tool}.json"), warmup=int(full["warmup"]), runs=int(full["runs"]), prepare=full.get("prepare"))))
    root_out = full_rerun_dir(args.run_id, "md")
    write_command_log(root_out.joinpath("commands.log"), records)
    write_config(root_out.joinpath("config.json"), {"run_id": args.run_id, "source_kind": "full_rerun", "category": "trajectory"})
    execute = args.execute and not args.dry_run
    for record in records:
        run_command(record, execute=execute)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify trajectory dry-run tests pass**

Run:

```bash
uv run pytest tests/test_run_trajectory_dry_run.py -q
```

Expected: PASS.

- [ ] **Step 5: Update scaffold check**

Add `scripts/run_trajectory_validation.py` and `scripts/run_trajectory.py` to required files and old-script reference scan.

- [ ] **Step 6: Verify and commit**

Run:

```bash
python scripts/check_scaffold.py
uv run pytest tests/test_run_trajectory_dry_run.py -q
git add scripts/run_trajectory_validation.py scripts/run_trajectory.py scripts/check_scaffold.py tests/test_run_trajectory_dry_run.py
git commit -m "feat: add native trajectory dry-run runners"
```

---

### Task 11: Add metrics and full-rerun import/export hooks

**Files:**
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/metrics.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/importers.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/import_validation_csv.py`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/export_validation_summary.py`
- Create: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_metrics_importers.py`

- [ ] **Step 1: Write failing metrics tests**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/tests/test_metrics_importers.py`:

```python
from __future__ import annotations

from scripts.benchlib.metrics import files_per_second, relative_error_percent, r2_score


def test_files_per_second() -> None:
    assert files_per_second(4370, 4.37) == 1000.0


def test_relative_error_percent() -> None:
    assert relative_error_percent(101.0, 100.0) == 1.0


def test_r2_score_perfect() -> None:
    assert r2_score([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0
```

Run:

```bash
uv run pytest tests/test_metrics_importers.py -q
```

Expected: FAIL because module does not exist.

- [ ] **Step 2: Implement metrics module**

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/metrics.py`:

```python
"""Metric helpers for benchmark exports."""

from __future__ import annotations


def files_per_second(n_files: int, seconds: float) -> float:
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    return n_files / seconds


def relative_error_percent(observed: float, reference: float) -> float:
    if reference == 0:
        return 0.0 if observed == 0 else float("inf")
    return abs(observed - reference) / abs(reference) * 100.0


def r2_score(reference: list[float], observed: list[float]) -> float:
    if len(reference) != len(observed):
        raise ValueError("reference and observed lengths differ")
    mean_ref = sum(reference) / len(reference)
    ss_tot = sum((value - mean_ref) ** 2 for value in reference)
    ss_res = sum((obs - ref) ** 2 for obs, ref in zip(observed, reference, strict=True))
    return 1.0 - (ss_res / ss_tot) if ss_tot else 1.0
```

Create `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/benchlib/importers.py`:

```python
"""Import helpers for native full-rerun outputs."""

from __future__ import annotations

from pathlib import Path


def source_kind_for_full_rerun() -> str:
    return "full_rerun"


def artifact_path(path: Path) -> str:
    return str(path)
```

- [ ] **Step 3: Add source-kind argument to export script**

Modify `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/export_validation_summary.py`:

Add argument:

```python
parser.add_argument("--source-kind", default=None, help="optional benchmark_runs.source_kind filter")
```

Modify `load_runs(conn)` to accept `source_kind: str | None` and use this SQL when provided:

```python
WHERE benchmark_kind = 'validation'
  AND (? IS NULL OR source_kind = ?)
```

Pass `[source_kind, source_kind]` to `execute`.

- [ ] **Step 4: Verify metrics tests and existing DB smoke pass**

Run:

```bash
uv run pytest tests/test_metrics_importers.py -q
uv run python scripts/smoke_db.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/benchlib/metrics.py scripts/benchlib/importers.py scripts/export_validation_summary.py tests/test_metrics_importers.py
git commit -m "feat: add full-rerun metric helpers"
```

---

### Task 12: Update docs and retire temporary planner

**Files:**
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/README.md`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/docs/benchmark-policy.md`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/docs/migration-plan.md`
- Modify: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py`
- Delete if present: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/plan_full_rerun.py`

- [ ] **Step 1: Update README command examples**

In `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/README.md`, replace `plan_full_rerun.py` examples with:

```bash
python scripts/check_tools.py --profile minimal --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --run-id v0_6_0_full --dry-run
python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --run-id v0_6_0_full --dry-run
python scripts/run_trajectory.py --manifest manifests/trajectory.toml --run-id v0_6_0_full --dry-run
```

- [ ] **Step 2: Retire temporary planner if it exists**

Run:

```bash
if [ -f scripts/plan_full_rerun.py ]; then git rm scripts/plan_full_rerun.py; fi
```

Expected: file is removed only if present.

- [ ] **Step 3: Update scaffold check for final required files**

Ensure `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/check_scaffold.py` checks:

```python
for runner in [
    "scripts/run_validation.py",
    "scripts/run_batch.py",
    "scripts/run_trajectory_validation.py",
    "scripts/run_trajectory.py",
]:
    text = ROOT.joinpath(runner).read_text(encoding="utf-8")
    if "benchmarks/scripts/" in text:
        fail(f"{runner} must not call old benchmark scripts")
```

- [ ] **Step 4: Run full verification**

Run:

```bash
python scripts/check_scaffold.py
python scripts/check_tools.py --profile minimal --dry-run
uv run ruff check scripts/
python -m py_compile scripts/*.py scripts/benchlib/*.py
uv run pytest -q
uv run python scripts/smoke_db.py
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --run-id verify --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --run-id verify --dry-run
python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --run-id verify --dry-run
python scripts/run_trajectory.py --manifest manifests/trajectory.toml --run-id verify --dry-run
```

Expected: all commands exit 0. Dry-run commands print native commands and do not call old benchmark scripts.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md docs/benchmark-policy.md docs/migration-plan.md scripts/check_scaffold.py
git status --short
git commit -m "docs: document native benchmark runners"
```

---

## Plan self-review

- Spec coverage: Phase 1 native runners, tool preflight, full-rerun layout, DuckDB hooks, and old-script removal are covered by Tasks 2--12.
- Single-file handling: explicitly reserved for Phase 2 in the scope section and excluded from native Phase 1 runners.
- Placeholder scan: the plan avoids open-ended placeholders and gives exact files, commands, and expected outcomes.
- Type consistency: command records use `list[str]`, manifest helpers return `dict[str, Any]`, and dry-run runner CLIs use the same `--manifest`, `--run-id`, `--dry-run`, and `--execute` convention.

## Final acceptance note

No Phase 1 runner command calls old benchmark scripts; all Phase 1 runner command lines are produced by native `benchlib` modules in this repository.
