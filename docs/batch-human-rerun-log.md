# Human batch rerun log

This log records the `zsasa`-only human proteome batch-throughput refresh.
Comparator tools were not rerun.

## Result set

- Date: 2026-05-21 JST
- Result directory:
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_human_t10`
- Source repository: `/Users/nagaet/freesasa-zig`
- Source revision: `v0.6.0` / `94fdc1ee0ba27063d7cfe69e915e8425474316e1`
- Dataset: `/Users/nagaet/pdb/afdb/UP000005640_9606_HUMAN_v6/pdb`
- Input count: 23,586 PDB files
- Tools rerun: `zig`, `zig_bitmask`
- Comparator tools rerun: no
- Points: 128
- Threads: 10
- Precisions: f64, f32
- Warmup: 3
- Runs: 10
- Hyperfine prepare: `sync`

## Summary

| Variant | Precision | Threads | Mean (s) | Stddev (s) | Median (s) | Files/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| standard | f64 | 10 | 44.574 | 1.039 | 44.213 | 529 |
| standard | f32 | 10 | 42.991 | 0.557 | 42.777 | 549 |
| bitmask | f64 | 10 | 14.145 | 0.588 | 13.741 | 1,667 |
| bitmask | f32 | 10 | 14.196 | 0.067 | 14.187 | 1,661 |

## Comparison note

Compared with the historical `human_t10` baseline, the refreshed standard-mode
10-thread timings are about 5--8% slower, `f32` bitmask is about 1% slower, and
`f64` bitmask is about 5% faster. Compared with the older `human` baseline, the
refreshed `zsasa` timings are faster across all four `zsasa` outputs.

The later repetitions in `bench_zsasa_f64_10t.json` and
`bench_zsasa_f64_bitmask_10t.json` are slower than the early repetitions, so
thermal or background-state effects may be visible. The result is kept as the
first controlled human t10 refresh; comparator timings remain provisional until
a same-harness full rerun is performed.
