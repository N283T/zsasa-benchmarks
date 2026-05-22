"""CLI entrypoint for trajectory benchmark tools.

The native dry-run runners emit commands through this module so each planned
trajectory invocation has one importable entrypoint, an explicit output path,
and a small command-stub mode for tests. Real execution is implemented for the
same tool labels used by the historical trajectory benchmark scripts, while
unit tests exercise command construction without running large trajectories.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, NoReturn

SUPPORTED_TOOLS = {
    "zig",
    "zig_bitmask",
    "mdtraj",
    "mdsasa_bolt",
    "zsasa_mdtraj",
    "zsasa_mdtraj_bitmask",
    "zsasa_mdanalysis",
    "zsasa_mdanalysis_bitmask",
}

DEFAULT_ZSASA_BINARY = "zsasa"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=sorted(SUPPORTED_TOOLS))
    parser.add_argument("--xtc", required=True, type=Path)
    parser.add_argument("--pdb", required=True, type=Path)
    parser.add_argument("--n-points", required=True, type=int)
    parser.add_argument("--stride", required=True, type=int)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--precision", choices=["f32", "f64"], default="f64")
    parser.add_argument("--classifier", default="naccess")
    parser.add_argument("--zsasa-binary", type=Path, default=Path(DEFAULT_ZSASA_BINARY))
    parser.add_argument("--output", required=True, type=Path)
    hydrogen = parser.add_mutually_exclusive_group()
    hydrogen.add_argument(
        "--include-hydrogens",
        action="store_true",
        default=True,
        help="include explicit hydrogens (trajectory benchmark default)",
    )
    hydrogen.add_argument(
        "--no-hydrogens",
        action="store_false",
        dest="include_hydrogens",
        help="exclude explicit hydrogens when a backend supports it",
    )
    parser.add_argument(
        "--write-command-stub",
        action="store_true",
        help="write a deterministic command-shape stub instead of running a benchmark",
    )
    return parser.parse_args()


def build_zsasa_traj_command(
    *,
    binary: Path,
    xtc: Path,
    pdb: Path,
    output_csv: Path,
    n_points: int,
    stride: int,
    threads: int,
    precision: str,
    use_bitmask: bool,
    include_hydrogens: bool,
    classifier: str,
) -> list[str]:
    """Build a zsasa CLI trajectory command matching historical MD benches."""
    cmd = [
        str(binary),
        "traj",
        str(xtc),
        str(pdb),
        "--include-hydrogens" if include_hydrogens else "--no-hydrogens",
        f"--classifier={classifier}",
        f"--threads={threads}",
        f"--precision={precision}",
        f"--stride={stride}",
        f"--n-points={n_points}",
    ]
    if use_bitmask:
        cmd.append("--use-bitmask")
    cmd.extend(["-o", str(output_csv), "-q"])
    return cmd


def write_json_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_command_stub(args: argparse.Namespace) -> None:
    write_json_output(
        args.output,
        {
            "tool": args.tool,
            "xtc": str(args.xtc),
            "pdb": str(args.pdb),
            "n_points": args.n_points,
            "stride": args.stride,
            "threads": args.threads,
            "precision": args.precision,
            "classifier": args.classifier,
            "include_hydrogens": args.include_hydrogens,
            "zsasa_binary": str(args.zsasa_binary),
            "status": "command_stub_only",
        },
    )


def _totals_payload(*, args: argparse.Namespace, totals_a2: list[float]) -> dict[str, Any]:
    return {
        "tool": args.tool,
        "xtc": str(args.xtc),
        "pdb": str(args.pdb),
        "n_points": args.n_points,
        "stride": args.stride,
        "threads": args.threads,
        "precision": args.precision,
        "classifier": args.classifier,
        "include_hydrogens": args.include_hydrogens,
        "n_frames": len(totals_a2),
        "total_sasa_a2": totals_a2,
    }


def parse_zsasa_csv_totals(path: Path) -> list[float]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [float(row["total_sasa"]) for row in reader]


def resolve_zsasa_binary(path: Path) -> Path:
    env_binary = os.environ.get("ZSASA_CLI")
    if env_binary:
        return Path(os.path.expanduser(env_binary))
    if path.parent == Path("."):
        found = shutil.which(str(path))
        if found:
            return Path(found)
    return path


def run_zsasa_cli(args: argparse.Namespace, *, use_bitmask: bool) -> None:
    binary = resolve_zsasa_binary(args.zsasa_binary)
    with tempfile.NamedTemporaryFile(suffix=".csv", prefix="zsasa_traj_") as tmp:
        output_csv = Path(tmp.name)
        cmd = build_zsasa_traj_command(
            binary=binary,
            xtc=args.xtc,
            pdb=args.pdb,
            output_csv=output_csv,
            n_points=args.n_points,
            stride=args.stride,
            threads=args.threads,
            precision=args.precision,
            use_bitmask=use_bitmask,
            include_hydrogens=args.include_hydrogens,
            classifier=args.classifier,
        )
        subprocess.run(cmd, check=True)
        totals = parse_zsasa_csv_totals(output_csv)
    write_json_output(args.output, _totals_payload(args=args, totals_a2=totals))


def run_mdtraj(args: argparse.Namespace) -> None:
    import mdtraj as md

    traj = md.load(str(args.xtc), top=str(args.pdb), stride=args.stride)
    sasa = md.shrake_rupley(traj, n_sphere_points=args.n_points, mode="atom")
    totals = [float(value) * 100.0 for value in sasa.sum(axis=1)]
    write_json_output(args.output, _totals_payload(args=args, totals_a2=totals))


def run_zsasa_mdtraj(args: argparse.Namespace, *, use_bitmask: bool) -> None:
    import mdtraj as md
    from zsasa.mdtraj import compute_sasa

    traj = md.load(str(args.xtc), top=str(args.pdb), stride=args.stride)
    totals_nm2 = compute_sasa(
        traj,
        n_points=args.n_points,
        n_threads=args.threads,
        mode="total",
        use_bitmask=use_bitmask,
    )
    totals = [float(value) * 100.0 for value in totals_nm2]
    write_json_output(args.output, _totals_payload(args=args, totals_a2=totals))


def run_zsasa_mdanalysis(args: argparse.Namespace, *, use_bitmask: bool) -> None:
    import MDAnalysis as mda
    from zsasa.mdanalysis import SASAAnalysis

    universe = mda.Universe(str(args.pdb), str(args.xtc))
    analysis = SASAAnalysis(universe)
    analysis.run(
        step=args.stride,
        n_points=args.n_points,
        n_threads=args.threads,
        use_bitmask=use_bitmask,
    )
    totals = [float(value) for value in analysis.results.total_area]
    write_json_output(args.output, _totals_payload(args=args, totals_a2=totals))


def run_mdsasa_bolt(args: argparse.Namespace) -> None:
    import MDAnalysis as mda
    from mdsasa_bolt import SASAAnalysis

    universe = mda.Universe(str(args.pdb), str(args.xtc))
    sasa = SASAAnalysis(universe.atoms, n_points=args.n_points)
    sasa.run(step=args.stride)
    totals_raw = getattr(getattr(sasa, "results", None), "total_area", [])
    totals = [float(value) for value in totals_raw]
    write_json_output(args.output, _totals_payload(args=args, totals_a2=totals))


def fail_unknown_tool(tool: str) -> NoReturn:
    raise SystemExit(f"unsupported trajectory benchmark tool: {tool}")


def run_tool(args: argparse.Namespace) -> None:
    tool = str(args.tool)
    if tool == "zig":
        run_zsasa_cli(args, use_bitmask=False)
    elif tool == "zig_bitmask":
        run_zsasa_cli(args, use_bitmask=True)
    elif tool == "mdtraj":
        run_mdtraj(args)
    elif tool == "zsasa_mdtraj":
        run_zsasa_mdtraj(args, use_bitmask=False)
    elif tool == "zsasa_mdtraj_bitmask":
        run_zsasa_mdtraj(args, use_bitmask=True)
    elif tool == "zsasa_mdanalysis":
        run_zsasa_mdanalysis(args, use_bitmask=False)
    elif tool == "zsasa_mdanalysis_bitmask":
        run_zsasa_mdanalysis(args, use_bitmask=True)
    elif tool == "mdsasa_bolt":
        run_mdsasa_bolt(args)
    else:
        fail_unknown_tool(tool)


def main() -> None:
    args = parse_args()
    if args.write_command_stub:
        write_command_stub(args)
        return
    # Avoid hidden thread oversubscription for Python tools when the runner asks
    # for a specific thread count. Backend libraries may ignore these variables.
    if args.threads > 0:
        os.environ.setdefault("OMP_NUM_THREADS", str(args.threads))
        os.environ.setdefault("OPENBLAS_NUM_THREADS", str(args.threads))
    run_tool(args)


if __name__ == "__main__":
    main()
