"""Run tools on cold blocks and read their rusage_info_v6: share of CPU time on P-cores, runnable (waiting for a core) time."""

import ctypes
import os
import shlex
import shutil
import subprocess
import sys
import time

import assay

FIELDS = ("user_time system_time pkg_idle_wkups interrupt_wkups pageins wired_size resident_size phys_footprint "
          "proc_start_abstime proc_exit_abstime child_user_time child_system_time child_pkg_idle_wkups "
          "child_interrupt_wkups child_pageins child_elapsed_abstime diskio_bytesread diskio_byteswritten "
          "cpu_time_qos_default cpu_time_qos_maintenance cpu_time_qos_background cpu_time_qos_utility "
          "cpu_time_qos_legacy cpu_time_qos_user_initiated cpu_time_qos_user_interactive billed_system_time "
          "serviced_system_time logical_writes lifetime_max_phys_footprint instructions cycles billed_energy "
          "serviced_energy interval_max_phys_footprint runnable_time flags user_ptime system_ptime pinstructions "
          "pcycles energy_nj penergy_nj secure_time_in_system secure_ptime_in_system neural_footprint "
          "lifetime_max_neural_footprint interval_max_neural_footprint").split()


class RUsage(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f, ctypes.c_uint64) for f in FIELDS] + [("reserved", ctypes.c_uint64 * 9)]


libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
TB = 125 / 3 * 1e-9  # mach ticks to seconds on Apple silicon


def rusage(pid: int):
    r = RUsage()
    if libproc.proc_pid_rusage(pid, 6, ctypes.byref(r)) != 0:
        return None
    return r


def main() -> None:
    names = sorted(e.name for e in os.scandir(assay.ROOT) if e.name.endswith(".pdb"))
    N = 8000
    # can we read the scanner's counters?
    for line in subprocess.run(["pgrep", "-f", "wdavdaemon_unprivileged"], capture_output=True, text=True).stdout.split():
        print("scanner rusage readable:", rusage(int(line)) is not None)
        break
    for spec in sys.argv[1:]:
        label, cmd = spec.split("|")
        warm = label.strip().startswith("+")
        if not warm:
            cursor = int(open(assay.CURSOR).read())
            block = [names[(cursor + i) % len(names)] for i in range(N)]
            open(assay.CURSOR, "w").write(str((cursor + N) % len(names)))
            d = os.path.join(assay.HERE, "pc_in")
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            for name in block:
                os.symlink(os.path.join(assay.ROOT, name), os.path.join(d, name))
            far = (cursor + 120_000) % len(names)
            for i in range(300_000):
                os.stat(os.path.join(assay.ROOT, names[(far + i) % len(names)]))
            time.sleep(2)
        out = os.path.join(assay.HERE, "pc_out")
        argv = shlex.split(cmd.strip().format(**{"in": d, "out": out}, **assay.VARS))
        t0 = time.perf_counter()
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        last = None
        while proc.poll() is None:
            r = rusage(proc.pid)
            if r is not None:
                last = r
            time.sleep(0.05)
        wall = time.perf_counter() - t0
        cpu = (last.user_time + last.system_time) * TB
        pcpu = (last.user_ptime + last.system_ptime) * TB
        print(
            f"{label.strip():30s} {N / wall:5.0f} files/s  CPU {cpu / N * 1e3:4.2f} ms/file  on P-cores {pcpu / cpu * 100:4.0f}%  "
            f"runnable-wait {last.runnable_time * TB / N * 1e3:5.2f} ms/file  instr/file {last.instructions / N / 1e6:5.1f} M  "
            f"IPC {last.instructions / max(last.cycles, 1):4.2f}  qos default {last.cpu_time_qos_default * TB / cpu * 100:3.0f}% "
            f"legacy {last.cpu_time_qos_legacy * TB / cpu * 100:3.0f}% utility {last.cpu_time_qos_utility * TB / cpu * 100:3.0f}%",
            flush=True,
        )
        for p in (out, out + ".jsonl"):
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else (os.path.exists(p) and os.remove(p))
    shutil.rmtree(os.path.join(assay.HERE, "pc_in"), ignore_errors=True)


main()
