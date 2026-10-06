# AFDB dimer delta-SASA workflows

Workflow files and run records for the large-scale workflow demonstration in the
`zsasa` manuscript: interface burial (delta-SASA, the SASA lost on complex
formation) for the AFDB/NVIDIA predicted human dimer models.

| Directory | Model set | Models | Wall time | Peak RSS |
| --- | --- | ---: | ---: | ---: |
| `homodimers/` | human homo-dimers | 91,637 | 183.2 s | 1,664 MiB |
| `heterodimers/` | human-human heterodimers | 531,605 | 1,447.2 s | 345 MiB |

These were ordinary-use runs on a machine in use, not controlled benchmarks, and
they are separate from the benchmark evidence in `results/`. They are not stored
in `results/benchmark.duckdb`.

## Files

- `workflow.toml`: the `zsasa batch --workflow` file (Shrake-Rupley, f32, 128
  sphere points, bitmask mode, CCD classifier, chains A and B as partners).
- `run-info.txt`: `zsasa` build, settings, input count, and machine.
- `job-status.txt`: start and finish times.
- `time-stderr.txt`: workflow summary and `/usr/bin/time -l` output.
- `delta_sasa_ab.jsonl.zst`: the per-model results, one JSON object per line,
  zstd-compressed (2.8 MB for the homo-dimers, 16 MB for the heterodimers).
- `delta_sasa_ab.meta.json`: the output and calculation settings written by
  `zsasa` next to the results.

`zsasa` was built from the main branch at commit `d06392f` (five commits after
v0.9.1), where the two-partner analysis is parallelized over structure files.
Each run was started as:

```bash
/usr/bin/time -l zsasa batch --workflow workflow.toml --threads=20 --quiet
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
