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

## Molecular-dynamics performance

### [Trajectory throughput and memory](md/png/md_performance_memory_story.png)

**Caption.** Throughput–memory trade-offs for three trajectories at 10 threads and 128 sphere points. Native zsasa f64 and zsasa bitmask f32 are shown with zsasa Python integrations and available external tools. Points show three-run means, and error bars show standard deviations for throughput and peak resident set size (RSS). Each panel title states the trajectory length and atom count.

### [Native thread overcommit](md/png/md_zsasa_performance_memory_detail.png)

**Caption.** Throughput and peak RSS of native zsasa f64 and corrected zsasa bitmask f32 on the 5vz0_A trajectory over 10, 20, and 40 threads. The benchmark system had 10 logical CPUs. Points show three-run means and error bars show standard deviations. All calculations used 128 sphere points.

### [Bitmask accuracy and throughput](md/png/md_correction_accuracy_throughput_story.png)

**Caption.** Accuracy–throughput trade-off for zsasa f32 and raw or corrected zsasa bitmask f32 on the 5wvo_C trajectory at 128 sphere points and 10 threads. Horizontal positions show the mean absolute relative difference from zsasa f32, with intervals spanning the 5th–95th percentiles over 1,001 validation frames. Vertical positions show three-run mean throughput, with error bars showing standard deviations. Correction reduces the bitmask difference without a measurable throughput cost.

### [6sup_A comparison with external tools](md/png/md_6sup_comparator_ratios_story.png)

**Caption.** Relative performance of zsasa f64 and zsasa bitmask f32 against MDTraj and mdsasa-bolt for the 1,001-frame, 33,377-atom 6sup_A trajectory. (a) zsasa-to-comparator throughput ratios. (b) Comparator-to-zsasa peak RSS ratios, so values above 1 indicate lower peak memory for zsasa. Ratios use three-run means and error bars show propagated standard deviations. All calculations used 10 threads and 128 sphere points.

### [5vz0_A comparison with mdsasa-bolt](md/png/md_5vz0_comparator_ratios_story.png)

**Caption.** Relative performance of zsasa f64 and zsasa bitmask f32 against mdsasa-bolt for the 10,001-frame, 17,910-atom 5vz0_A trajectory. (a) zsasa-to-comparator throughput ratios. (b) Comparator-to-zsasa peak RSS ratios. Ratios use three-run means and error bars show propagated standard deviations. MDTraj was not measured for this trajectory. All calculations used 10 threads and 128 sphere points.

## E. coli AFDB batch benchmark

### [Throughput scaling](batch_ecoli/png/ecoli_throughput_scaling_story.png)

**Caption.** Batch throughput for 4,370 E. coli AFDB structures as a function of thread count. zsasa f64 and zsasa bitmask f32 represent the higher- and lower-accuracy zsasa configurations, respectively, and are compared with FreeSASA batch, RustSASA, and Lahuta bitmask. Points show three-run means and error bars show standard deviations; all calculations used 128 sphere points.

### [Performance and memory](batch_ecoli/png/ecoli_performance_memory_story.png)

**Caption.** Throughput–memory trade-off for the E. coli AFDB batch benchmark at 10 threads and 128 sphere points. Each marker shows the three-run mean throughput and peak resident set size (RSS) for 4,370 structures. Higher and further left indicate greater throughput and lower peak memory, respectively.

### [Throughput ratios against comparators](batch_ecoli/png/ecoli_t10_runtime_speedup_vs_comparators.png)

**Caption.** Throughput ratios of zsasa f64 and zsasa bitmask f32 to three external comparators for 4,370 E. coli AFDB structures at 10 threads and 128 sphere points. Ratios were calculated from three-run mean runtimes, and error bars show uncertainty propagated from the runtime standard deviations. Values above 1 indicate higher throughput for zsasa. The vertical reference line denotes equal throughput.

### [Peak RSS ratios against comparators](batch_ecoli/png/ecoli_t10_rss_reduction_vs_comparators.png)

**Caption.** Peak RSS ratios of the external comparators to zsasa f64 and zsasa bitmask f32 for the E. coli AFDB batch benchmark. Ratios were calculated from three-run mean peak RSS values at 10 threads and 128 sphere points, and error bars show uncertainty propagated from the peak RSS standard deviations. Values above 1 indicate lower peak memory for zsasa. The vertical reference line denotes equal peak RSS.

## Human AFDB mmCIF batch benchmark

### [Ranking and performance recovery](batch_human_cif/png/human_cif_ranking_recovery_story.png)

**Caption.** Effect of input format, parser path, and input I/O on the zsasa–Lahuta throughput comparison for 23,586 Human AFDB structures. (a) Ratio of zsasa bitmask f32 throughput to Lahuta bitmask throughput for PDB input and for mmCIF input with the generic parser and memory mapping; values above 1 favor zsasa. Ratio error bars were propagated from the throughput standard deviations. (b) mmCIF throughput of the generic and AF-fast parser paths with memory-mapped and read-all input. The vertical purple line marks Lahuta bitmask throughput. Points show three-run means and error bars show standard deviations; zsasa calculations used 10 threads and 128 sphere points.

### [AF-fast thread overcommit](batch_human_cif/png/human_cif_af_fast_overcommit_tradeoff.png)

