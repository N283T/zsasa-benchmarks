#!/usr/bin/env python3
"""Import native full-rerun benchmark outputs into DuckDB."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.db_common import (  # noqa: E402
    DEFAULT_DB,
    apply_schema,
    connect,
    load_toml,
    resolve,
    stable_id,
)
from scripts.init_db import seed_dataset_from_manifest, seed_tools  # noqa: E402

DEFAULT_RUN_ID = "v0_6_0_full"
DEFAULT_TOOL_VERSIONS = ROOT.joinpath("config/tool-versions.toml")
DEFAULT_DATASETS = ROOT.joinpath("config/datasets.local.toml")
FALLBACK_DATASETS = ROOT.joinpath("config/datasets.toml.example")
ZSASA_FILENAME_RE = re.compile(r'"filename":"([^"]+)"')
ZSASA_TOTAL_RE = re.compile(r'"total_area":([-+0-9.eE]+)')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--results-root", type=Path, default=None)
    parser.add_argument(
        "--validation-run-id",
        default=None,
        help=(
            "run-id whose validation/validation_md outputs should be imported; "
            "defaults to --run-id"
        ),
    )
    parser.add_argument(
        "--validation-results-root",
        type=Path,
        default=None,
        help="explicit root containing validation/ and validation_md/ outputs",
    )
    parser.add_argument("--tool-versions", type=Path, default=DEFAULT_TOOL_VERSIONS)
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS)
    parser.add_argument("--reset", action="store_true", help="delete and recreate the DB first")
    return parser.parse_args()


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    try:
        apply_schema(conn)
    finally:
        conn.close()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_zsasa_jsonl_total(line: str) -> tuple[str, float, int | None]:
    filename = ZSASA_FILENAME_RE.search(line)
    total = ZSASA_TOTAL_RE.search(line)
    if filename is not None and total is not None:
        return Path(filename.group(1)).name, float(total.group(1)), None
    item = json.loads(line)
    return Path(item["filename"]).name, float(item["total_area"]), len(item.get("atom_areas", []))


def parse_validation_zsasa_name(filename: str) -> dict[str, Any]:
    sr = re.fullmatch(r"sr_(f32|f64)_(standard|bitmask)_(\d+)\.jsonl", filename)
    if sr:
        precision, mode, n_points = sr.groups()
        return {
            "algorithm": "sr",
            "precision": precision,
            "mode": mode,
            "n_points": int(n_points),
            "n_slices": None,
        }
    lr = re.fullmatch(r"lr_(f32|f64)_(\d+)\.jsonl", filename)
    if lr:
        precision, n_slices = lr.groups()
        return {
            "algorithm": "lr",
            "precision": precision,
            "mode": "standard",
            "n_points": None,
            "n_slices": int(n_slices),
        }
    raise ValueError(f"unrecognized zSASA validation file name: {filename}")


def parse_batch_record_name(name: str) -> dict[str, Any]:
    zsasa = re.fullmatch(r"zsasa_batch_(f32|f64)_(standard|bitmask)_(\d+)t_(\d+)p", name)
    if zsasa:
        precision, mode, threads, n_points = zsasa.groups()
        return {
            "tool_id": "zsasa",
            "algorithm": "sr",
            "precision": precision,
            "mode": mode,
            "threads": int(threads),
            "n_points": int(n_points),
        }
    comparator = re.fullmatch(
        r"(freesasa_batch|rustsasa|lahuta)_(?:(standard|bitmask)_)?(\d+)t_(\d+)p", name
    )
    if comparator:
        tool_id, mode, threads, n_points = comparator.groups()
        return {
            "tool_id": tool_id,
            "algorithm": "sr",
            "precision": "f64",
            "mode": mode or "standard",
            "threads": int(threads),
            "n_points": int(n_points),
        }
    raise ValueError(f"unrecognized batch record name: {name}")


def parse_trajectory_record_name(name: str) -> dict[str, Any]:
    dataset_id, rest = split_dataset_prefix(name)
    m = re.fullmatch(r"(zig|zig_bitmask)_(f32|f64)_(\d+)t_(\d+)p", rest)
    if m:
        tool_id, precision, threads, n_points = m.groups()
        return {
            "dataset_id": dataset_id,
            "tool_id": tool_id,
            "algorithm": "sr",
            "precision": precision,
            "mode": "bitmask" if tool_id.endswith("bitmask") else "standard",
            "threads": int(threads),
            "n_points": int(n_points),
        }
    m = re.fullmatch(
        r"(zsasa_mdtraj(?:_bitmask)?|zsasa_mdanalysis(?:_bitmask)?|mdtraj|mdsasa_bolt)(?:_(\d+)t)?_(\d+)p",
        rest,
    )
    if m:
        tool_id, threads, n_points = m.groups()
        return {
            "dataset_id": dataset_id,
            "tool_id": tool_id,
            "algorithm": "sr",
            "precision": "f64",
            "mode": "bitmask" if tool_id.endswith("bitmask") else "standard",
            "threads": int(threads) if threads is not None else None,
            "n_points": int(n_points),
        }
    raise ValueError(f"unrecognized trajectory record name: {name}")


def split_dataset_prefix(name: str) -> tuple[str, str]:
    for prefix in ["5wvo_C_analysis", "6sup_A_analysis", "5vz0_A_protein"]:
        marker = f"{prefix}_"
        if name.startswith(marker):
            return prefix, name[len(marker) :]
    raise ValueError(f"unrecognized trajectory dataset prefix: {name}")



def parse_single_tool_label(tool_label: str) -> dict[str, Any]:
    if tool_label.startswith("zsasa_"):
        suffix = tool_label.removeprefix("zsasa_")
        precision = suffix.removesuffix("_bitmask")
        return {
            "tool_id": "zsasa",
            "algorithm": "sr",
            "precision": precision,
            "mode": "bitmask" if suffix.endswith("_bitmask") else "standard",
        }
    if tool_label in {"freesasa", "rustsasa"}:
        return {
            "tool_id": tool_label,
            "algorithm": "sr",
            "precision": "f64",
            "mode": "standard",
        }
    raise ValueError(f"unrecognized single-file tool label: {tool_label}")


def parse_single_run_stem(stem: str) -> tuple[str, int, int]:
    match = re.fullmatch(r"(.+)_(\d+)t_(\d+)p", stem)
    if match is None:
        raise ValueError(f"unrecognized single-file run stem: {stem}")
    structure_id, threads, n_points = match.groups()
    return structure_id, int(threads), int(n_points)


def single_structure_metadata() -> dict[str, dict[str, Any]]:
    manifest = load_toml(ROOT.joinpath("manifests/single-file-sample.toml"))
    entries: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("structures", []):
        if not isinstance(entry, dict):
            continue
        structure_id = str(entry["id"])
        entries[structure_id] = {
            "role": str(entry.get("role") or ""),
            "n_atoms": int(entry.get("expected_atoms") or 0),
            "expected_chains": int(entry.get("expected_chains") or 0),
        }
    return entries


def single_notes(*, tool_label: str, structure_id: str, metadata: dict[str, Any]) -> str:
    return "; ".join(
        [
            f"tool_label={tool_label}",
            f"structure_id={structure_id}",
            f"role={metadata.get('role', '')}",
            f"n_atoms={metadata.get('n_atoms', 0)}",
            f"expected_chains={metadata.get('expected_chains', 0)}",
            "phases=wall,timing",
        ]
    )


def single_run_id(
    *,
    run_label: str,
    dataset_id: str,
    tool_label: str,
    structure_id: str,
    threads: int,
    n_points: int,
) -> str:
    return stable_id(
        run_label,
        "single_file",
        dataset_id,
        tool_label,
        structure_id,
        f"{threads}t",
        f"{n_points}p",
    )


def insert_performance_metrics(
    conn, run_id: str, metrics: list[tuple[str, str, float, str, int | None]]
) -> None:
    conn.executemany(
        """
        INSERT INTO performance_results
        (run_id, metric, statistic, value, unit, n)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (run_id, metric, statistic, value, unit, n)
            for metric, statistic, value, unit, n in metrics
        ],
    )

