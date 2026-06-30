# FreeSASA PDB Coordinate Overflow Investigation

This directory records the investigation of a FreeSASA single-file runtime and memory outlier observed for `8rbs` in the large-structure benchmark subset.

## Summary

The outlier is caused by FreeSASA's PDB coordinate parser reading whitespace-separated floating-point tokens from the 24-character coordinate section rather than reading the three fixed-width PDB coordinate fields separately.

For `8rbs.pdb`, coordinates exceed the usual PDB `8.3` coordinate field width and adjacent coordinate fields become concatenated, for example:

```text
1145.4261487.1441862.471
```

Interpreted as fixed-width PDB columns this is:

```text
x = 1145.426, y = 1487.144, z = 1862.471
```

FreeSASA's parser uses `sscanf(coord_section, "%lf%lf%lf", ...)`, which parses the same 24-character section as:

```text
x = 1145.4261487, y = 0.1441862, z = 0.471
```

This collapses much of the structure along `y` and `z`, creating a very large number of artificial atomic contacts. FreeSASA's Shrake-Rupley implementation stores neighbor lists for those contacts, causing large runtime and memory use.

The original mmCIF source for the same structure does not have this PDB fixed-width overflow problem. Running FreeSASA with `--cif` on the source mmCIF gives normal runtime/memory and the expected SASA total.

## Files

- `report.md` — investigation report with commands and observed measurements.
- `scripts/detect_pdb_coordinate_overflow.py` — dependency-free PDB coordinate range checker.
- `scripts/scanf_coord_demo.c` — minimal C demo of the `sscanf` misparse.
- `scripts/compare_freesasa_pdb_vs_cif.sh` — compares upstream FreeSASA on benchmark `8rbs.pdb` vs source `8rbs.cif.gz`.

## Quick checks

From the repository root:

```bash
uv run python investigations/freesasa-pdb-coordinate-overflow/scripts/detect_pdb_coordinate_overflow.py \
  datasets/single-file-large-structure/pdb
```

Compile and run the parser demo:

```bash
cc investigations/freesasa-pdb-coordinate-overflow/scripts/scanf_coord_demo.c \
  -o /tmp/scanf_coord_demo
/tmp/scanf_coord_demo
```

Compare PDB vs mmCIF FreeSASA behavior using a locally built upstream FreeSASA binary:

```bash
FREESASA_BIN=/path/to/upstream/freesasa \
  investigations/freesasa-pdb-coordinate-overflow/scripts/compare_freesasa_pdb_vs_cif.sh
```
