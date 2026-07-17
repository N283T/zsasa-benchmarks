#!/usr/bin/env python3
"""Build a standalone HTML gallery for generated benchmark figures."""

from __future__ import annotations

import argparse
import html
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIGURES_DIR = ROOT.joinpath("results", "figures")
DEFAULT_OUTPUT = DEFAULT_FIGURES_DIR.joinpath("gallery.html")
STORY_FILE_NAME = "story-figures.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--story-file",
        type=Path,
        help=f"figure paths to highlight (default: FIGURES_DIR/{STORY_FILE_NAME})",
    )
    return parser.parse_args()


def display_name(value: str) -> str:
    return value.replace("_", " ").replace("-", " ")


def counterpart(relative_png: Path, format_name: str) -> Path:
    parts = list(relative_png.parts)
    parts[parts.index("png")] = format_name
    return Path(*parts).with_suffix(f".{format_name}")


def load_story_paths(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line
        for raw_line in path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    }


def figure_cards(
    figures_dir: Path, story_paths: set[str]
) -> tuple[list[str], Counter[str]]:
    cards: list[str] = []
    counts: Counter[str] = Counter()
    png_paths = list(figures_dir.glob("*/png/**/*.png"))
    png_paths.sort(
        key=lambda path: (
            path.relative_to(figures_dir).as_posix() not in story_paths,
            path.relative_to(figures_dir).as_posix(),
        )
    )

    for png_path in png_paths:
        relative_png = png_path.relative_to(figures_dir)
        is_story = relative_png.as_posix() in story_paths
        group = relative_png.parts[0]
        counts[group] += 1
        label = display_name(png_path.stem)
        context_parts = relative_png.parts[2:-1]
        context = " / ".join(display_name(part) for part in context_parts)
        searchable = " ".join((group, context, label, "story" if is_story else "")).lower()
        svg_path = counterpart(relative_png, "svg")
        pdf_path = counterpart(relative_png, "pdf")
        links = [
            f'<a href="{html.escape(relative_png.as_posix())}" target="_blank">PNG</a>'
        ]
        if figures_dir.joinpath(svg_path).exists():
            links.append(
                f'<a href="{html.escape(svg_path.as_posix())}" target="_blank">SVG</a>'
            )
        if figures_dir.joinpath(pdf_path).exists():
            links.append(
                f'<a href="{html.escape(pdf_path.as_posix())}" target="_blank">PDF</a>'
            )

        context_html = (
            f'\n          <span class="context">{html.escape(context)}</span>'
            if context
            else ""
        )
        story_badge = '<span class="story-badge">STORY</span>' if is_story else ""
        cards.append(
            f"""
      <article class="figure-card"
               data-group="{html.escape(group)}"
               data-story="{str(is_story).lower()}"
               data-search="{html.escape(searchable)}">
        <button class="preview" type="button"
                data-image="{html.escape(relative_png.as_posix())}"
                data-label="{html.escape(label)}">
          <img src="{html.escape(relative_png.as_posix())}"
               alt="{html.escape(label)}" loading="lazy">
        </button>
        <div class="metadata">{story_badge}{context_html}
          <strong>{html.escape(label)}</strong>
          <span class="formats">{' · '.join(links)}</span>
        </div>
      </article>"""
        )

    return cards, counts


