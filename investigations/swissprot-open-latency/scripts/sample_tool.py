"""Run a command on a fresh cold block, sample it for 4 s, and list kernel-entry leaf symbols of worker threads."""

import os
import re
import shlex
import shutil
import subprocess
import sys
import time

import assay

names = sorted(e.name for e in os.scandir(assay.ROOT) if e.name.endswith(".pdb"))
N = 8000
for label, cmd in [l.split("|") for l in sys.argv[1:]]:
    cursor = int(open(assay.CURSOR).read())
    block = [names[(cursor + i) % len(names)] for i in range(N)]
    open(assay.CURSOR, "w").write(str((cursor + N) % len(names)))
    d = os.path.join(assay.HERE, "st_in")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for name in block:
        os.symlink(os.path.join(assay.ROOT, name), os.path.join(d, name))
    far = (cursor + 120_000) % len(names)
    for i in range(300_000):
        os.stat(os.path.join(assay.ROOT, names[(far + i) % len(names)]))
    time.sleep(2)
    out = os.path.join(assay.HERE, "st_out")
    argv = shlex.split(cmd.strip().format(**{"in": d, "out": out}, **assay.VARS))
    t0 = time.perf_counter()
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    sfile = os.path.join(assay.HERE, "st.sample")
    subprocess.run(["sample", str(proc.pid), "4", "-file", sfile], capture_output=True)
    proc.wait()
    wall = time.perf_counter() - t0
    text = open(sfile).read()
    body = text[text.index("Call graph:"):text.index("Total number in stack")].split("\n")
    heads = [i for i, l in enumerate(body) if re.match(r"^\s+\d+ Thread_", l)] + [len(body)]
    agg, total = {}, 0
    for a, b in zip(heads, heads[1:]):
        sect = body[a:b]
        tot = int(re.match(r"^\s+(\d+)", sect[0]).group(1))
        frames = []
        for l in sect[1:]:
            m = re.match(r"^([\s+!:|]+)(\d+) (.+?)\s+\(in ([^)]+)\)", l)
            if m:
                frames.append((len(m.group(1)), int(m.group(2)), m.group(3), m.group(4)))
        leaf = {}
        for i, (depth, count, sym, lib) in enumerate(frames):
            if i + 1 == len(frames) or frames[i + 1][0] <= depth:
                key = sym if lib == "libsystem_kernel.dylib" else "(user code)"
                leaf[key] = leaf.get(key, 0) + count
        if leaf.get("__psynch_cvwait", 0) + leaf.get("__semwait_signal", 0) + leaf.get("mach_msg2_trap", 0) > 0.8 * tot:
            continue  # idle main / writer thread
        total += tot
        for k, v in leaf.items():
            agg[k] = agg.get(k, 0) + v
    top = ", ".join(f"{k} {v / total * 100:.1f}%" for k, v in sorted(agg.items(), key=lambda x: -x[1]) if v / total >= 0.002)
    print(f"{label.strip():24s} {N / wall:5.0f} files/s (sampled run) | {top}", flush=True)
    for p in (d, out, out + ".jsonl", sfile):
        shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else (os.path.exists(p) and os.remove(p))
