from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path


def test_prepare_single_file_mmcif_structures_decompresses_gzip(tmp_path: Path) -> None:
    source_dir = tmp_path.joinpath("source")
    source_dir.mkdir()
    source = source_dir.joinpath("sample.cif.gz")
    payload = b"data_sample\n_entry.id sample\n"
    with gzip.open(source, "wb") as handle:
        handle.write(payload)

    manifest = tmp_path.joinpath("single.toml")
    manifest.write_text(
        """
id = "single-file-test"

[preprocess]
output_dir_default = "unused"

[[structures]]
id = "sample"
role = "test"
source_dataset = "source"
source_file = "sample.cif.gz"
input_file = "sample.cif"
""".lstrip(),
        encoding="utf-8",
    )
    datasets = tmp_path.joinpath("datasets.toml")
    datasets.write_text(f'[source]\npath = "{source_dir}"\n', encoding="utf-8")
    output_dir = tmp_path.joinpath("out")

    subprocess.run(
        [
            sys.executable,
            "scripts/prepare_single_file_mmcif_structures.py",
            "--manifest",
            str(manifest),
            "--datasets",
            str(datasets),
            "--output-dir",
            str(output_dir),
            "--execute",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_dir.joinpath("sample.cif").read_bytes() == payload
