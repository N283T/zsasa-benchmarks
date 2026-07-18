# Draft captions for STORY figures

These captions are manuscript-oriented drafts. They define the comparison, fixed conditions, reference direction, and uncertainty display so that the corresponding figures can remain visually concise.

## Static validation

### [zsasa and FreeSASA agreement](validation/png/static_sr_standard_and_bitmask_vs_freesasa_1024p.png)

**Caption.** Agreement between zsasa and FreeSASA for 4,370 static structures. Total solvent-accessible surface area (SASA) calculated with (a) zsasa f64 and (b) zsasa bitmask f32 at 1,024 sphere points is plotted against the FreeSASA result. The dashed line denotes identity. Insets report the number of structures, the coefficient of determination, and the mean and maximum relative differences.

### [Bitmask difference across sphere-point counts](validation/png/static_sr_bitmask_f32_error_vs_points.png)

**Caption.** Signed relative difference between zsasa bitmask f32 and FreeSASA as a function of sphere-point count for 4,370 static structures. The line shows the median and the shaded band spans the 5th–95th percentiles. Negative values indicate lower total SASA from zsasa than from FreeSASA.

### [Bitmask quantization correction](validation/png/static_sr_bitmask_correction_vs_points.png)

**Caption.** Effect of the bitmask quantization-correction option on the signed relative difference from FreeSASA for 4,370 static structures. Lines show medians and shaded bands show the 5th–95th percentiles. The current correction changes the direction of the median bias but does not eliminate the difference.

## Molecular-dynamics validation

### [zsasa and MDTraj convergence](validation/png/md_standard_f64_convergence_vs_mdtraj.png)

**Caption.** Signed relative difference between zsasa f64 and MDTraj across 1,001 trajectory frames as a function of sphere-point count. The line shows the median and the shaded band spans the 5th–95th percentiles. The distribution moves toward zero as the sphere-point count increases.

### [Bitmask correction across points and frames](validation/png/md_bitmask_correction_vs_standard.png)

**Caption.** Raw and corrected zsasa bitmask f32 results relative to zsasa f32 across 1,001 trajectory frames. (a) Median signed relative differences and 5th–95th percentile bands across sphere-point counts. (b) Frame-wise signed relative differences at 1,024 sphere points. The same colors and line styles identify the raw and corrected modes in both panels.

## E. coli AFDB batch benchmark

### [Throughput scaling](batch_ecoli/png/ecoli_throughput_scaling_story.png)

**Caption.** Batch throughput for 4,370 E. coli AFDB structures as a function of thread count. zsasa f64 and zsasa bitmask f32 represent the higher- and lower-accuracy zsasa configurations, respectively, and are compared with FreeSASA batch, RustSASA, and Lahuta bitmask. Points show three-run means and error bars show standard deviations; all calculations used 128 sphere points.

### [Performance and memory](batch_ecoli/png/ecoli_performance_memory_story.png)

**Caption.** Throughput–memory trade-off for the E. coli AFDB batch benchmark at 10 threads and 128 sphere points. Each marker shows the three-run mean throughput and peak resident set size (RSS) for 4,370 structures. Higher and further left indicate greater throughput and lower peak memory, respectively.

### [Throughput ratios against comparators](batch_ecoli/png/ecoli_t10_runtime_speedup_vs_comparators.png)

**Caption.** Throughput ratios of zsasa f64 and zsasa bitmask f32 to three external comparators for 4,370 E. coli AFDB structures at 10 threads and 128 sphere points. Ratios were calculated from three-run mean runtimes; values above 1 indicate higher throughput for zsasa. The horizontal reference line denotes equal throughput.

### [Peak RSS ratios against comparators](batch_ecoli/png/ecoli_t10_rss_reduction_vs_comparators.png)

**Caption.** Peak RSS ratios of the external comparators to zsasa f64 and zsasa bitmask f32 for the E. coli AFDB batch benchmark. Ratios were calculated from three-run mean peak RSS values at 10 threads and 128 sphere points; values above 1 indicate lower peak memory for zsasa. The horizontal reference line denotes equal peak RSS.

## Human AFDB mmCIF batch benchmark

### [Ranking and performance recovery](batch_human_cif/png/human_cif_ranking_recovery_story.png)

**Caption.** Effect of input format, parser path, and input I/O on the zsasa–Lahuta throughput comparison for 23,586 Human AFDB structures. (a) Ratio of zsasa bitmask f32 throughput to Lahuta bitmask throughput for PDB input and for mmCIF input with the generic parser and memory mapping; values above 1 favor zsasa. Ratio error bars were propagated from the throughput standard deviations. (b) mmCIF throughput of the generic and AF-fast parser paths with memory-mapped and read-all input. The vertical purple line marks Lahuta bitmask throughput. Points show three-run means and error bars show standard deviations; zsasa calculations used 10 threads and 128 sphere points.

### [AF-fast thread overcommit](batch_human_cif/png/human_cif_af_fast_overcommit_tradeoff.png)

**Caption.** Throughput and memory behavior of the zsasa AF-fast mmCIF path under thread overcommit on a system with 10 logical CPUs. (a) Throughput change relative to 10 threads for read-all and memory-mapped input. (b) Peak RSS over the same 10–40-thread range. Points show three-run means; error bars show propagated standard deviations in panel (a) and standard deviations in panel (b). All calculations used zsasa bitmask f32 with 128 sphere points on 23,586 Human AFDB structures.

## Human AFDB PDB batch benchmark

### [Performance and memory](batch_human/png/human_t10_throughput_vs_peak_rss.png)

**Caption.** Throughput–memory trade-off for 23,586 Human AFDB PDB structures at 10 threads and 128 sphere points. Each marker shows the three-run mean throughput and peak RSS. Higher and further left indicate greater throughput and lower peak memory, respectively.

### [Throughput ratios against comparators](batch_human/png/human_t10_runtime_speedup_vs_comparators.png)

**Caption.** Throughput ratios of zsasa f64 and zsasa bitmask f32 to FreeSASA batch, RustSASA, and Lahuta bitmask for 23,586 Human AFDB PDB structures at 10 threads and 128 sphere points. Ratios were calculated from three-run mean runtimes; values above 1 indicate higher throughput for zsasa. The horizontal reference line denotes equal throughput.

### [Peak RSS ratios against comparators](batch_human/png/human_t10_rss_reduction_vs_comparators.png)

**Caption.** Peak RSS ratios of FreeSASA batch, RustSASA, and Lahuta bitmask to zsasa f64 and zsasa bitmask f32 for the Human AFDB PDB batch benchmark. Ratios were calculated from three-run mean peak RSS values at 10 threads and 128 sphere points; values above 1 indicate lower peak memory for zsasa. The horizontal reference line denotes equal peak RSS.
