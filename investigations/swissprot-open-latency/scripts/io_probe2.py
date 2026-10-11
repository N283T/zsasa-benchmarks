"""Thread sweep of cold open/read latency, then the same block again warm. Read-only."""

import os
import sys

import io_probe


def main() -> None:
    root = sys.argv[1]
    n = int(sys.argv[2])
    names = sorted(e.name for e in os.scandir(root) if e.name.endswith(".pdb"))
    cursor = len(names) // 2  # away from the blocks the first probe read
    last: list[str] = []
    for threads in (1, 2, 5, 10, 20, 40):
        io_probe.THREADS = threads
        last = names[cursor : cursor + n]
        cursor += n
        io_probe.run(f"cold, {threads:2d} threads", root, last, io_probe.read_whole, False)
    for threads in (40, 10, 1):
        io_probe.THREADS = threads
        io_probe.run(f"warm (same block), {threads:2d} threads", root, last, io_probe.read_whole, False)


if __name__ == "__main__":
    main()
