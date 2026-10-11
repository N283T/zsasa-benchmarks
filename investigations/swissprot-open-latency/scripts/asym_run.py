"""Does the scanner's cost depend on which program opens a file, and on what opened it before?

Cold Swiss-Prot blocks; each block is opened by a sequence of tools. 10 threads, bitmask.
"""

import os
import re
import shutil
import subprocess
import time

import full_run3 as base

ROOT = base.ROOT
WORK = os.path.join(base.HERE, "asym_work")
THREADS = 10
N = 8000
SEQUENCES = [
    ["lahuta", "zsasa", "zsasa"],
    ["zsasa", "lahuta", "lahuta"],
    ["zsasa", "zsasa"],
    ["lahuta", "lahuta"],
    ["lahuta", "zsasa-read", "zsasa-read"],
    ["zsasa-read", "lahuta"],
]


def command(kind: str, src: str, out: str) -> list[str]:
    if kind == "lahuta":
        return [base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", src, "--is_af2_model", "--points", "128", "-t", "10",
                "--output", out, "--progress", "0", "--use-bitmask"]
    cmd = [base.BINARIES["zsasa"], "batch", src, "--format=jsonl", "-o", out + ".jsonl", "--threads=10",
           "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask", "--timing", "--profile-stages"]
    if kind == "zsasa-read":
        cmd.append("--input-io=read")
    return cmd


names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))
k = len(SEQUENCES)
pool = names[200_000 : 200_000 + N * k]
shutil.rmtree(WORK, ignore_errors=True)
for b in range(k):
    d = os.path.join(WORK, f"in{b}")
    os.makedirs(d)
    for name in pool[b::k]:
        os.symlink(os.path.join(ROOT, name), os.path.join(d, name))
time.sleep(5)

for b, seq in enumerate(SEQUENCES):
    src = os.path.join(WORK, f"in{b}")
    for step, kind in enumerate(seq):
        out = os.path.join(WORK, "out")
        d0 = base.defender_cpu()
        t0 = time.perf_counter()
        proc = subprocess.Popen(command(kind, src, out), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        err = proc.stderr.read()
        _, status, usage = os.wait4(proc.pid, 0)
        wall = time.perf_counter() - t0
        d1 = base.defender_cpu()
        cpu = usage.ru_utime + usage.ru_stime
        m = re.search(r"BATCH_READ_PARSE_TIME_MS:([\d.]+)", err)
        extra = f"  read+parse {float(m.group(1)) / N:5.2f}" if m else ""
        history = " -> ".join(seq[:step]) or "(cold)"
        print(
            f"block {b}  {kind:10s} after {history:24s} {N / wall:5.0f} files/s  CPU {cpu / N * 1e3:4.2f}  "
            f"wait {(THREADS * wall - cpu) / N * 1e3:5.2f} ms/file  Defender {(d1 - d0) / N * 1e3:4.2f} ms/file{extra}",
            flush=True,
        )
        for entry in os.listdir(WORK):
            if entry.startswith("out"):
                path = os.path.join(WORK, entry)
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        time.sleep(2)
shutil.rmtree(WORK, ignore_errors=True)
