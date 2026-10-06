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

`zsasa` was built from the main branch at commit `d06392f` (five commits after
v0.9.1), where the two-partner analysis is parallelized over structure files.
Each run was started as:

```bash
/usr/bin/time -l zsasa batch --workflow workflow.toml --threads=20 --quiet
```

## Inputs

The source structures come from the AFDB/NVIDIA release at
<https://ftp.ebi.ac.uk/pub/databases/alphafold/collaborations/nvda/> and are not
redistributed here. Homo-dimer models were read as distributed (`.cif.zst`).
Heterodimer models are distributed in the ZAF format and were restored to
`.cif.zst` before the run. Paths in the workflow files are those of the machine
the runs were made on.
