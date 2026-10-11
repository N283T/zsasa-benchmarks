"""Cold open latency by syscall form: open(O_RDONLY) as fopen does, vs openat(AT_FDCWD, O_RDONLY|O_CLOEXEC). Read-only."""

import ctypes
import os
import statistics
import sys
import threading
import time

libc = ctypes.CDLL(None, use_errno=True)
libc.open.argtypes = [ctypes.c_char_p, ctypes.c_int]
libc.openat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
AT_FDCWD = -2
O_CLOEXEC = 0x1000000


def plain_open(path: bytes) -> int:
    return libc.open(path, os.O_RDONLY)


def openat_cloexec(path: bytes) -> int:
    return libc.openat(AT_FDCWD, path, os.O_RDONLY | O_CLOEXEC)


def run(label, paths, opener, threads=10):
    it = iter(paths)
    lock = threading.Lock()
    lat = []

    def worker():
        mine = []
        while True:
            with lock:
                path = next(it, None)
            if path is None:
                break
            t0 = time.perf_counter()
            fd = opener(path)
            t1 = time.perf_counter()
            if fd < 0:
                raise OSError(ctypes.get_errno(), path)
            size = os.fstat(fd).st_size
            while size > 0:
                size -= len(os.read(fd, size))
            os.close(fd)
            mine.append((t1 - t0) * 1e3)
        with lock:
            lat.extend(mine)

    ts = [threading.Thread(target=worker) for _ in range(threads)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    lat.sort()
    print(f"{label:34s} {len(paths) / wall:6.0f} files/s  open mean {statistics.fmean(lat):5.2f}  p50 {lat[len(lat) // 2]:5.2f}  p95 {lat[int(len(lat) * 0.95)]:5.2f} ms", flush=True)


root = sys.argv[1]
n = int(sys.argv[2])
names = sorted(e.name for e in os.scandir(root) if e.name.endswith(".pdb"))
pool = [os.path.join(root, x).encode() for x in names[150_000 : 150_000 + 4 * n]]
for i, (label, opener) in enumerate([
    ("open(O_RDONLY)", plain_open),
    ("openat(AT_FDCWD, RDONLY|CLOEXEC)", openat_cloexec),
    ("open(O_RDONLY) repeat", plain_open),
    ("openat(...) repeat", openat_cloexec),
]):
    run(label, pool[i::4], opener)
