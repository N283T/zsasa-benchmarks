# Single-file subset rerun log

This log records the `zsasa` v0.6.0 rerun for the curated single-file
representative subset. Comparator tools were not rerun; historical FreeSASA and
RustSASA values remain comparator baselines for the first archive/preprint.

## Result set

- Date: 2026-05-22 JST
- Result directory:
  `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/single/subset_v0_6_0`
- Source repository: `/Users/nagaet/freesasa-zig`
- Source revision: `v0.6.0` / `94fdc1ee0ba27063d7cfe69e915e8425474316e1`
- Dataset: `/Users/nagaet/freesasa-zig/benchmarks/dataset/pdb`
- Manifest: `/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/manifests/single-file-sample.toml`
- Input count: 12 PDB files
- Tools rerun: `zig_f64`, `zig_f32`, `zig_f64_bitmask`, `zig_f32_bitmask`
- Comparator tools rerun: no
- Points: 100
- Threads: 1, 4, 8, 10
- Warmup: 1
- Runs: 3
- Hyperfine prepare: `sync`

## Commands

The rerun is wrapped by:

```bash
/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/run_single_file_subset.py --execute --force
```

Without `--execute`, the wrapper only prints the planned commands and writes the
ignored `sample.json` file used by the historical `bench.py` sample-file filter.

Summary exports are generated without running benchmarks:

```bash
/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/scripts/export_single_file_subset_summary.py
```

This writes ignored CSVs under
`/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks/results/exports`:

- `single-file-subset-refreshed.csv`
- `single-file-subset-comparison-t10.csv`

## Completion checks

The output contains four refreshed tool directories for both wall-clock and
internal timing measurements. Each refreshed tool has:

- 48 wall-clock rows (`12 structures x 4 thread counts`)
- 48 timing rows (`12 structures x 4 thread counts`)
- 48 per-run hyperfine JSON files

No missing rows, missing thread counts, negative timings, or still-running
benchmark processes were observed during the post-run check.

## t10 summary

| Tool | Median wall time (s) | Max wall time (s) | Max structure |
| --- | ---: | ---: | --- |
| `zig_f64` | 0.0839 | 4.6863 | `9fqr` |
| `zig_f32` | 0.0835 | 4.6630 | `9fqr` |
| `zig_f64_bitmask` | 0.0769 | 3.7939 | `9fqr` |
| `zig_f32_bitmask` | 0.0769 | 3.8020 | `9fqr` |

## Parser/runtime outlier subset at t10

| Structure | Atoms | zsasa f64 (s) | zsasa bitmask f64 (s) | Historical FreeSASA (s) | Historical RustSASA (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `9fqr` | 4,506,416 | 4.686 | 3.794 | 181.490 | 8.965 |
| `5vyc` | 249,168 | 0.237 | 0.200 | 0.598 | 13.655 |
| `8fon` | 93,062 | 0.089 | 0.082 | 0.228 | 4.764 |
| `8rbs` | 164,605 | 0.118 | 0.102 | 24.007 | 0.239 |

## Notes

- The largest structure, `9fqr`, remains the dominant runtime case.
- Refreshed `9fqr` parse timing is about 0.71 s across variants. This is a
  little slower than the historical `zsasa` parse time recorded in the subset
  planning note, but is plausible after parser/classifier changes such as CCD
  handling and should be treated as environment/version-sensitive.
- For very small AFDB structures, bitmask wall time can be slower than the
  standard path because fixed overhead dominates. This does not affect the large
  structure headline, where bitmask remains faster.
- Comparator ratios are provisional because FreeSASA and RustSASA values are
  historical baselines, not same-session reruns.
