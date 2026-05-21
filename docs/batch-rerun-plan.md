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
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_t10`
- `source_kind`: `zsasa_v0.6.0_refresh`
- Comparator policy: do not rerun FreeSASA, RustSASA, Lahuta, or
  `freesasa_batch` for the first archive/preprint refresh.

## Settings to match the existing `ecoli_t10` report

| Setting | Value |
| --- | --- |
| Tools | `zig`, `zig_bitmask` |
| Precision | `f64`, `f32` |
| Threads | `10` |
| Points | `128` |
| Warmup | `3` |
| Runs | `10` |
| Hyperfine prepare | `sync` |

The historical `ecoli_t10` configuration used the same thread count, point
count, warmup, run count, and prepare command. The only intentional difference
is that the input path below uses the local absolute AFDB path instead of the
old repository-relative dataset path.

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
  --name zsasa_v0_6_0_ecoli_t10 \
  --tool zig \
  --tool zig_bitmask \
  --threads 10 \
  --runs 10 \
  --warmup 3 \
  --n-points 128 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_t10 \
  --dry-run
```

## Actual rerun command

Run this outside Codex if minimizing interactive workload and background
interference is important:

```bash
cd /Users/nagaet/freesasa-zig
./benchmarks/scripts/bench_batch.py \
  --input /Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb \
  --name zsasa_v0_6_0_ecoli_t10 \
  --tool zig \
  --tool zig_bitmask \
  --threads 10 \
  --runs 10 \
  --warmup 3 \
  --n-points 128 \
  --precision f64 \
  --precision f32 \
  --prepare sync \
  --output /Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/batch/zsasa_v0_6_0_ecoli_t10
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

The refresh should create:

- `config.json`
- `bench_zsasa_f64_10t.json`
- `bench_zsasa_f32_10t.json`
- `bench_zsasa_f64_bitmask_10t.json`
- `bench_zsasa_f32_bitmask_10t.json`

These are generated artifacts and should stay ignored until archive staging.
