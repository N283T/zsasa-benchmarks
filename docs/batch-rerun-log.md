# Batch rerun log

This log records the first `zsasa`-only E. coli batch-throughput refresh.
Comparator tools were not rerun.

## Result set

- Date: 2026-05-21 JST
- Result directory:
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_scaling`
- Source repository: `/Users/nagaet/freesasa-zig`
- Source revision: `v0.6.0` / `94fdc1ee0ba27063d7cfe69e915e8425474316e1`
- Dataset: `/Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb`
- Input count: 4,370 PDB files
- Tools rerun: `zig`, `zig_bitmask`
- Comparator tools rerun: no
- Points: 128
- Threads: 1, 2, 4, 8, 10
- Precisions: f64, f32
- Warmup: 3
- Runs: 3
- Hyperfine prepare: `sync`

## Provenance notes

The output directory was populated by multiple `bench_batch.py` invocations.
The generated `config.json` was normalized by hand afterward so that it
describes the complete merged result set rather than only the final single
invocation.

Run sequence:

1. Initial scaling run produced threads 1, 8, and 10 for `zig` and
   `zig_bitmask` in f64 and f32.
2. A second scaling run added threads 2 and 4 for `zig` and `zig_bitmask` in
   f64 and f32.
3. `bench_zsasa_f64_2t.json` was rerun after one timing outlier was observed in
   the first 2-thread f64 standard result. The final rerun has no comparable
   outlier.

## Summary

| Variant | Precision | Threads | Mean (s) | Stddev (s) | Files/s |
| --- | --- | ---: | ---: | ---: | ---: |
| standard | f64 | 1 | 29.457 | 0.010 | 148 |
| standard | f64 | 2 | 14.898 | 0.009 | 293 |
| standard | f64 | 4 | 7.952 | 0.007 | 550 |
| standard | f64 | 8 | 4.975 | 0.059 | 878 |
| standard | f64 | 10 | 4.340 | 0.036 | 1,007 |
| standard | f32 | 1 | 28.855 | 0.143 | 151 |
| standard | f32 | 2 | 14.535 | 0.020 | 301 |
| standard | f32 | 4 | 7.715 | 0.013 | 566 |
| standard | f32 | 8 | 4.851 | 0.042 | 901 |
| standard | f32 | 10 | 4.247 | 0.037 | 1,029 |
| bitmask | f64 | 1 | 10.116 | 0.008 | 432 |
| bitmask | f64 | 2 | 5.139 | 0.023 | 850 |
| bitmask | f64 | 4 | 2.603 | 0.022 | 1,679 |
| bitmask | f64 | 8 | 1.655 | 0.014 | 2,641 |
| bitmask | f64 | 10 | 1.478 | 0.055 | 2,957 |
| bitmask | f32 | 1 | 10.063 | 0.036 | 434 |
| bitmask | f32 | 2 | 5.101 | 0.027 | 857 |
| bitmask | f32 | 4 | 2.568 | 0.030 | 1,701 |
| bitmask | f32 | 8 | 1.633 | 0.025 | 2,676 |
| bitmask | f32 | 10 | 1.464 | 0.016 | 2,984 |

## Comparison note

Against the historical `/Users/nagaet/freesasa-zig/benchmarks/results/batch/128/ecoli_t10`
baseline, the refreshed 10-thread timings are approximately 3--6% slower for
`zsasa` and `zsasa_bitmask`. This is close enough for the initial archive
refresh, but performance comparisons remain provisional until comparator tools
are rerun in the same harness.
