---
name: publication-figures
description: Create, refine, and review publication-ready scientific figures in this benchmark repository. Use for Matplotlib plotting, manuscript figure selection, multi-panel composition, labels and units, uncertainty displays, color and typography, PNG/SVG/PDF export, or visual quality review of generated benchmark figures.
---

# Publication Figures

Turn benchmark results into a small set of figures that support explicit scientific claims. Prefer clarity and reproducibility over exhaustive plotting.

## Workflow

1. Read the repository `AGENTS.md`, relevant plotting code, and existing figures before editing.
2. State the claim or story the figure should communicate.
3. Identify the comparison, reference, statistic, and fixed conditions. Do not plot every available tool merely because data exists.
4. Reuse project conventions and make the smallest plotting change that supports the claim.
5. Regenerate only affected outputs. Avoid broad regeneration that rewrites unrelated tracked SVG or PDF files.
6. Inspect the rendered PNG, not only script completion. Check representative panels at their intended final size.
7. Run focused lint and tests, then update the gallery, indices, and story manifest when applicable.

Use `references/review-checklist.md` before presenting a figure as complete.

## Language and Labels

- Use concise, natural English in titles and labels.
- Avoid semicolons in titles and labels. Put experimental conditions in parentheses, for example `Difference from zsasa f32 (1,024 points)`.
- Use sentence case.
- Name the comparison target in the title, axis label, or panel heading when it is not otherwise unmistakable.
- Do not add `standard` when the unqualified tool name already denotes the non-bitmask implementation. Add mode qualifiers only to disambiguate.
- Include physical units in parentheses, such as `Total SASA (Å²)`.
- Use mathematical typography for symbols, such as `$R^2$` and `$n$`.
- Prefer `difference` over `error` when neither method is a ground truth.
- Do not place implementation details in the title unless they are essential to interpreting the result.

## Scientific Encoding

- Choose signed differences when bias direction matters and absolute differences when magnitude alone matters.
- Define the denominator and reference for relative differences.
- Show uncertainty only when it has a meaningful interpretation. State whether it is SD, SEM, CI, percentile range, or another statistic.
- Treat zero and identity lines as quiet references. Emphasize them only when the scientific story depends on agreement.
- Use log scales only when they materially improve interpretation. Make the scale evident from ticks and axis behavior, not title suffixes.
- Avoid implying temporal accumulation from frame-wise variation unless the data demonstrates accumulation.

## Visual Design

- Follow the repository tool palette before introducing new colors.
- Encode important distinctions with line style or marker shape as well as color.
- Keep the main result visually prominent and contextual series secondary.
- Use restrained grids, reference lines, and annotations. Remove decorations that do not help interpretation.
- Keep panel dimensions, limits, typography, and spacing consistent when panels are meant to be compared.
- Use lowercase parenthesized panel labels, such as `(a)` and `(b)`, in bold at a consistent position just outside the upper-left of each panel. Keep the panel title separate from the label.
- Keep figure and panel titles concise. Move sample counts, fixed benchmark conditions, uncertainty definitions, and methodological qualifications to the caption when they are not required to read the axes.
- Ensure legends do not obscure data. Prefer direct labels when they reduce lookup effort without clutter.
- Use frameless legends by default across STORY figures. Reposition a legend before adding a box; use a framed legend only when no clear placement is practical.
- Preserve legibility in grayscale and for common color-vision deficiencies.

## Project Conventions

- Use `zsasa`, not `zSASA`.
- Use the established orange/yellow family for zsasa, blue for FreeSASA or MDTraj, red for RustSASA, and purple for Lahuta.
- Export each selected figure as PNG, SVG, and PDF under `results/figures/`.
- Keep stable filenames unless renaming is explicitly part of the task.
- Do not delete older tracked figures unless the user explicitly requests deletion.
- Add manuscript-story PNG paths to `results/figures/story-figures.txt`.
- Rebuild `results/figures/gallery.html` after adding or changing gallery figures.
- Use `uv run` for Python commands and focused repository checks.

## Verification

- Open every new or materially changed story figure with an image viewer.
- Confirm titles, units, comparison targets, legend text, panel labels, and mathematical notation.
- Check that lines, markers, and uncertainty bands remain distinguishable.
- Parse or open vector outputs when practical.
- Run `git diff --check` and focused Ruff/tests.
- Report what was regenerated and what was visually inspected.

## Provenance

This skill was informed by the K-Dense `scientific-visualization` skill but was rewritten for this repository. No upstream executable code is included. See `references/upstream-audit.md` for the reviewed source and security notes.
