# Trajectory validation rerun log

This log records the `zsasa` v0.6.0 MD trajectory validation refresh for
`5wvo_C_analysis`. The native MDTraj reference was not rerun; the historical
`mdtraj` reference column was reused from the existing validation CSVs.

## Result set

- Date: 2026-05-21 JST
- Result directory:
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/validation_md/zsasa_v0_6_0_5wvo_C_validation`
- Source repository: `/Users/nagaet/freesasa-zig`
- Source revision: `v0.6.0` / `94fdc1ee0ba27063d7cfe69e915e8425474316e1`
- Historical reference directory:
  `/Users/nagaet/freesasa-zig/benchmarks/results/validation_md/5wvo_C_analysis`
- Dataset: `5wvo_C_analysis`
- Atoms: 3,858
- Frames: 1,001
- n_points: 100, 200, 500, 1000
- Threads: 10
- Stride: 1
- Native MDTraj rerun: no

## Command

```bash
./scripts/refresh_validation_md.py \
  --zsasa-root /Users/nagaet/freesasa-zig \
  --historical-dir /Users/nagaet/freesasa-zig/benchmarks/results/validation_md/5wvo_C_analysis \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C_R1.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C.pdb \
  --name zsasa_v0_6_0_5wvo_C_validation \
  --n-points 100,200,500,1000 \
  --stride 1 \
  --threads 10 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/validation_md/zsasa_v0_6_0_5wvo_C_validation
```

## Summary

| n_points | tool | R² | ΔR² | mean error % | max error % |
| ---: | --- | ---: | ---: | ---: | ---: |
| 100 | `zsasa_mdtraj` | 0.985626 | 0.894791 | 0.9456 | 1.9019 |
| 100 | `zsasa_mdanalysis` | 0.984656 | 0.897937 | 0.3782 | 1.6966 |
| 100 | `zsasa_cli_f64` | 0.978922 | 0.859744 | 1.2696 | 2.6611 |
| 100 | `zsasa_cli_f32` | 0.978925 | 0.859776 | 1.2697 | 2.6612 |
| 100 | `zsasa_cli_bitmask_f64` | 0.977626 | 0.851534 | 2.9970 | 4.2952 |
| 100 | `zsasa_cli_bitmask_f32` | 0.977647 | 0.851500 | 2.9973 | 4.2954 |
| 200 | `zsasa_mdtraj` | 0.993893 | 0.953215 | 0.4677 | 1.2194 |
| 200 | `zsasa_mdanalysis` | 0.992324 | 0.948809 | 0.2444 | 0.9755 |
| 200 | `zsasa_cli_f64` | 0.988952 | 0.927331 | 0.7812 | 1.6721 |
| 200 | `zsasa_cli_f32` | 0.988954 | 0.927326 | 0.7813 | 1.6722 |
| 200 | `zsasa_cli_bitmask_f64` | 0.988114 | 0.923837 | 2.4181 | 3.2872 |
| 200 | `zsasa_cli_bitmask_f32` | 0.988120 | 0.923822 | 2.4180 | 3.2873 |
| 500 | `zsasa_mdtraj` | 0.998681 | 0.989566 | 0.1977 | 0.5307 |
| 500 | `zsasa_mdanalysis` | 0.996991 | 0.981963 | 0.4449 | 1.0040 |
| 500 | `zsasa_cli_f64` | 0.993304 | 0.960503 | 0.5159 | 1.2676 |
| 500 | `zsasa_cli_f32` | 0.993305 | 0.960500 | 0.5157 | 1.2674 |
| 500 | `zsasa_cli_bitmask_f64` | 0.992814 | 0.958053 | 2.2140 | 2.8990 |
| 500 | `zsasa_cli_bitmask_f32` | 0.992829 | 0.958061 | 2.2138 | 2.8990 |
| 1000 | `zsasa_mdtraj` | 0.999539 | 0.996260 | 0.0998 | 0.2880 |
| 1000 | `zsasa_mdanalysis` | 0.997858 | 0.988574 | 0.5437 | 0.8892 |
| 1000 | `zsasa_cli_f64` | 0.994519 | 0.968812 | 0.4163 | 1.0291 |
| 1000 | `zsasa_cli_f32` | 0.994519 | 0.968810 | 0.4163 | 1.0291 |
| 1000 | `zsasa_cli_bitmask_f64` | 0.993729 | 0.964953 | 2.1027 | 2.7307 |
| 1000 | `zsasa_cli_bitmask_f32` | 0.993739 | 0.964932 | 2.1025 | 2.7256 |

## Notes

- `mdtraj.shrake_rupley` was not rerun; the `mdtraj` column was copied from the historical validation CSVs.
- Standard `zsasa_mdtraj` converges strongly with n_points and reaches R² = 0.999539 at 1000 points.
- CLI f64/f32 are nearly identical for this validation, as expected.
- Bitmask variants track frame-to-frame changes well but retain a larger absolute offset, consistent with the LUT approximation behavior.
