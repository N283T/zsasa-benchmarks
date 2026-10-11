"""Is --input-io honoured? Page faults per file on a warm block, old and fixed builds."""

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(HERE, "pf_work", "in")
N = 6000
ZA = ["--format=jsonl", "--threads=10", "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask", "-q"]
for label, binary, extra in [
    ("0.9.0 release, default", "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa", []),
    ("0.9.0 release, --input-io=read", "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa", ["--input-io=read"]),
    ("0.10.1 main, default", os.path.join(HERE, "zsasa-main"), []),
    ("0.10.1 main, --input-io=read", os.path.join(HERE, "zsasa-main"), ["--input-io=read"]),
    ("fixed build, default (mmap)", os.path.join(HERE, "zsasa-readfix"), []),
    ("fixed build, --input-io=mmap", os.path.join(HERE, "zsasa-readfix"), ["--input-io=mmap"]),
    ("fixed build, --input-io=read", os.path.join(HERE, "zsasa-readfix"), ["--input-io=read"]),
]:
    proc = subprocess.Popen([binary, "batch", IN, "-o", os.path.join(HERE, "pf_work", "o.jsonl"), *ZA, *extra],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _, _, ru = os.wait4(proc.pid, 0)
    lines = sum(1 for _ in open(os.path.join(HERE, "pf_work", "o.jsonl"), "rb"))
    print(f"{label:34s} minor faults/file {ru.ru_minflt / N:6.2f}  user {ru.ru_utime / N * 1e3:4.2f}  sys {ru.ru_stime / N * 1e3:4.2f} ms/file  lines {lines}", flush=True)
