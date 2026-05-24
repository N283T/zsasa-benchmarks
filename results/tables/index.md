# Benchmark summary tables

CSV tables generated from `results/benchmark.duckdb` for reporting and manuscript/table drafting.

| file | rows | description |
| --- | ---: | --- |
| `batch_t10_summary.csv` | 16 | 10-thread batch performance table, including runtime/RSS ratios versus comparators. |
| `batch_thread_scaling.csv` | 40 | Batch runtime, throughput, RSS, speedup, and efficiency across thread counts. |
| `best_by_context.csv` | 39 | Fastest/highest-throughput/lowest-RSS winners by benchmark context. |
| `comparator_ratios.csv` | 252 | Long-format runtime and RSS ratios used by the comparator-ratio figures. |
| `datasets.csv` | 6 | Dataset metadata copied from the benchmark database. |
| `md_summary.csv` | 25 | Trajectory/MD performance summary with runtime/RSS ratios versus available comparators. |
| `runs_long.csv` | 327 | One row per benchmark run with raw hyperfine-style statistics and common derived metrics. |
| `single_file_t10_summary.csv` | 48 | 10-thread single-file performance by structure and variant. |
| `single_file_thread_scaling.csv` | 192 | Single-file runtime, RSS, speedup, and efficiency across thread counts. |
| `tools.csv` | 14 | Tool metadata copied from the benchmark database. |
| `validation_pairwise_summary.csv` | 59 | Pairwise SASA agreement against FreeSASA/MDTraj references. |

Notes:
- Runtime ratios are `comparator runtime / variant runtime`; higher is faster than the comparator.
- RSS ratios are `comparator peak RSS / variant peak RSS`; higher uses less memory than the comparator.
- CPU utilization proxy is `(user_time + system_time) / wall_time`.
