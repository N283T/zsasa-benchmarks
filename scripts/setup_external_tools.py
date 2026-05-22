#!/usr/bin/env python3
"""Set up pinned external comparator tools under the ignored external/ tree."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
EXTERNAL: Final = ROOT.joinpath("external")
BIN: Final = EXTERNAL.joinpath("bin")
FREESASA_BATCH_SRC: Final = ROOT.joinpath("tools", "freesasa_batch")
DEFAULT_TESTDATA: Final = Path.home().joinpath("freesasa-zig", "benchmarks", "external", "testdata")


@dataclass(frozen=True)
class ToolPlan:
    name: str
    repo: str | None
    ref: str | None
    commit: str | None
    directory: Path
    binary: Path
    link_name: str


TOOLS: Final[dict[str, ToolPlan]] = {
    "freesasa": ToolPlan(
        name="freesasa",
        repo="https://github.com/N283T/freesasa.git",
        ref="feat/add-timing",
        commit="9c9f204fd990ba2f50f47be8d4b96a61355f7a10",
        directory=EXTERNAL.joinpath("freesasa"),
        binary=EXTERNAL.joinpath("freesasa", "src", "freesasa"),
        link_name="freesasa",
    ),
    "freesasa_batch": ToolPlan(
        name="freesasa_batch",
        repo=None,
        ref=None,
        commit=None,
        directory=EXTERNAL.joinpath("freesasa_batch"),
        binary=EXTERNAL.joinpath("freesasa_batch", "freesasa_batch"),
        link_name="freesasa_batch",
    ),
    "rustsasa": ToolPlan(
        name="rustsasa",
        repo="https://github.com/N283T/RustSASA.git",
        ref="feat/add-timing",
        commit="530277785533d0336bbdb43b041fb7de2f7e23f3",
        directory=EXTERNAL.joinpath("rustsasa"),
        binary=EXTERNAL.joinpath("rustsasa", "target", "release", "rust-sasa"),
        link_name="rust-sasa",
    ),
    "lahuta": ToolPlan(
        name="lahuta",
        repo="https://github.com/bisejdiu/lahuta.git",
        ref=None,
        commit="4b5d6f9ae2bc13bcf897b1df3483b9c1e3da1de9",
        directory=EXTERNAL.joinpath("lahuta"),
        binary=EXTERNAL.joinpath("lahuta", "build", "cli", "lahuta"),
        link_name="lahuta",
    ),
}
DEFAULT_TOOLS: Final = ["freesasa", "freesasa_batch", "rustsasa", "lahuta"]


class SetupError(RuntimeError):
    """Raised when external tool setup fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tools", nargs="*", choices=[*DEFAULT_TOOLS, "verify"], default=DEFAULT_TOOLS
    )
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    parser.add_argument(
        "--reset", action="store_true", help="remove selected external build dirs first"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print commands without changing files"
    )
    parser.add_argument("--no-nix", action="store_true", help="do not auto-enter nix develop")
    parser.add_argument("--verify", action="store_true", help="run smoke verification after setup")
    parser.add_argument("--testdata", type=Path, default=DEFAULT_TESTDATA)
    return parser.parse_args()


def maybe_reexec_in_nix(args: argparse.Namespace) -> None:
    if args.no_nix or args.dry_run or os.environ.get("IN_NIX_SHELL"):
        return
    if os.environ.get("ZSASA_BENCH_EXTERNAL_NO_NIX"):
        return
    if shutil.which("nix") is None:
        print("WARNING: nix not found; continuing with current environment", file=sys.stderr)
        return
    os.execvp(
        "nix",
        [
            "nix",
            "develop",
            str(ROOT),
            "--command",
            "python",
            str(Path(__file__).resolve()),
            *sys.argv[1:],
            "--no-nix",
        ],
    )


def info(message: str) -> None:
    print(f"==> {message}")


