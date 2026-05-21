# Migration plan

## Phase 1: scaffold only

- Create this standalone benchmark repository.
- Add reproducible Nix dev shell.
- Add manifests for validation, batch, single-file, and trajectory benchmark roles.
- Add a `zsasa`-only validation refresh script that reuses existing comparator CSVs.
- Add a DuckDB schema plus import/export scripts for historical and refreshed validation results.
- Do not move historical result files.

## Phase 2: dry-run and review

- Run scaffold and database smoke checks.
- Dry-run the validation refresh command plan.
- Import a tiny fixture into DuckDB and export validation summaries.
- Confirm dataset paths, output layout, DB provenance labels, and archive naming.

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
