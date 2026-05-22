from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_setup_external_tools_dry_run_lists_pinned_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/setup_external_tools.py",
            "--dry-run",
            "--reset",
            "--no-nix",
            "freesasa",
            "lahuta",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "https://github.com/N283T/freesasa.git" in proc.stdout
    assert "9c9f204fd990ba2f50f47be8d4b96a61355f7a10" in proc.stdout
    assert "https://github.com/bisejdiu/lahuta.git" in proc.stdout
    assert "4b5d6f9ae2bc13bcf897b1df3483b9c1e3da1de9" in proc.stdout
    assert "-DBUILD_TESTING=OFF" in proc.stdout


def test_freesasa_batch_source_is_tracked() -> None:
    assert Path("tools/freesasa_batch/freesasa_batch.cc").is_file()
    assert Path("tools/freesasa_batch/Makefile").is_file()
