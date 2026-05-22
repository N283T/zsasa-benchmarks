"""Metric helpers for benchmark exports."""

from __future__ import annotations


def files_per_second(n_files: int, seconds: float) -> float:
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    return n_files / seconds


def relative_error_percent(observed: float, reference: float) -> float:
    if reference == 0:
        return 0.0 if observed == 0 else float("inf")
    return abs(observed - reference) / abs(reference) * 100.0


def r2_score(reference: list[float], observed: list[float]) -> float:
    if len(reference) != len(observed):
        raise ValueError("reference and observed lengths differ")
    mean_ref = sum(reference) / len(reference)
    ss_tot = sum((value - mean_ref) ** 2 for value in reference)
    ss_res = sum((obs - ref) ** 2 for obs, ref in zip(observed, reference, strict=True))
    return 1.0 - (ss_res / ss_tot) if ss_tot else 1.0
