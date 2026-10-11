"""One block of files, single thread: cold pass, then the same block warm. Read-only."""

import os
import sys

import io_probe

root, n, phase = sys.argv[1], int(sys.argv[2]), sys.argv[3]
names = sorted(e.name for e in os.scandir(root) if e.name.endswith(".pdb"))
start = len(names) * 3 // 4
io_probe.THREADS = 1
io_probe.run(f"{phase}, 1 thread", root, names[start : start + n], io_probe.read_whole, False)
