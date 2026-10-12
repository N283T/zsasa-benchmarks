# SwissProt Open-Latency Investigation

This directory records why the SwissProt batch benchmark (550,122 AlphaFold PDB files, 119 GB) kept only two to four of ten cores busy on the benchmark machine, and why `zsasa` 0.9.0 was slower than Lahuta there although it is faster on the Human and *E. coli* collections. The measurements were taken on 10 and 11 October 2026 on the benchmark machine (MacBook Pro, Apple M4, 4 performance and 6 efficiency cores, 32 GB, macOS 26).

All full-collection runs used 10 threads, 128 sphere points, bitmask f32 for `zsasa` and bitmask for Lahuta 2.0.3, with the command lines of `manifests/batch-swissprot-version-refresh.toml`, unless a row says otherwise.

## Summary

1. **The idle workers wait inside `open()`, not for the disk.** The machine runs endpoint-security software with on-access scanning (Microsoft Defender for Endpoint). The first `open()` of a file returns only when the scan has finished.
2. **macOS throttles the scanner while the tool reads.** Lower-priority disk I/O is held back while a normal-priority process does disk I/O on the same device. Under the passive disk I/O policy (`taskpolicy -d passive`, `IOPOL_PASSIVE`) the tools no longer cause that throttling and both run faster.
3. **`zsasa` 0.9.0 was hit harder than Lahuta** because it memory-maps its inputs. A mapping costs about 14 page faults per file, and each waits once the file cache has filled memory. Output volume (16.6 GB against 9.6 GB) is a smaller part.

## Findings

### Opening a file that has not been scanned

One thread, 4,000 SwissProt files, opened and read (`scripts/io_probe3.py`), then the same files again:

| Pass | `open` | read | Scanner CPU |
| --- | ---: | ---: | ---: |
| first | 5.83 ms | 0.34 ms | 19.6 s (4.9 ms per file) |
| second | 0.21 ms | 0.24 ms | 1.6 s |

A `stat` of a file not yet scanned takes about 0.1 ms. Visiting order (sorted or `readdir`), a `stat` just before the open, whole-file or 4 KiB reads, and `open` against `openat` with `O_CLOEXEC` do not change the first-open latency (`scripts/io_probe.py`, `scripts/open_flags.py`). With 10 threads and no computation the latency stays at 5.6 ms up to about 10 concurrent opens and grows beyond that (`scripts/io_probe2.py`).

Sampling running processes on files not yet scanned (`scripts/sample_tool.py`, macOS `sample`): `zsasa` workers spent 64-71% of their wall time in `openat`, Lahuta workers about 50% in `open` and 5% in `read`. Both tools run exactly 10 workers; Lahuta's writer thread was idle 97% of the time.

### Default disk I/O policy, repeated in October

Runs on the idle machine, in rotating order (`logs/full_run3.txt` to `logs/full_run11.txt`):

| Tool | Runtime (s) |
| --- | --- |
| zsasa 0.9.0 | 634.0, 631.5, 622.9, 616.3, 656.3, 623.6, 654.0, 658.9 |
| zsasa 0.10.1 | 645.3, 657.1, 658.8, 623.6, 686.6 |
| Lahuta 2.0.3 | 596.6, 587.2, 602.0, 588.9, 594.9, 594.2, 588.4, 661.6 |
| Lahuta 2.0.0-dev (local build) | 602.0, 596.0, 590.1 |

The July values in the database (`zsasa` 0.9.0 670.2 s, Lahuta 588.1 s) are reproduced. With other work on the machine Lahuta lost about 9% and the difference disappeared (`logs/full_run.txt`), so these runs need an idle machine.

### Passive disk I/O policy

Through the harness (`manifests/batch-swissprot-passive-io.toml`), `zsasa` 0.9.0 and Lahuta 2.0.3:

| Tool / mode | Workers | Runtime (s) |
| --- | ---: | ---: |
| zsasa f32 | 10 / 20 / 40 | 804.3 / 797.6 / 791.3 |
| zsasa bitmask f32 | 10 / 20 / 40 | 460.6 / 419.2 / 428.7 |
| Lahuta bitmask | 10 | 487.9 |
| zsasa bitmask f32, three alternating rounds | 10 | 440.4, 431.3, 451.1 |
| Lahuta bitmask, three alternating rounds | 10 | 484.0, 473.9, 483.7 |

