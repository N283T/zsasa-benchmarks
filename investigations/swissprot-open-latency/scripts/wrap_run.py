"""Cold first-open cost: zsasa through the Nix bash wrapper vs the real binary run directly vs Lahuta."""

import os
import re
import shutil
import subprocess
import sys
import time

import full_run3 as base

ROOT = base.ROOT
WORK = os.path.join(base.HERE, "wrap_work")
N = 8000
START = int(sys.argv[1])
PLAN = sys.argv[2].split(",")
REAL = "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa"
ZARGS = ["--format=jsonl", "--threads=10", "--precision=f32", "--n-points=128", "--classifier=protor",
         "--use-bitmask", "--timing", "--profile-stages"]


def command(kind: str, src: str, out: str) -> list[str]:
    if kind == "lahuta":
        return [base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", src, "--is_af2_model", "--points", "128", "-t", "10",
                "--output", out, "--progress", "0", "--use-bitmask"]
    if kind == "lahuta-via-bash":
        return ["/bin/bash", "-c", 'exec "$0" "$@"', base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", src,
                "--is_af2_model", "--points", "128", "-t", "10", "--output", out, "--progress", "0", "--use-bitmask"]
    binary = {"zsasa-wrapper": base.BINARIES["zsasa"], "zsasa-direct": REAL}[kind]
    return [binary, "batch", src, "-o", out + ".jsonl", *ZARGS]


names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))
k = len(PLAN)
pool = names[START : START + N * k]
shutil.rmtree(WORK, ignore_errors=True)
for b in range(k):
    d = os.path.join(WORK, f"in{b}")
    os.makedirs(d)
    for name in pool[b::k]:
        os.symlink(os.path.join(ROOT, name), os.path.join(d, name))
time.sleep(5)

for b, kind in enumerate(PLAN):
    src = os.path.join(WORK, f"in{b}")
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
    print(
        f"block {b}  {kind:16s} cold  {N / wall:5.0f} files/s  CPU {cpu / N * 1e3:4.2f}  "
        f"wait {(10 * wall - cpu) / N * 1e3:5.2f} ms/file  Defender {(d1 - d0) / N * 1e3:4.2f} ms/file{extra}",
        flush=True,
    )
    for entry in os.listdir(WORK):
        if entry.startswith("out"):
            path = os.path.join(WORK, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    time.sleep(2)
shutil.rmtree(WORK, ignore_errors=True)
