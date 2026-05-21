# Batch benchmark rerun plan

This note fixes the first controlled batch rerun settings without executing the
benchmark. The goal is to refresh only the `zsasa` timings for the existing
E. coli batch-throughput comparison while preserving historical comparator
timings until a full same-harness rerun is approved.

## Scope

- Dataset: `/Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb`
- Expected input count: 4,370 PDB files
- Historical baseline:
  `/Users/nagaet/freesasa-zig/benchmarks/results/batch/128/ecoli_t10`
- New output directory:
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_scaling`
- `source_kind`: `zsasa_v0.6.0_refresh`
- Comparator policy: do not rerun FreeSASA, RustSASA, Lahuta, or
  `freesasa_batch` for the first archive/preprint refresh.

## Settings for the refreshed scaling run

| Setting | Value |
| --- | --- |
| Tools | `zig`, `zig_bitmask` |
| Precision | `f64`, `f32` |
| Threads | `1,2,4,8,10` |
| Points | `128` |
| Warmup | `3` |
| Runs | `3` |
| Hyperfine prepare | `sync` |

The refreshed run extends the historical `ecoli_t10` headline comparison to a
small scaling series (`1,2,4,8,10`) while keeping the same point count, warmup,
and prepare command. The run count is `3` for the scaling refresh, matching the
older scaling run convention rather than the `ecoli_t10` headline run count. The
input path below uses the local absolute AFDB path instead of the old
repository-relative dataset path.

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

Optionally confirm the command plan without running benchmark timings:

```bash
cd /Users/nagaet/freesasa-zig
./benchmarks/scripts/bench_batch.py \
  --input /Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb \
  --name zsasa_v0_6_0_ecoli_scaling \
  --tool zig \
  --tool zig_bitmask \
  --threads 1,2,4,8,10 \
  --runs 3 \
  --warmup 3 \
  --n-points 128 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_scaling \
  --dry-run
```

## Actual rerun command

Run this outside Codex if minimizing interactive workload and background
interference is important:

```bash
cd /Users/nagaet/freesasa-zig
./benchmarks/scripts/bench_batch.py \
  --input /Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb \
  --name zsasa_v0_6_0_ecoli_scaling \
  --tool zig \
  --tool zig_bitmask \
  --threads 1,2,4,8,10 \
  --runs 3 \
  --warmup 3 \
  --n-points 128 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_scaling
```

The script rebuilds `zsasa` with `zig build --release=fast` before running
`zig` or `zig_bitmask`. Keep `/Users/nagaet/freesasa-zig` checked out at the
expected tag/commit before starting the benchmark.

## Interference notes

- Avoid running this while `rclone`, indexing, package builds, or other heavy
  CPU/I/O tasks are active.
- Keep the machine plugged in and avoid changing power/thermal state mid-run.
- Closing Codex during the actual benchmark is reasonable; the generated JSON
  files are ignored under `results/` and can be imported later.
- Do not write refreshed outputs into
  `/Users/nagaet/freesasa-zig/benchmarks/results/batch/128/ecoli_t10`; keep the
  historical baseline untouched.

## Expected generated files

The refresh should create `config.json` plus 20 hyperfine JSON files: standard
and bitmask results for f64 and f32 at 1, 2, 4, 8, and 10 threads.

These are generated artifacts and should stay ignored until archive staging.
