# Trajectory benchmark rerun plan

This note fixes the first controlled trajectory rerun settings without executing
the benchmark. The goal is to refresh the `zsasa` trajectory paths while
preserving historical external comparator timings until a full same-harness
rerun is approved.

## Scope

Rerun the `zsasa` implementations:

- `zig` (`zsasa traj`, standard CLI path)
- `zig_bitmask` (`zsasa traj --use-bitmask`, CLI path)
- `zsasa_mdtraj` (zsasa Python binding with MDTraj trajectory loading)
- `zsasa_mdtraj_bitmask`
- `zsasa_mdanalysis` (zsasa Python binding with MDAnalysis trajectory loading)
- `zsasa_mdanalysis_bitmask`

Do not rerun the external comparators for the first archive/preprint refresh:

- `mdtraj`
- `mdsasa_bolt`

All three datasets are rerun at 10 threads only. This refresh targets headline
trajectory-throughput and memory numbers while avoiding expensive 1-thread runs,
especially for the 10K-frame `5vz0_A_protein` dataset.

## Datasets

| ID | Atoms | Frames | Threads | XTC | PDB |
| --- | ---: | ---: | --- | --- | --- |
| `5wvo_C_analysis` | 3,858 | 1,001 | `10` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C_R1.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C.pdb` |
| `6sup_A_analysis` | 33,377 | 1,001 | `10` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A_R1.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A.pdb` |
| `5vz0_A_protein` | 17,910 | 10,001 | `10` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A_prod_R1_fit.xtc` | `/Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A.pdb` |

## Settings

| Setting | Value |
| --- | --- |
| Tools | `zig`, `zig_bitmask`, `zsasa_mdtraj`, `zsasa_mdtraj_bitmask`, `zsasa_mdanalysis`, `zsasa_mdanalysis_bitmask` |
| CLI precision | `f64`, `f32` |
| Python wrapper precision | binding default |
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

The Python wrapper runs use `uv run --script benchmarks/scripts/bench_md_runner.py`
inside `bench_md.py`, so their Python dependencies are resolved from the runner
script metadata and the local `python/` package path in `/Users/nagaet/freesasa-zig`.

## Dry-run commands

These commands print the command plan without running benchmark timings:

```bash
cd /Users/nagaet/freesasa-zig

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C_R1.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/5wvo_C_analysis/5wvo_C.pdb \
  --name zsasa_v0_6_0_5wvo_C_refresh \
  --tool zig \
  --tool zig_bitmask \
  --tool zsasa_mdtraj \
  --tool zsasa_mdtraj_bitmask \
  --tool zsasa_mdanalysis \
  --tool zsasa_mdanalysis_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_refresh/5wvo_C_analysis \
  --dry-run

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A_R1.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/6sup_A_analysis/6sup_A.pdb \
  --name zsasa_v0_6_0_6sup_A_refresh \
  --tool zig \
  --tool zig_bitmask \
  --tool zsasa_mdtraj \
  --tool zsasa_mdtraj_bitmask \
  --tool zsasa_mdanalysis \
  --tool zsasa_mdanalysis_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_refresh/6sup_A_analysis \
  --dry-run

./benchmarks/scripts/bench_md.py \
  --xtc /Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A_prod_R1_fit.xtc \
  --pdb /Users/nagaet/freesasa-zig/benchmarks/md_data/5vz0_A_protein/5vz0_A.pdb \
  --name zsasa_v0_6_0_5vz0_A_refresh \
  --tool zig \
  --tool zig_bitmask \
  --tool zsasa_mdtraj \
  --tool zsasa_mdtraj_bitmask \
  --tool zsasa_mdanalysis \
  --tool zsasa_mdanalysis_bitmask \
  --threads 10 \
  --runs 3 \
  --warmup 1 \
  --stride 1 \
  --n-points 100 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --timeout 1200 \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/md/zsasa_v0_6_0_refresh/5vz0_A_protein \
  --dry-run
```

## Actual rerun commands

Remove `--dry-run` from the commands above. Run outside Codex if minimizing
interactive workload and background interference is important.

## Expected generated files

Each output directory should contain `config.json` plus 10-thread results:

- CLI: `bench_zig_f64_*t.json`, `bench_zig_f32_*t.json`,
  `bench_zig_f64_bitmask_*t.json`, `bench_zig_f32_bitmask_*t.json`
- Python wrappers: `bench_zsasa_mdtraj_*t.json`,
  `bench_zsasa_mdtraj_bitmask_*t.json`, `bench_zsasa_mdanalysis_*t.json`,
  `bench_zsasa_mdanalysis_bitmask_*t.json`

Only the `10t` versions are expected. These generated artifacts should stay ignored until archive staging.
