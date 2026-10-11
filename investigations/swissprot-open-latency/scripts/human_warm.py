"""Warm Human and E. coli AFDB PDB sets: mmap against a single read, same build, alternating."""

import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "zsasa-readfix")
SETS = {"Human": "/Users/nagaet/pdb/afdb/UP000005640_9606_HUMAN_v6/pdb", "E. coli": "/Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6/pdb"}
ZA = ["--format=jsonl", "-o", "/dev/null", "--threads=10", "--precision=f32", "--n-points=128", "--classifier=protor", "-q"]

for name, path in SETS.items():
    n = sum(1 for e in os.scandir(path) if e.name.endswith(".pdb"))
    for mode_args, mode in ((["--use-bitmask"], "bitmask"), ([], "standard")):
        subprocess.run([BIN, "batch", path, *ZA, *mode_args], capture_output=True)  # warm-up
        times = {"mmap": [], "read": []}
        for rep in range(4):
            for io in (("mmap", "read") if rep % 2 == 0 else ("read", "mmap")):
                t0 = time.perf_counter()
                proc = subprocess.Popen([BIN, "batch", path, *ZA, *mode_args, f"--input-io={io}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                _, _, ru = os.wait4(proc.pid, 0)
                times[io].append(time.perf_counter() - t0)
        fmt = lambda xs: " ".join(f"{x:6.2f}" for x in xs)  # noqa: E731
        m, r = sorted(times["mmap"])[1:3], sorted(times["read"])[1:3]
        print(f"{name:8s} {mode:8s} {n:6d} files  mmap {fmt(times['mmap'])} s  read {fmt(times['read'])} s  "
              f"median mmap {sum(m) / 2:6.2f}  read {sum(r) / 2:6.2f}  ({(sum(r) / sum(m) - 1) * 100:+.1f}%)", flush=True)
