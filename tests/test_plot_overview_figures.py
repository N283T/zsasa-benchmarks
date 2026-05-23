from __future__ import annotations

from pathlib import Path

from scripts.plot_overview_figures import (
    FigureSection,
    figure_sections,
    format_markdown_table,
    speedup_against_baseline,
)


def test_speedup_against_baseline_uses_higher_is_better_metric() -> None:
    rows = [
        {"dataset": "E. coli", "variant": "FreeSASA batch", "throughput": 10.0},
        {"dataset": "E. coli", "variant": "zsasa f64", "throughput": 25.0},
        {"dataset": "Human", "variant": "FreeSASA batch", "throughput": 5.0},
        {"dataset": "Human", "variant": "zsasa f64", "throughput": 20.0},
    ]

    result = speedup_against_baseline(
        rows,
        group_key="dataset",
        variant_key="variant",
        value_key="throughput",
        baseline_variant="FreeSASA batch",
    )

    assert result == [
        {
            "dataset": "E. coli",
            "variant": "zsasa f64",
            "baseline": "FreeSASA batch",
            "speedup": 2.5,
        },
        {
            "dataset": "Human",
            "variant": "zsasa f64",
            "baseline": "FreeSASA batch",
            "speedup": 4.0,
        },
    ]


def test_figure_sections_counts_pngs(tmp_path: Path) -> None:
    tmp_path.joinpath("validation", "png").mkdir(parents=True)
    tmp_path.joinpath("validation", "png", "a.png").write_bytes(b"")
    tmp_path.joinpath("validation", "png", "b.png").write_bytes(b"")
    tmp_path.joinpath("validation", "index.md").write_text("# validation\n", encoding="utf-8")

    assert figure_sections(tmp_path) == [
        FigureSection(
            name="validation",
            png_count=2,
            index_path=tmp_path / "validation" / "index.md",
        )
    ]


def test_format_markdown_table() -> None:
    text = format_markdown_table(
        ["dataset", "runs"],
        [{"dataset": "batch", "runs": 3}, {"dataset": "md", "runs": 2}],
    )

    assert text == "| dataset | runs |\n| --- | --- |\n| batch | 3 |\n| md | 2 |"
