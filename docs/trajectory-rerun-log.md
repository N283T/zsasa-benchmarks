# Trajectory rerun log

This log records the `zsasa` v0.6.0 trajectory refresh. The refresh reran zsasa CLI paths for all three trajectory datasets and reran zsasa Python wrapper paths for the two 1K-frame datasets. External comparators were not rerun.

## Result set

- Date: 2026-05-21 JST
- Base result directory: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_refresh`
- Source repository: `/Users/nagaet/freesasa-zig`
- Source revision: `v0.6.0` / `94fdc1ee0ba27063d7cfe69e915e8425474316e1`
- Points: 100
- Threads: 10
- Stride: 1
- Warmup: 1
- Runs: 3
- Hyperfine prepare: `sync`
- External comparators rerun: no (`mdtraj` and `mdsasa_bolt` remain historical baselines)

## Dataset scope

| Dataset | Atoms | Frames | Rerun tools |
| --- | ---: | ---: | --- |
| `5wvo_C_analysis` | 3,858 | 1,001 | CLI + zsasa Python wrappers |
| `6sup_A_analysis` | 33,377 | 1,001 | CLI + zsasa Python wrappers |
| `5vz0_A_protein` | 17,910 | 10,001 | CLI only |

## Summary

| Dataset | Tool | Mean (s) | Stddev (s) | Median (s) | FPS | RSS (MiB) | vs historical |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `5wvo_C_analysis` | CLI standard f64 | 1.726 | 0.007 | 1.727 | 579.8 | 15.4 | -2.2% |
| `5wvo_C_analysis` | CLI standard f32 | 1.681 | 0.010 | 1.684 | 595.6 | 14.8 | -0.5% |
| `5wvo_C_analysis` | CLI bitmask f64 | 0.796 | 0.001 | 0.795 | 1257.3 | 18.0 | +0.4% |
| `5wvo_C_analysis` | CLI bitmask f32 | 0.782 | 0.001 | 0.782 | 1280.3 | 17.1 | +0.9% |
| `5wvo_C_analysis` | Python MDTraj standard | 1.741 | 0.030 | 1.724 | 574.9 | 202.3 | +6.3% |
| `5wvo_C_analysis` | Python MDTraj bitmask | 0.874 | 0.048 | 0.848 | 1144.7 | 200.7 | -0.0% |
| `5wvo_C_analysis` | Python MDAnalysis standard | 2.097 | 0.005 | 2.100 | 477.3 | 167.3 | +5.7% |
| `5wvo_C_analysis` | Python MDAnalysis bitmask | 1.253 | 0.003 | 1.252 | 798.8 | 167.5 | +4.8% |
| `6sup_A_analysis` | CLI standard f64 | 15.260 | 0.102 | 15.300 | 65.6 | 119.1 | -3.4% |
| `6sup_A_analysis` | CLI standard f32 | 14.767 | 0.037 | 14.752 | 67.8 | 114.2 | -0.1% |
| `6sup_A_analysis` | CLI bitmask f64 | 6.985 | 0.018 | 6.990 | 143.3 | 123.2 | -2.4% |
| `6sup_A_analysis` | CLI bitmask f32 | 6.830 | 0.010 | 6.833 | 146.6 | 116.0 | -1.3% |
| `6sup_A_analysis` | Python MDTraj standard | 15.000 | 0.140 | 15.005 | 66.7 | 1260.0 | -3.8% |
| `6sup_A_analysis` | Python MDTraj bitmask | 6.724 | 0.043 | 6.723 | 148.9 | 1266.7 | -7.9% |
| `6sup_A_analysis` | Python MDAnalysis standard | 15.204 | 0.082 | 15.188 | 65.8 | 740.9 | -11.1% |
| `6sup_A_analysis` | Python MDAnalysis bitmask | 7.226 | 0.004 | 7.227 | 138.5 | 743.5 | -6.2% |
| `5vz0_A_protein` | CLI standard f64 | 82.144 | 0.175 | 82.176 | 121.7 | 65.4 | -4.6% |
| `5vz0_A_protein` | CLI standard f32 | 79.800 | 0.056 | 79.799 | 125.3 | 62.7 | -3.4% |
| `5vz0_A_protein` | CLI bitmask f64 | 38.351 | 0.036 | 38.368 | 260.8 | 68.5 | -1.6% |
| `5vz0_A_protein` | CLI bitmask f32 | 37.388 | 0.083 | 37.406 | 267.5 | 64.6 | -1.7% |

## Notes

- `5vz0_A_protein` was intentionally kept CLI only because it is the 10K-frame large trajectory benchmark and Python-wrapper runs are heavier.
- The refreshed CLI results are broadly consistent with historical timings and are mostly slightly faster on this environment.
- The 6sup Python-wrapper results are also faster than historical baselines, while the 5wvo Python-wrapper standard paths are slightly slower; these differences are acceptable for the initial archive refresh but should be treated as environment-sensitive.
- External comparator ratios should remain provisional until `mdtraj` and `mdsasa_bolt` are rerun in the same harness.
