"""Cold-read probe: per-file open/read latency by visiting order and read method.

Read-only. Each condition uses its own block of files so that every file is
read once, from a cold cache.
"""

import os
import queue
import statistics
import sys
import threading
import time

THREADS = 10
QUEUE_DEPTH = 1024


def read_whole(fd: int) -> int:
    size = os.fstat(fd).st_size
    total = 0
    while total < size:
        chunk = os.read(fd, size - total)
        if not chunk:
            break
        total += len(chunk)
    return total


def read_4k(fd: int) -> int:
    total = 0
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return total
        total += len(chunk)


def run(label: str, root: str, names: list[str], reader, stat_ahead: bool) -> None:
    q: queue.Queue = queue.Queue(maxsize=QUEUE_DEPTH)
    open_ms: list[float] = []
    read_ms: list[float] = []
    nbytes = [0]
    lock = threading.Lock()

    def worker() -> None:
        lo: list[float] = []
        lr: list[float] = []
        b = 0
        while True:
            path = q.get()
            if path is None:
                break
            t0 = time.perf_counter()
            fd = os.open(path, os.O_RDONLY)
            t1 = time.perf_counter()
            b += reader(fd)
            t2 = time.perf_counter()
            os.close(fd)
            lo.append((t1 - t0) * 1e3)
            lr.append((t2 - t1) * 1e3)
        with lock:
            open_ms.extend(lo)
            read_ms.extend(lr)
            nbytes[0] += b

    workers = [threading.Thread(target=worker) for _ in range(THREADS)]
    start = time.perf_counter()
    for w in workers:
        w.start()
    stat_s = 0.0
    for name in names:
        path = os.path.join(root, name)
        if stat_ahead:
            s0 = time.perf_counter()
            os.stat(path)
            stat_s += time.perf_counter() - s0
        q.put(path)
    for _ in workers:
        q.put(None)
    for w in workers:
        w.join()
    wall = time.perf_counter() - start

    n = len(names)
    open_ms.sort()
    read_ms.sort()
    print(
        f"{label:34s} {n / wall:7.0f} files/s  {nbytes[0] / wall / 1e6:6.0f} MB/s  "
        f"open mean {statistics.fmean(open_ms):5.2f} p50 {open_ms[n // 2]:5.2f} p95 {open_ms[int(n * 0.95)]:6.2f} ms  "
        f"read mean {statistics.fmean(read_ms):5.2f} p50 {read_ms[n // 2]:5.2f} p95 {read_ms[int(n * 0.95)]:6.2f} ms  "
        f"stat-ahead {stat_s / n * 1e3:5.2f} ms/file",
        flush=True,
    )


def median_inode_step(inodes: list[int]) -> float:
    return statistics.median(abs(b - a) for a, b in zip(inodes, inodes[1:]))


def main() -> None:
    root = sys.argv[1]
    n = int(sys.argv[2])

    t0 = time.perf_counter()
    entries = [(e.name, e.inode()) for e in os.scandir(root) if e.name.endswith(".pdb")]
    print(
        f"scandir: {len(entries)} files in {time.perf_counter() - t0:.1f} s", flush=True
    )

    inode_of = dict(entries)
    readdir_names = [name for name, _ in entries]
    sorted_names = sorted(readdir_names)
    print(
        "median inode step between neighbours: "
        f"readdir order {median_inode_step([i for _, i in entries]):.0f}, "
        f"sorted order {median_inode_step([inode_of[x] for x in sorted_names]):.0f}",
        flush=True,
    )

    used: set[str] = set()
    cursors = {"sorted": len(sorted_names) // 5, "readdir": 0}
    sources = {"sorted": sorted_names, "readdir": readdir_names}

    def take(order: str) -> list[str]:
        src = sources[order]
        block: list[str] = []
        i = cursors[order]
        while len(block) < n:
            name = src[i]
            i += 1
            if name not in used:
                used.add(name)
                block.append(name)
        cursors[order] = i
        return block

    plan = [
        ("sorted  + whole read (zsasa read)", "sorted", read_whole, False),
        ("readdir + 4K reads", "readdir", read_4k, False),
        ("readdir + 4K reads + stat-ahead", "readdir", read_4k, True),
        ("sorted  + 4K reads", "sorted", read_4k, False),
        ("readdir + whole read", "readdir", read_whole, False),
        ("sorted  + whole read + stat-ahead", "sorted", read_whole, True),
        ("sorted  + whole read (repeat)", "sorted", read_whole, False),
    ]
    for label, order, reader, stat_ahead in plan:
        run(label, root, take(order), reader, stat_ahead)


if __name__ == "__main__":
    main()