def insert_run(
    conn,
    *,
    run_id: str,
    benchmark_kind: str,
    dataset_id: str,
    tool_id: str,
    algorithm: str | None,
    precision: str | None,
    mode: str | None,
    n_points: int | None,
    n_slices: int | None = None,
    threads: int | None = None,
    source_path: Path,
    manifest_id: str | None,
    notes: str | None = None,
) -> None:
    conn.execute("DELETE FROM validation_results WHERE run_id = ?", [run_id])
    conn.execute("DELETE FROM performance_results WHERE run_id = ?", [run_id])
    conn.execute("DELETE FROM benchmark_runs WHERE run_id = ?", [run_id])
    conn.execute(
        """
        INSERT INTO benchmark_runs
        (run_id, benchmark_kind, dataset_id, tool_id, algorithm, precision, mode,
         n_points, n_slices, threads, source_kind, source_path, manifest_id,
         created_at, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'full_rerun', ?, ?, ?, 'imported', ?)
        """,
        [
            run_id,
            benchmark_kind,
            dataset_id,
            tool_id,
            algorithm,
            precision,
            mode,
            n_points,
            n_slices,
            threads,
            str(source_path),
            manifest_id,
            datetime.now(UTC),
            notes,
        ],
    )


def insert_validation_rows(conn, run_id: str, rows: list[tuple[str, int | None, float]]) -> None:
    conn.executemany(
        """
        INSERT INTO validation_results (run_id, structure_id, n_atoms, total_sasa)
        VALUES (?, ?, ?, ?)
        """,
        [(run_id, structure_id, n_atoms, total_sasa) for structure_id, n_atoms, total_sasa in rows],
    )


