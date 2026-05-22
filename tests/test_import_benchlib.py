from __future__ import annotations


def test_benchlib_imports() -> None:
    import scripts.benchlib as benchlib

    assert benchlib.__all__ == []
