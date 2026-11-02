from __future__ import annotations

from pathlib import Path

from scripts.upload_zenodo_archive import local_files, plan_changes


def test_plan_keeps_unchanged_uploads_changed_and_removes_stale() -> None:
    local = {"SHA256SUMS": "md5:a", "parts-code.tar.gz": "md5:b", "parts-inputs.tar.gz": "md5:c"}
    remote = {"SHA256SUMS": "md5:old", "parts-inputs.tar.gz": "md5:c", "old-single.tar.gz": "md5:d"}

    plan = plan_changes(local, remote)

    assert plan.keep == ["parts-inputs.tar.gz"]
    assert plan.upload == ["SHA256SUMS", "parts-code.tar.gz"]
    assert plan.delete == ["old-single.tar.gz"]


def test_local_files_are_the_checksum_file_and_its_entries(tmp_path: Path) -> None:
    tmp_path.joinpath("SHA256SUMS").write_text("abc  MANIFEST.md\ndef  part.tar.gz\n")

    names = [path.name for path in local_files(tmp_path)]

    assert names == ["SHA256SUMS", "MANIFEST.md", "part.tar.gz"]