def import_validation_static(conn, validation_dir: Path, run_label: str) -> None:
    dataset_id = "UP000000625_83333_ECOLI_v6_pdb"
    manifest_id = "validation-ecoli-full-rerun"
    for path in sorted(validation_dir.joinpath("zsasa").glob("*.jsonl")):
        meta = parse_validation_zsasa_name(path.name)
        run_id = stable_id(run_label, "validation", "ecoli", "zsasa", path.stem)
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="validation",
            dataset_id=dataset_id,
            tool_id="zsasa",
            source_path=path,
            manifest_id=manifest_id,
            **meta,
        )
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                structure_id, total_sasa, n_atoms = parse_zsasa_jsonl_total(line)
                rows.append((structure_id, n_atoms, total_sasa))
        insert_validation_rows(conn, run_id, rows)

    for path in sorted(validation_dir.joinpath("freesasa_batch").glob("sr_*")):
        n_points = int(path.name.removeprefix("sr_"))
        run_id = stable_id(run_label, "validation", "ecoli", "freesasa_batch", path.name)
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="validation",
            dataset_id=dataset_id,
            tool_id="freesasa_batch",
            algorithm="sr",
            precision="f64",
            mode="standard",
            n_points=n_points,
            n_slices=None,
            threads=None,
            source_path=path,
            manifest_id=manifest_id,
        )
        rows = [
            (txt.with_suffix(".pdb").name, None, float(txt.read_text(encoding="utf-8").strip()))
            for txt in sorted(path.glob("*.txt"))
        ]
        insert_validation_rows(conn, run_id, rows)

    for path in sorted(validation_dir.joinpath("rustsasa").glob("sr_*")):
        n_points = int(path.name.removeprefix("sr_"))
        run_id = stable_id(run_label, "validation", "ecoli", "rustsasa", path.name)
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="validation",
            dataset_id=dataset_id,
            tool_id="rustsasa",
            algorithm="sr",
            precision="f64",
            mode="standard",
            n_points=n_points,
            n_slices=None,
            threads=None,
            source_path=path,
            manifest_id=manifest_id,
        )
        rows = [
            (
                js.with_suffix(".pdb").name,
                None,
                float(read_json(js)["Protein"]["global_total"]),
            )
            for js in sorted(path.glob("*.json"))
        ]
        insert_validation_rows(conn, run_id, rows)

    for path in sorted(validation_dir.joinpath("lahuta").glob("sr_*.jsonl")):
        m = re.fullmatch(r"sr_(standard|bitmask)_(\d+)\.jsonl", path.name)
        if m is None:
            continue
        mode, n_points = m.groups()
        run_id = stable_id(run_label, "validation", "ecoli", "lahuta", path.stem)
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="validation",
            dataset_id=dataset_id,
            tool_id="lahuta",
            algorithm="sr",
            precision="f64",
            mode=mode,
            n_points=int(n_points),
            n_slices=None,
            threads=None,
            source_path=path,
            manifest_id=manifest_id,
        )
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                rows.append(
                    (
                        Path(item["model"]).name,
                        len(item.get("sasa", [])) or None,
                        sum(float(value) for value in item["sasa"]),
                    )
                )
        insert_validation_rows(conn, run_id, rows)


