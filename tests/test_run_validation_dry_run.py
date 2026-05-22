from __future__ import annotations

import subprocess
import sys


def test_run_validation_dry_run_outputs_native_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_validation.py",
            "--manifest",
            "manifests/validation-ecoli.toml",
            "--run-id",
            "test_run",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "source_kind=full_rerun" in proc.stdout
    assert "zsasa" in proc.stdout
    assert "freesasa_batch" in proc.stdout
    assert "scripts/validation.py" not in proc.stdout
