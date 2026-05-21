# Single-file representative subset plan

This note records a curated subset plan for the historical 2,013-structure
single-file benchmark. The initial archive/preprint does not need to rerun the
full 2,013-structure benchmark; a small representative subset is enough to show
single-file behavior while the manuscript focuses on batch and trajectory
workloads.

## Historical source

- Dataset: `/Users/nagaet/freesasa-zig/benchmarks/dataset/pdb`
- Count: 2,013 PDB files
- Historical results: `/Users/nagaet/freesasa-zig/benchmarks/results/single/100`
- Atom counts and historical timings are already available in the historical
  `timing.csv` and `results.csv` files.
- Lahuta is not part of this single-file historical set because the historical
  Lahuta comparison was AFDB-only.

## Dataset composition

The historical sample is effectively two regimes:

| Source | Count | Chain profile | Atom range |
| --- | ---: | --- | --- |
| AFDB | 1,082 | single-chain | 122--21,611 atoms |
| PDB | 931 | mostly multi-chain cryo-EM / large assemblies | 20,049--4,506,416 atoms |

This means medium multi-chain structures are not common in the usual small
protein sense. The smallest PDB multi-chain cases are already around 20k atoms.

## Proposed subset

| Structure | Source | Atoms | Chains | Role |
| --- | --- | ---: | ---: | --- |
| `af-o00175-f1-model_v6` | AFDB | 917 | 1 | small single-chain AFDB |
| `af-a8mxt2-f1-model_v6` | AFDB | 2,642 | 1 | median single-chain AFDB |
| `af-q6zuj8-f1-model_v6` | AFDB | 6,350 | 1 | large single-chain AFDB |
| `af-q6zs30-f1-model_v6` | AFDB | 21,611 | 1 | maximum single-chain AFDB |
| `9mih` | PDB | 20,049 | 14 | lower-bound PDB multi-chain EM |
| `3jc8` | PDB | 107,500 | 3 | median-size PDB multi-chain EM |
| `7qoi` | PDB | 310,182 | 4 | large PDB multi-chain EM |
| `9mog` | PDB | 652,111 | 9 | very large PDB multi-chain EM |
| `9fqr` | PDB | 4,506,416 | 57 | maximum structure; FreeSASA absolute parse-time outlier |
| `5vyc` | PDB | 249,168 | 4 | RustSASA parse-time outlier maximum |
| `8fon` | PDB | 93,062 | 2 | smaller two-chain RustSASA parse-time outlier |
| `8rbs` | PDB | 164,605 | 5 | FreeSASA total-runtime outlier versus zsasa |

## Historical parser/runtime signals

| Structure | FreeSASA parse (ms) | RustSASA parse (ms) | zsasa f64 parse (ms) | FreeSASA total (s) | RustSASA total (s) | zsasa f64 total (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `9fqr` | 3,402.17 | 1,849.83 | 640.94 | 181.490 | 8.965 | 4.933 |
| `5vyc` | 203.73 | 13,253.40 | 37.46 | 0.598 | 13.655 | 0.236 |
| `8fon` | 75.45 | 4,671.63 | 13.09 | 0.228 | 4.764 | 0.090 |
| `8rbs` | 127.89 | 73.54 | 21.98 | 24.007 | 0.239 | 0.121 |

The subset intentionally includes parser-heavy and comparator-pathological
cases because a clean, fast parser is part of the `zsasa` value proposition for
large single-file structures.

## Rerun policy

For the first archive/preprint refresh:

1. Rerun only `zsasa` variants for this subset at `n_points = 100`.
2. Reuse historical FreeSASA and RustSASA values as comparator baselines.
3. Keep the full 2,013-structure benchmark as a historical broad benchmark.
4. If reviewers ask for a same-harness broad rerun, rerun all tools later.
