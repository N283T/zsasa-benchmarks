# Benchmark figure index

Exploratory figures generated from `results/benchmark.duckdb` in PNG/SVG/PDF formats.

[Open the filterable figure gallery](gallery.html).

[Open the draft STORY figure captions](story-captions.md).

## Sections

| section | png_figures |
| --- | --- |
| [Overview summaries](overview/index.md) | 3 |
| [Validation](validation/index.md) | 101 |
| [E. coli batch](batch_ecoli/index.md) | 15 |
| [Human batch](batch_human/index.md) | 8 |
| [Batch t10 comparison](batch_t10_comparison/index.md) | 3 |
| [MD / trajectory](md/index.md) | 19 |
| [batch_human_cif](batch_human_cif/index.md) | 10 |
| [batch_swissprot](batch_swissprot/index.md) | 1 |
| [single_file](single_file/index.md) | 14 |

## Database contents

| benchmark_kind | runs | datasets |
| --- | --- | --- |
| batch | 275 | 5 |
| single_file | 1016 | 2 |
| trajectory | 407 | 3 |
| trajectory_validation | 178 | 1 |
| validation | 146 | 1 |

## Performance metrics in DB

| metric | rows | runs |
| --- | --- | --- |
| parse_time | 1016 | 1016 |
| peak_rss | 13520 | 1698 |
| runtime | 13488 | 1698 |
| sasa_time | 1016 | 1016 |
| system_time | 1698 | 1698 |
| total_time | 1016 | 1016 |
| user_time | 1698 | 1698 |

## Quick winners

### Batch at 10 threads

| dataset | best_throughput | structures_per_sec | lowest_rss | rss_mib |
| --- | --- | --- | --- | --- |
| E. coli | zsasa bitmask f32 | 2863.6 | zsasa f32 | 52.1 |
| Human | zsasa bitmask f32 | 1643.7 | zsasa f32 | 91.3 |

### MD / trajectory

| dataset | best_throughput | frames_per_sec | lowest_rss | rss_mib |
| --- | --- | --- | --- | --- |
| 5wvo_C (1,001 frames, 3,858 atoms) | zsasa CLI bitmask f32 | 1176.7 | zsasa CLI f32 | 25.3 |
| 6sup_A (1,001 frames, 33,377 atoms) | zsasa CLI bitmask f32 | 143.7 | zsasa CLI f32 | 136.0 |
| 5vz0_A (10,001 frames, 17,910 atoms) | zsasa CLI bitmask f32 | 265.5 | zsasa CLI bitmask f32 | 81.4 |

## Representative figures

### Validation static scatter

![Validation static scatter](validation/png/static_sr_scatter_grid.png)

### Validation MD scatter

![Validation MD scatter](validation/png/md_scatter_grid.png)

### E. coli throughput

![E. coli throughput](batch_ecoli/png/ecoli_throughput_vs_threads.png)

### Human t10 throughput

![Human t10 throughput](batch_human/png/human_t10_throughput_bar.png)

### Batch t10 size comparison

![Batch t10 size comparison](batch_t10_comparison/png/t10_ms_per_structure_ecoli_human.png)

### MD throughput vs RSS

![MD throughput vs RSS](md/png/md_throughput_vs_peak_rss_logx_grid.png)

### Batch speedup overview

![Batch speedup overview](overview/png/batch_t10_speedup_vs_freesasa.png)

### MD speedup overview

![MD speedup overview](overview/png/md_speedup_vs_mdtraj_grid.png)
