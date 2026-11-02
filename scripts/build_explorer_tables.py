"""Build the Parquet tables behind the zsasa website's SASA explorer.

`afdb_homodimers.parquet` and `afdb_heterodimers.parquet` join, for every
AFDB/NVIDIA human dimer model, the
`zsasa` BSA workflow output (with the polar/apolar split), the chain metadata
from `extract_explorer_metadata.py` and the AFDB/NVIDIA confidence scores. The
two homo-dimer models distributed in PDB format have no mmCIF metadata; they
take their accession and gene from the homo-dimer score table.
`swissprot.parquet` joins the `zsasa batch --polar` output of the SwissProt
AFDB models with their metadata.

    uv run python scripts/build_explorer_tables.py \
        --homodimers workflows/sasa-explorer/homodimers/delta_sasa_ab.jsonl.zst \
        --heterodimers workflows/sasa-explorer/heterodimers/delta_sasa_ab.jsonl.zst \
        --swissprot workflows/sasa-explorer/swissprot/sasa.jsonl.zst \
        --homodimer-scores ~/pdb/afdb/nvda/homodimers/9606_HUMAN/data.csv \
        --heterodimer-scores ~/pdb/afdb/nvda/heterodimer_metadata.csv \
        --out-dir workflows/sasa-explorer/tables

The heterodimer score CSV declares 43 columns, but every data row has 42: the
trailing `ipSAE_dist_cutoff` is absent and the 42nd field is `local_tar_name`.
It is read by position, as for the manuscript figure, and a model listed more
than once keeps its row with the highest ipSAE (A->B, then B->A, then ipTM).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

METADATA_DIR = Path("workflows/sasa-explorer/metadata")

# Areas are written with two decimals, scores with four.
AREA = "round({}, 2)"
SCORE = "round({}, 4)"


def sql_path(path: Path) -> str:
    return str(path.expanduser()).replace("'", "''")


def model_key(column: str) -> str:
    return f"regexp_extract({column}, '^(AF-[0-9A-Za-z]+(-F[0-9]+)?)', 1)"


def bsa_rows(con: duckdb.DuckDBPyConnection, name: str, jsonl: Path) -> None:
    con.execute(f"""
        create table {name} as
        select {model_key("filename")} as model_id, *
        from read_json_auto('{sql_path(jsonl)}', format = 'newline_delimited')
        where status = 'ok'
    """)


def build_dimers(con: duckdb.DuckDBPyConnection, args: argparse.Namespace, out_dir: Path) -> None:
    bsa_rows(con, "homo_bsa", args.homodimers)
    bsa_rows(con, "hetero_bsa", args.heterodimers)
    con.execute(f"""
        create table homo_scores as
        select modelEntityId as model_id,
               uniprotAccession as accession,
               gene,
               ipTM as iptm,
               least(ipSAE_AB, ipSAE_BA) as ipsae_min,
               pDockQ as pdockq,
               N_clash_backbone as n_clash_backbone
        from read_csv('{sql_path(args.homodimer_scores)}')
    """)
    con.execute(f"""
        create table hetero_scores as
        select * exclude (rn) from (
            select model_id, null::varchar as accession, null::varchar as gene,
                   iptm, least(ipsae_ab, ipsae_ba) as ipsae_min, pdockq,
                   n_clash_backbone,
                   row_number() over (
                       partition by model_id order by ipsae_ab desc, ipsae_ba desc, iptm desc
                   ) as rn
            from (
                select column00 as model_id,
                       try_cast(column06 as bigint) as n_clash_backbone,
                       try_cast(column19 as double) as ipsae_ab,
                       try_cast(column20 as double) as ipsae_ba,
                       try_cast(column25 as double) as iptm,
                       try_cast(column37 as double) as pdockq
                from read_csv('{sql_path(args.heterodimer_scores)}',
                              header = false, skip = 1, all_varchar = true)
                where column00 in (select model_id from hetero_bsa)
            )
        ) where rn = 1
    """)
    areas = ",\n".join(
        f"{AREA.format('b.' + src)} as {dst}"
        for src, dst in [
            ("sasa_partner_a", "sasa_a"),
            ("sasa_partner_b", "sasa_b"),
            ("sasa_complex", "sasa_ab"),
            ("delta_sasa_total", "delta_sasa"),
            ("bsa", "bsa"),
            ("sasa_partner_a_polar", "sasa_a_polar"),
            ("sasa_partner_a_apolar", "sasa_a_apolar"),
            ("sasa_partner_b_polar", "sasa_b_polar"),
            ("sasa_partner_b_apolar", "sasa_b_apolar"),
            ("sasa_complex_polar", "sasa_ab_polar"),
            ("sasa_complex_apolar", "sasa_ab_apolar"),
            ("delta_sasa_polar", "delta_sasa_polar"),
            ("delta_sasa_apolar", "delta_sasa_apolar"),
        ]
    )
    for kind, bsa, scores in (
        ("homo", "homo_bsa", "homo_scores"),
        ("hetero", "hetero_bsa", "hetero_scores"),
    ):
        meta = sql_path(args.metadata_dir / f"{kind}dimers.parquet")
        out = out_dir / f"afdb_{kind}dimers.parquet"
        con.execute(f"""
          copy (
            select b.model_id,
                   coalesce(m.accession_a, s.accession) as accession_a, m.entry_name_a,
                   coalesce(m.gene_a, s.gene) as gene_a, m.description_a, m.n_residues_a,
                   coalesce(m.accession_b, s.accession) as accession_b, m.entry_name_b,
                   coalesce(m.gene_b, s.gene) as gene_b, m.description_b, m.n_residues_b,
                   {areas},
                   {SCORE.format("m.plddt_global")} as plddt,
                   {SCORE.format("s.iptm")} as iptm,
                   {SCORE.format("s.ipsae_min")} as ipsae_min,
                   {SCORE.format("s.pdockq")} as pdockq,
                   s.n_clash_backbone,
                   s.ipsae_min >= 0.6 and m.plddt_global >= 70 and s.n_clash_backbone <= 10
                       as high_quality
            from {bsa} b
            left join read_parquet('{meta}') m using (model_id)
            left join {scores} s using (model_id)
            order by gene_a, gene_b, model_id
          ) to '{sql_path(out)}' (format parquet, compression zstd, row_group_size 32768)
        """)


def build_swissprot(con: duckdb.DuckDBPyConnection, args: argparse.Namespace, out: Path) -> None:
    meta = sql_path(args.metadata_dir / "swissprot.parquet")
    con.execute(f"""
        copy (
            select m.accession, m.fragment, m.model_id, m.description, m.organism,
                   m.taxonomy_id, m.n_residues,
                   {SCORE.format("m.plddt_mean")} as plddt,
                   {AREA.format("s.total_area")} as sasa,
                   {AREA.format("s.polar_area")} as sasa_polar,
                   {AREA.format("s.apolar_area")} as sasa_apolar
            from read_json_auto('{sql_path(args.swissprot)}', format = 'newline_delimited') s
            join read_parquet('{meta}') m
              on m.model_id = {model_key("s.filename")}
            where s.status = 'ok'
            order by m.accession, m.fragment
        ) to '{sql_path(out)}' (format parquet, compression zstd, row_group_size 32768)
    """)


def summarize(con: duckdb.DuckDBPyConnection, out_dir: Path) -> None:
    for kind in ("homo", "hetero"):
        dimers = out_dir / f"afdb_{kind}dimers.parquet"
        print(
            con.sql(f"""
                select '{kind}' as kind, count(*) as models, count(iptm) as with_scores,
                       median(delta_sasa) as median_delta_sasa,
                       round(avg(high_quality::int) * 100, 1) as pct_high_quality,
                       median(delta_sasa_apolar / nullif(delta_sasa, 0)) as median_apolar_fraction
                from read_parquet('{sql_path(dimers)}')
            """)
        )
    swissprot = out_dir / "swissprot.parquet"
    print(
        con.sql(f"""
            select count(*) as models, median(sasa) as median_sasa,
                   median(sasa_apolar / sasa) as median_apolar_fraction
            from read_parquet('{sql_path(swissprot)}')
        """)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--homodimers", type=Path, required=True)
    parser.add_argument("--heterodimers", type=Path, required=True)
    parser.add_argument("--swissprot", type=Path, required=True)
    parser.add_argument("--homodimer-scores", type=Path, required=True)
    parser.add_argument("--heterodimer-scores", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, default=METADATA_DIR)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    build_dimers(con, args, args.out_dir)
    build_swissprot(con, args, args.out_dir / "swissprot.parquet")
    summarize(con, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