def import_hyperfine_directory(
    conn,
    *,
    base: Path,
    run_label: str,
    benchmark_kind: str,
    dataset_id: str,
    manifest_id: str,
    name_parser,
) -> None:
    for path in sorted(base.joinpath("hyperfine").glob("*.json")):
        name = path.stem
        meta = name_parser(name)
        row_dataset_id = meta.pop("dataset_id", dataset_id)
        run_id = stable_id(run_label, benchmark_kind, row_dataset_id, name)
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind=benchmark_kind,
            dataset_id=row_dataset_id,
            source_path=path,
            manifest_id=manifest_id,
            n_slices=None,
            notes=name,
            **meta,
        )
        result = read_json(path)["results"][0]
        metrics = [
            ("runtime", "mean", result.get("mean"), "s"),
            ("runtime", "stddev", result.get("stddev"), "s"),
            ("runtime", "median", result.get("median"), "s"),
            ("runtime", "min", result.get("min"), "s"),
            ("runtime", "max", result.get("max"), "s"),
            ("user_time", "mean", result.get("user"), "s"),
            ("system_time", "mean", result.get("system"), "s"),
        ]
        times = result.get("times", [])
        metrics.extend(
            ("runtime", f"run_{idx}", float(value), "s") for idx, value in enumerate(times, start=1)
        )
        memory_values = [float(value) for value in result.get("memory_usage_byte", [])]
        if memory_values:
            metrics.extend(
                [
                    ("peak_rss", "mean", sum(memory_values) / len(memory_values), "bytes"),
                    ("peak_rss", "median", median(memory_values), "bytes"),
                    ("peak_rss", "min", min(memory_values), "bytes"),
                    ("peak_rss", "max", max(memory_values), "bytes"),
                ]
            )
            metrics.extend(
                ("peak_rss", f"run_{idx}", value, "bytes")
                for idx, value in enumerate(memory_values, start=1)
            )
            if len(memory_values) > 1:
                mean_memory = sum(memory_values) / len(memory_values)
                variance = sum((value - mean_memory) ** 2 for value in memory_values) / (
                    len(memory_values) - 1
                )
                metrics.append(("peak_rss", "stddev", variance**0.5, "bytes"))
            else:
                metrics.append(("peak_rss", "stddev", 0.0, "bytes"))
        conn.executemany(
            """
            INSERT INTO performance_results
            (run_id, metric, statistic, value, unit, n)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (run_id, metric, statistic, float(value), unit, len(times) or None)
                for metric, statistic, value, unit in metrics
                if value is not None
            ],
        )



def hyperfine_metrics(path: Path) -> list[tuple[str, str, float, str, int | None]]:
    result = read_json(path)["results"][0]
    times = result.get("times", [])
    metrics: list[tuple[str, str, float, str, int | None]] = [
        ("runtime", "mean", float(result["mean"]), "s", len(times) or None),
        ("runtime", "stddev", float(result.get("stddev", 0.0)), "s", len(times) or None),
        ("runtime", "median", float(result.get("median", result["mean"])), "s", len(times) or None),
        ("runtime", "min", float(result.get("min", result["mean"])), "s", len(times) or None),
        ("runtime", "max", float(result.get("max", result["mean"])), "s", len(times) or None),
    ]
    metrics.extend(
        ("runtime", f"run_{idx}", float(value), "s", len(times) or None)
        for idx, value in enumerate(times, start=1)
    )
    if result.get("user") is not None:
        metrics.append(("user_time", "mean", float(result["user"]), "s", len(times) or None))
    if result.get("system") is not None:
        metrics.append(("system_time", "mean", float(result["system"]), "s", len(times) or None))
    memory_values = [float(value) for value in result.get("memory_usage_byte", [])]
    if memory_values:
        metrics.extend(
            [
                (
                    "peak_rss",
                    "mean",
                    sum(memory_values) / len(memory_values),
                    "bytes",
                    len(memory_values),
                ),
                ("peak_rss", "median", median(memory_values), "bytes", len(memory_values)),
                ("peak_rss", "min", min(memory_values), "bytes", len(memory_values)),
                ("peak_rss", "max", max(memory_values), "bytes", len(memory_values)),
            ]
        )
        metrics.extend(
            ("peak_rss", f"run_{idx}", value, "bytes", len(memory_values))
            for idx, value in enumerate(memory_values, start=1)
        )
        if len(memory_values) > 1:
            mean_memory = sum(memory_values) / len(memory_values)
            variance = sum((value - mean_memory) ** 2 for value in memory_values) / (
                len(memory_values) - 1
            )
            metrics.append(("peak_rss", "stddev", variance**0.5, "bytes", len(memory_values)))
        else:
            metrics.append(("peak_rss", "stddev", 0.0, "bytes", len(memory_values)))
    return metrics


def import_single_file_results(conn, single_dir: Path, run_label: str) -> None:
    dataset_id = "single_file_large_structure_subset"
    manifest_id = "single-file-large-structure-subset"
    metadata_by_structure = single_structure_metadata()
    if not single_dir.exists():
        return

    for path in sorted(single_dir.glob("wall/*/runs/*.json")):
        tool_label = path.parent.parent.name
        structure_id, threads, n_points = parse_single_run_stem(path.stem)
        meta = parse_single_tool_label(tool_label)
        structure_meta = metadata_by_structure.get(structure_id, {})
        run_id = single_run_id(
            run_label=run_label,
            dataset_id=dataset_id,
            tool_label=tool_label,
            structure_id=structure_id,
            threads=threads,
            n_points=n_points,
        )
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="single_file",
            dataset_id=dataset_id,
            n_points=n_points,
            n_slices=None,
            threads=threads,
            source_path=path,
            manifest_id=manifest_id,
            notes=single_notes(
                tool_label=tool_label,
                structure_id=structure_id,
                metadata=structure_meta,
            ),
            **meta,
        )
        insert_performance_metrics(conn, run_id, hyperfine_metrics(path))

    for path in sorted(single_dir.glob("timing/*/timing.csv")):
        tool_label = path.parent.name
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                structure_id = str(row["structure"])
                threads = int(row["threads"])
                n_points = int(row["n_points"])
                run_id = single_run_id(
                    run_label=run_label,
                    dataset_id=dataset_id,
                    tool_label=tool_label,
                    structure_id=structure_id,
                    threads=threads,
                    n_points=n_points,
                )
                metrics: list[tuple[str, str, float, str, int | None]] = []
                for column, metric in [
                    ("parse_time_ms", "parse_time"),
                    ("sasa_time_ms", "sasa_time"),
                    ("total_time_ms", "total_time"),
                ]:
                    value = row.get(column, "")
                    if value:
                        metrics.append((metric, "single", float(value), "ms", 1))
                if metrics:
                    insert_performance_metrics(conn, run_id, metrics)

def import_trajectory_validation(conn, validation_dir: Path, run_label: str) -> None:
    dataset_id = "5wvo_C_analysis"
    manifest_id = "validation-md-5wvo-full-rerun"
    raw = validation_dir.joinpath("raw")
    for path in sorted(raw.rglob("results.json")):
        rel_parts = path.relative_to(raw).parts
        meta = parse_trajectory_validation_parts(rel_parts)
        run_id = stable_id(run_label, "trajectory_validation", dataset_id, "_".join(rel_parts[:-1]))
        insert_run(
            conn,
            run_id=run_id,
            benchmark_kind="trajectory_validation",
            dataset_id=dataset_id,
            source_path=path,
            manifest_id=manifest_id,
            n_slices=None,
            threads=meta.pop("threads"),
            **meta,
        )
        data = read_json(path)
        rows = [
            (f"frame_{idx:06d}", None, float(value))
            for idx, value in enumerate(data["total_sasa_a2"])
        ]
        insert_validation_rows(conn, run_id, rows)


def parse_trajectory_validation_parts(parts: tuple[str, ...]) -> dict[str, Any]:
    if parts[0] in {"zig", "zig_bitmask"}:
        tool_id, precision, points_part, _ = parts
        return {
            "tool_id": tool_id,
            "algorithm": "sr",
            "precision": precision,
            "mode": "bitmask" if tool_id.endswith("bitmask") else "standard",
            "n_points": int(points_part.removesuffix("p")),
            "threads": 10,
        }
    tool_id, points_part, _ = parts
    return {
        "tool_id": tool_id,
        "algorithm": "sr",
        "precision": "f64",
        "mode": "bitmask" if tool_id.endswith("bitmask") else "standard",
        "n_points": int(points_part.removesuffix("p")),
        "threads": 10 if tool_id.startswith("zsasa_") else None,
    }


def seed_all_datasets(conn, datasets_path: Path) -> None:
    from scripts.benchlib.datasets import load_dataset_catalog

    dataset_catalog = load_dataset_catalog(datasets_path)
    for manifest_path in [
        ROOT.joinpath("manifests/validation-ecoli.toml"),
        ROOT.joinpath("manifests/batch-ecoli.toml"),
        ROOT.joinpath("manifests/batch-human.toml"),
        ROOT.joinpath("manifests/single-file-sample.toml"),
    ]:
        seed_dataset_from_manifest(conn, load_toml(manifest_path), dataset_catalog)

    for dataset in load_toml(ROOT.joinpath("manifests/trajectory.toml"))["datasets"]:
        dataset_id = str(dataset["id"])
        conn.execute(
            """
            INSERT OR REPLACE INTO datasets
            (dataset_id, name, role, expected_count, path_or_uri, redistribution_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                dataset_id,
                dataset_id,
                "trajectory-throughput",
                dataset.get("frames"),
                str(dataset_catalog[dataset_id]),
                None,
                f"atoms={dataset.get('atoms')}; frames={dataset.get('frames')}",
            ],
        )


