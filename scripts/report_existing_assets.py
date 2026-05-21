#!/usr/bin/env python3
"""Report historical benchmark assets without running any benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def count_files(path: Path, suffix: str) -> int | None:
    if not path.exists():
        return None
    return sum(1 for item in path.iterdir() if item.is_file() and item.name.endswith(suffix))


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zsasa-repo",
        type=Path,
        default=Path("/Users/nagaet/freesasa-zig"),
        help="historical zsasa repository path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.zsasa_repo
    print(f"historical_repo={root}")

    ecoli = root.joinpath("benchmarks/UP000000625_83333_ECOLI_v6/pdb")
    single = root.joinpath("benchmarks/dataset/pdb")
    print(f"ecoli_validation_batch_files={count_files(ecoli, '.pdb')}")
    print(f"single_file_sample_files={count_files(single, '.pdb')}")

    configs = [
        root.joinpath("benchmarks/results/validation/ecoli/sr/config.json"),
        root.joinpath("benchmarks/results/validation/ecoli/lr/config.json"),
        root.joinpath("benchmarks/results/batch/128/ecoli_t10/config.json"),
    ]
    for config_path in configs:
        config = read_json(config_path)
        if config is None:
            print(f"missing_config={config_path}")
            continue
        params = config.get("parameters", {})
        print(
            "config="
            f"{config_path} "
            f"timestamp={config.get('timestamp')} "
            f"n_files={params.get('n_files')} "
            f"algorithm={params.get('algorithm', 'batch')} "
            f"n_points={params.get('n_points')}"
        )


if __name__ == "__main__":
    main()
