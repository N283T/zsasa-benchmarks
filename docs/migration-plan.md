# Migration plan

## Phase 1: scaffold only

- Create this standalone benchmark repository.
- Add reproducible Nix dev shell.
- Add manifests for validation, batch, single-file, and trajectory benchmark roles.
- Add a `zsasa`-only validation refresh script that reuses existing comparator CSVs.
- Do not move historical result files.

## Phase 2: dry-run and review

- Run scaffold checks.
- Dry-run the validation refresh command plan.
- Confirm dataset paths, output layout, and archive naming.

## Phase 3: controlled rerun

- Build or select `zsasa` v0.6.0.
- Run only the approved `zsasa` validation refresh.
- Preserve historical comparator columns.
- Write new outputs under ignored `results/`.

## Phase 4: archive staging

- Copy selected generated CSVs, configs, logs, figures, and environment reports into `archives/`.
- Add checksums and source manifests.
- Only then decide which artifacts should be published or cited by the paper repository.
