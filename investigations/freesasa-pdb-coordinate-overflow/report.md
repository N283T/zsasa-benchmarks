# FreeSASA 8rbs PDB Coordinate Overflow Report

## Context

The `single_file_large_structure_subset` benchmark includes `8rbs` with the role `freesasa-runtime-outlier`. In archived single-file results, FreeSASA is much slower and uses much more memory for `8rbs` than expected from atom count alone.

Relevant files:

- Benchmark PDB: `datasets/single-file-large-structure/pdb/8rbs.pdb`
- Source mmCIF: `datasets/single-file-large-structure-sources/pdb_mmcif/8rbs.cif.gz`
- Metadata: `datasets/single-file-large-structure/metadata.csv`

## Archived benchmark signal

From `results/benchmark.duckdb`, FreeSASA single-thread SR/100p metrics for selected large structures show `8rbs` is an outlier relative to similarly sized structures:

| Structure | Atoms | FreeSASA runtime median | FreeSASA SASA time | FreeSASA peak RSS |
| --- | ---: | ---: | ---: | ---: |
| `3jc8` | 107,500 | 0.361 s | 277.02 ms | 442 MiB |
| `5vyc` | 249,168 | 0.886 s | 699.06 ms | 1006 MiB |
| `8rbs` | 164,605 | 16.64 s | 17319.96 ms | 24961 MiB |
| `9fqr` | 4,506,416 | 210.43 s | 199434.21 ms | 24591 MiB |

The `8rbs` atom count is between `3jc8` and `5vyc`, but its runtime and memory are much larger.

## Root cause

`8rbs.pdb` contains coordinates above 1000 Å. In PDB `8.3` fields this causes adjacent coordinate fields to be concatenated in the 24-character coordinate section. The first ATOM record contains:

```text
ATOM      1  N   ALA A   1    1145.4261487.1441862.471  1.00 72.06           N
```

Fixed-width PDB interpretation:

```text
x = 1145.426
 y = 1487.144
 z = 1862.471
```

FreeSASA 2.1.3 parses PDB coordinates in `src/pdb.c` by copying columns 30-53 into a 24-character buffer and applying:

```c
sscanf(coord_section, "%lf%lf%lf", &xyz[0], &xyz[1], &xyz[2])
```

For the first `8rbs` coordinate section, that parsing gives:

```text
input:  1145.4261487.1441862.471
sscanf parsed fields: 3
x=1145.4261487 y=0.1441862 z=0.471
```

This collapses much of the structure into a narrow `y/z` range. As a result, FreeSASA constructs an extremely large neighbor list during Shrake-Rupley setup.

A one-off diagnostic using FreeSASA-classified radii and the exact SR neighbor condition found:

| Structure | Atoms | Neighbor pairs | Average neighbors/atom | Estimated neighbor-list storage |
| --- | ---: | ---: | ---: | ---: |
| `3jc8` | 107,500 | 1,353,004 | 25.17 | ~72 MiB pair payload |
| `5vyc` | 249,168 | 4,759,111 | 38.20 | ~254 MiB pair payload |
| `8rbs` | 164,605 | 393,274,398 | 4778.40 | ~21 GiB pair payload |

The ~21 GiB pair-payload estimate matches the observed ~22-25 GiB RSS range.

## mmCIF comparison

The source mmCIF does not suffer from PDB fixed-width coordinate overflow. With upstream FreeSASA 2.1.3 built from `mittinatten/freesasa` master commit `6af4c97`, the same structure via mmCIF behaves normally.

Command:

```bash
gzip -cd datasets/single-file-large-structure-sources/pdb_mmcif/8rbs.cif.gz > /tmp/8rbs.cif
/usr/bin/time -l /tmp/freesasa-upstream-investigate/freesasa/src/freesasa \
  --cif --shrake-rupley --resolution=100 --n-threads=1 --no-warnings \
  /tmp/8rbs.cif
```

Observed mmCIF result:

```text
1.31 real
1011171328 maximum resident set size
Total     : 2096679.59
```

For comparison, the benchmark PDB input with the same upstream binary produced:

```text
19.43 real
21826584576 maximum resident set size
Total     :   12025.82
```

A temporary PDB rewritten from fixed-width coordinates after translating the structure back below 1000 Å produced the same total as mmCIF (`2096679.59`) and normal runtime/memory. That temporary rewrite was used only to confirm the diagnosis; this repository should keep the original benchmark inputs unchanged so the FreeSASA issue remains reproducible.

## Dataset scan

Running `detect_pdb_coordinate_overflow.py` on the large-structure PDB subset showed two structures with coordinates outside the safe PDB `8.3` range:

| Structure | Overflow? | Notes |
| --- | --- | --- |
| `8rbs` | yes | coordinates exceed 1000 Å on all axes |
| `9fqr` | yes | `z_max` exceeds 1000 Å |
| remaining six structures | no | coordinates stay within the safe PDB range |

## Reproduction scripts

Detect overflowing coordinate ranges:

```bash
uv run python investigations/freesasa-pdb-coordinate-overflow/scripts/detect_pdb_coordinate_overflow.py \
  datasets/single-file-large-structure/pdb
```

Demonstrate the `sscanf` behavior:

```bash
cc investigations/freesasa-pdb-coordinate-overflow/scripts/scanf_coord_demo.c \
  -o /tmp/scanf_coord_demo
/tmp/scanf_coord_demo 1145.4261487.1441862.471
```

Compare FreeSASA on the benchmark PDB and source mmCIF:

```bash
FREESASA_BIN=/path/to/upstream/freesasa \
  investigations/freesasa-pdb-coordinate-overflow/scripts/compare_freesasa_pdb_vs_cif.sh
```

## Suggested upstream issue framing

FreeSASA's PDB parser should either:

1. parse coordinate fields using fixed PDB columns (`x = line[30:38]`, `y = line[38:46]`, `z = line[46:54]`), or
2. detect non-whitespace-separated/overflowed coordinate fields and fail with a clear error recommending mmCIF input.

For `8rbs`, mmCIF input confirms that FreeSASA's SASA calculation itself is not the problem; the pathological runtime and incorrect total originate from PDB coordinate parsing.
