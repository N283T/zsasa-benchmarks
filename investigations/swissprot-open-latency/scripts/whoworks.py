"""Which processes burn CPU during a stat-only pass, the seconds after it, and a cold or pre-stat-ed run?"""

import os
import shutil
import subprocess
import time

import assay

names = sorted(e.name for e in os.scandir(assay.ROOT) if e.name.endswith(".pdb"))
N = 8000


def snapshot() -> dict:
    out = subprocess.run(["ps", "-axo", "pid=,cputime=,comm="], capture_output=True, text=True).stdout
    snap = {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        t = [float(x) for x in parts[1].split(":")]
        snap[(parts[0], os.path.basename(parts[2]))] = sum(p * 60**i for i, p in enumerate(reversed(t)))
    return snap


def report(label, before, after, n=N):
    deltas = sorted(((after[k] - before.get(k, 0.0), k[1]) for k in after), reverse=True)
    top = ", ".join(f"{name[:26]} {d:.2f}" for d, name in deltas[:7] if d >= 0.05)
    print(f"{label:34s} {top}", flush=True)


def fresh_block():
    cursor = int(open(assay.CURSOR).read())
    block = [names[(cursor + i) % len(names)] for i in range(N)]
    open(assay.CURSOR, "w").write(str((cursor + N) % len(names)))
    d = os.path.join(assay.HERE, "ww_in")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for name in block:
        os.symlink(os.path.join(assay.ROOT, name), os.path.join(d, name))
    far = (cursor + 120_000) % len(names)
    for i in range(300_000):
        os.stat(os.path.join(assay.ROOT, names[(far + i) % len(names)]))
    time.sleep(3)
    return d


def run_mimic(d):
    subprocess.run([assay.VARS["mimic"], d, "--mode=read", "--spin-us=2700"], capture_output=True)


d = fresh_block()
s0 = snapshot(); time.sleep(8); report("idle 8 s", s0, snapshot())
s0 = snapshot()
for name in os.listdir(d):
    os.stat(os.path.join(d, name))
s1 = snapshot(); report("stat-only pass", s0, s1)
time.sleep(8); s2 = snapshot(); report("8 s after the stat pass", s1, s2)
run_mimic(d); s3 = snapshot(); report("mimic run, pre-stat-ed block", s2, s3)
d = fresh_block()
s0 = snapshot(); run_mimic(d); report("mimic run, cold block", s0, snapshot())
shutil.rmtree(d, ignore_errors=True)
