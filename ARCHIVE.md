# Zenodo benchmark archive guide

This repository is prepared for the Zenodo DOI record [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561),
covering benchmark evidence and analysis artifacts for `zsasa` v0.6.0.

## Recommended Zenodo metadata

- **Resource type:** Dataset
- **Title:** Benchmark dataset and analysis artifacts for zsasa v0.6.0
- **Creators:** Tsubasa Nagae
- **Version:** v0.6.0-benchmark-archive
- **DOI:** [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561)
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
> configuration for zsasa v0.6.0, a high-throughput solvent-accessible surface
> area analysis engine for structural bioinformatics workflows. The archive
> includes the DuckDB benchmark evidence database, generated summary tables,
> rendered manuscript figures, benchmark manifests, scripts, schemas, and pinned
> environment metadata used to reproduce the reported analyses.

## Archive profiles

`scripts/build_zenodo_archive.py` provides two profiles:

- `curated` (recommended for first DOI upload): source code, manifests,
  reproducibility configuration, `results/benchmark.duckdb`, rendered figures,
  exports, and summary tables. It excludes `results/full_rerun/` raw outputs.
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

The curated benchmark archive DOI is [10.5281/zenodo.20577561](https://doi.org/10.5281/zenodo.20577561).

For future updates, create a new Zenodo version and rebuild the upload archive
after updating DOI/version metadata in this repository.
