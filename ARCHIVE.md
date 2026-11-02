# Zenodo benchmark archive guide

This repository is prepared for the Zenodo DOI record [10.5281/zenodo.23898582](https://doi.org/10.5281/zenodo.23898582),
covering benchmark evidence and analysis artifacts for `zsasa` v0.12.1. It is revision 3
of the v0.12.1 archive and supersedes revision 2
([10.5281/zenodo.23893502](https://doi.org/10.5281/zenodo.23893502)), revision 1
([10.5281/zenodo.23794793](https://doi.org/10.5281/zenodo.23794793)), the first v0.12.1 archive
([10.5281/zenodo.23788710](https://doi.org/10.5281/zenodo.23788710)), revision 2 of the v0.9.0 archive ([10.5281/zenodo.23306698](https://doi.org/10.5281/zenodo.23306698)),
revision 1 ([10.5281/zenodo.23184113](https://doi.org/10.5281/zenodo.23184113))
and the first v0.9.0 archive ([10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149));
the `zsasa` v0.6.0 record is [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

Changes in revision 3:

- `workflows/sasa-explorer/` adds the polar/apolar SASA of the AFDB/NVIDIA human
  homo- and heterodimers and of the SwissProt AFDB v6 models, computed with the
  `zsasa` v0.13.0 release, with per-model metadata and the three Parquet tables
  behind the SASA explorer on the `zsasa` website. The tables are also uploaded
  as separate files (`afdb_heterodimers.parquet`, `afdb_homodimers.parquet`,
  `swissprot.parquet`) so that the website can fetch them. The dimer totals
  equal those of `workflows/afdb-dimers/v0.12.1/`; its README describes the runs
  and the chain-entity order of the heterodimer input files.
- The new part `zsasa-benchmarks-sasa-explorer.tar.gz` holds that directory. The
  other parts are unchanged except `code-and-tables`.
- No reported benchmark value changed.

Changes in revision 2:

- The archive is split into parts that are extracted into the same directory
  (see "Build upload artifacts"), so later versions replace only the parts that
  changed.
- The FreeSASA 20-slice Lee-Richards reference was run again (the original
  outputs were lost) and is kept, with the `zsasa` totals, in
  `results/tables/validation_lr_totals.csv`. `scripts/run_validation.py` now
  runs it with the `zsasa` Lee-Richards runs.
- The per-atom and per-residue agreement with FreeSASA was checked again and is
  recorded in `results/tables/validation_atom_residue_agreement.csv`.
- No reported benchmark value changed.

Changes in revision 1:

- SwissProt under the default disk I/O policy was measured again with `zsasa`
  0.12.1 and Lahuta (`v0_12_1_swissprot_default_io`), and the reports now take
  it from that run set instead of the 0.9.0 session.
- The AFDB dimer delta-SASA workflows were run again with the `zsasa` v0.12.1
  release under the default and the passive policy
  (`workflows/afdb-dimers/v0.12.1/`). The values differ from the earlier runs
  by about one part in a million, because f32 totals are now accumulated in
  f64; no model has a negative delta-SASA any more.
  `docs/v0.12.1-rerun.md` and `workflows/afdb-dimers/README.md` describe both.

Changes in the v0.12.1 archive:

- Every `zsasa` benchmark was run again with `zsasa` 0.12.1 (run sets
  `v0_12_1_*`). Comparators were measured again in the same session for
  validation, the E. coli, Human and Human mmCIF batches, SwissProt under the
  passive disk I/O policy, and MDTraj and mdsasa-bolt on 5wvo and 6sup. The
  single-file comparators and mdsasa-bolt on 5vz0 keep their earlier rows, and
  SwissProt under the default policy kept the 0.9.0 session until revision 1.
  `docs/v0.12.1-rerun.md` lists the scope and compares the session with 0.9.0.
- The summary tables and figures report the 0.12.1 run sets
  (`scripts/benchlib/reporting.py`); the earlier run sets stay in the database.

Changes in revision 2:

- The SwissProt batch runs were repeated under the passive disk I/O policy of
  macOS for `zsasa` 0.9.0 and Lahuta (dataset id `swissprot_500k_pdb_passive_io`),
  with one run of `zsasa` 0.11.0 for comparison. The test machine scans files on
  access, and the default policy throttles that scan; the default-policy runs
  remain under `swissprot_500k_pdb`. `investigations/swissprot-open-latency/`
  holds the measurements behind this, and the SwissProt story figure now shows
  the passive-policy runs.
- The Human mmCIF parser and input I/O matrix was measured again with `zsasa`
  0.11.0 (`v0_11_0_human_cif`), because batch runs of 0.9.0 to 0.10.1 ignore
  `--input-io`. The Human mmCIF tables and figures report that run set.
- Batch manifests accept `[full_rerun] disk_io_policy`.

Changes in revision 1:

- The MDTraj reference for trajectory validation is computed one frame at a time
  (`docs/mdtraj-per-frame-reference.md`); the trajectory validation tables and
  figures changed accordingly.
- The mmCIF single-file tables record the real chain counts of 3jc8 (115) and
  8rbs (85). No timing or memory value changed.
- `workflows/afdb-dimers/` adds the workflow files, run records, and per-model
  delta-SASA results of the AFDB dimer runs.
- `scripts/check_residue_agreement.py` checks per-atom and per-residue agreement
  with FreeSASA.

## Recommended Zenodo metadata

- **Resource type:** Dataset
- **Title:** Benchmark dataset and analysis artifacts for zsasa v0.12.1
- **Creators:** Tsubasa Nagae
- **Version:** v0.12.1-benchmark-archive-r3
- **DOI:** [10.5281/zenodo.23898582](https://doi.org/10.5281/zenodo.23898582)
- **Language:** English
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Keywords:** solvent accessible surface area; structural bioinformatics;
  benchmark; protein structure; molecular dynamics; Zig
- **Related identifiers:**
  - Software repository: <https://github.com/N283T/zsasa>
  - Benchmark repository: <https://github.com/N283T/zsasa-benchmarks>
  - Manuscript repository: <https://github.com/N283T/zsasa-paper>

Suggested description:

> Benchmark evidence, validation summaries, plotting outputs, and reproducibility
> configuration for zsasa v0.12.1, a high-throughput solvent-accessible surface
> area analysis engine for structural bioinformatics workflows. The archive
> includes the DuckDB benchmark evidence database, generated summary tables,
> rendered manuscript figures, benchmark manifests, scripts, schemas, pinned
> environment metadata used to reproduce the reported analyses, the workflow
> files and per-model delta-SASA results of the AFDB dimer workflow demonstration,
> and the polar/apolar SASA tables of the zsasa website's SASA explorer.

## Archive profiles

`scripts/build_zenodo_archive.py` provides two profiles:

- `curated` (recommended for first DOI upload): source code, manifests,
  reproducibility configuration, `results/benchmark.duckdb`, rendered figures,
  exports, and summary tables. It excludes `results/full_rerun/` raw outputs, the
  derived single-file structure files, and smoke-test outputs.
- `full`: everything in `curated`, plus selected raw full-rerun output
  directories:
  - `results/full_rerun/v0_6_0_full/`
  - `results/full_rerun/nix_full_20260524/`
  - `results/full_rerun/nix_validation_20260524/`

The full profile is much larger and slower to upload. Use it only when the
Zenodo record should preserve raw command outputs in addition to the imported
DuckDB evidence and generated artifacts.

## Build upload artifacts

Create a manifest and checksum file for the curated profile:

```bash
uv run python scripts/build_zenodo_archive.py --profile curated
```

Create the curated upload tarballs:

```bash
uv run python scripts/build_zenodo_archive.py --profile curated --make-archive
```

The archive is written as one tarball per part, each rooted at `zsasa-benchmarks/`:

| Part | Contents |
| --- | --- |
| `zsasa-benchmarks-inputs.tar.gz` | `datasets/single-file-large-structure-sources/` |
| `zsasa-benchmarks-figures.tar.gz` | `results/figures/` |
| `zsasa-benchmarks-database.tar.gz` | `results/benchmark.duckdb` |
| `zsasa-benchmarks-afdb-dimers.tar.gz` | `workflows/afdb-dimers/` |
| `zsasa-benchmarks-sasa-explorer.tar.gz` | `workflows/sasa-explorer/` |
| `zsasa-benchmarks-raw-runs.tar.gz` | `results/full_rerun/` (full profile only) |
| `zsasa-benchmarks-code-and-tables.tar.gz` | everything else |

The manifest lists the part of every file. The tarballs are reproducible (sorted
members, fixed timestamps and owners, no gzip timestamp), so a part whose files did
not change keeps its name and checksum from one version to the next.

Create a large full-profile upload tarball without gzip compression:

```bash
uv run python scripts/build_zenodo_archive.py \
  --profile full \
  --compression none \
  --make-archive
```

`archives/` is intentionally ignored by git.

To publish a new version, choose "New version" on the Zenodo record and "Import
files" to copy the files of the previous version into the draft. Then upload from
`archives/zenodo/`, which keeps every file whose checksum matches, replaces the
changed ones and removes draft files that are no longer part of the archive:

```bash
uv run python scripts/upload_zenodo_archive.py <draft-id> --dry-run
uv run python scripts/upload_zenodo_archive.py <draft-id>
```

The token is read from `ZENODO_TOKEN` or from the terminal and needs the
`deposit:write` scope.

## Published DOI

The curated benchmark archive DOI for `zsasa` v0.12.1 is [10.5281/zenodo.23898582](https://doi.org/10.5281/zenodo.23898582) (revision 3).
Revision 2 remains available as [10.5281/zenodo.23893502](https://doi.org/10.5281/zenodo.23893502), revision 1 remains available as [10.5281/zenodo.23794793](https://doi.org/10.5281/zenodo.23794793), the first v0.12.1 archive remains available as [10.5281/zenodo.23788710](https://doi.org/10.5281/zenodo.23788710), the v0.9.0 archive remains available as [10.5281/zenodo.23306698](https://doi.org/10.5281/zenodo.23306698) (revision 2), [10.5281/zenodo.23184113](https://doi.org/10.5281/zenodo.23184113) (revision 1) and [10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149), and the `zsasa` v0.6.0 archive as [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

For future updates, update the DOI and version metadata in this repository,
rebuild the parts, and upload them to a new Zenodo version as described above.
