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
