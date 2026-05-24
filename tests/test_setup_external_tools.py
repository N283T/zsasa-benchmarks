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
    assert "136411ee6ac797cab84a35d8183e6be6e6a270b2" in proc.stdout
    assert "-DBUILD_TESTING=OFF" in proc.stdout
    assert "-DLAHUTA_ENABLE_LTO=OFF" in proc.stdout


def test_setup_external_tools_dry_run_applies_rustsasa_timing_patch() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/setup_external_tools.py",
            "--dry-run",
            "--reset",
            "--no-nix",
            "rustsasa",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "https://github.com/maxall41/RustSASA.git" in proc.stdout
    assert "c3c9c4da021c2d0a8822ca5b8c8b14fede1e6da1" in proc.stdout
    assert "nix/patches/rustsasa-add-timing.patch" in proc.stdout


def test_setup_external_tools_is_documented_as_legacy_fallback() -> None:
    text = Path("scripts/setup_external_tools.py").read_text(encoding="utf-8")
    assert "legacy fallback" in text


def test_freesasa_batch_source_is_tracked() -> None:
    assert Path("tools/freesasa_batch/freesasa_batch.cc").is_file()
    assert Path("tools/freesasa_batch/Makefile").is_file()
