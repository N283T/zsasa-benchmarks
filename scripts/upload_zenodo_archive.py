#!/usr/bin/env python3
"""Upload the Zenodo archive parts to a draft, replacing only files that changed.

A new version of a Zenodo record can import the files of the previous version. This
script compares the MD5 checksums that Zenodo reports for the draft's files with the
local files listed in SHA256SUMS (the manifest, the checksum file, and the part
tarballs written by `scripts/build_zenodo_archive.py`). Files with the same name and
checksum are kept, changed or new files are uploaded, and draft files that are not in
the local list (for example the single tarball of an earlier layout) are removed.

The token is read from ZENODO_TOKEN or from the terminal and is not stored.

Usage:
    uv run python scripts/upload_zenodo_archive.py <draft-id> --dry-run
    uv run python scripts/upload_zenodo_archive.py <draft-id>
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API = "https://zenodo.org/api"


@dataclass(frozen=True)
class Plan:
    upload: list[str]
    keep: list[str]
    delete: list[str]


def plan_changes(local: dict[str, str], remote: dict[str, str]) -> Plan:
    """Compare local and draft files by name and `md5:` checksum."""
    upload = sorted(name for name, digest in local.items() if remote.get(name) != digest)
    keep = sorted(name for name, digest in local.items() if remote.get(name) == digest)
    delete = sorted(name for name in remote if name not in local)
    return Plan(upload=upload, keep=keep, delete=delete)


def local_files(archive_dir: Path) -> list[Path]:
    """The files to publish: SHA256SUMS and every file it lists."""
    sums = archive_dir.joinpath("SHA256SUMS")
    names = [line.split(maxsplit=1)[1].strip() for line in sums.read_text().splitlines() if line]
    return [sums, *(archive_dir.joinpath(name) for name in names)]


def md5_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return f"md5:{digest.hexdigest()}"


class Draft:
    def __init__(self, record_id: str, token: str) -> None:
        self.base = f"{API}/records/{record_id}/draft"
        self.token = token

    def request(self, method: str, path: str = "", data=None, headers=None) -> dict:
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read()[:300].decode(errors="replace")
            raise SystemExit(f"{method} {self.base + path}: HTTP {error.code} {detail}") from None
        return json.loads(body) if body else {}

    def files(self) -> dict[str, str]:
        entries = self.request("GET", "/files").get("entries", [])
        return {entry["key"]: entry.get("checksum", "") for entry in entries}

    def delete(self, name: str) -> None:
        self.request("DELETE", f"/files/{urllib.parse.quote(name)}")

    def upload(self, path: Path) -> str:
        key = urllib.parse.quote(path.name)
        self.request(
            "POST",
            "/files",
            data=json.dumps([{"key": path.name}]).encode(),
            headers={"Content-Type": "application/json"},
        )
        with path.open("rb") as handle:
            self.request(
                "PUT",
                f"/files/{key}/content",
                data=handle,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(path.stat().st_size),
                },
            )
        return self.request("POST", f"/files/{key}/commit").get("checksum", "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("record_id", help="Zenodo draft (record) id")
    parser.add_argument("--archive-dir", type=Path, default=Path("archives/zenodo"))
    parser.add_argument("--dry-run", action="store_true", help="show the plan only")
    args = parser.parse_args()

    files = local_files(args.archive_dir)
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise SystemExit(f"missing local files: {', '.join(missing)}")
    by_name = {path.name: path for path in files}
    local = {name: md5_file(path) for name, path in by_name.items()}

    token = os.environ.get("ZENODO_TOKEN") or getpass.getpass("Zenodo token: ")
    draft = Draft(args.record_id, token)
    plan = plan_changes(local, draft.files())
    for name in plan.keep:
        print(f"keep    {name}")
    for name in plan.upload:
        print(f"upload  {name} ({by_name[name].stat().st_size / 2**20:.1f} MiB)")
    for name in plan.delete:
        print(f"delete  {name}")
    if args.dry_run:
        return 0

    for name in plan.delete:
        draft.delete(name)
    for name in plan.upload:
        if name in draft.files():
            draft.delete(name)
        print(f"uploading {name} ...", flush=True)
        remote = draft.upload(by_name[name])
        if remote != local[name]:
            print(f"CHECKSUM MISMATCH for {name}: remote {remote}, local {local[name]}")
            return 1
    print("Done. Check the draft in the browser, then publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
