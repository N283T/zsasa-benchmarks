"""New default (one read) against main: identical output on PDB and mmCIF, page faults, and warm timings."""

import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.join(HERE, "zsasa-readdefault")
MAIN = os.path.join(HERE, "zsasa-main")
HUMAN = "/Users/nagaet/pdb/afdb/UP000005640_9606_HUMAN_v6"
ECOLI = "/Users/nagaet/pdb/afdb/UP000000625_83333_ECOLI_v6"
WORK = os.path.join(HERE, "rd_work")
os.makedirs(WORK, exist_ok=True)
BASE = ["--format=jsonl", "--threads=10", "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask", "-q"]


def sorted_lines(path):
    with open(path, "rb") as f:
        return sorted(f.read().splitlines())


def run(binary, src, out, extra=()):
    t0 = time.perf_counter()
    proc = subprocess.Popen([binary, "batch", src, "-o", out, *BASE, *extra], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _, status, ru = os.wait4(proc.pid, 0)
    return time.perf_counter() - t0, ru, os.waitstatus_to_exitcode(status)


# 1. identical output
for label, src, extra in (("E. coli PDB", ECOLI + "/pdb", ()), ("E. coli mmCIF, generic", ECOLI + "/cif", ()),
                          ("E. coli mmCIF, --af-model-fast", ECOLI + "/cif", ("--af-model-fast",))):
    a, b, c = (os.path.join(WORK, n) for n in ("main.jsonl", "new.jsonl", "new_mmap.jsonl"))
    run(MAIN, src, a, extra)
    run(NEW, src, b, extra)
    run(NEW, src, c, (*extra, "--input-io=mmap"))
    la, lb, lc = sorted_lines(a), sorted_lines(b), sorted_lines(c)
    print(f"{label:32s} {len(la)} rows  new default == main: {la == lb}  new --input-io=mmap == main: {la == lc}", flush=True)

# 2. warm timings, alternating
for label, src, extra in (("Human PDB, bitmask", HUMAN + "/pdb", ()), ("Human mmCIF generic, bitmask", HUMAN + "/cif", ()),
                          ("Human mmCIF --af-model-fast", HUMAN + "/cif", ("--af-model-fast",)),
                          ("E. coli mmCIF generic, bitmask", ECOLI + "/cif", ())):
    n = sum(1 for e in os.scandir(src) if not e.name.startswith("."))
    run(NEW, src, "/dev/null", extra)
    times = {"read": [], "mmap": []}
    faults = {}
    for rep in range(4):
        for io in (("mmap", "read") if rep % 2 == 0 else ("read", "mmap")):
            t, ru, rc = run(NEW, src, "/dev/null", (*extra, f"--input-io={io}"))
            times[io].append(t)
            faults[io] = ru.ru_minflt / n
    med = {k: sum(sorted(v)[1:3]) / 2 for k, v in times.items()}
    print(f"{label:32s} {n:6d} files  mmap {med['mmap']:6.2f} s ({faults['mmap']:5.1f} faults/file)  "
          f"read {med['read']:6.2f} s ({faults['read']:5.1f} faults/file)  read vs mmap {(med['read'] / med['mmap'] - 1) * 100:+.1f}%", flush=True)
