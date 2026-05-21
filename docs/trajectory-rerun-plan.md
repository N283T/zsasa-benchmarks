# Trajectory benchmark rerun plan

This note fixes the first controlled trajectory rerun settings without executing
the benchmark. The goal is to refresh only the `zsasa` CLI timings for the
existing MD trajectory benchmark datasets while preserving historical Python
wrapper and comparator timings until a full same-harness rerun is approved.

## Scope

Rerun only:

- `zig`
- `zig_bitmask`
- f64 and f32
- 10 threads
- 100 Shrake--Rupley test points

Do not rerun for the first archive/preprint refresh:

- `zsasa_mdtraj`
- `zsasa_mdtraj_bitmask`
- `zsasa_mdanalysis`
- `zsasa_mdanalysis_bitmask`
- `mdtraj`
- `mdsasa_bolt`

The historical website report also contains 1-thread and 8-thread `zsasa` CLI
results. Those are useful for scaling plots, but the 1-thread 10K-frame 5vz0 run
is expensive. For the first refresh, t10 is enough to support the headline
trajectory-throughput and memory claims.

## Datasets

| ID | Atoms | Frames | XTC | PDB |
| --- | ---: | ---: | --- | --- |
| `5wvo_C_analysis` | 3,858 | 1,001 | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C_R1.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C.pdb` |
| `6sup_A_analysis` | 33,377 | 1,001 | `/Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A_R1.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A.pdb` |
| `5vz0_A_protein` | 17,910 | 10,001 | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A_prod_R1_fit.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A.pdb` |

## Settings

| Setting | Value |
| --- | --- |
| Tools | `zig`, `zig_bitmask` |
| Precision | `f64`, `f32` |
| Threads | `10` |
| Points | `100` |
| Stride | `1` |
| Warmup | `1` |
| Runs | `3` |
| Hyperfine prepare | `sync` |
| Timeout | `1200` seconds |

## Pre-flight checks

Run these checks before starting the actual benchmark:

```bash
cd /Users/nagaet/freesasa-zig
git status --short --branch
git describe --tags --always --dirty
git rev-parse HEAD
```

Expected version for this refresh:

```text
v0.6.0
94fdc1ee0ba27063d7cfe69e915e8425474316e1
```

## Dry-run commands

These commands print the command plan without running benchmark timings:

```bash
cd /Users/nagaet/freesasa-zig

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C_R1.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C.pdb \
  --name zsasa_v0_6_0_5wvo_C_t10 \
  --tool zig \
  --tool zig_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_t10/5wvo_C_analysis \
  --dry-run

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A_R1.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A.pdb \
  --name zsasa_v0_6_0_6sup_A_t10 \
  --tool zig \
  --tool zig_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_t10/6sup_A_analysis \
  --dry-run

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A_prod_R1_fit.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A.pdb \
  --name zsasa_v0_6_0_5vz0_A_t10 \
  --tool zig \
  --tool zig_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_t10/5vz0_A_protein \
  --dry-run
```

## Actual rerun commands

Remove `--dry-run` from the commands above. Run outside Codex if minimizing
interactive workload and background interference is important.

## Expected generated files per dataset

Each output directory should contain:

- `config.json`
- `bench_zig_f64_10t.json`
- `bench_zig_f32_10t.json`
- `bench_zig_f64_bitmask_10t.json`
- `bench_zig_f32_bitmask_10t.json`

These generated artifacts should stay ignored until archive staging.
