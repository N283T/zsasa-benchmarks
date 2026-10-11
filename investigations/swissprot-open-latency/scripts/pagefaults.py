"""Page faults and context switches per file for each tool on a warm 6,000-file block. Leaves its work directory in place."""

import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/nagaet/pdb/afdb/swissprot_pdb_v6"
WORK = os.path.join(HERE, "pf_work")
IN = os.path.join(WORK, "in")
N = 6000
LAHUTA = "/nix/store/b3p88xra8id76i9zk9yhrdkpmpqbkw96-lahuta-2.0.3/bin/lahuta"
ZA = ["--format=jsonl", "--threads=10", "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask", "-q"]

if not os.path.isdir(IN):
    os.makedirs(IN)
    names = sorted(e.name for e in os.scandir(ROOT) if e.name.endswith(".pdb"))[30000 : 30000 + N]
    for name in names:
        os.symlink(os.path.join(ROOT, name), os.path.join(IN, name))


def run(label: str, argv: list[str]) -> None:
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _, _, ru = os.wait4(proc.pid, 0)
    print(f"{label:32s} minor faults/file {ru.ru_minflt / N:7.1f}  major/file {ru.ru_majflt / N:5.2f}  "
          f"voluntary switches/file {ru.ru_nvcsw / N:6.1f}  involuntary/file {ru.ru_nivcsw / N:6.1f}  "
          f"sys {ru.ru_stime / N * 1e3:4.2f} ms/file  RSS {ru.ru_maxrss / 2**20:5.0f} MiB", flush=True)


zs = os.path.join(HERE, "zsasa-opt")
zr = os.path.join(HERE, "zsasa-readonce")
out = os.path.join(WORK, "o.jsonl")
run("(warm-up)", [zs, "batch", IN, "-o", "/dev/null", *ZA])
run("zsasa mmap, output discarded", [zs, "batch", IN, "-o", "/dev/null", *ZA])
run("zsasa mmap, output file", [zs, "batch", IN, "-o", out, *ZA])
run("zsasa one read, discarded", [zr, "batch", IN, "-o", "/dev/null", *ZA, "--input-io=read"])
run("zsasa one read, output file", [zr, "batch", IN, "-o", out, *ZA, "--input-io=read"])
run("lahuta", [LAHUTA, "sasa-sr", "-d", IN, "--is_af2_model", "--points", "128", "-t", "10",
               "--output", os.path.join(WORK, "lo"), "--progress", "0", "--use-bitmask"])
run("mimic read + 2.7 ms", [os.path.join(HERE, "mimic"), IN, "--mode=read", "--spin-us=2700"])
run("mimic mmap + 2.7 ms", [os.path.join(HERE, "mimic"), IN, "--mode=mmap", "--spin-us=2700"])
