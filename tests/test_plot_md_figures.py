from __future__ import annotations

from scripts.plot_md_figures import (
    atom_frames_per_second,
    display_name,
    marker_for,
    md_rss_label_style,
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


def test_md_rss_label_style_matches_manual_offsets() -> None:
    arrow = {"arrowstyle": "-", "color": "0.35", "lw": 0.7}

    assert md_rss_label_style("5wvo_C_analysis", "zsasa_cli_f32") == {
        "xytext": (8, 7),
        "ha": "left",
        "va": "bottom",
    }
    assert md_rss_label_style("5wvo_C_analysis", "zsasa_cli_f64") == {
        "xytext": (8, -7),
        "ha": "left",
        "va": "top",
    }
    assert md_rss_label_style("5wvo_C_analysis", "mdsasa_bolt") == {
        "xytext": (-10, 0),
        "ha": "right",
        "va": "center",
        "arrowprops": arrow,
    }
    assert md_rss_label_style("6sup_A_analysis", "zsasa_mdanalysis") == {
        "xytext": (8, -7),
        "ha": "left",
        "va": "top",
    }
    assert md_rss_label_style("6sup_A_analysis", "zsasa_mdtraj") == {
        "xytext": (8, 7),
        "ha": "left",
        "va": "bottom",
    }
    assert md_rss_label_style("5vz0_A_protein", "zsasa_cli_bitmask_f64") == {
        "xytext": (24, -12),
        "ha": "left",
        "va": "top",
        "arrowprops": arrow,
    }


def test_md_display_names_omit_xtc_suffix() -> None:
    assert display_name("zsasa_mdtraj") == "zsasa + MDTraj"
    assert display_name("zsasa_mdtraj_bitmask") == "zsasa + MDTraj bitmask"
    assert display_name("zsasa_mdanalysis") == "zsasa + MDAnalysis"
    assert display_name("zsasa_mdanalysis_bitmask") == "zsasa + MDAnalysis bitmask"
