from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchlib.trajectory_tools import build_zsasa_traj_command, resolve_zsasa_binary


def test_build_zsasa_traj_command_includes_hydrogens_classifier_and_precision() -> None:
    cmd = build_zsasa_traj_command(
        binary=Path("/bin/zsasa"),
        xtc=Path("traj.xtc"),
        pdb=Path("top.pdb"),
        output_csv=Path("out.csv"),
        n_points=100,
        stride=1,
        threads=10,
        precision="f64",
        use_bitmask=True,
        include_hydrogens=True,
        classifier="naccess",
    )

    assert cmd == [
        "/bin/zsasa",
        "traj",
        "traj.xtc",
        "top.pdb",
        "--include-hydrogens",
        "--classifier=naccess",
        "--threads=10",
        "--precision=f64",
        "--stride=1",
        "--n-points=100",
        "--use-bitmask",
        "-o",
        "out.csv",
        "-q",
    ]


def test_trajectory_tools_stub_records_execution_settings(tmp_path: Path) -> None:
    output = tmp_path / "stub.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.benchlib.trajectory_tools",
            "--tool",
            "zig_bitmask",
            "--xtc",
            "traj.xtc",
            "--pdb",
            "top.pdb",
            "--n-points",
            "100",
            "--stride",
            "1",
            "--threads",
            "10",
            "--precision",
            "f32",
            "--classifier",
            "naccess",
            "--include-hydrogens",
            "--zsasa-binary",
            "/bin/zsasa",
            "--output",
            str(output),
            "--write-command-stub",
        ],
        check=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["tool"] == "zig_bitmask"
    assert payload["threads"] == 10
    assert payload["precision"] == "f32"
    assert payload["classifier"] == "naccess"
    assert payload["include_hydrogens"] is True
    assert payload["zsasa_binary"] == "/bin/zsasa"


def test_resolve_zsasa_binary_uses_path(tmp_path: Path, monkeypatch) -> None:
    binary = tmp_path.joinpath("zsasa")
    binary.write_text("#!/bin/sh\necho zsasa 0.6.0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert resolve_zsasa_binary(Path("zsasa")) == binary


def test_resolve_zsasa_binary_prefers_zsasa_cli_env(tmp_path: Path, monkeypatch) -> None:
    env_binary = tmp_path.joinpath("nix-zsasa")
    env_binary.write_text("#!/bin/sh\necho zsasa 0.6.0\n", encoding="utf-8")
    env_binary.chmod(0o755)
    path_binary = tmp_path.joinpath("path", "zsasa")
    path_binary.parent.mkdir()
    path_binary.write_text("#!/bin/sh\necho path zsasa\n", encoding="utf-8")
    path_binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(path_binary.parent))
    monkeypatch.setenv("ZSASA_CLI", str(env_binary))
    assert resolve_zsasa_binary(Path("zsasa")) == env_binary
