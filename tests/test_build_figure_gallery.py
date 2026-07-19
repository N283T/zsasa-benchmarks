from pathlib import Path

from scripts.build_figure_gallery import build_html, figure_cards, load_figure_paths


def touch_figure(figures_dir: Path, relative_path: str) -> None:
    path = figures_dir.joinpath(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_load_figure_paths_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    manifest = tmp_path.joinpath("figures.txt")
    manifest.write_text("# comment\n\nbatch/png/current.png\n", encoding="utf-8")

    assert load_figure_paths(manifest) == {"batch/png/current.png"}


def test_working_figures_are_highlighted_and_sorted_first(tmp_path: Path) -> None:
    touch_figure(tmp_path, "batch/png/archived.png")
    touch_figure(tmp_path, "batch/png/current.png")
    cards, _ = figure_cards(
        tmp_path,
        story_paths={"batch/png/archived.png"},
        working_paths={"batch/png/current.png"},
    )

    assert "current.png" in cards[0]
    assert 'data-working="true"' in cards[0]
    assert '<span class="working-badge">WORKING</span>' in cards[0]
    assert '<span class="story-badge">STORY</span>' in cards[1]


def test_gallery_includes_working_filter_and_viewer_navigation(tmp_path: Path) -> None:
    relative_path = "batch/png/current.png"
    touch_figure(tmp_path, relative_path)

    output = build_html(tmp_path, story_paths=set(), working_paths={relative_path})

    assert 'data-group="working">working (1)</button>' in output
    assert 'aria-label="Previous figure">‹</button>' in output
    assert 'aria-label="Next figure">›</button>' in output
    assert "event.key === 'ArrowLeft'" in output
    assert "event.key === 'ArrowRight'" in output
