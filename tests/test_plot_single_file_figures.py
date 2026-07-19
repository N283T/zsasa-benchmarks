from __future__ import annotations

from scripts.plot_single_file_figures import single_story_rows


def test_single_story_rows_separates_formats_and_omits_bitmask() -> None:
    rows = [
        {"format": format_label, "variant": variant, "threads": threads}
        for format_label in ("PDB", "mmCIF")
        for variant in (
            "zsasa_f64",
            "zsasa_f32",
            "zsasa_bitmask_f64",
            "zsasa_bitmask_f32",
            "freesasa",
            "rustsasa",
            "pdbtools_jl",
        )
        for threads in (1, 10)
    ]

    selected = single_story_rows(rows, "PDB")

    assert {row["format"] for row in selected} == {"PDB"}
    assert {row["threads"] for row in selected} == {10}
    assert {row["variant"] for row in selected} == {
        "zsasa_f64",
        "freesasa",
        "rustsasa",
        "pdbtools_jl",
    }
