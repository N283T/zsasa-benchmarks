# Zenodo benchmark archive guide

This repository is prepared for the Zenodo DOI record [10.5281/zenodo.23794793](https://doi.org/10.5281/zenodo.23794793),
covering benchmark evidence and analysis artifacts for `zsasa` v0.12.1. It is revision 1
of the v0.12.1 archive and supersedes the first v0.12.1 archive
([10.5281/zenodo.23788710](https://doi.org/10.5281/zenodo.23788710)), revision 2 of the v0.9.0 archive ([10.5281/zenodo.23306698](https://doi.org/10.5281/zenodo.23306698)),
revision 1 ([10.5281/zenodo.23184113](https://doi.org/10.5281/zenodo.23184113))
and the first v0.9.0 archive ([10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149));
the `zsasa` v0.6.0 record is [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

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
- **Version:** v0.12.1-benchmark-archive-r1
- **DOI:** [10.5281/zenodo.23794793](https://doi.org/10.5281/zenodo.23794793)
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
> environment metadata used to reproduce the reported analyses, and the workflow
> files and per-model delta-SASA results of the AFDB dimer workflow demonstration.

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

Create the curated upload tarball:

```bash
uv run python scripts/build_zenodo_archive.py --profile curated --make-archive
```

Create a large full-profile upload tarball without gzip compression:

```bash
uv run python scripts/build_zenodo_archive.py \
  --profile full \
  --compression none \
  --make-archive
```

Upload the generated tarball and `SHA256SUMS` from `archives/zenodo/` to Zenodo.
`archives/` is intentionally ignored by git.

## Published DOI

The curated benchmark archive DOI for `zsasa` v0.12.1 is [10.5281/zenodo.23794793](https://doi.org/10.5281/zenodo.23794793) (revision 1).
The first v0.12.1 archive remains available as [10.5281/zenodo.23788710](https://doi.org/10.5281/zenodo.23788710), the v0.9.0 archive remains available as [10.5281/zenodo.23306698](https://doi.org/10.5281/zenodo.23306698) (revision 2), [10.5281/zenodo.23184113](https://doi.org/10.5281/zenodo.23184113) (revision 1) and [10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149), and the `zsasa` v0.6.0 archive as [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

For future updates, create a new Zenodo version and rebuild the upload archive
after updating DOI/version metadata in this repository.