def run(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> None:
    prefix = f"cd {cwd} && " if cwd else ""
    print("+ " + prefix + subprocess.list2cmdline(cmd))
    if dry_run:
        return
    subprocess.run(cmd, cwd=cwd, check=True)


def remove_path(path: Path, *, dry_run: bool) -> None:
    if not path.exists() and not path.is_symlink():
        return
    print(f"rm -rf {path}")
    if dry_run:
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def symlink(binary: Path, link_name: str, *, external_dir: Path, dry_run: bool) -> None:
    link = external_dir.joinpath("bin", link_name)
    print(f"ln -sf {binary} {link}")
    if dry_run:
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(binary)


def clone_checkout(plan: ToolPlan, *, dry_run: bool, assume_missing: bool = False) -> None:
    if plan.repo is None or plan.commit is None:
        return
    if assume_missing or not plan.directory.exists():
        cmd = ["git", "clone", "--recursive"]
        if plan.ref:
            cmd.extend(["--branch", plan.ref])
        cmd.extend([plan.repo, str(plan.directory)])
        run(cmd, dry_run=dry_run)
    else:
        run(["git", "fetch", "--tags", "--prune"], cwd=plan.directory, dry_run=dry_run)
    run(["git", "checkout", plan.commit], cwd=plan.directory, dry_run=dry_run)
    run(
        ["git", "submodule", "update", "--init", "--recursive"], cwd=plan.directory, dry_run=dry_run
    )


def build_freesasa(plan: ToolPlan, *, jobs: int, reset: bool, dry_run: bool) -> None:
    info("FreeSASA fork with timing")
    if reset:
        remove_path(plan.directory, dry_run=dry_run)
        remove_path(EXTERNAL.joinpath("bin", plan.link_name), dry_run=dry_run)
    clone_checkout(plan, dry_run=dry_run, assume_missing=reset)
    if not plan.binary.exists() or reset or dry_run:
        run(["autoreconf", "-i"], cwd=plan.directory, dry_run=dry_run)
        run(
            ["./configure", "--enable-threads", "--disable-json", "--disable-xml"],
            cwd=plan.directory,
            dry_run=dry_run,
        )
        run(["make", f"-j{jobs}"], cwd=plan.directory, dry_run=dry_run)
    symlink(plan.binary, plan.link_name, external_dir=EXTERNAL, dry_run=dry_run)


def build_freesasa_batch(plan: ToolPlan, *, dry_run: bool, reset: bool) -> None:
    info("freesasa_batch wrapper")
    if reset:
        remove_path(plan.directory, dry_run=dry_run)
        remove_path(EXTERNAL.joinpath("bin", plan.link_name), dry_run=dry_run)
    if not EXTERNAL.joinpath("freesasa", "src", "libfreesasa.a").exists() and not dry_run:
        raise SetupError(
            "freesasa_batch requires external/freesasa/src/libfreesasa.a; build freesasa first"
        )
    if not plan.binary.exists() or reset or dry_run:
        run(
            [
                "make",
                f"FREESASA={EXTERNAL.joinpath('freesasa')}",
                f"OUT={plan.binary}",
            ],
            cwd=FREESASA_BATCH_SRC,
            dry_run=dry_run,
        )
    symlink(plan.binary, plan.link_name, external_dir=EXTERNAL, dry_run=dry_run)


def build_rustsasa(plan: ToolPlan, *, reset: bool, dry_run: bool) -> None:
    info("RustSASA fork with timing")
    if reset:
        remove_path(plan.directory, dry_run=dry_run)
        remove_path(EXTERNAL.joinpath("bin", plan.link_name), dry_run=dry_run)
    clone_checkout(plan, dry_run=dry_run, assume_missing=reset)
    if not plan.binary.exists() or reset or dry_run:
        run(
            ["cargo", "build", "--release", "--features", "cli"],
            cwd=plan.directory,
            dry_run=dry_run,
        )
    symlink(plan.binary, plan.link_name, external_dir=EXTERNAL, dry_run=dry_run)


def build_lahuta(plan: ToolPlan, *, jobs: int, reset: bool, dry_run: bool) -> None:
    info("Lahuta")
    if reset:
        remove_path(plan.directory, dry_run=dry_run)
        remove_path(EXTERNAL.joinpath("bin", plan.link_name), dry_run=dry_run)
    clone_checkout(plan, dry_run=dry_run, assume_missing=reset)
    if not plan.binary.exists() or reset or dry_run:
        run(
            [
                "cmake",
                "-B",
                "build",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DLAHUTA_BUILD_PYTHON=OFF",
                "-DLAHUTA_BUILD_SHARED_CORE=OFF",
                "-DLAHUTA_BUILD_EXAMPLES=OFF",
                "-DBUILD_TESTING=OFF",
                "-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF",
            ],
            cwd=plan.directory,
            dry_run=dry_run,
        )
        run(
            ["cmake", "--build", "build", "--target", "lahuta", "--config", "Release", f"-j{jobs}"],
            cwd=plan.directory,
            dry_run=dry_run,
        )
    symlink(plan.binary, plan.link_name, external_dir=EXTERNAL, dry_run=dry_run)


def first_pdb(testdata: Path) -> Path:
    pdbs = sorted(testdata.glob("*.pdb"))
    if not pdbs:
        raise SetupError(f"no PDB files found in {testdata}")
    return pdbs[0]


def verify_tools(*, testdata: Path, dry_run: bool) -> None:
    info("Smoke verification")
    pdb = first_pdb(testdata)
    tmp = Path(os.environ.get("TMPDIR", "/tmp")).joinpath("zsasa-bench-external-smoke")
    commands = [
        [str(BIN.joinpath("freesasa")), str(pdb)],
        [str(BIN.joinpath("freesasa_batch")), str(testdata), str(tmp.joinpath("freesasa_batch"))],
        [str(BIN.joinpath("rust-sasa")), str(pdb), str(tmp.joinpath("rustsasa_out"))],
        [
            str(BIN.joinpath("lahuta")),
            "sasa-sr",
            "-f",
            str(pdb),
            "-o",
            str(tmp.joinpath("lahuta.jsonl")),
            "--progress",
            "0",
            "--is_af2_model",
        ],
    ]
    if not dry_run:
        tmp.mkdir(parents=True, exist_ok=True)
    for cmd in commands:
        run(cmd, dry_run=dry_run)


def selected_tools(raw_tools: list[str]) -> list[str]:
    tools = raw_tools if raw_tools else DEFAULT_TOOLS
    if "verify" in tools:
        return [tool for tool in tools if tool != "verify"]
    return tools


def main() -> None:
    args = parse_args()
    maybe_reexec_in_nix(args)
    if not args.dry_run:
        EXTERNAL.mkdir(parents=True, exist_ok=True)
        BIN.mkdir(parents=True, exist_ok=True)
    tools = selected_tools(args.tools)
    for tool in tools:
        plan = TOOLS[tool]
        if tool == "freesasa":
            build_freesasa(plan, jobs=args.jobs, reset=args.reset, dry_run=args.dry_run)
        elif tool == "freesasa_batch":
            build_freesasa_batch(plan, reset=args.reset, dry_run=args.dry_run)
        elif tool == "rustsasa":
            build_rustsasa(plan, reset=args.reset, dry_run=args.dry_run)
        elif tool == "lahuta":
            build_lahuta(plan, jobs=args.jobs, reset=args.reset, dry_run=args.dry_run)
        else:
            raise SetupError(f"unsupported tool: {tool}")
    if args.verify or "verify" in args.tools:
        testdata = Path(os.path.expandvars(str(args.testdata))).expanduser()
        verify_tools(testdata=testdata, dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except (SetupError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
