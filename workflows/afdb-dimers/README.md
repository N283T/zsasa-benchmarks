# AFDB dimer delta-SASA workflows

Workflow files and run records for the large-scale workflow demonstration in the
`zsasa` manuscript: interface burial (delta-SASA, the SASA lost on complex
formation) for the AFDB/NVIDIA predicted human dimer models.

## zsasa 0.12.1 runs (reported)

The runs in `v0.12.1/` were made on 2026-10-30 with the `zsasa` v0.12.1 release
on an otherwise idle machine, one run per model set and disk I/O policy, in the
order homo-dimers default, heterodimers default, homo-dimers passive,
heterodimers passive (directly after the SwissProt default-policy benchmark).
The passive runs were started under `taskpolicy -d passive`.

| Directory | Model set | Models | Disk I/O policy | Wall time | Peak RSS |
| --- | --- | ---: | --- | ---: | ---: |
| `v0.12.1/homodimers/default/` | human homo-dimers | 91,637 | default | 177.1 s | 1,655 MiB |
| `v0.12.1/homodimers/passive/` | human homo-dimers | 91,637 | passive | 177.4 s | 1,668 MiB |
| `v0.12.1/heterodimers/default/` | human-human heterodimers | 531,605 | default | 1,418.8 s | 350 MiB |
| `v0.12.1/heterodimers/passive/` | human-human heterodimers | 531,605 | passive | 1,404.6 s | 345 MiB |

Every model succeeded in all four runs. The results of the two policies are
identical line for line once sorted (the order of the lines follows the
workers), so they are stored once, in the `default/` directories.

## Earlier runs (`homodimers/`, `heterodimers/`)

| Directory | Model set | Models | Wall time | Peak RSS |
| --- | --- | ---: | ---: | ---: |
| `homodimers/` | human homo-dimers | 91,637 | 183.2 s | 1,664 MiB |
| `heterodimers/` | human-human heterodimers | 531,605 | 1,447.2 s | 345 MiB |

These were ordinary-use runs on a machine in use, made in October 2026 with a
build from the main branch at commit `d06392f` (five commits after v0.9.1),
where the two-partner analysis is parallelized over structure files.

Their values differ from the 0.12.1 values in the sixth or seventh significant
digit (median relative difference of `sasa_complex` 1.0e-6 for the homo-dimers
and 1.4e-6 for the heterodimers, at most 2.1e-5; median `delta_sasa_total`
2,828.66 against 2,828.65 Å² and 2,932.50 against 2,932.57 Å²). Both builds give
the same values from run to run. Bisecting on 20 models places the change at
zsasa commit `0e769ac` (#456), which accumulates f32 totals in f64; the results
of that commit equal those of 0.12.1. The earlier totals were rounded to f32,
so their differences could fall below zero: delta-SASA was negative (down to
-2.25 and -2.83 Å²) for 580 homo-dimers and 6,989 heterodimers. With 0.12.1 each
of these models has a delta-SASA of exactly 0, and no model is negative
(879 homo-dimers and 9,288 heterodimers have exactly 0).

None of these runs is a controlled benchmark, and they are separate from the
benchmark evidence in `results/`. They are not stored in
`results/benchmark.duckdb`.

## Files

- `workflow.toml`: the `zsasa batch --workflow` file (Shrake-Rupley, f32, 128
  sphere points, bitmask mode, CCD classifier, chains A and B as partners).
- `run-info.txt`: `zsasa` build, settings, input count, and machine.
- `job-status.txt`: start and finish times.
- `time-stderr.txt`: workflow summary and `/usr/bin/time -l` output.
- `delta_sasa_ab.jsonl.zst`: the per-model results, one JSON object per line,
  zstd-compressed (about 3 MB for the homo-dimers, 16-19 MB for the
  heterodimers).
- `delta_sasa_ab.meta.json`: the output and calculation settings written by
  `zsasa` next to the results.

Each run was started as:

```bash
/usr/bin/time -l [taskpolicy -d passive] zsasa batch --workflow workflow.toml --threads=20 --quiet
```

## Results

Each line of `delta_sasa_ab.jsonl.zst` describes one model:

| Field | Meaning |
| --- | --- |
| `filename` | input file; the leading `AF-<number>` is the AFDB model identifier |
| `sasa_partner_a`, `sasa_partner_b` | SASA of chain A and of chain B alone (Å²) |
| `sasa_complex` | SASA of the two chains together (Å²) |
| `delta_sasa_total` | `sasa_partner_a + sasa_partner_b - sasa_complex` (Å²) |
| `bsa` | half of `delta_sasa_total` (Å²) |

Values are from the bitmask f32 mode at 128 sphere points, which underestimates
total SASA by about 0.7% relative to the exact mode on static structures. Read
the files with, for example, `zstd -dc delta_sasa_ab.jsonl.zst | head` or
DuckDB's `read_json_auto`.

The values are derived from AlphaFold Database models, which are distributed
under CC-BY 4.0; cite the AFDB/NVIDIA release when reusing them.

## Inputs

The source structures come from the AFDB/NVIDIA release at
<https://ftp.ebi.ac.uk/pub/databases/alphafold/collaborations/nvda/> and are not
redistributed here. Homo-dimer models were read as distributed (`.cif.zst`).
Heterodimer models are distributed in the ZAF format and were restored to
`.cif.zst` before the run. Paths in the workflow files are those of the machine
the runs were made on.
