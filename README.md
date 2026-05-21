# zsasa-benchmarks

Release-fixed benchmark and validation harness for the `zsasa` manuscript.

This repository is a clean benchmark workspace split out from the historical benchmark tree in `/Users/nagaet/freesasa-zig`. It intentionally starts without copied result files. Existing comparator results can be reused as baselines for the first archive/preprint, while `zsasa` itself is refreshed from a fixed release.

## Policy for the first archive/preprint

- Reuse existing FreeSASA/RustSASA/Lahuta comparator outputs where they are already present and documented.
- Rerun `zsasa` from the fixed `v0.6.0` release for validation refreshes.
- Do not rerun heavy speed benchmarks or comparator tools until the benchmark scope is explicitly approved.
- Keep generated results out of git; archive final outputs separately after review.

## Quick start

```bash
nix develop
python scripts/check_scaffold.py
python scripts/report_existing_assets.py --zsasa-repo /Users/nagaet/freesasa-zig
python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --dry-run
```

`refresh_validation.py` defaults to dry-run behavior. It prints the `zsasa` commands that would be run and does not execute benchmarks unless `--execute` is passed.

## Repository layout

```text
config/      pinned tool/version policy
manifests/   dataset and baseline manifests; no raw data
scripts/     benchmark orchestration and scaffold checks
docs/        migration notes and benchmark policy
results/     ignored generated benchmark outputs
archives/    ignored final archive staging area
```

## Historical source tree

The historical benchmark assets currently live in:

```text
/Users/nagaet/freesasa-zig/benchmarks
```

Result migration is intentionally deferred. See `docs/migration-plan.md`.
