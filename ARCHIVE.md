# Zenodo benchmark archive guide

This repository is prepared for the Zenodo DOI record [10.5281/zenodo.23181213](https://doi.org/10.5281/zenodo.23181213),
covering benchmark evidence and analysis artifacts for `zsasa` v0.9.0. It is revision 1
of the v0.9.0 archive and supersedes [10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149);
the `zsasa` v0.6.0 record is [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

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
- **Title:** Benchmark dataset and analysis artifacts for zsasa v0.9.0
- **Creators:** Tsubasa Nagae
- **Version:** v0.9.0-benchmark-archive-r1
- **DOI:** [10.5281/zenodo.23181213](https://doi.org/10.5281/zenodo.23181213)
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
> configuration for zsasa v0.9.0, a high-throughput solvent-accessible surface
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

The curated benchmark archive DOI for `zsasa` v0.9.0 is [10.5281/zenodo.23181213](https://doi.org/10.5281/zenodo.23181213) (revision 1).
The first v0.9.0 archive remains available as [10.5281/zenodo.23175149](https://doi.org/10.5281/zenodo.23175149), and the `zsasa` v0.6.0 archive as [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

For future updates, create a new Zenodo version and rebuild the upload archive
after updating DOI/version metadata in this repository.
