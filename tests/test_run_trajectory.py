from __future__ import annotations

from scripts.run_trajectory import command_variants


def test_command_variants_separate_multi_thread_raw_outputs() -> None:
    settings = {
        "threads": [10, 20, 40],
        "wrapper_threads": [10],
        "cli_precisions": ["f64", "f32"],
        "cli_bitmask_variants": ["single", "single_corrected"],
    }
    dataset = {"id": "trajectory"}

    native = command_variants(
        tool="zig", dataset=dataset, n_points=128, settings=settings
    )
    bitmask = command_variants(
        tool="zig_bitmask", dataset=dataset, n_points=128, settings=settings
    )
    wrapper = command_variants(
        tool="zsasa_mdtraj", dataset=dataset, n_points=128, settings=settings
    )

    assert {row["threads"] for row in native} == {10, 20, 40}
    assert len({tuple(row["raw_parts"]) for row in native}) == len(native)
    assert len({tuple(row["raw_parts"]) for row in bitmask}) == len(bitmask)
    assert {row["threads"] for row in wrapper} == {10}
