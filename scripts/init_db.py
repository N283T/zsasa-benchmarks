#!/usr/bin/env python3
"""Initialize a DuckDB benchmark database and seed static metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchlib.datasets import DEFAULT_DATASETS_CONFIG, dataset_path, load_dataset_catalog
from db_common import DEFAULT_DB, apply_schema, connect, load_toml, resolve

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--tool-versions",
        type=Path,
        default=ROOT.joinpath("config/tool-versions.toml"),
    )
    parser.add_argument("--datasets", type=Path, default=DEFAULT_DATASETS_CONFIG)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    return parser.parse_args()


def seed_tools(conn, tool_versions: dict) -> None:
    for tool_id, info in tool_versions.items():
        if tool_id == "runner":
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO tools
            (tool_id, name, version, commit_sha, repository, policy, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                tool_id,
                tool_id,
                info.get("version") or info.get("tag"),
                info.get("commit") or info.get("commit_sha"),
                info.get("repository"),
                info.get("policy"),
                f"upstream={info.get('upstream')}" if info.get("upstream") else None,
            ],
        )


def seed_dataset_from_manifest(conn, manifest: dict, dataset_catalog: dict) -> None:
    dataset = manifest.get("dataset", {})
    if not dataset:
        return
    dataset_id = str(dataset.get("id"))
    path_or_uri = str(dataset_path(dataset_catalog, dataset_id, "path"))
    conn.execute(
        """
        INSERT OR REPLACE INTO datasets
        (dataset_id, name, role, expected_count, path_or_uri, redistribution_status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            dataset_id,
            dataset.get("name") or dataset.get("id"),
            (
                ",".join(dataset.get("role", []))
                if isinstance(dataset.get("role"), list)
                else dataset.get("role")
            ),
            dataset.get("expected_count"),
            path_or_uri,
            dataset.get("redistribution_status"),
            manifest.get("description") or manifest.get("status"),
        ],
    )


def main() -> None:
    args = parse_args()
    db_path = resolve(args.db)
    conn = connect(db_path)
    try:
        apply_schema(conn)
        seed_tools(conn, load_toml(resolve(args.tool_versions)))
        dataset_catalog = load_dataset_catalog(args.datasets)
        for manifest_path in args.manifest:
            seed_dataset_from_manifest(conn, load_toml(resolve(manifest_path)), dataset_catalog)
    finally:
        conn.close()
    print(f"initialized {db_path}")


if __name__ == "__main__":
    main()