def build_html(figures_dir: Path, story_paths: set[str]) -> str:
    cards, counts = figure_cards(figures_dir, story_paths)
    story_count = len(story_paths)
    group_buttons = [
        f'<button type="button" data-group="{html.escape(group)}">'
        f"{html.escape(display_name(group))} ({count})</button>"
        for group, count in sorted(counts.items())
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Benchmark figure gallery</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: Canvas; color: CanvasText; }}
    header {{
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 1rem;
      background: color-mix(in srgb, Canvas 92%, transparent);
      border-bottom: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 .75rem; font-size: 1.25rem; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }}
    input {{ min-width: min(22rem, 80vw); padding: .55rem .7rem; font: inherit; }}
    button {{ padding: .45rem .7rem; font: inherit; cursor: pointer; }}
    .filters {{ display: flex; flex-wrap: wrap; gap: .35rem; }}
    .filters button[aria-pressed="true"] {{
      color: HighlightText;
      background: Highlight;
      border-color: Highlight;
    }}
    #status {{ margin: .65rem 0 0; color: GrayText; font-size: .9rem; }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
      padding: 1rem;
    }}
    .figure-card {{
      min-width: 0;
      overflow: hidden;
      border: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      border-radius: .6rem;
      background: color-mix(in srgb, CanvasText 3%, Canvas);
    }}
    .figure-card[hidden] {{ display: none; }}
    .figure-card[data-story="true"] {{ border-color: Highlight; }}
    .preview {{
      display: block;
      width: 100%;
      height: 260px;
      padding: 0;
      border: 0;
      border-radius: 0;
      background: white;
    }}
    .preview img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}
    .metadata {{ display: grid; gap: .25rem; padding: .7rem .8rem .8rem; }}
    .metadata strong {{ overflow-wrap: anywhere; font-size: .95rem; font-weight: 600; }}
    .story-badge {{
      width: fit-content;
      padding: .15rem .4rem;
      border-radius: .3rem;
      color: HighlightText;
      background: Highlight;
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .04em;
    }}
    .context {{ color: GrayText; font-size: .8rem; }}
    .formats {{ font-size: .85rem; }}
    .formats a {{ color: LinkText; }}
    dialog {{
      width: min(96vw, 1500px);
      max-width: none;
      padding: .75rem;
      border: 1px solid color-mix(in srgb, CanvasText 25%, transparent);
      border-radius: .7rem;
      background: Canvas;
      color: CanvasText;
    }}
    dialog::backdrop {{ background: rgb(0 0 0 / 72%); }}
    .dialog-head {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: center;
      margin-bottom: .6rem;
    }}
    .dialog-head strong {{ overflow-wrap: anywhere; }}
    #dialog-image {{
      display: block;
      width: 100%;
      max-height: 82vh;
      object-fit: contain;
      background: white;
    }}
    @media (max-width: 520px) {{
      main {{ grid-template-columns: 1fr; padding: .65rem; }}
      header {{ padding: .75rem; }}
      .preview {{ height: 220px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Benchmark figure gallery</h1>
    <div class="controls">
      <input id="search" type="search" placeholder="Filter by figure name…"
             aria-label="Filter figures">
      <div class="filters" aria-label="Figure groups">
        <button type="button" data-group="all" aria-pressed="true">all ({len(cards)})</button>
        <button type="button" data-group="story">story ({story_count})</button>
        {' '.join(group_buttons)}
      </div>
    </div>
    <p id="status">Showing {len(cards)} figures</p>
  </header>
  <main id="gallery">
    {''.join(cards)}
  </main>
  <dialog id="viewer">
    <div class="dialog-head">
      <strong id="dialog-label"></strong>
      <button id="close-dialog" type="button">Close</button>
    </div>
    <img id="dialog-image" alt="">
  </dialog>
  <script>
    const cards = [...document.querySelectorAll('.figure-card')];
    const search = document.getElementById('search');
    const status = document.getElementById('status');
    const groupButtons = [...document.querySelectorAll('[data-group]')]
      .filter(button => button.closest('.filters'));
    const viewer = document.getElementById('viewer');
    const dialogImage = document.getElementById('dialog-image');
    const dialogLabel = document.getElementById('dialog-label');
    let activeGroup = 'all';

    function updateGallery() {{
      const query = search.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach(card => {{
        const matchesGroup = activeGroup === 'all'
          || (activeGroup === 'story' && card.dataset.story === 'true')
          || card.dataset.group === activeGroup;
        const matchesSearch = !query || card.dataset.search.includes(query);
        card.hidden = !(matchesGroup && matchesSearch);
        if (!card.hidden) visible += 1;
      }});
      status.textContent = `Showing ${{visible}} of ${{cards.length}} figures`;
    }}

    groupButtons.forEach(button => button.addEventListener('click', () => {{
      activeGroup = button.dataset.group;
      groupButtons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      updateGallery();
    }}));
    search.addEventListener('input', updateGallery);

    document.querySelectorAll('.preview').forEach(button => {{
      button.addEventListener('click', () => {{
        dialogImage.src = button.dataset.image;
        dialogImage.alt = button.dataset.label;
        dialogLabel.textContent = button.dataset.label;
        viewer.showModal();
      }});
    }});
    document.getElementById('close-dialog').addEventListener('click', () => viewer.close());
    viewer.addEventListener('click', event => {{ if (event.target === viewer) viewer.close(); }});
  </script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    figures_dir = args.figures_dir.resolve()
    output = args.output.resolve()
    story_file = (
        args.story_file.resolve()
        if args.story_file
        else figures_dir.joinpath(STORY_FILE_NAME)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_html(figures_dir, load_story_paths(story_file)), encoding="utf-8"
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
