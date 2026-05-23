from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_prepare_single_file_structures_dry_run_reports_sources(tmp_path: Path) -> None:
    manifest = tmp_path.joinpath("single.toml")
    datasets = tmp_path.joinpath("datasets.toml")
    source_dir = tmp_path.joinpath("source")
    source_dir.mkdir()
    source_dir.joinpath("a.pdb").write_text(
        "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 20.00           N  \n",
        encoding="utf-8",
    )
    manifest.write_text(
        """
id = "single-file-test"

[[structures]]
id = "a"
role = "single-test"
source_kind = "preprocessed_pdb"
source_dataset = "source"
source_file = "a.pdb"
expected_atoms = 1
expected_chains = 1
""".lstrip(),
        encoding="utf-8",
    )
    datasets.write_text(f'[source]\npath = "{source_dir}"\n', encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_single_file_structures.py",
            "--manifest",
            str(manifest),
            "--datasets",
            str(datasets),
            "--output-dir",
            str(tmp_path.joinpath("out")),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "mode=dry-run" in proc.stdout
    assert "single-test" in proc.stdout
    assert "preprocessed_pdb" in proc.stdout
    assert not tmp_path.joinpath("out", "metadata.csv").exists()
