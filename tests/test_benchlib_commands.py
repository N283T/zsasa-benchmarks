from __future__ import annotations

from pathlib import Path

from scripts.benchlib.commands import (
    batch_command,
    freesasa_batch_command,
    lahuta_batch_command,
    mdtraj_runner_command,
    rustsasa_single_command,
    zsasa_calc_command,
)


def test_zsasa_calc_command_includes_precision_and_bitmask() -> None:
    cmd = zsasa_calc_command(
        binary=Path("/bin/zsasa"),
        input_path=Path("input.pdb"),
        output_path=Path("out.json"),
        algorithm="sr",
        precision="f32",
        n_points=128,
        threads=10,
        bitmask=True,
        timing=True,
    )
    assert cmd == [
        "/bin/zsasa",
        "calc",
        "--algorithm=sr",
        "--threads=10",
        "--precision=f32",
        "--n-points=128",
        "--use-bitmask",
        "--timing",
        "input.pdb",
        "out.json",
    ]


def test_batch_command_writes_jsonl() -> None:
    cmd = batch_command(
        binary=Path("/bin/zsasa"),
        input_dir=Path("pdbs"),
        output_jsonl=Path("out.jsonl"),
        precision="f64",
        n_points=128,
        threads=4,
        bitmask=False,
    )
    assert "--format=jsonl" in cmd
    assert "--precision=f64" in cmd
    assert "--threads=4" in cmd


def test_freesasa_batch_command() -> None:
    cmd = freesasa_batch_command(Path("/bin/freesasa_batch"), Path("pdbs"), Path("out"), 128, 10)
    assert cmd == ["/bin/freesasa_batch", "pdbs", "out", "--n-threads=10", "--n-points=128"]


def test_rustsasa_single_command() -> None:
    cmd = rustsasa_single_command(
        Path("/bin/rust-sasa"),
        Path("input.pdb"),
        Path("out.json"),
        100,
        2,
    )
    assert "--allow-vdw-fallback" in cmd
    assert "-n" in cmd
    assert "100" in cmd


def test_lahuta_batch_command() -> None:
    cmd = lahuta_batch_command(Path("/bin/lahuta"), Path("pdbs"), Path("out"), 128, 10, True)
    assert "sasa-sr" in cmd
    assert "--use-bitmask" in cmd
    assert "--points" in cmd


def test_mdtraj_runner_command() -> None:
    cmd = mdtraj_runner_command("mdtraj", Path("traj.xtc"), Path("top.pdb"), 100, 1)
    assert cmd[:3] == ["python", "-m", "scripts.benchlib.trajectory_tools"]
    assert "--tool" in cmd
    assert "mdtraj" in cmd
