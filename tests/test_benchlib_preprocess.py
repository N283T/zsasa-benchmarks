from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from scripts.benchlib.preprocess import (
    PreprocessError,
    clean_structure_to_pdb,
    prepare_manifest_structures,
)


def test_clean_structure_to_pdb_removes_non_protein_records_and_wraps_pdb_fields(
    tmp_path: Path,
) -> None:
    source = tmp_path.joinpath("input.pdb")
    source.write_text(
        "\n".join(
            [
                "CRYST1   10.000   10.000   10.000  90.00  90.00  90.00 P 1           ",
                "ATOM      1  N   ALA A10000      1.000   2.000   3.000  1.00 20.00           N  ",
                "ATOM      2  H   ALA A10000      1.100   2.100   3.100  1.00 20.00           H  ",
                "ATOM      3  CA AALA A10000      2.000   2.000   3.000  1.00 20.00           C  ",
                "ATOM      4  CA BALA A10000      3.000   2.000   3.000  1.00 20.00           C  ",
                "HETATM    5  O   HOH A10001      4.000   2.000   3.000  1.00 20.00           O  ",
                "END",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path.joinpath("cleaned.pdb")

    result = clean_structure_to_pdb(source, output, structure_id="example")

    lines = output.read_text(encoding="utf-8").splitlines()
    atom_lines = [line for line in lines if line.startswith("ATOM  ")]
    assert result.structure_id == "example"
    assert result.n_atoms == 2
    assert result.n_chains == 1
    assert len(atom_lines) == 2
    assert not any(line.startswith("HETATM") for line in lines)
    assert not any(line[76:78].strip() == "H" for line in atom_lines)
    assert all(line[22:26].strip().isdigit() for line in atom_lines)
    assert max(int(line[22:26].strip()) for line in atom_lines) <= 9999
    assert all(line[6:11].strip().isdigit() for line in atom_lines)
    assert lines[0].startswith("CRYST1")
    assert lines[0][66:70].strip() == "1"


def test_prepare_manifest_structures_copies_and_cleans_sources(tmp_path: Path) -> None:
    afdb_dir = tmp_path.joinpath("afdb")
    pdb_dir = tmp_path.joinpath("pdb2013")
    afdb_dir.mkdir()
    pdb_dir.mkdir()
    afdb_source = afdb_dir.joinpath("AF-P49792-F10-model_v6.pdb")
    afdb_source.write_text(
        "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 20.00           N  \n",
        encoding="utf-8",
    )
    pdb_source = pdb_dir.joinpath("3jc8.pdb")
    pdb_source.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 20.00           N  ",
                "ATOM      2  CA  ALA A   1       2.000   2.000   3.000  1.00 20.00           C  ",
                "END",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path.joinpath("prepared")
    manifest = {
        "id": "single-file-sample",
        "structures": [
            {
                "id": "AF-P49792-F10-model_v6",
                "role": "single-medium",
                "source_kind": "afdb_pdb",
                "source_dataset": "human_afdb",
                "source_file": "AF-P49792-F10-model_v6.pdb",
                "expected_chains": 1,
            },
            {
                "id": "3jc8",
                "role": "multi-100k",
                "source_kind": "preprocessed_pdb",
                "source_dataset": "pdb2013",
                "source_file": "3jc8.pdb",
                "expected_chains": 1,
            },
        ],
    }
    dataset_catalog = {
        "human_afdb": {"path": str(afdb_dir)},
        "pdb2013": {"path": str(pdb_dir)},
    }

    rows = prepare_manifest_structures(
        manifest=manifest,
        dataset_catalog=dataset_catalog,
        output_dir=output_dir,
    )

    assert [row.structure_id for row in rows] == ["AF-P49792-F10-model_v6", "3jc8"]
    assert output_dir.joinpath("pdb", "AF-P49792-F10-model_v6.pdb").is_file()
    assert output_dir.joinpath("pdb", "3jc8.pdb").is_file()
    metadata_rows = list(csv.DictReader(output_dir.joinpath("metadata.csv").open()))
    assert [row["role"] for row in metadata_rows] == ["single-medium", "multi-100k"]
    sample = json.loads(output_dir.joinpath("sample.json").read_text(encoding="utf-8"))
    assert sample == {"samples": ["AF-P49792-F10-model_v6", "3jc8"]}


def test_prepare_manifest_structures_rejects_unknown_source_kind(tmp_path: Path) -> None:
    manifest = {
        "id": "single-file-sample",
        "structures": [
            {
                "id": "bad",
                "role": "bad",
                "source_kind": "unknown",
                "source_dataset": "missing",
                "source_file": "bad.pdb",
            }
        ],
    }

    with pytest.raises(PreprocessError, match="unsupported source_kind"):
        prepare_manifest_structures(manifest=manifest, dataset_catalog={}, output_dir=tmp_path)
