#!/usr/bin/env python3
"""Build curated Zenodo archive manifests and optional tarballs.

The default `curated` profile is intended for the DOI record linked from the
paper: source code, manifests, reproducibility configuration, DuckDB evidence,
summary tables, and rendered figures. The `full` profile additionally includes
selected raw full-rerun directories that are large enough to make the archive
slow to build and upload.

The archive is split into parts (see `PARTS`) that are extracted into the same
directory. The tarballs are reproducible: an unchanged part gives a byte-identical
file with the same name, so a new Zenodo version can import the previous files and
replace only the parts whose checksum changed (`scripts/upload_zenodo_archive.py`).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import tarfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".direnv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "archives",
    "data",
    "external",
    "inputs",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".env",
    "datasets.local.toml",
}

EXCLUDED_FILE_SUFFIXES = (".log",)

FULL_PROFILE_RUN_IDS = {
    "v0_6_0_full",
    "nix_full_20260524",
    "nix_validation_20260524",
}

GENERATED_DIRECTORIES = {
    ("datasets", "single-file-large-structure-mmcif"),
    ("results", "smoke-clean-cif"),
}

PROFILE_CHOICES = ("curated", "full")

# zsasa release and archive revision; recorded in the manifest.
ARCHIVE_VERSION = "v0.12.1-r3"

# Archive parts, matched on leading path components in order. Large parts that rarely
# change are kept apart from the small, frequently changing code and tables.
PARTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("inputs", ("datasets", "single-file-large-structure-sources")),
    ("figures", ("results", "figures")),
    ("database", ("results", "benchmark.duckdb")),
    ("afdb-dimers", ("workflows", "afdb-dimers")),
    ("sasa-explorer", ("workflows", "sasa-explorer")),
    ("raw-runs", ("results", "full_rerun")),
)
DEFAULT_PART = "code-and-tables"
PART_NAMES = (*(name for name, _ in PARTS), DEFAULT_PART)


@dataclass(frozen=True)
class ArchiveItem:
    """A file selected for the Zenodo archive."""

    path: Path
    relative_path: str
    size_bytes: int


def part_of(relative_path: str) -> str:
    """Return the archive part that holds a repository-relative path."""
    parts = Path(relative_path).parts
    for name, prefix in PARTS:
        if parts[: len(prefix)] == prefix:
            return name
    return DEFAULT_PART


def part_archive_name(part: str, compression: str = "gzip") -> str:
    """Archive filename of a part; it carries no version so unchanged parts keep their name."""
    suffix = ".tar" if compression == "none" else ".tar.gz"
    return f"zsasa-benchmarks-{part}{suffix}"


def _normalise_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _should_prune_dir(relative_parts: tuple[str, ...], profile: str) -> bool:
    if not relative_parts:
        return False
    dirname = relative_parts[-1]
    if dirname in EXCLUDED_DIRECTORY_NAMES:
        return True
    if relative_parts[:2] == ("results", "full_rerun"):
        if profile == "curated":
            return True
        if len(relative_parts) >= 3 and relative_parts[2] not in FULL_PROFILE_RUN_IDS:
            return True
    return False


def _should_include_file(relative_parts: tuple[str, ...], profile: str) -> bool:
    if not relative_parts:
        return False
    if relative_parts[-1] in EXCLUDED_FILE_NAMES:
        return False
    if relative_parts[-1].endswith(EXCLUDED_FILE_SUFFIXES):
        return False
    if relative_parts[:3] == ("datasets", "single-file-large-structure", "pdb"):
        return False
    # Derived structure files and smoke outputs are regenerated from the tracked sources.
    if relative_parts[:2] in GENERATED_DIRECTORIES:
        return False
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts[:-1]):
        return False
    if relative_parts[:2] == ("results", "full_rerun"):
        if profile == "curated":
            return False
        if len(relative_parts) < 3 or relative_parts[2] not in FULL_PROFILE_RUN_IDS:
            return False
    return True


def collect_archive_files(repo_root: Path, profile: str = "curated") -> list[ArchiveItem]:
    """Return repository files to include in a Zenodo archive profile."""
    if profile not in PROFILE_CHOICES:
        msg = f"profile must be one of {', '.join(PROFILE_CHOICES)}"
        raise ValueError(msg)

    root = repo_root.resolve()
    selected: list[ArchiveItem] = []
    for current_dir, dirnames, filenames in root.walk(top_down=True):
        rel_dir = current_dir.relative_to(root)
        rel_dir_parts = () if rel_dir == Path(".") else rel_dir.parts
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            rel_parts = (*rel_dir_parts, dirname)
            if not _should_prune_dir(rel_parts, profile):
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            path = current_dir.joinpath(filename)
            relative_path = _normalise_relative(path, root)
            relative_parts = Path(relative_path).parts
            if _should_include_file(relative_parts, profile):
                selected.append(
                    ArchiveItem(
                        path=path,
                        relative_path=relative_path,
                        size_bytes=path.stat().st_size,
                    )
                )
    return selected


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _human_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{size_bytes} B"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


def format_manifest(repo_root: Path, files: Sequence[ArchiveItem], profile: str) -> str:
    """Format a checksum manifest for the selected archive files."""
    total_size = sum(item.size_bytes for item in files)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    lines = [
        "# zsasa-benchmarks Zenodo archive manifest",
        "",
        f"Generated at: {generated_at}",
        f"Archive version: {ARCHIVE_VERSION}",
        f"Profile: {profile}",
        f"Repository root: {repo_root.resolve()}",
        f"Total files: {len(files)}",
        f"Total size: {total_size} bytes ({_human_size(total_size)})",
        "",
        "Extract every part into the same directory to rebuild the repository layout.",
        "",
        "## Parts",
        "",
        "| Part | Archive | Files | Size |",
        "| --- | --- | ---: | ---: |",
    ]
    for part in PART_NAMES:
        members = [item for item in files if part_of(item.relative_path) == part]
        if members:
            size = sum(item.size_bytes for item in members)
            lines.append(
                f"| {part} | `{part_archive_name(part)}` | {len(members)} | {_human_size(size)} |"
            )
    lines += [
        "",
        "## Files",
        "",
        "| Path | Part | Size bytes | SHA-256 |",
        "| --- | --- | ---: | --- |",
    ]
    for item in files:
        digest = sha256_file(item.path)
        lines.append(
            f"| `{item.relative_path}` | {part_of(item.relative_path)} | "
            f"{item.size_bytes} | sha256:{digest} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_manifest(
    repo_root: Path, out_dir: Path, files: Sequence[ArchiveItem], profile: str
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir.joinpath(f"ZENODO_ARCHIVE_MANIFEST-{profile}.md")
    manifest_path.write_text(format_manifest(repo_root, files, profile), encoding="utf-8")
    return manifest_path


def write_checksums(out_dir: Path, generated_files: Iterable[Path]) -> Path:
    checksum_path = out_dir.joinpath("SHA256SUMS")
    lines = []
    for path in sorted(generated_files):
        lines.append(f"{sha256_file(path)}  {path.name}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def create_tarball(archive_path: Path, files: Sequence[ArchiveItem], compression: str) -> Path:
    """Write a reproducible tarball: sorted members, fixed metadata, no gzip timestamp."""
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("wb") as raw:
        stream = (
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6)
            if compression == "gzip"
            else raw
        )
        try:
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for item in sorted(files, key=lambda entry: entry.relative_path):
                    info = archive.gettarinfo(
                        item.path, arcname=f"zsasa-benchmarks/{item.relative_path}"
                    )
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o755 if info.mode & 0o111 else 0o644
                    with item.path.open("rb") as handle:
                        archive.addfile(info, handle)
        finally:
            if stream is not raw:
                stream.close()
    return archive_path


def create_part_tarballs(
    out_dir: Path, files: Sequence[ArchiveItem], compression: str
) -> list[Path]:
    """Write one tarball per non-empty part and return their paths."""
    paths = []
    for part in PART_NAMES:
        members = [item for item in files if part_of(item.relative_path) == part]
        if members:
            paths.append(
                create_tarball(
                    out_dir.joinpath(part_archive_name(part, compression)), members, compression
                )
            )
    return paths


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to archive. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("archives/zenodo"),
        help="Directory for manifest, checksums, and optional tarball.",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default="curated",
        help="curated excludes raw full_rerun outputs; full includes selected full reruns.",
    )
    parser.add_argument(
        "--compression",
        choices=("none", "gzip"),
        default="gzip",
        help="Tarball compression when --make-archive is used.",
    )
    parser.add_argument(
        "--make-archive",
        action="store_true",
        help="Create the part tarballs in addition to the manifest and checksums.",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="Print selected archive paths to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    out_dir = args.out_dir.resolve()
    files = collect_archive_files(repo_root, profile=args.profile)
    if args.list_files:
        for item in files:
            print(item.relative_path)

    manifest_text = format_manifest(repo_root, files, profile=args.profile)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir.joinpath(f"ZENODO_ARCHIVE_MANIFEST-{args.profile}.md")
    manifest_path.write_text(manifest_text, encoding="utf-8")
    generated = [manifest_path]

    if args.make_archive:
        generated.extend(create_part_tarballs(out_dir, files, args.compression))

    checksum_path = write_checksums(out_dir, generated)
    total_size = sum(item.size_bytes for item in files)
    print(f"Profile: {args.profile}")
    print(f"Selected files: {len(files)}")
    print(f"Selected size: {total_size} bytes ({_human_size(total_size)})")
    print(f"Manifest: {manifest_path}")
    for path in generated[1:]:
        print(f"Archive: {path} ({_human_size(path.stat().st_size)})")
    print(f"Checksums: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
