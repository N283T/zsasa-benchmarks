"""Cold-block assay runner.

Plan file: one run per line, "label | command"; {in} is the input directory, {out} an output path.
A line starting with "+" reuses the previous block (second or later pass); "sleep N" waits.
Blocks are consecutive slices of the sorted Swiss-Prot names, taken round-robin from a persistent cursor.
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/nagaet/pdb/afdb/swissprot_pdb_v6"
WORK = os.path.join(HERE, "work")
CURSOR = os.path.join(HERE, "cursor.txt")
LOG = os.path.join(HERE, "assay.log")
N = int(os.environ.get("ASSAY_N", "8000"))
THREADS = 10
EVICT = int(os.environ.get("ASSAY_EVICT", "300000"))
DEFENDER = ("wdavdaemon", "epsext", "Microsoft Defender")
VARS = {
    "zsasa": "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa",
    "lahuta": "/nix/store/b3p88xra8id76i9zk9yhrdkpmpqbkw96-lahuta-2.0.3/bin/lahuta",
    "mimic": os.path.join(HERE, "mimic"),
    "zargs": "--format=jsonl --threads=10 --precision=f32 --n-points=128 --classifier=protor --use-bitmask --timing --profile-stages",
    "largs": "--is_af2_model --points 128 -t 10 --progress 0 --use-bitmask",
    "here": HERE,
}


def defender_cpu() -> float:
    out = subprocess.run(["ps", "-axo", "cputime=,command="], capture_output=True, text=True).stdout
    total = 0.0
    for line in out.splitlines():
        cpu, _, command = line.strip().partition(" ")
        if any(tag in command for tag in DEFENDER):
            parts = [float(x) for x in cpu.split(":")]
            total += sum(p * 60**i for i, p in enumerate(reversed(parts)))
    return total


def emit(text: str) -> None:
    print(text, flush=True)
    with open(LOG, "a") as f:
        f.write(text + "\n")


def main() -> None:
    names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))
    cursor = int(open(CURSOR).read()) if os.path.exists(CURSOR) else 330_000
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    block_dir = None
    block_id = 0
    emit(f"## {time.strftime('%H:%M:%S')} plan {sys.argv[1]} (cursor {cursor}, N {N})")
    for raw in open(sys.argv[1]):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("sleep "):
            time.sleep(float(line.split()[1]))
            continue
        reuse = line.startswith("+")
        label, _, cmd = line.lstrip("+ ").partition("|")
        threads = THREADS
        m = re.search(r"\[t=(\d+)\]", label)
        if m:
            threads = int(m.group(1))
        if not reuse:
            if block_dir:
                shutil.rmtree(block_dir, ignore_errors=True)
            block_id += 1
            block_dir = os.path.join(WORK, f"in{block_id}")
            os.makedirs(block_dir)
            block = [names[(cursor + i) % len(names)] for i in range(N)]
            cursor = (cursor + N) % len(names)
            open(CURSOR, "w").write(str(cursor))
            for name in block:
                os.symlink(os.path.join(ROOT, name), os.path.join(block_dir, name))
            if EVICT:
                far = (cursor + 120_000) % len(names)
                for i in range(EVICT):
                    os.stat(os.path.join(ROOT, names[(far + i) % len(names)]))
            time.sleep(2)
        if "@prestat" in label:
            for name in os.listdir(block_dir):
                os.stat(os.path.join(block_dir, name))
            lead = re.search(r"@lead=(\d+)", label)
            time.sleep(float(lead.group(1)) if lead else 1)
        if "@evict" in label:
            far = (cursor + 120_000) % len(names)
            for i in range(EVICT or 300_000):
                os.stat(os.path.join(ROOT, names[(far + i) % len(names)]))
            time.sleep(1)
        out = os.path.join(WORK, "out")
        argv = shlex.split(cmd.strip().format(**{"in": block_dir, "out": out}, **VARS))
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        free_gb = int(re.search(r"Pages free:\s+(\d+)", vm).group(1)) * 16384 / 1e9
        d0 = defender_cpu()
        t0 = time.perf_counter()
        env_extra = dict(kv.split("=") for kv in re.findall(r"@env:(\w+=\w+)", label))
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env={**os.environ, **env_extra})
        err = proc.stderr.read()
        _, status, usage = os.wait4(proc.pid, 0)
        wall = time.perf_counter() - t0
        d1 = defender_cpu()
        cpu = usage.ru_utime + usage.ru_stime
        extra = ""
        m = re.search(r"BATCH_READ_PARSE_TIME_MS:([\d.]+)", err)
        if m:
            extra = f" | read+parse {float(m.group(1)) / N:5.2f}"
        m = re.search(r"MIMIC .*", err)
        if m:
            f = dict(kv.split("=") for kv in m.group(0).split()[1:])
            extra = f" | open {float(f['open_ms']):5.2f}  data {float(f['data_ms']):4.2f}  close {float(f['close_ms']):4.2f}  write {float(f['write_ms']):4.2f}"
        rc = os.waitstatus_to_exitcode(status)
        emit(
            f"{'+' if reuse else ' '} {label.strip():44s} {N / wall:6.0f} files/s  CPU {cpu / N * 1e3:5.2f}  "
            f"wait {(threads * wall - cpu) / N * 1e3:5.2f}  Defender {(d1 - d0) / N * 1e3:4.2f} ms/file  free {free_gb:4.1f} GB{extra}"
            + (f"  rc={rc} {err[-200:]!r}" if rc else "")
        )
        for entry in os.listdir(WORK):
            if entry.startswith("out"):
                path = os.path.join(WORK, entry)
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        time.sleep(2)
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    main()
