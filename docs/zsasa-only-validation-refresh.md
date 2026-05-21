# zsasa-only validation refresh

The historical validation script reruns FreeSASA before `zsasa`. That is not the desired first archive/preprint workflow because the existing FreeSASA baseline is already available and FreeSASA itself is not changing.

The replacement workflow is:

1. Read historical E. coli validation CSVs.
2. Preserve comparator columns such as `freesasa`, `rustsasa`, and `lahuta_bitmask`.
3. Rerun only `zsasa` variants from the fixed release.
4. Merge refreshed `zsasa_*` columns into new CSVs.
5. Write outputs to a new ignored result directory.

Dry run:

```bash
uv run python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --dry-run
```

Actual execution requires explicit approval and then:

```bash
uv run python scripts/refresh_validation.py --manifest manifests/validation-ecoli.toml --execute
```


After an approved `zsasa` refresh has written new CSVs, import the refreshed `zsasa` columns into DuckDB with explicit provenance:

```bash
uv run python scripts/import_validation_csv.py \
  --manifest manifests/validation-ecoli.toml \
  --baseline-dir results/validation/zsasa_v0_6_0_ecoli \
  --tools zsasa \
  --source-kind zsasa_v0.6.0_refresh
```

For the initial archive, import historical comparator baselines separately:

```bash
uv run python scripts/import_validation_csv.py \
  --manifest manifests/validation-ecoli.toml \
  --tools comparators \
  --source-kind historical_baseline
```
