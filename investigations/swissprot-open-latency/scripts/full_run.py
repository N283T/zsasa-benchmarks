"""Alternating full Swiss-Prot runs of Lahuta and zsasa (10 threads, bitmask).

Samples tool CPU, Defender CPU and output size every 10 s. Outputs are
counted and removed after each run.
"""

import os
import shutil
import subprocess
import sys
import time

ROOT = "/Users/nagaet/pdb/afdb/swissprot_pdb_v6"
ZSASA = "/nix/store/mhwkiafxdy31wn7bmz3f4zd0am9n4whx-zsasa-0.9.0/bin/zsasa-0.9.0"
LAHUTA = "/nix/store/b3p88xra8id76i9zk9yhrdkpmpqbkw96-lahuta-2.0.3/bin/lahuta"
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "full_work")
SAMPLES = os.path.join(HERE, "full_run_samples.csv")
DEFENDER = ("wdavdaemon", "epsext", "Microsoft Defender")
N_FILES = 550_122
INTERVAL = 10.0


def cputime_seconds(text: str) -> float:
    parts = [float(x) for x in text.split(":")]
    return sum(p * 60**i for i, p in enumerate(reversed(parts)))


def defender_cpu() -> float:
    out = subprocess.run(
        ["ps", "-axo", "cputime=,command="], capture_output=True, text=True
    ).stdout
    total = 0.0
    for line in out.splitlines():
        cpu, _, command = line.strip().partition(" ")
        if any(tag in command for tag in DEFENDER):
            total += cputime_seconds(cpu)
    return total


def process_cpu(pid: int) -> float:
    out = subprocess.run(
        ["ps", "-o", "cputime=", "-p", str(pid)], capture_output=True, text=True
    ).stdout.strip()
    return cputime_seconds(out) if out else float("nan")


def output_files() -> list[str]:
    return [os.path.join(dp, f) for dp, _, fs in os.walk(WORK) for f in fs]


def output_bytes() -> int:
    total = 0
    for path in output_files():
        try:
            total += os.path.getsize(path)
        except OSError:
            pass
    return total


def count_lines() -> int:
    lines = 0
    for path in output_files():
        with open(path, "rb", buffering=0) as f:
            while chunk := f.read(8 << 20):
                lines += chunk.count(b"\n")
    return lines


def command(kind: str, out: str) -> list[str]:
    if kind == "lahuta":
        return [
            LAHUTA,
            "sasa-sr",
            "-d",
            ROOT,
            "--is_af2_model",
            "--points",
            "128",
            "-t",
            "10",
            "--output",
            out,
            "--progress",
            "0",
            "--use-bitmask",
        ]
    return [
        ZSASA,
        "batch",
        ROOT,
        "--format=jsonl",
        "-o",
        out + ".jsonl",
        "--threads=10",
        "--precision=f32",
        "--n-points=128",
        "--classifier=protor",
        "--use-bitmask",
    ]


def main() -> None:
    plan = sys.argv[1].split(",")
    shutil.rmtree(WORK, ignore_errors=True)
    with open(SAMPLES, "w") as samples:
        samples.write("run,tool,elapsed_s,tool_cpu_s,defender_cpu_s,output_bytes\n")
        for i, kind in enumerate(plan):
            os.makedirs(WORK)
            subprocess.run(["sync"])
            d0 = defender_cpu()
            t0 = time.perf_counter()
            proc = subprocess.Popen(
                command(kind, os.path.join(WORK, "out")),
                stdout=subprocess.DEVNULL,
                stderr=open(os.path.join(HERE, f"full_run_{i}_{kind}.stderr"), "w"),
            )
            status, usage = 0, None
            next_sample = INTERVAL
            while True:
                pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
                if pid:
                    break
                elapsed = time.perf_counter() - t0
                if elapsed >= next_sample:
                    samples.write(
                        f"{i},{kind},{elapsed:.1f},{process_cpu(proc.pid):.2f},"
                        f"{defender_cpu() - d0:.2f},{output_bytes()}\n"
                    )
                    samples.flush()
                    next_sample += INTERVAL
                time.sleep(0.2)
            wall = time.perf_counter() - t0
            d1 = defender_cpu()
            cpu = usage.ru_utime + usage.ru_stime
            size = output_bytes()
            lines = count_lines()
            print(
                f"{i} {kind:7s} rc={os.waitstatus_to_exitcode(status)} wall {wall:7.1f} s  "
                f"{N_FILES / wall:6.1f} files/s  user {usage.ru_utime:7.1f} s  sys {usage.ru_stime:6.1f} s  "
                f"busy {cpu / wall:4.2f}  tool CPU {cpu / N_FILES * 1e3:5.2f} ms/file  "
                f"wait {(10 * wall - cpu) / N_FILES * 1e3:5.2f} ms/file  "
                f"Defender CPU {d1 - d0:7.1f} s ({(d1 - d0) / N_FILES * 1e3:5.2f} ms/file, busy {(d1 - d0) / wall:4.2f})  "
                f"peak RSS {usage.ru_maxrss / 2**20:6.1f} MiB  out {size / 1e9:5.2f} GB  lines {lines}  "
                f"finished {time.strftime('%H:%M:%S')}",
                flush=True,
            )
            shutil.rmtree(WORK, ignore_errors=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
