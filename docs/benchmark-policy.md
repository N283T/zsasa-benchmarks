# Benchmark policy

## First archive/preprint stance

The first archive/preprint does not need a complete regeneration of every historical benchmark. The practical policy is:

1. Treat existing FreeSASA/RustSASA/Lahuta outputs as comparator baselines.
2. Rerun only `zsasa` for release-fixed validation evidence when needed.
3. Keep speed benchmark reruns separate from validation refreshes.
4. Never overwrite historical result directories.
5. Archive final rerun outputs with commands, versions, manifests, and environment metadata.

## Dataset roles

- `benchmarks/UP000000625_83333_ECOLI_v6/pdb`: E. coli validation and batch throughput.
- `benchmarks/dataset/pdb`: 2,013-structure stratified single-file benchmark sample.
- `benchmarks/md_data/*`: trajectory benchmark inputs.

## What not to do by default

- Do not rerun FreeSASA for validation refreshes unless the baseline is missing or invalidated.
- Do not use the 2,013 single-file sample as the validation dataset.
- Do not move historical `benchmarks/results/` into this repository until the archive layout is approved.


## Database-first result handling

New benchmark evidence should flow through DuckDB rather than ad-hoc CSV/JSON summaries:

1. Preserve raw tool outputs under ignored `results/raw/` or archive staging.
2. Import per-structure and summary values into `results/benchmark.duckdb`.
3. Export manuscript tables and figure inputs from SQL-backed scripts.
4. Keep historical comparator provenance visible through `source_kind` and `source_path`.

For the first archive/preprint, validation can combine historical comparator columns with refreshed `zsasa` columns because SASA values are deterministic. Performance comparisons that mix runs from different environments must be labeled as provisional until comparator reruns are complete.


## Native runner dry-runs

Phase 1 full-rerun planning uses native runner CLIs in this repository, not the temporary full-rerun planner or legacy scripts. Use dry-run mode to review command plans and output paths before any approved execution:

```bash
python scripts/check_tools.py --profile minimal --dry-run
python scripts/run_validation.py --manifest manifests/validation-ecoli.toml --run-id v0_6_0_full --dry-run
python scripts/run_batch.py --manifest manifests/batch-ecoli.toml --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory_validation.py --manifest manifests/validation-md-5wvo.toml --run-id v0_6_0_full --dry-run
uv run python scripts/run_trajectory.py --manifest manifests/trajectory.toml --run-id v0_6_0_full --dry-run
```

Phase 1 full-rerun artifacts belong under `results/full_rerun/<run_id>/...` and remain ignored until reviewed for archive staging. Trajectory plans use explicit hydrogens and `classifier = "naccess"` for `zsasa traj`, matching the historical MD benchmark treatment of hydrogenated trajectory topologies. Single-file benchmark redesign remains Phase 2 work; do not fold the 2,013-structure single-file sample into the Phase 1 native runners.

For reproducibility, `zsasa` CLI execution must resolve from the Nix dev shell (`github:N283T/zsasa/v0.6.0`). The shell exports `ZSASA_CLI` to the Nix-store binary, and runners prefer that path over `PATH` so uv-installed Python console scripts cannot shadow the CLI benchmark target. Python backends must resolve from the uv environment pinned by `pyproject.toml` and `uv.lock` (`zsasa==0.6.0`, MDTraj, MDAnalysis, and mdsasa-bolt). Do not add local source-tree imports such as `/Users/nagaet/freesasa-zig/python` to the benchmark runners.


## FreeSASA batch wrapper provenance

FreeSASA has no native directory batch mode. Historical FreeSASA comparator baselines in this project were generated with the tracked `freesasa_batch` wrapper around the FreeSASA C API, not by an upstream FreeSASA batch command. New infrastructure must preserve that provenance when importing or reporting FreeSASA-derived values.
