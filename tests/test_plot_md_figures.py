from __future__ import annotations

from scripts.plot_md_figures import (
    atom_frames_per_second,
    marker_for,
    md_variant_name,
    milliseconds_per_frame,
)


def test_md_variant_name_maps_tools() -> None:
    assert (
        md_variant_name({"tool_id": "zig", "precision": "f64", "mode": "standard"})
        == "zsasa_cli_f64"
    )
    assert (
        md_variant_name({"tool_id": "zig_bitmask", "precision": "f32", "mode": "bitmask"})
        == "zsasa_cli_bitmask_f32"
    )
    assert (
        md_variant_name({"tool_id": "zsasa_mdtraj_bitmask", "precision": "f64", "mode": "bitmask"})
        == "zsasa_mdtraj_bitmask"
    )
    assert (
        md_variant_name({"tool_id": "mdsasa_bolt", "precision": "f64", "mode": "standard"})
        == "mdsasa_bolt"
    )


def test_milliseconds_per_frame() -> None:
    assert milliseconds_per_frame(2.0, 1000) == 2.0


def test_atom_frames_per_second() -> None:
    assert atom_frames_per_second(1000, 10, 2.0) == 5000.0



def test_marker_for_backend_families() -> None:
    assert marker_for("zsasa_cli_f64") == "o"
    assert marker_for("zsasa_cli_bitmask_f32") == "o"
    assert marker_for("zsasa_mdtraj") == "^"
    assert marker_for("zsasa_mdtraj_bitmask") == "^"
    assert marker_for("mdtraj") == "^"
    assert marker_for("zsasa_mdanalysis") == "s"
    assert marker_for("zsasa_mdanalysis_bitmask") == "s"
    assert marker_for("mdsasa_bolt") == "s"
