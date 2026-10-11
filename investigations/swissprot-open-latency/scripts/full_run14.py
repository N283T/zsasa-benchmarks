"""Full Swiss-Prot runs under `taskpolicy -d passive`, sampled every 5 s: finished files, tool CPU, scanner CPU, memory state."""

import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import full_run3 as base  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = base.WORK
N = base.N_FILES
REAL_ZSASA = "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa"
CMDS = {
    "zsasa": [REAL_ZSASA, "batch", base.ROOT, "--format=jsonl", "-o", os.path.join(WORK, "out.jsonl"), "--threads=10",
              "--precision=f32", "--n-points=128", "--classifier=protor", "--use-bitmask"],
    "lahuta": [base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", base.ROOT, "--is_af2_model", "--points", "128", "-t", "10",
               "--output", os.path.join(WORK, "out"), "--progress", "0", "--use-bitmask"],
}
OUT = os.path.join(WORK, "out.jsonl")


def vm_state() -> dict:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    pages = {m.group(1): int(m.group(2)) for m in re.finditer(r"^(.+?):\s+(\d+)\.", out, re.M)}
    gb = lambda key: pages.get(key, 0) * 16384 / 1e9  # noqa: E731
    vnodes = subprocess.run(["sysctl", "-n", "kern.num_vnodes"], capture_output=True, text=True).stdout.strip()
    return {"free_gb": gb("Pages free"), "file_gb": gb("File-backed pages"), "inactive_gb": gb("Pages inactive"),
            "spec_gb": gb("Pages speculative"), "vnodes": vnodes}


shutil.rmtree(WORK, ignore_errors=True)
with open(os.path.join(HERE, "full_run14_samples.csv"), "w") as samples:
    samples.write("tool,elapsed_s,files_done,tool_cpu_s,defender_cpu_s,free_gb,file_gb,inactive_gb,spec_gb,vnodes\n")
    for kind in sys.argv[1].split(","):
        os.makedirs(WORK)
        subprocess.run(["sync"])
        d0 = base.defender_cpu()
        t0 = time.perf_counter()
        proc = subprocess.Popen(["/usr/sbin/taskpolicy", "-d", "passive", *CMDS[kind]],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        done, pos, next_sample = 0, 0, 5.0
        status, usage = 0, None
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            elapsed = time.perf_counter() - t0
            if elapsed >= next_sample:
                try:
                    with open(OUT, "rb") as f:
                        f.seek(pos)
                        while chunk := f.read(8 << 20):
                            done += chunk.count(b"\n")
                            pos += len(chunk)
                except FileNotFoundError:
                    pass
                vm = vm_state()
                samples.write(f"{kind},{time.perf_counter() - t0:.1f},{done},{base.process_cpu(proc.pid):.2f},"
                              f"{base.defender_cpu() - d0:.2f},{vm['free_gb']:.2f},{vm['file_gb']:.2f},"
                              f"{vm['inactive_gb']:.2f},{vm['spec_gb']:.2f},{vm['vnodes']}\n")
                samples.flush()
                next_sample += 5.0
            time.sleep(0.2)
        wall = time.perf_counter() - t0
        cpu = usage.ru_utime + usage.ru_stime
        print(f"{kind:7s} wall {wall:6.1f} s  {N / wall:5.0f} files/s  CPU {cpu / N * 1e3:4.2f}  "
              f"wait {(10 * wall - cpu) / N * 1e3:5.2f} ms/file  Defender {(base.defender_cpu() - d0) / N * 1e3:4.2f} ms/file  "
              f"lines {base.count_lines()}", flush=True)
        shutil.rmtree(WORK, ignore_errors=True)
        time.sleep(10)
