# Benchmark summary tables

CSV tables generated from `results/benchmark.duckdb` for reporting and manuscript/table drafting.

| file | rows | description |
| --- | ---: | --- |
| `batch_t10_summary.csv` | 25 | 10-thread batch performance table, including runtime/RSS ratios versus comparators. |
| `batch_thread_scaling.csv` | 75 | Batch runtime, throughput, RSS, speedup, and efficiency across thread counts. |
| `best_by_context.csv` | 69 | Fastest/highest-throughput/lowest-RSS winners by benchmark context. |
| `comparator_ratios.csv` | 506 | Long-format runtime and RSS ratios used by the comparator-ratio figures. |
| `datasets.csv` | 10 | Dataset metadata copied from the benchmark database. |
| `md_summary.csv` | 25 | Trajectory/MD performance summary with runtime/RSS ratios versus available comparators. |
| `md_thread_scaling.csv` | 108 | Native zsasa trajectory scaling at 10/20/40 workers, with LUT and correction options. |
| `runs_long.csv` | 1297 | One row per benchmark run with raw hyperfine-style statistics and common derived metrics. |
| `single_file_t10_summary.csv` | 110 | 10-thread single-file performance by structure and variant. |
| `single_file_thread_scaling.csv` | 440 | Single-file runtime, RSS, speedup, and efficiency across thread counts. |
| `tools.csv` | 18 | Tool metadata copied from the benchmark database. |
| `validation_pairwise_summary.csv` | 115 | Pairwise SASA agreement against FreeSASA/MDTraj references. |

Notes:
- Runtime ratios are `comparator runtime / variant runtime`; higher is faster than the comparator.
- RSS ratios are `comparator peak RSS / variant peak RSS`; higher uses less memory than the comparator.
- CPU utilization proxy is `(user_time + system_time) / wall_time`.
