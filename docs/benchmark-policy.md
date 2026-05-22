# Benchmark policy

The benchmark repository now targets a same-harness rerun from pinned tool versions.
Do not mix refreshed `zsasa` timings with previous comparator timings for manuscript
claims. Generated evidence should be created under this repository's runners and
ignored `results/` tree.

## Rerun principles

1. Build comparator tools under `external/` from pinned commits with `scripts/setup_external_tools.py`.
2. Resolve `zsasa` CLI from the Nix dev shell (`github:N283T/zsasa/v0.6.0`).
3. Resolve Python trajectory backends from the uv environment pinned by `pyproject.toml` and `uv.lock`.
4. Write generated outputs under `results/full_rerun/<run_id>/...`; review before staging archives.
5. Keep raw generated results, local DB files, and external source/build trees out of git.
6. Keep local data paths out of manifests. Put them in ignored `config/datasets.local.toml`; use `config/datasets.toml.example` as the tracked template.

## Setup and dry-run checks

```bash
python scripts/check_tools.py --profile minimal --dry-run
python scripts/setup_external_tools.py --dry-run --reset freesasa freesasa_batch rustsasa lahuta verify
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --datasets config/datasets.toml.example --run-id v0_6_0_full --dry-run
```

Remove `--dry-run` / use `--execute` only when a real benchmark run is explicitly approved.

## FreeSASA batch wrapper provenance

FreeSASA has no native directory batch mode. This repository therefore tracks
`tools/freesasa_batch/`, a small wrapper around the FreeSASA C API, and builds it
against the pinned FreeSASA fork during external setup.
