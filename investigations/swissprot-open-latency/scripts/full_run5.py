"""Full Swiss-Prot runs testing two levers on zsasa 0.9.0: stat-ing files ahead of the workers, and a lower QoS clamp.

"pacer": a helper thread stats files in zsasa's processing order, staying WINDOW files ahead of the
number of finished results (counted from the JSONL output). "upfront": every file is stat-ed once
before zsasa starts, as Lahuta's directory source does. Helper time is inside the measured wall time.
"""

import os
import shutil
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import full_run3 as base  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = base.WORK
OUT = os.path.join(WORK, "out.jsonl")
N = base.N_FILES
WINDOW = 20_000
REAL_ZSASA = "/nix/store/wasadywb88gj4g78hrm2nwis477yriqz-zsasa-0.9.0/bin/zsasa"
ZCMD = [REAL_ZSASA, "batch", base.ROOT, "--format=jsonl", "-o", OUT, "--threads=10", "--precision=f32",
        "--n-points=128", "--classifier=protor", "--use-bitmask"]
LCMD = [base.BINARIES["lahuta-2.0.3"], "sasa-sr", "-d", base.ROOT, "--is_af2_model", "--points", "128", "-t", "10",
        "--output", os.path.join(WORK, "out"), "--progress", "0", "--use-bitmask"]
UTILITY = ["/usr/sbin/taskpolicy", "-c", "utility"]


def pacer(names: list[str], stop: threading.Event, stats: dict) -> None:
    done = 0
    cursor = 0
    pos = 0
    while not stop.is_set():
        try:
            with open(OUT, "rb") as f:
                f.seek(pos)
                while chunk := f.read(8 << 20):
                    done += chunk.count(b"\n")
                    pos += len(chunk)
        except FileNotFoundError:
            pass
        target = min(done + WINDOW, len(names))
        while cursor < target:
            os.stat(os.path.join(base.ROOT, names[cursor]))
            cursor += 1
        stats["stat_calls"] = cursor
        time.sleep(0.1)


def main() -> None:
    plan = sys.argv[1].split(",")
    names = sorted(e.name for e in os.scandir(base.ROOT) if e.name.endswith(".pdb"))
    shutil.rmtree(WORK, ignore_errors=True)
    for i, kind in enumerate(plan):
        os.makedirs(WORK)
        subprocess.run(["sync"])
        parts = kind.split("+")
        cmd = LCMD if parts[0] == "lahuta" else ZCMD
        if "utility" in parts:
            cmd = UTILITY + cmd
        d0 = base.defender_cpu()
        started = time.strftime("%H:%M:%S")
        t0 = time.perf_counter()
        stop = threading.Event()
        stats: dict = {}
        helper = None
        note = ""
        if "upfront" in parts:
            for name in names:
                os.stat(os.path.join(base.ROOT, name))
            note = f"  upfront stat {time.perf_counter() - t0:.1f} s"
        if "pacer" in parts:
            for name in names[:WINDOW]:
                os.stat(os.path.join(base.ROOT, name))
            helper = threading.Thread(target=pacer, args=(names, stop, stats))
        with open(os.path.join(HERE, f"full_run5_{i}_{kind}.stderr"), "w") as err:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err)
        if helper:
            helper.start()
        _, status, usage = os.wait4(proc.pid, 0)
        wall = time.perf_counter() - t0
        stop.set()
        if helper:
            helper.join()
            note += f"  pacer stat calls {stats.get('stat_calls', 0)}"
        d1 = base.defender_cpu()
        cpu = usage.ru_utime + usage.ru_stime
        lines = base.count_lines()
        print(
            f"{i} {kind:22s} rc={os.waitstatus_to_exitcode(status)} start {started}  wall {wall:6.1f} s  {N / wall:5.0f} files/s  "
            f"CPU {cpu / N * 1e3:4.2f}  wait {(10 * wall - cpu) / N * 1e3:5.2f} ms/file  busy {cpu / wall:4.2f}  "
            f"Defender {(d1 - d0) / N * 1e3:4.2f} ms/file  lines {lines}{note}",
            flush=True,
        )
        shutil.rmtree(WORK, ignore_errors=True)
        time.sleep(10)


if __name__ == "__main__":
    main()
