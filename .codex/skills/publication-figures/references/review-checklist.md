# Figure review checklist

## Scientific message

- Can the intended claim be stated in one sentence?
- Is the comparison target explicit?
- Are fixed conditions and omitted methods intentional?
- Does the statistic match the claim?
- Are difference direction and denominator unambiguous?

## Text

- Use `zsasa` consistently.
- Avoid semicolons in titles and labels.
- Put conditions in parentheses.
- Use sentence case and concise wording.
- Include units.
- Format mathematical symbols correctly.
- Remove redundant words such as `standard` when the base name is sufficient.

## Appearance

- Check the figure at final manuscript size.
- Keep text, lines, markers, and panel labels crisp and readable.
- Keep colors consistent with the project and distinguishable without color alone.
- Ensure the legend does not hide data.
- Keep grids and reference lines subordinate to the data.
- Verify multi-panel alignment and comparable axis treatment.

## Statistics

- Identify every uncertainty band or error bar.
- Do not imply ground truth unless one exists.
- Do not claim convergence, accumulation, or correction without direct evidence.
- Avoid excessive precision in displayed statistics.

## Artifacts and checks

- Generate PNG, SVG, and PDF.
- Inspect the PNG visually.
- Check vector output when practical.
- Regenerate only the affected figure group.
- Update story manifest, indices, and gallery when applicable.
- Run focused Ruff, tests, and `git diff --check`.
