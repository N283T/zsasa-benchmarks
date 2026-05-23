"""Command builders for native benchmark runners."""

from __future__ import annotations

import sys
from pathlib import Path


def zsasa_calc_command(
    *,
    binary: Path,
    input_path: Path,
    output_path: Path,
    algorithm: str,
    precision: str,
    n_points: int | None,
    threads: int,
    bitmask: bool,
    timing: bool = False,
    n_slices: int | None = None,
) -> list[str]:
    cmd = [
        str(binary),
        "calc",
        f"--algorithm={algorithm}",
        f"--threads={threads}",
        f"--precision={precision}",
    ]
    if n_points is not None:
        cmd.append(f"--n-points={n_points}")
    if n_slices is not None:
        cmd.append(f"--n-slices={n_slices}")
    if bitmask:
        cmd.append("--use-bitmask")
    if timing:
        cmd.append("--timing")
    cmd.extend([str(input_path), str(output_path)])
    return cmd


def batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_jsonl: Path,
    precision: str,
    n_points: int,
    threads: int,
    bitmask: bool,
) -> list[str]:
    cmd = [
        str(binary),
        "batch",
        str(input_dir),
        "--format=jsonl",
        "-o",
        str(output_jsonl),
        f"--threads={threads}",
        f"--precision={precision}",
        f"--n-points={n_points}",
    ]
    if bitmask:
        cmd.append("--use-bitmask")
    return cmd


def freesasa_batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    n_points: int,
    threads: int,
) -> list[str]:
    return [
        str(binary),
        str(input_dir),
        str(output_dir),
        f"--n-threads={threads}",
        f"--n-points={n_points}",
    ]


def freesasa_single_command(
    *,
    binary: Path,
    input_path: Path,
    n_points: int,
    threads: int,
    timing: bool = False,
) -> list[str]:
    cmd = [
        str(binary),
        "--shrake-rupley",
        f"--resolution={n_points}",
        f"--n-threads={threads}",
    ]
    if timing:
        cmd.append("--timing")
    cmd.append(str(input_path))
    return cmd


def rustsasa_single_command(
    *,
    binary: Path,
    input_path: Path,
    output_path: Path,
    n_points: int,
    threads: int,
    timing: bool = False,
) -> list[str]:
    cmd = [
        str(binary),
        str(input_path),
        str(output_path),
        "-n",
        str(n_points),
        "-f",
        "json",
        "-t",
        str(threads),
        "-o",
        "protein",
        "--allow-vdw-fallback",
    ]
    if timing:
        cmd.append("--timing")
    return cmd


def lahuta_batch_command(
    *,
    binary: Path,
    input_dir: Path,
    output_dir: Path,
    n_points: int,
    threads: int,
    bitmask: bool,
) -> list[str]:
    cmd = [
        str(binary),
        "sasa-sr",
        "-d",
        str(input_dir),
        "--is_af2_model",
        "--points",
        str(n_points),
        "-t",
        str(threads),
        "--output",
        str(output_dir),
        "--progress",
        "0",
    ]
    if bitmask:
        cmd.append("--use-bitmask")
    return cmd


def mdtraj_runner_command(
    *,
    tool: str,
    xtc: Path,
    pdb: Path,
    n_points: int,
    stride: int,
    python: Path | str | None = None,
    output: Path | None = None,
    threads: int | None = None,
    precision: str | None = None,
    classifier: str | None = None,
    include_hydrogens: bool | None = None,
    zsasa_binary: Path | None = None,
) -> list[str]:
    cmd = [
        str(python or sys.executable),
        "-m",
        "scripts.benchlib.trajectory_tools",
        "--tool",
        tool,
        "--xtc",
        str(xtc),
        "--pdb",
        str(pdb),
        "--n-points",
        str(n_points),
        "--stride",
        str(stride),
    ]
    if threads is not None:
        cmd.extend(["--threads", str(threads)])
    if precision is not None:
        cmd.extend(["--precision", precision])
    if classifier is not None:
        cmd.extend(["--classifier", classifier])
    if include_hydrogens is not None:
        cmd.append("--include-hydrogens" if include_hydrogens else "--no-hydrogens")
    if zsasa_binary is not None:
        cmd.extend(["--zsasa-binary", str(zsasa_binary)])
    if output is not None:
        cmd.extend(["--output", str(output)])
    return cmd
