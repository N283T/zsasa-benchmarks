# SASA explorer tables

Data behind the SASA explorer on the `zsasa` website
(<https://n283t.github.io/zsasa/docs/data/explorer/>): the SASA, interface
burial (delta-SASA) and polar/apolar split of the AFDB/NVIDIA human dimer models
and of the SwissProt models of AFDB v6, joined with model metadata and the
AFDB/NVIDIA confidence scores.

## Runs

The runs were made on 2026-11-02/03 with the `zsasa` v0.13.0 release (a
ReleaseFast build of N283T/zsasa `6aa9bc2`, the commit tagged `v0.13.0`), while
the machine was in ordinary use. They are not benchmarks and are not stored in
`results/benchmark.duckdb`.

| Directory | Models | Run | Wall time | Peak RSS |
| --- | ---: | --- | ---: | ---: |
| `homodimers/` | 91,637 | BSA analysis, chains A and B | 351 s | 1,592 MiB |
| `heterodimers/` | 531,605 | BSA analysis, chains A and B | 2,682 s | 223 MiB |
| `swissprot/` | 550,122 | one job over every model | 461 s | 127 MiB |

Every model succeeded. The settings are those of the manuscript's dimer
workflows (`../afdb-dimers/`): Shrake-Rupley, bitmask mode, f32, 128 sphere
points, 1.4 Å probe, CCD classifier, with `polar = true` added. The heterodimer
run was started once before and stopped part way; the files here are from the
complete second run.

The dimer totals equal those of the `zsasa` 0.12.1 runs in
`../afdb-dimers/v0.12.1/` exactly (`sasa_partner_a`, `sasa_partner_b`,
`sasa_complex`, `delta_sasa_total` and `bsa` of every model). In every row the
polar and apolar parts add up to their total within the 6-decimal rounding of the
output.

## Files

- `*/workflow.toml`, `run-info.txt`, `job-status.txt`, `time-stderr.txt`: the
  workflow file, the `zsasa` build and input count, start and finish times, and
  the workflow summary with `/usr/bin/time -l` output.
- `homodimers/delta_sasa_ab.jsonl.zst`, `heterodimers/delta_sasa_ab.jsonl.zst`:
  one BSA row per model, with `sasa_partner_a_polar`/`_apolar`,
  `sasa_partner_b_polar`/`_apolar`, `sasa_complex_polar`/`_apolar` and
  `delta_sasa_polar`/`_apolar` next to the totals.
- `swissprot/sasa.jsonl.zst`: one row per model with `total_area`, `polar_area`
  and `apolar_area`.
- `metadata/*.parquet`: per-model metadata from
  `scripts/extract_explorer_metadata.py` (see below).
- `tables/afdb_heterodimers.parquet`, `tables/afdb_homodimers.parquet`,
  `tables/swissprot.parquet`: the explorer tables, built by
  `scripts/build_explorer_tables.py`. Areas are rounded to two decimals and
  scores to four.

Rebuild the metadata and the tables with:

```bash
uv run python scripts/extract_explorer_metadata.py dimers \
    --input-dir ~/pdb/afdb/nvda/homodimers/9606_HUMAN/structure --out workflows/sasa-explorer/metadata/homodimers.parquet
uv run python scripts/extract_explorer_metadata.py dimers \
    --input-dir ~/pdb/afdb/nvda/heterodimers-cif --out workflows/sasa-explorer/metadata/heterodimers.parquet
uv run python scripts/extract_explorer_metadata.py swissprot \
    --input-dir ~/pdb/afdb/swissprot_pdb_v6 --out workflows/sasa-explorer/metadata/swissprot.parquet
uv run python scripts/build_explorer_tables.py \
    --homodimers workflows/sasa-explorer/homodimers/delta_sasa_ab.jsonl.zst \
    --heterodimers workflows/sasa-explorer/heterodimers/delta_sasa_ab.jsonl.zst \
    --swissprot workflows/sasa-explorer/swissprot/sasa.jsonl.zst \
    --homodimer-scores ~/pdb/afdb/nvda/homodimers/9606_HUMAN/data.csv \
    --heterodimer-scores ~/pdb/afdb/nvda/heterodimer_metadata.csv \
    --out-dir workflows/sasa-explorer/tables
```

## Table columns

Dimer tables, one row per model:

| Column | Meaning |
| --- | --- |
| `model_id` | AFDB model identifier |
| `accession_a`, `entry_name_a`, `gene_a`, `description_a`, `n_residues_a` | UniProt accession, entry name, gene, protein name and sequence length of chain A; `_b` for chain B |
| `sasa_a`, `sasa_b`, `sasa_ab` | SASA of chain A alone, chain B alone and the complex (Å²) |
| `delta_sasa`, `bsa` | `sasa_a + sasa_b - sasa_ab`, and half of it (Å²) |
| `*_polar`, `*_apolar` | polar and apolar parts of each of these areas |
| `plddt` | global pLDDT of the model (`_ma_qa_metric_global`) |
| `iptm`, `ipsae_min`, `pdockq`, `n_clash_backbone` | AFDB/NVIDIA scores; `ipsae_min` is the smaller of ipSAE A->B and B->A |
| `high_quality` | AFDB complex definition: `ipsae_min >= 0.6`, `plddt >= 70`, `n_clash_backbone <= 10` |

SwissProt table: `accession`, `fragment`, `model_id`, `description`,
`organism`, `taxonomy_id` and `n_residues` from the PDB header, `plddt` (mean of
the CA B-factors), and `sasa`, `sasa_polar`, `sasa_apolar`. The PDB files carry
no gene names.

## Inputs and their quirks

The inputs are the same as for `../afdb-dimers/` plus the SwissProt PDB files of
AFDB v6; none of them is redistributed here. The values are derived from
AlphaFold Database models, which are available under CC-BY 4.0; cite the AFDB
and the AFDB/NVIDIA release when reusing them.

**Chain entities.** In 271,238 of the 531,605 heterodimer files used here, the
atoms of chain A carry the sequence of entity 2 while their `label_entity_id`
(and `_struct_asym`) say entity 1, so the chain-to-protein mapping of the file
header is reversed. This was already so in the files as downloaded in 2026
(checked on the original downloads); the files the AFDB website and the FTP
release serve now are consistent. The metadata script therefore matches each
chain to the entity whose `_entity_poly` sequence equals the sequence of its
atoms, and uses the atom-site entity only when none does (no model needed it).
The coordinates are not affected: those of the models compared with the current
FTP release are identical, and delta-SASA, ipSAEmin and ipTM do not depend on the
chain order.

**Heterodimer scores.** `heterodimer_metadata.csv` declares 43 columns, but every
data row has 42: the trailing `ipSAE_dist_cutoff` is missing and the 42nd field
is `local_tar_name`. The table builder reads it by position, as the manuscript
figure did, and a model listed more than once keeps its row with the highest
ipSAE (A->B, then B->A, then ipTM). Every dimer has scores.

**PDB-format homo-dimers.** Two homo-dimer models are distributed as PDB files
and have no mmCIF metadata; they take their accession and gene from the
homo-dimer score table.
