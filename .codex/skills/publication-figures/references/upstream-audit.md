# Upstream review

## Source

- Repository: `K-Dense-AI/scientific-agent-skills`
- Skill: `skills/scientific-visualization`
- Reviewed commit: `3f825caafe149b7853ec8c4d1dd7f4553ea6b2a5`
- Upstream skill license: MIT
- Review date: 2026-07-17

## Security review

The upstream directory was fetched into an isolated temporary directory and reviewed before this project skill was created.

Reviewed content:

- `SKILL.md`
- three Matplotlib style files
- one color-palette Python module
- two Python helper scripts
- four Markdown references

Static checks found no:

- network requests or data upload
- subprocess or shell execution
- environment-variable, credential, token, or SSH access
- deletion or broad filesystem traversal
- dynamic evaluation, deserialization, or obfuscated payloads
- prompt-injection instructions
- symlinks or executable binary files

The upstream helpers only configure Matplotlib, export figures to caller-selected paths, optionally inspect a caller-selected PDF, or write a caller-selected style file. They were not vendored because the project already has export and style infrastructure, and excluding executable code keeps this skill smaller and safer.

## Adaptation decisions

- Rewrote the skill instead of copying the large upstream instructions.
- Added repository-specific naming, palette, export, gallery, and verification rules.
- Removed categorical advice such as always showing uncertainty.
- Added language guidance based on the project's iterative figure review.
- Included no external scripts, dependencies, or assets.