def seed_derived_tools(conn) -> None:
    derived = [
        ("zig", "zsasa CLI trajectory backend"),
        ("zig_bitmask", "zsasa CLI trajectory backend with bitmask mode"),
        ("zsasa_mdtraj", "zsasa Python wrapper over MDTraj frames"),
        ("zsasa_mdtraj_bitmask", "zsasa Python wrapper over MDTraj frames with bitmask mode"),
        ("zsasa_mdanalysis", "zsasa Python wrapper over MDAnalysis frames"),
        (
            "zsasa_mdanalysis_bitmask",
            "zsasa Python wrapper over MDAnalysis frames with bitmask mode",
        ),
    ]
    for tool_id, notes in derived:
        conn.execute(
            """
            INSERT OR REPLACE INTO tools
            (tool_id, name, repository, policy, notes)
            VALUES (?, ?, 'https://github.com/N283T/zsasa', 'derived full-rerun tool label', ?)
            """,
            [tool_id, tool_id, notes],
        )


def import_full_rerun(
    db_path: Path,
    results_root: Path,
    run_label: str,
    datasets_path: Path,
    validation_results_root: Path | None = None,
    validation_run_label: str | None = None,
) -> None:
    conn = connect(db_path)
    try:
        apply_schema(conn)
        seed_tools(conn, load_toml(DEFAULT_TOOL_VERSIONS))
        seed_derived_tools(conn)
        seed_all_datasets(conn, datasets_path)
        validation_root = validation_results_root or results_root
        validation_label = validation_run_label or run_label
        import_validation_static(
            conn, validation_root.joinpath("validation", "ecoli"), validation_label
        )
        import_trajectory_validation(
            conn, validation_root.joinpath("validation_md", "5wvo_C_analysis"), validation_label
        )
        import_hyperfine_directory(
            conn,
            base=results_root.joinpath("batch", "ecoli"),
            run_label=run_label,
            benchmark_kind="batch",
            dataset_id="UP000000625_83333_ECOLI_v6_pdb",
            manifest_id="batch-ecoli-full-rerun",
            name_parser=parse_batch_record_name,
        )
        import_hyperfine_directory(
            conn,
            base=results_root.joinpath("batch", "human"),
            run_label=run_label,
            benchmark_kind="batch",
            dataset_id="UP000005640_9606_HUMAN_v6_pdb",
            manifest_id="batch-human-full-rerun",
            name_parser=parse_batch_record_name,
        )
        import_hyperfine_directory(
            conn,
            base=results_root.joinpath("md"),
            run_label=run_label,
            benchmark_kind="trajectory",
            dataset_id="",
            manifest_id="trajectory-full-rerun",
            name_parser=parse_trajectory_record_name,
        )
        import_single_file_results(
            conn,
            results_root.joinpath("single", "single_file_large_structure_subset"),
            run_label,
        )
    finally:
        conn.close()


