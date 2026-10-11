"""Paper-protocol Swiss-Prot runs through the zsasa-benchmarks harness, every tool under `taskpolicy -d passive`.

Three run ids, tool order alternating. Large JSONL outputs are counted and removed; hyperfine JSON is kept.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import full_run3 as base  # noqa: E402

BENCH = "/Users/nagaet/ghq/github.com/N283T/zsasa-benchmarks"
N = base.N_FILES
ENV = dict(os.environ)
ENV["PATH"] = (
    "/nix/store/mhwkiafxdy31wn7bmz3f4zd0am9n4whx-zsasa-0.9.0/bin:"
    "/nix/store/b3p88xra8id76i9zk9yhrdkpmpqbkw96-lahuta-2.0.3/bin:" + ENV["PATH"]
)
TOOLS = {
    "zsasa": ("zsasa_0_9_0_batch_f32_bitmask_10t_128p", "zsasa_0_9_0/f32_bitmask_10t_128p.jsonl"),
    "lahuta": ("lahuta_bitmask_10t_128p", "lahuta/bitmask_10t_128p.jsonl"),
}
PLAN = [("r1", "zsasa"), ("r1", "lahuta"), ("r2", "lahuta"), ("r2", "zsasa"), ("r3", "zsasa"), ("r3", "lahuta")]


def count_lines(path: str) -> int:
    lines = 0
    with open(path, "rb", buffering=0) as f:
        while chunk := f.read(8 << 20):
            lines += chunk.count(b"\n")
    return lines


for rnd, tool in PLAN:
    run_id = f"v0_9_0_swissprot_passive_io_{rnd}"
    name, out_rel = TOOLS[tool]
    out_base = os.path.join(BENCH, "results/full_rerun", run_id, "batch/swissprot")
    d0 = base.defender_cpu()
    started = time.strftime("%H:%M:%S")
    proc = subprocess.run(
        ["uv", "run", "python", "scripts/run_batch.py", "--manifest", "manifests/batch-swissprot-passive-io.toml",
         "--run-id", run_id, "--only", name, "--execute"],
        cwd=BENCH, env=ENV, capture_output=True, text=True,
    )
    d1 = base.defender_cpu()
    if proc.returncode != 0:
        print(f"{run_id} {tool} FAILED rc={proc.returncode}: {proc.stderr[-500:]}", flush=True)
        continue
    os.replace(os.path.join(out_base, "commands.log"), os.path.join(out_base, f"commands_{tool}.log"))
    res = json.load(open(os.path.join(out_base, "hyperfine", name + ".json")))["results"][0]
    wall, cpu = res["mean"], res["user"] + res["system"]
    out_path = os.path.join(out_base, out_rel)
    lines = count_lines(out_path)
    size = os.path.getsize(out_path)
    os.remove(out_path)
    print(
        f"{run_id} {tool:7s} start {started}  wall {wall:6.1f} s  {N / wall:5.0f} files/s  user {res['user']:7.1f}  sys {res['system']:6.1f}  "
        f"CPU {cpu / N * 1e3:4.2f}  wait {(10 * wall - cpu) / N * 1e3:5.2f} ms/file  busy {cpu / wall:4.2f}  "
        f"Defender {(d1 - d0) / N * 1e3:4.2f} ms/file  lines {lines}  out {size / 1e9:5.2f} GB (removed)",
        flush=True,
    )
    time.sleep(10)
