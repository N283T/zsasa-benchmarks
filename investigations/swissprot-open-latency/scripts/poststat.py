"""After stat-ing a cold block (no open at all), does the scanner keep working on those files?"""

import os
import time

import assay

names = sorted(e.name for e in os.scandir(assay.ROOT) if e.name.endswith(".pdb"))
cursor = int(open(assay.CURSOR).read())
N = 8000
block = [names[(cursor + i) % len(names)] for i in range(N)]
open(assay.CURSOR, "w").write(str((cursor + N) % len(names)))
far = (cursor + 120_000) % len(names)
for i in range(300_000):
    os.stat(os.path.join(assay.ROOT, names[(far + i) % len(names)]))
time.sleep(3)

def rate(seconds, label):
    d0 = assay.defender_cpu()
    t0 = time.perf_counter()
    time.sleep(seconds)
    used = assay.defender_cpu() - d0
    print(f"{label:38s} Defender {used:6.2f} CPU-s in {time.perf_counter() - t0:4.1f} s", flush=True)

rate(8, "idle baseline")
d0 = assay.defender_cpu()
t0 = time.perf_counter()
for name in block:
    os.stat(os.path.join(assay.ROOT, name))
print(f"stat of {N} cold files took {time.perf_counter() - t0:.2f} s, Defender {assay.defender_cpu() - d0:.2f} CPU-s", flush=True)
for k in range(6):
    rate(4, f"after stat, {k * 4:2d}-{k * 4 + 4:2d} s")
print(f"total since stat: Defender {assay.defender_cpu() - d0:.2f} CPU-s ({(assay.defender_cpu() - d0) / N * 1e3:.2f} ms/file)")
