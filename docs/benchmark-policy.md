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
