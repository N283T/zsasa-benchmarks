from __future__ import annotations

from scripts.plot_md_figures import (
    atom_frames_per_second,
    correction_runtime_rows,
    display_name,
    marker_for,
    md_performance_story_rows,
    md_rss_label_style,
    md_variant_name,
    milliseconds_per_frame,
    native_overcommit_rows,
    ratio_with_propagated_sd,
    zsasa_detail_rows,
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


def test_md_performance_story_rows_keeps_wrappers_and_precision_extremes() -> None:
    rows = [
        {"variant": variant}
        for variant in (
            "zsasa_cli_f64",
            "zsasa_cli_f32",
            "zsasa_cli_bitmask_f64",
            "zsasa_cli_bitmask_f32",
            "zsasa_mdtraj",
            "zsasa_mdtraj_bitmask",
            "zsasa_mdanalysis",
            "zsasa_mdanalysis_bitmask",
            "mdtraj",
            "mdsasa_bolt",
        )
    ]

    assert {row["variant"] for row in md_performance_story_rows(rows)} == {
        "zsasa_cli_f64",
        "zsasa_cli_bitmask_f32",
        "zsasa_mdtraj",
        "zsasa_mdtraj_bitmask",
        "zsasa_mdanalysis",
        "zsasa_mdanalysis_bitmask",
        "mdtraj",
        "mdsasa_bolt",
    }


def test_native_overcommit_rows_keeps_endpoints_and_corrected_bitmask() -> None:
    rows = [
        {"variant": variant, "threads": threads, "bitmask_variant": option}
        for variant, option in (
            ("zsasa_cli_f64", None),
            ("zsasa_cli_bitmask_f32", "single"),
            ("zsasa_cli_bitmask_f32", "single_corrected"),
        )
        for threads in (10, 20, 40)
    ]

    assert native_overcommit_rows(rows) == [
        {"variant": "zsasa_cli_f64", "threads": 10, "bitmask_variant": None},
        {"variant": "zsasa_cli_f64", "threads": 40, "bitmask_variant": None},
        {
            "variant": "zsasa_cli_bitmask_f32",
            "threads": 10,
            "bitmask_variant": "single_corrected",
        },
        {
            "variant": "zsasa_cli_bitmask_f32",
            "threads": 40,
            "bitmask_variant": "single_corrected",
        },
    ]


def test_correction_runtime_rows_keeps_raw_and_corrected_single_f32() -> None:
    rows = [
        {
            "run_set": "v0_9_0_md_128",
            "variant": "zsasa_cli_bitmask_f32",
            "threads": 10,
            "bitmask_variant": option,
        }
        for option in ("single", "single_corrected", "cycle")
    ]

    assert {row["bitmask_variant"] for row in correction_runtime_rows(rows)} == {
        "single",
        "single_corrected",
    }


def test_ratio_with_propagated_sd() -> None:
    ratio, uncertainty = ratio_with_propagated_sd(
        {"value": 2.0, "sd": 0.2},
        {"value": 4.0, "sd": 0.4},
        value_key="value",
        sd_key="sd",
    )

    assert ratio == 0.5
    assert uncertainty == 0.07071067811865477


def test_zsasa_detail_rows_keeps_only_5vz0_native_overcommit_paths() -> None:
    rows = [
        {
            "dataset_id": dataset_id,
            "variant": variant,
            "threads": threads,
            "bitmask_variant": option,
        }
        for dataset_id in ("5wvo_C_analysis", "5vz0_A_protein")
        for variant, option in (
            ("zsasa_cli_f64", None),
            ("zsasa_cli_bitmask_f32", "single"),
            ("zsasa_cli_bitmask_f32", "single_corrected"),
            ("zsasa_mdtraj", None),
            ("mdtraj", None),
        )
        for threads in (10, 20, 40)
    ]

    selected = zsasa_detail_rows(rows)

    assert {
        (
            row["dataset_id"],
            row["variant"],
            row["threads"],
            row["bitmask_variant"],
        )
        for row in selected
    } == {
        ("5vz0_A_protein", "zsasa_cli_f64", threads, None)
        for threads in (10, 20, 40)
    } | {
        ("5vz0_A_protein", "zsasa_cli_bitmask_f32", threads, "single_corrected")
        for threads in (10, 20, 40)
    }



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
        "arrowprops": arrow,
    }
    assert md_rss_label_style("6sup_A_analysis", "zsasa_mdtraj") == {
        "xytext": (8, 7),
        "ha": "left",
        "va": "bottom",
        "arrowprops": arrow,
    }
    assert md_rss_label_style("6sup_A_analysis", "zsasa_cli_f32") == {
        "xytext": (8, 7),
        "ha": "left",
        "va": "bottom",
        "arrowprops": arrow,
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



def test_plot_rss_grid_uses_legend_only_for_unlabeled_linear_plot(tmp_path) -> None:
    import matplotlib.pyplot as plt
    from scripts.plot_md_figures import plot_throughput_vs_rss_grid

    legend_calls: list[dict[str, object]] = []
    original_legend = plt.Figure.legend

    def recording_legend(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        legend_calls.append(kwargs)
        return original_legend(self, *args, **kwargs)

    rows = [
        {
            "dataset_id": "5wvo_C_analysis",
            "variant": "zsasa_cli_f64",
            "rss_mib": 10.0,
            "fps": 20.0,
        }
    ]
    try:
        plt.Figure.legend = recording_legend  # type: ignore[method-assign]
        plot_throughput_vs_rss_grid(rows, tmp_path / "linear", log_x=False)
        plot_throughput_vs_rss_grid(rows, tmp_path / "log", log_x=True)
    finally:
        plt.Figure.legend = original_legend  # type: ignore[method-assign]

    assert len(legend_calls) == 1



def test_log_rss_plot_has_plain_title(tmp_path) -> None:
    import matplotlib.pyplot as plt
    from scripts.plot_md_figures import plot_throughput_vs_rss_grid

    titles: list[str] = []
    original_suptitle = plt.Figure.suptitle

    def recording_suptitle(self, text, *args, **kwargs):  # type: ignore[no-untyped-def]
        titles.append(str(text))
        return original_suptitle(self, text, *args, **kwargs)

    rows = [
        {
            "dataset_id": "5wvo_C_analysis",
            "variant": "zsasa_cli_f64",
            "rss_mib": 10.0,
            "fps": 20.0,
        }
    ]
    try:
        plt.Figure.suptitle = recording_suptitle  # type: ignore[method-assign]
        plot_throughput_vs_rss_grid(rows, tmp_path, log_x=True)
    finally:
        plt.Figure.suptitle = original_suptitle  # type: ignore[method-assign]

    assert titles == ["MD throughput vs peak RSS"]


def test_main_generates_only_log_rss_tradeoff(monkeypatch, tmp_path) -> None:
    import argparse

    import scripts.plot_md_figures as module

    rss_log_flags: list[bool] = []
    rows = [
        {
            "dataset_id": "5wvo_C_analysis",
            "variant": "zsasa_cli_f64",
            "rss_mib": 10.0,
            "fps": 20.0,
            "mean_s": 1.0,
            "user_time_s": 1.0,
            "system_time_s": 0.0,
        }
    ]

    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(db=tmp_path / "db", out_dir=tmp_path),
    )
    monkeypatch.setattr(module, "setup_style", lambda: None)
    monkeypatch.setattr(module, "load_md_rows", lambda _db: rows)
    monkeypatch.setattr(module, "load_md_correction_accuracy", lambda _db: [])
    monkeypatch.setattr(module, "plot_bar_grid", lambda *args, **kwargs: [])
    monkeypatch.setattr(module, "plot_cpu_utilization_grid", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        module, "plot_md_performance_memory_story", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        module, "plot_md_zsasa_performance_memory_detail", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        module, "plot_md_correction_accuracy_throughput", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        module, "plot_md_comparator_ratios_by_trajectory", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(module, "plot_md_overcommit_tradeoff", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        module, "plot_md_correction_runtime_effect", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(module, "write_index", lambda out_dir, outputs: out_dir / "index.md")

    def recording_rss_grid(_rows, _out_dir, *, log_x=False):  # type: ignore[no-untyped-def]
        rss_log_flags.append(log_x)
        return []

    monkeypatch.setattr(module, "plot_throughput_vs_rss_grid", recording_rss_grid)

    module.main()

    assert rss_log_flags == [True]
