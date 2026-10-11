"""Full Swiss-Prot runs of zsasa 0.9.0 with stage timings: mmap/read input, kept/discarded output.

10 threads, bitmask. Stage times are thread-time sums reported by --profile-stages.
"""

import os
import re
import shutil
import subprocess
import sys
import time

import full_run3 as base

HERE = base.HERE
N = base.N_FILES
THREADS = 10
VARIANTS = {
    "mmap": ([], True),
    "read": (["--input-io=read"], True),
    "mmap-null": ([], False),
    "read-null": (["--input-io=read"], False),
}


def command(kind: str) -> list[str]:
    extra, keep_output = VARIANTS[kind]
    out = os.path.join(base.WORK, "out.jsonl") if keep_output else "/dev/null"
    return [base.BINARIES["zsasa"], "batch", base.ROOT, "--format=jsonl", "-o", out, f"--threads={THREADS}",
            "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask",
            "--timing", "--profile-stages", *extra]


def main() -> None:
    plan = sys.argv[1].split(",")
    shutil.rmtree(base.WORK, ignore_errors=True)
    for i, kind in enumerate(plan):
        os.makedirs(base.WORK)
        subprocess.run(["sync"])
        err_path = os.path.join(HERE, f"full_run4_{i}_{kind}.stderr")
        d0 = base.defender_cpu()
        started = time.strftime("%H:%M:%S")
        t0 = time.perf_counter()
        with open(err_path, "w") as err:
            proc = subprocess.Popen(command(kind), stdout=subprocess.DEVNULL, stderr=err)
        _, status, usage = os.wait4(proc.pid, 0)
        wall = time.perf_counter() - t0
        d1 = base.defender_cpu()
        cpu = usage.ru_utime + usage.ru_stime
        stages = {k: float(v) for k, v in re.findall(r"BATCH_(\w+)_TIME_MS:([\d.]+)", open(err_path).read())}
        per = {k: stages.get(k, float("nan")) / N for k in ("READ_PARSE", "CLASSIFIER", "SASA", "JSONL_WRITE")}
        cycle = THREADS * wall / N * 1e3
        lines = base.count_lines()
        print(
            f"{i} {kind:9s} rc={os.waitstatus_to_exitcode(status)} start {started}  wall {wall:6.1f} s  "
            f"{N / wall:5.0f} files/s  CPU {cpu / N * 1e3:4.2f}  wait {cycle - cpu / N * 1e3:4.2f}  cycle {cycle:5.2f} ms/file | "
            f"read+parse {per['READ_PARSE']:5.2f}  classify {per['CLASSIFIER']:4.2f}  sasa {per['SASA']:4.2f}  "
            f"jsonl {per['JSONL_WRITE']:4.2f}  other {cycle - sum(per.values()):5.2f} | "
            f"Defender {(d1 - d0) / N * 1e3:4.2f} ms/file  RSS {usage.ru_maxrss / 2**20:5.0f} MiB  lines {lines}",
            flush=True,
        )
        shutil.rmtree(base.WORK, ignore_errors=True)
        time.sleep(10)


if __name__ == "__main__":
    main()
