"""Interleaved zsasa / Lahuta runs on disjoint cold subsets of the Swiss-Prot directory.

Each subset is every k-th file of one sorted range, so all subsets have the
same size distribution. Inputs are symlinks; outputs are removed after each run.
"""

import os
import resource
import shutil
import subprocess
import sys
import time

ROOT = "/Users/nagaet/pdb/afdb/swissprot_pdb_v6"
ZSASA = "/nix/store/mhwkiafxdy31wn7bmz3f4zd0am9n4whx-zsasa-0.9.0/bin/zsasa-0.9.0"
LAHUTA = "/nix/store/b3p88xra8id76i9zk9yhrdkpmpqbkw96-lahuta-2.0.3/bin/lahuta"
WORK = os.path.abspath("ab_work")
PER_SUBSET = int(sys.argv[1])
PLAN = sys.argv[2].split(",")
DEFENDER = ("wdavdaemon", "epsext", "Microsoft Defender")


def defender_cpu() -> float:
    out = subprocess.run(["ps", "-axo", "cputime=,command="], capture_output=True, text=True).stdout
    total = 0.0
    for line in out.splitlines():
        cpu, _, command = line.strip().partition(" ")
        if any(tag in command for tag in DEFENDER):
            parts = [float(x) for x in cpu.split(":")]
            total += sum(p * 60**i for i, p in enumerate(reversed(parts)))
    return total


def command(kind: str, src: str, out: str) -> list[str]:
    if kind == "lahuta":
        return [LAHUTA, "sasa-sr", "-d", src, "--is_af2_model", "--points", "128", "-t", "10",
                "--output", out, "--progress", "0", "--use-bitmask"]
    cmd = [ZSASA, "batch", src, "--format=jsonl", "-o", out + ".jsonl", "--threads=10",
           "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask"]
    if kind == "zsasa-read":
        cmd.append("--input-io=read")
    return cmd


def main() -> None:
    names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))
    k = len(PLAN)
    pool = names[320_000 : 320_000 + PER_SUBSET * k]
    shutil.rmtree(WORK, ignore_errors=True)
    for i in range(k):
        d = os.path.join(WORK, f"in{i}")
        os.makedirs(d)
        for name in pool[i::k]:
            os.symlink(os.path.join(ROOT, name), os.path.join(d, name))
    time.sleep(5)  # let the scanner settle after the symlink burst

    for i, kind in enumerate(PLAN):
        src = os.path.join(WORK, f"in{i}")
        out = os.path.join(WORK, f"out{i}")
        size = sum(os.stat(os.path.join(src, n)).st_size for n in os.listdir(src))
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        d0 = defender_cpu()
        t0 = time.perf_counter()
        proc = subprocess.run(command(kind, src, out), capture_output=True, text=True)
        wall = time.perf_counter() - t0
        d1 = defender_cpu()
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
        n = PER_SUBSET
        out_bytes = sum(
            os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(WORK) for f in fs if "out" in dp or f.endswith(".jsonl")
        )
        print(
            f"{i} {kind:11s} rc={proc.returncode} wall {wall:6.1f} s  {n / wall:6.0f} files/s  "
            f"tool CPU {cpu / n * 1e3:5.2f} ms/file (busy {cpu / wall:4.1f})  "
            f"wait {(10 * wall - cpu) / n * 1e3:5.2f} ms/file  "
            f"Defender CPU {(d1 - d0) / n * 1e3:5.2f} ms/file (busy {(d1 - d0) / wall:4.1f})  "
            f"in {size / 1e9:4.2f} GB  out {out_bytes / 1e9:4.2f} GB",
            flush=True,
        )
        if proc.returncode != 0:
            print(proc.stderr[-600:], flush=True)
        for entry in os.listdir(WORK):
            if entry.startswith("out"):
                path = os.path.join(WORK, entry)
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        time.sleep(3)
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    main()
