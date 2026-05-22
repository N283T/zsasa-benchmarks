# Migration plan

## Phase 1: native dry-run runners

- Create this standalone benchmark repository.
- Add reproducible Nix dev shell.
- Add manifests for validation, batch, single-file, and trajectory benchmark roles.
- Add native dry-run runners for static validation, batch throughput, trajectory validation, and trajectory throughput.
- Use `scripts/check_tools.py --profile minimal --dry-run` for tool preflight planning.
- Plan Phase 1 full reruns under `results/full_rerun/<run_id>/...` with `source_kind = 'full_rerun'`.
- Add a DuckDB schema plus import/export scripts for historical and refreshed validation results.
- Do not move historical result files or execute heavy benchmarks during scaffold review.

## Phase 2: single-file redesign and review

- Keep the 2,013-structure single-file benchmark out of Phase 1 native runners.
- Design a native single-file runner separately, preserving the curated sample and historical logs.
- Run scaffold and database smoke checks.
- Dry-run native Phase 1 command plans and review output layout, DB provenance labels, and archive naming.
- Import a tiny fixture into DuckDB and export validation summaries.

## Phase 3: controlled rerun

- Build or select `zsasa` v0.6.0.
- Run only the approved `zsasa` validation refresh.
- Preserve historical comparator columns.
- Write new outputs under ignored `results/`.
- Import refreshed `zsasa` columns into DuckDB using `source_kind = 'zsasa_v0.6.0_refresh'`.

## Phase 4: archive staging

- Copy selected generated CSVs, configs, logs, figures, DB exports, and environment reports into `archives/`.
- Add checksums and source manifests.
- Only then decide which artifacts should be published or cited by the paper repository.

## Phase 5: revision/full rerun

- Rerun comparator tools in the same harness when time permits.
- Re-import full-rerun results with `source_kind = 'full_rerun'`.
- Replace provisional performance comparisons that mixed historical and refreshed runs.