def main() -> None:
    args = parse_args()
    db_path = resolve(args.db)
    results_root = (
        resolve(args.results_root)
        if args.results_root is not None
        else ROOT.joinpath("results", "full_rerun", args.run_id)
    )
    datasets_path = resolve(args.datasets if args.datasets.exists() else FALLBACK_DATASETS)
    validation_run_id = args.validation_run_id or args.run_id
    validation_results_root = (
        resolve(args.validation_results_root)
        if args.validation_results_root is not None
        else ROOT.joinpath("results", "full_rerun", validation_run_id)
    )
    if args.reset:
        reset_database(db_path)
    import_full_rerun(
        db_path,
        results_root,
        args.run_id,
        datasets_path,
        validation_results_root=validation_results_root,
        validation_run_label=validation_run_id,
    )
    conn = connect(db_path)
    try:
        summary = {
            "benchmark_runs": conn.execute("SELECT count(*) FROM benchmark_runs").fetchone()[0],
            "validation_results": conn.execute(
                "SELECT count(*) FROM validation_results"
            ).fetchone()[0],
            "performance_results": conn.execute(
                "SELECT count(*) FROM performance_results"
            ).fetchone()[0],
        }
    finally:
        conn.close()
    print(f"imported benchmark results {results_root} into {db_path}")
    print(
        f"imported validation results {validation_results_root} "
        f"with run label {validation_run_id}"
    )
    for key, value in summary.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
