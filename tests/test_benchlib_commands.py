from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from scripts.benchlib.commands import (
    batch_command,
    freesasa_batch_command,
    freesasa_single_command,
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
    cmd = freesasa_batch_command(
        binary=Path("/bin/freesasa_batch"),
        input_dir=Path("pdbs"),
        output_dir=Path("out"),
        n_points=128,
        threads=10,
    )
    assert cmd == [
        "/bin/freesasa_batch",
        "pdbs",
        "out",
        "--n-threads=10",
        "--n-points=128",
    ]


def test_freesasa_single_command_with_timing() -> None:
    cmd = freesasa_single_command(
        binary=Path("/bin/freesasa"),
        input_path=Path("input.pdb"),
        n_points=100,
        threads=4,
        timing=True,
    )
    assert cmd == [
        "/bin/freesasa",
        "--shrake-rupley",
        "--resolution=100",
        "--n-threads=4",
        "--timing",
        "input.pdb",
    ]


def test_rustsasa_single_command() -> None:
    cmd = rustsasa_single_command(
        binary=Path("/bin/rust-sasa"),
        input_path=Path("input.pdb"),
        output_path=Path("out.json"),
        n_points=100,
        threads=2,
        timing=True,
    )
    assert cmd == [
        "/bin/rust-sasa",
        "input.pdb",
        "out.json",
        "-n",
        "100",
        "-f",
        "json",
        "-t",
        "2",
        "-o",
        "protein",
        "--allow-vdw-fallback",
        "--timing",
    ]


def test_lahuta_batch_command() -> None:
    cmd = lahuta_batch_command(
        binary=Path("/bin/lahuta"),
        input_dir=Path("pdbs"),
        output_dir=Path("out"),
        n_points=128,
        threads=10,
        bitmask=True,
    )
    assert cmd == [
        "/bin/lahuta",
        "sasa-sr",
        "-d",
        "pdbs",
        "--is_af2_model",
        "--points",
        "128",
        "-t",
        "10",
        "--output",
        "out",
        "--progress",
        "0",
        "--use-bitmask",
    ]


def test_mdtraj_runner_command() -> None:
    cmd = mdtraj_runner_command(
        tool="mdtraj",
        xtc=Path("traj.xtc"),
        pdb=Path("top.pdb"),
        n_points=100,
        stride=1,
        python="python",
    )
    assert cmd == [
        "python",
        "-m",
        "scripts.benchlib.trajectory_tools",
        "--tool",
        "mdtraj",
        "--xtc",
        "traj.xtc",
        "--pdb",
        "top.pdb",
        "--n-points",
        "100",
        "--stride",
        "1",
    ]


@pytest.mark.parametrize(
    ("builder", "args"),
    [
        (
            freesasa_batch_command,
            (Path("/bin/freesasa_batch"), Path("pdbs"), Path("out"), 128, 10),
        ),
        (
            rustsasa_single_command,
            (Path("/bin/rust-sasa"), Path("input.pdb"), Path("out.json"), 100, 2),
        ),
        (
            freesasa_single_command,
            (Path("/bin/freesasa"), Path("input.pdb"), 100, 2, True),
        ),
        (
            lahuta_batch_command,
            (Path("/bin/lahuta"), Path("pdbs"), Path("out"), 128, 10, True),
        ),
        (mdtraj_runner_command, ("mdtraj", Path("traj.xtc"), Path("top.pdb"), 100, 1)),
    ],
)
def test_command_builders_are_keyword_only(builder: Any, args: tuple[object, ...]) -> None:
    with pytest.raises(TypeError):
        builder(*args)
