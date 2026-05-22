from __future__ import annotations

import subprocess
import sys


def test_run_batch_dry_run_outputs_native_hyperfine_commands() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_batch.py",
            "--manifest",
            "manifests/batch-ecoli.toml",
            "--run-id",
            "test_run",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "hyperfine" in proc.stdout
    assert "freesasa_batch" in proc.stdout
    assert "results/full_rerun/test_run/batch" in proc.stdout
    assert "scripts/bench_batch.py" not in proc.stdout
    assert "benchmarks/scripts/" not in proc.stdout
    assert "--n-points=128" in proc.stdout
    assert "--threads=1" in proc.stdout
    assert "--threads=10" in proc.stdout
    assert "--precision=f64" in proc.stdout
    assert "--precision=f32" in proc.stdout
    assert "--use-bitmask" in proc.stdout
    assert "lahuta" in proc.stdout
    assert "rustsasa" in proc.stdout