**Caption.** Throughput and memory behavior of the zsasa AF-fast mmCIF path under thread overcommit on a system with 10 logical CPUs. (a) Throughput change relative to 10 threads for read-all and memory-mapped input. (b) Peak RSS over the same 10–40-thread range. Points show three-run means; error bars show propagated standard deviations in panel (a) and standard deviations in panel (b). All calculations used zsasa bitmask f32 with 128 sphere points on 23,586 Human AFDB structures.

## Human AFDB PDB batch benchmark

### [Performance and memory](batch_human/png/human_t10_throughput_vs_peak_rss.png)

**Caption.** Throughput–memory trade-off for 23,586 Human AFDB PDB structures at 10 threads and 128 sphere points. Each marker shows the three-run mean throughput and peak RSS. Higher and further left indicate greater throughput and lower peak memory, respectively.

### [Throughput ratios against comparators](batch_human/png/human_t10_runtime_speedup_vs_comparators.png)

**Caption.** Throughput ratios of zsasa f64 and zsasa bitmask f32 to FreeSASA batch, RustSASA, and Lahuta bitmask for 23,586 Human AFDB PDB structures at 10 threads and 128 sphere points. Ratios were calculated from three-run mean runtimes, and error bars show uncertainty propagated from the runtime standard deviations. Values above 1 indicate higher throughput for zsasa. The vertical reference line denotes equal throughput.

### [Peak RSS ratios against comparators](batch_human/png/human_t10_rss_reduction_vs_comparators.png)

**Caption.** Peak RSS ratios of FreeSASA batch, RustSASA, and Lahuta bitmask to zsasa f64 and zsasa bitmask f32 for the Human AFDB PDB batch benchmark. Ratios were calculated from three-run mean peak RSS values at 10 threads and 128 sphere points, and error bars show uncertainty propagated from the peak RSS standard deviations. Values above 1 indicate lower peak memory for zsasa. The vertical reference line denotes equal peak RSS.

## SwissProt AFDB batch benchmark

### [Thread overcommit performance and memory](batch_swissprot/png/swissprot_overcommit_performance_memory.png)

**Caption.** Observed throughput–memory paths for zsasa f32 and zsasa bitmask f32 over 10, 20, and 40 threads on 500,000 SwissProt AFDB structures. The Lahuta bitmask marker shows its 10-thread result. All calculations used 128 sphere points on a system with 10 logical CPUs. Each configuration was measured once, so the figure is a descriptive large-scale observation without uncertainty estimates.

## Single-file benchmark

### [PDB runtime across structure sizes](single_file/png/single_pdb_runtime_vs_atoms_story.png)

**Caption.** Full-process runtime for eight protein-only PDB inputs selected to span medium and large single chains, two-chain complexes, large assemblies, and known parser or runtime stress cases. Points show the median of three Hyperfine runs at 10 threads and 100 sphere points; error bars span the minimum and maximum. PDBTools.jl values include the full Julia wrapper invocation. zsasa f64 and PDBTools.jl were measured in the zsasa 0.9.0 rerun, whereas the unchanged FreeSASA and RustSASA PDB values are retained from the historical 0.6.0 benchmark suite.

### [Selected PDB component-timing cases](single_file/png/single_pdb_case_studies_story.png)

**Caption.** Parse and SASA component timing for four selected PDB inputs at 10 threads and 100 sphere points: (a) a large single-chain AlphaFold model, (b) the largest assembly in the subset, (c) the 8rbs FreeSASA coordinate-overflow case, and (d) the 5vyc RustSASA parser outlier. The 8rbs PDB coordinates exceed the fixed-width 8.3 field range and are misread by the pinned FreeSASA parser, producing pathological SASA setup time. Component timings are reported separately from full-process wall time; the PDBTools.jl timing phase represents warmed in-process execution and excludes Julia startup. FreeSASA and RustSASA PDB component values are retained from the historical 0.6.0 benchmark suite.

### [mmCIF runtime across structure sizes](single_file/png/single_mmcif_runtime_vs_atoms_si.png)

**Caption.** Supplementary single-file runtime comparison using mmCIF representations of the same eight-structure subset. Points show the median of three Hyperfine runs at 10 threads and 100 sphere points; error bars span the minimum and maximum. The mmCIF representation avoids PDB fixed-width coordinate overflow, and FreeSASA no longer shows the pathological 8rbs behavior. The 5vyc and 9fqr inputs were filtered to protein-only atom sets to match the PDB workloads, and stale assembly-generation metadata unsupported by the pinned FreeSASA parser was removed. FreeSASA was excluded for the two NVDA structures because it aborted without assigning atomic radii. PDBTools.jl values include the full Julia wrapper invocation.

### [Selected mmCIF component-timing cases](single_file/png/single_mmcif_case_studies_si.png)

**Caption.** Supplementary parse and SASA component timing for mmCIF representations of the four PDB case-study structures at 10 threads and 100 sphere points. The PDB-specific FreeSASA coordinate-overflow behavior for 8rbs and RustSASA parser outlier for 5vyc are absent, although mmCIF parsing contributes appreciably to runtime, particularly for the largest assembly. Titles report chain instances from the cleaned source structure. The corresponding PDB writer reuses its finite set of one-character chain identifiers across TER-delimited chain instances, so unique PDB chain-ID counts are smaller even though the atom and chain-instance workloads are aligned. The 5vyc and 9fqr mmCIF inputs were filtered to the same protein-only atom sets as their PDB counterparts. PDBTools.jl component timing represents warmed in-process execution and excludes Julia startup.
