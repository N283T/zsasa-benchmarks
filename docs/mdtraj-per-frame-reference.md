# MDTraj per-frame reference for trajectory validation

## Behaviour

`mdtraj.shrake_rupley` (checked with MDTraj 1.11.2; the harness pins 1.11.1.post1)
returns inflated per-atom areas for frames 2..N when it is given a multi-frame
trajectory: the result for a frame depends on the frames before it. Calling it one
frame at a time gives the correct values, and an independent NumPy Shrake-Rupley
implementation matches those per-frame values point for point. Frame 0 is identical
either way.

The inflation is about `1 + 4*pi*r^2/n_points` per atom (r in nm). On the 5wvo_C
trajectory this is +1.5% of total SASA at 64 points, +0.75% at 128, +0.37% at 256,
+0.19% at 512, and +0.09% at 1,024.

## Harness handling

`scripts/benchlib/trajectory_tools.py` exposes `--mdtraj-per-frame` for the `mdtraj`
tool, threaded through `mdtraj_runner_command(..., mdtraj_per_frame=True)`.

- Validation (`scripts/run_trajectory_validation.py`) enables it for `mdtraj`, so the
  per-frame reference that zsasa is compared against is correct.
- Throughput timing (`scripts/run_trajectory.py`) keeps the single multi-frame call,
  which is how MDTraj is normally used. Its command lines are unchanged and existing
  timing results are not affected.

## Regenerating the reference

```bash
nix develop -c uv run python scripts/run_trajectory_validation.py \
  --manifest manifests/validation-md-5wvo.toml --datasets config/datasets.local.toml \
  --run-id v0_9_0_validation --only 'mdtraj_*' --replace --execute
```

Re-import `results/full_rerun/v0_9_0_validation/validation_md/5wvo_C_analysis`
(`import_trajectory_validation` in `scripts/import_full_rerun.py`), then re-export
`results/tables/` and re-plot `results/figures/validation/`.

## Effect on results (5wvo_C, 1,001 frames)

Against the per-frame reference, the median signed relative difference is about 0.00%
for `zsasa_mdtraj` at every point count (mean absolute difference 0.38% at 64 points
falling to 0.05% at 1,024), about -0.31% for `zsasa_cli_f64`, about -2.0% for the
uncorrected bitmask (`single`), and about -0.37% for `single_corrected`. Earlier
values computed from the multi-frame MDTraj call overstated the differences, most
visibly at low point counts.
