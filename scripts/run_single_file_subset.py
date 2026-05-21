#!/usr/bin/env python3
"""Run the curated single-file zsasa subset benchmark.

This wrapper intentionally reruns only zsasa variants. Comparator baselines
(FreeSASA/RustSASA) are reused from historical outputs for the first archive.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZSASA_ROOT = Path("/Users/nagaet/freesasa-zig")
DEFAULT_MANIFEST = ROOT.joinpath("manifests", "single-file-sample.toml")
DEFAULT_OUTPUT = ROOT.joinpath("results", "single", "subset_v0_6_0")
DEFAULT_TOOLS = ["zig_f64", "zig_f32", "zig_f64_bitmask", "zig_f32_bitmask"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--zsasa-root", type=Path, default=DEFAULT_ZSASA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--tools",
        default=",".join(DEFAULT_TOOLS),
        help="comma-separated bench.py tool names",
    )
    parser.add_argument("--threads", default="1,4,8,10")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--n-points", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--prepare", default="sync")
    parser.add_argument("--phase", choices=["all", "wall", "sasa"], default="all")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="run commands; otherwise print the plan",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing outputs")
    return parser.parse_args()


def load_selection(manifest_path: Path) -> list[str]:
    with manifest_path.open("rb") as handle:
        manifest = tomllib.load(handle)
    selection = manifest.get("subset", {}).get("selection")
    if not isinstance(selection, list) or not selection:
        raise SystemExit(f"missing subset.selection in {manifest_path}")
    return [str(item) for item in selection]


def write_sample_file(output_dir: Path, selection: list[str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_path = output_dir.joinpath("sample.json")
    sample_path.write_text(json.dumps({"samples": selection}, indent=2) + "\n", encoding="utf-8")
    return sample_path


def quote_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run(command: list[str], *, cwd: Path, execute: bool) -> None:
    print(quote_command(command), flush=True)
    if not execute:
        return
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT.joinpath(args.manifest)
    zsasa_root = args.zsasa_root
    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else ROOT.joinpath(args.output_dir)
    )
    bench_py = zsasa_root.joinpath("benchmarks", "scripts", "bench.py")

    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")
    if not bench_py.exists():
        raise SystemExit(f"bench.py not found: {bench_py}")

    tools = [tool.strip() for tool in args.tools.split(",") if tool.strip()]
    if not tools:
        raise SystemExit("no tools selected")

    selection = load_selection(manifest_path)
    sample_path = write_sample_file(output_dir, selection)

    print(f"manifest={manifest_path}")
    print(f"zsasa_root={zsasa_root}")
    print(f"output_dir={output_dir}")
    print(f"sample_file={sample_path}")
    print(f"structures={len(selection)}")
    print(f"tools={','.join(tools)}")
    print(f"threads={args.threads}")
    print(f"mode={'execute' if args.execute else 'plan'}")

    # Build once up front so all tools use the same release-fast binary.
    if args.execute:
        run(["zig", "build", "-Doptimize=ReleaseFast"], cwd=zsasa_root, execute=True)
        run(
            [str(zsasa_root.joinpath("zig-out", "bin", "zsasa")), "--version"],
            cwd=zsasa_root,
            execute=True,
        )

    for tool in tools:
        if args.phase in {"all", "wall"}:
            command = [
                str(bench_py),
                "wall",
                "--tool",
                tool,
                "--threads",
                args.threads,
                "--runs",
                str(args.runs),
                "--warmup",
                str(args.warmup),
                "--n-points",
                str(args.n_points),
                "--sample-file",
                str(sample_path),
                "--output-dir",
                str(output_dir.joinpath("wall", f"{tool}_sr")),
                "--timeout",
                str(args.timeout),
            ]
            if args.prepare:
                command.extend(["--prepare", args.prepare])
            if args.force:
                command.append("--force")
            run(command, cwd=zsasa_root, execute=args.execute)

        if args.phase in {"all", "sasa"}:
            command = [
                str(bench_py),
                "sasa",
                "--tool",
                tool,
                "--threads",
                args.threads,
                "--n-points",
                str(args.n_points),
                "--sample-file",
                str(sample_path),
                "--output-dir",
                str(output_dir.joinpath("timing", f"{tool}_sr")),
                "--timeout",
                str(args.timeout),
            ]
            if args.force:
                command.append("--force")
            run(command, cwd=zsasa_root, execute=args.execute)


if __name__ == "__main__":
    main()