Runs over files the scanner had already seen take as long under either policy (8,000-file blocks: `zsasa` 2,696 against 2,676 files/s, Lahuta 1,751 against 1,727).

### Why `zsasa` waited longer than Lahuta

Per file and thread, waiting time is the thread count times the runtime minus the CPU time, divided by the number of files.

| Condition (full collection) | zsasa | Lahuta |
| --- | ---: | ---: |
| default policy | 8.5-9.2 ms | 6.7-7.0 ms |
| passive policy | 5.1-5.6 ms | 4.1-4.4 ms |
| passive policy, input read instead of mapped | 4.6-4.7 ms | |

- A time series under the passive policy (`logs/full_run14_samples.csv`) shows `zsasa` at 4.8-5.1 ms until free memory runs out, after about 120,000 files, and at 5.5-5.8 ms from then on. Lahuta stays at 4.2 ms.
- `zsasa` takes 14.3 minor page faults per file (one per 16 KiB page of the mapped input), Lahuta 2.1 (`scripts/pagefaults.py`).
- With the input read by one `read` instead of mapped, the full run takes 408.3 and 414.3 s against 437.7 and 453.5 s (`logs/full_run16.txt`). On collections that fit in memory the two are within 1% (`scripts/human_warm.py`, `scripts/read_default_check.py`).
- Discarding the output, or rounding it to three decimals (6.7 GB), saves 2-4% (`logs/full_run15.txt`).

### Ruled out

Lahuta's version (2.0.0-dev and 2.0.3 take the same time), the number of threads, the JSONL mutex (0.1 ms per file with `--profile-stages`, `logs/full_run4.txt`), the Nix wrapper script of `zsasa-0.9.0`, anonymous memory-map churn, the progress display, the kind of computation, and the share of CPU time on performance cores (`scripts/pcore.py`: 75% for `zsasa`, 72% for Lahuta). A lower QoS clamp (`taskpolicy -c utility`) helps on small blocks and loses on the full collection. Stat-ing files a few thousand ahead of the workers gains 11-14% under the default policy and nothing under the passive one (`logs/full_run5.txt`, `logs/full_run6.txt`); stat-ing every file first, as Lahuta's directory source does, gains nothing at this size.

### A defect found on the way

`zsasa batch --input-io=read|mmap` was ignored outside a workflow in 0.9.0 to 0.10.1 ([N283T/zsasa#478](https://github.com/N283T/zsasa/issues/478)): 14.3 page faults per file with either value, 1.6 with the option passed on (`scripts/pagefaults3.py`). The read/mmap controls recorded with those versions therefore repeat each parser's default; see `docs/benchmark-policy.md`.

## What changed because of this

- `zsasa` 0.11.0: `--input-io` takes effect (N283T/zsasa#479), a batch reads each input with one read (N283T/zsasa#480), and `zsasa batch --passive-io` requests the passive policy (N283T/zsasa#481).
- This repository: `[full_rerun] disk_io_policy` in batch manifests and the passive-I/O SwissProt manifest and results.

## Files

- `scripts/assay.py` with `scripts/plan*.txt`: short runs on blocks of 8,000 files that the scanner has not seen recently; `logs/assay.txt` holds every result. A block is made "cold" by stat-ing 300,000 other files first.
- `scripts/mimic.c`: a small program that reproduces a tool's per-file system calls (open, stat, read or map, close, compute, write) with switches for each part and for the disk I/O policy.
- `scripts/full_run*.py`, `scripts/run_b.py`: drivers of the full-collection runs; `logs/full_run*.txt` are their outputs, renamed from `.log` because this repository ignores `*.log` files. The scripts hold the absolute paths of the benchmark machine and are kept as run.
- `scripts/io_probe*.py`, `scripts/open_flags.py`, `scripts/pagefaults*.py`, `scripts/pcore.py`, `scripts/sample_tool.py`, `scripts/whoworks.py`, `scripts/poststat.py`: the single measurements quoted above.
