"""Human AFDB PDB, two halves: first (cold) and repeated (warm) passes of zsasa 0.9.0 and Lahuta 2.0.3."""

import os
import re
import shutil
import subprocess
import time

import full_run3 as base

ROOT = "/Users/nagaet/pdb/afdb/UP000005640_9606_HUMAN_v6/pdb"
WORK = os.path.join(base.HERE, "human_work")
THREADS = 10
PLAN = [("lahuta", 0, "first open"), ("zsasa", 1, "first open"), ("zsasa", 0, "opened once by Lahuta"),
        ("lahuta", 1, "opened once by zsasa"), ("zsasa", 0, "warm"), ("lahuta", 1, "warm"),
        ("zsasa", 1, "warm"), ("lahuta", 0, "warm")]


def command(kind: str, src: str, out: str) -> list[str]:
    if kind == "lahuta":
        return [base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", src, "--is_af2_model", "--points", "128", "-t", "10",
                "--output", out, "--progress", "0", "--use-bitmask"]
    return [base.BINARIES["zsasa"], "batch", src, "--format=jsonl", "-o", out + ".jsonl", "--threads=10",
            "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask", "--timing", "--profile-stages"]


names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))
shutil.rmtree(WORK, ignore_errors=True)
halves = []
for h in range(2):
    d = os.path.join(WORK, f"in{h}")
    os.makedirs(d)
    part = names[h::2]
    for name in part:
        os.symlink(os.path.join(ROOT, name), os.path.join(d, name))
    halves.append((d, len(part)))
time.sleep(5)

for i, (kind, h, state) in enumerate(PLAN):
    src, n = halves[h]
    out = os.path.join(WORK, f"out{i}")
    d0 = base.defender_cpu()
    t0 = time.perf_counter()
    proc = subprocess.Popen(command(kind, src, out), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    err = proc.stderr.read()
    _, status, usage = os.wait4(proc.pid, 0)
    wall = time.perf_counter() - t0
    d1 = base.defender_cpu()
    cpu = usage.ru_utime + usage.ru_stime
    cycle = THREADS * wall / n * 1e3
    stages = {k: float(v) / n for k, v in re.findall(r"BATCH_(READ_PARSE|SASA|JSONL_WRITE)_TIME_MS:([\d.]+)", err)}
    extra = (f" | read+parse {stages['READ_PARSE']:5.2f}  sasa {stages['SASA']:4.2f}  jsonl {stages['JSONL_WRITE']:4.2f}" if stages else "")
    print(
        f"{i} {kind:6s} half {h} {state:22s} wall {wall:5.1f} s  {n / wall:5.0f} files/s  busy {cpu / wall:4.1f}  "
        f"CPU {cpu / n * 1e3:5.2f}  wait {cycle - cpu / n * 1e3:5.2f} ms/file  Defender {(d1 - d0) / n * 1e3:4.2f} ms/file{extra}",
        flush=True,
    )
    for entry in os.listdir(WORK):
        if entry.startswith("out"):
            path = os.path.join(WORK, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    time.sleep(3)
shutil.rmtree(WORK, ignore_errors=True)
