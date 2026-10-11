"""Full-directory runs of the mimic program: processing order (sorted or readdir) x up-front stat."""

import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import full_run3 as base  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
N = base.N_FILES

for i, spec in enumerate(sys.argv[1].split(",")):
    flags = ["--" + f for f in spec.split("+")[1:]]
    mode, spin = spec.split("+")[0].split(":")
    cmd = [os.path.join(HERE, "mimic"), base.ROOT, f"--mode={mode}", f"--spin-us={spin}", *flags]
    subprocess.run(["sync"])
    d0 = base.defender_cpu()
    started = time.strftime("%H:%M:%S")
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    err = proc.stderr.read()
    _, status, usage = os.wait4(proc.pid, 0)
    wall = time.perf_counter() - t0
    d1 = base.defender_cpu()
    cpu = usage.ru_utime + usage.ru_stime
    m = re.search(r"MIMIC .*", err)
    f = dict(kv.split("=") for kv in m.group(0).split()[1:]) if m else {}
    pre = re.search(r"prestat ([\d.]+) s", err)
    inner = float(f.get("wall", "nan"))
    print(
        f"{i} {spec:34s} start {started}  wall {wall:6.1f} s (workers {inner:6.1f} s{', prestat ' + pre.group(1) + ' s' if pre else ''})  "
        f"{N / inner:5.0f} files/s  CPU {cpu / N * 1e3:4.2f}  wait {(10 * inner - cpu) / N * 1e3:5.2f} ms/file  "
        f"open {float(f.get('open_ms', 'nan')):5.2f}  data {float(f.get('data_ms', 'nan')):4.2f}  Defender {(d1 - d0) / N * 1e3:4.2f} ms/file",
        flush=True,
    )
    time.sleep(10)
