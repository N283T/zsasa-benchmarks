# Zenodo benchmark archive guide

This repository is prepared for a Zenodo DOI record covering benchmark evidence
and analysis artifacts for `zsasa` v0.6.0.

## Recommended Zenodo metadata

- **Resource type:** Dataset
- **Title:** Benchmark dataset and analysis artifacts for zsasa v0.6.0
- **Creators:** Tsubasa Nagae
- **Version:** v0.6.0-benchmark-archive
- **Language:** English
- **License:** MIT, unless a different license is selected for the Zenodo record
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

## DOI reservation workflow

1. Create a new Zenodo upload.
2. Select **Dataset** as the resource type.
3. In the DOI field, answer **No** to existing DOI and click **Get a DOI now!**.
4. Add the reserved DOI to the manuscript or repository metadata if needed.
5. Rebuild the upload archive after any DOI text changes.
6. Upload the tarball and `SHA256SUMS`.
7. Preview and publish the Zenodo record.

Zenodo registers the DOI only after publication. If the draft upload is deleted,
its reserved DOI is lost.
