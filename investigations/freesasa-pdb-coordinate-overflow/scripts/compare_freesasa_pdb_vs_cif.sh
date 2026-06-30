#!/usr/bin/env bash
# Compare upstream FreeSASA behavior on the benchmark PDB and source mmCIF.
#
# Usage:
#   FREESASA_BIN=/path/to/freesasa ./compare_freesasa_pdb_vs_cif.sh
#
# The script writes only to a temporary directory unless OUT_DIR is provided.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FREESASA_BIN="${FREESASA_BIN:-freesasa}"
OUT_DIR="${OUT_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/freesasa-8rbs-compare.XXXXXX")}"
PDB_PATH="$REPO_ROOT/datasets/single-file-large-structure/pdb/8rbs.pdb"
CIF_GZ_PATH="$REPO_ROOT/datasets/single-file-large-structure-sources/pdb_mmcif/8rbs.cif.gz"
CIF_PATH="$OUT_DIR/8rbs.cif"

mkdir -p "$OUT_DIR"
gzip -cd "$CIF_GZ_PATH" > "$CIF_PATH"

run_freesasa() {
  local label="$1"
  shift
  local stdout_path="$OUT_DIR/${label}.out"
  local stderr_path="$OUT_DIR/${label}.time.txt"
  echo "== $label =="
  echo "$FREESASA_BIN $*"
  /usr/bin/time -l "$FREESASA_BIN" "$@" >"$stdout_path" 2>"$stderr_path"
  grep '^Total' "$stdout_path" || true
  grep -E 'real|maximum resident set size' "$stderr_path" || true
  echo "stdout: $stdout_path"
  echo "time:   $stderr_path"
}

run_freesasa pdb --shrake-rupley --resolution=100 --n-threads=1 --no-warnings "$PDB_PATH"
run_freesasa cif --cif --shrake-rupley --resolution=100 --n-threads=1 --no-warnings "$CIF_PATH"

echo "wrote temporary comparison artifacts to: $OUT_DIR"
