from __future__ import annotations

from scripts.plot_batch_figures import (
    batch_column_name,
    memory_summary_mb,
    speedup_rows,
    throughput_per_second,
)


def test_batch_column_name_maps_variants() -> None:
    assert (
        batch_column_name({"tool_id": "zsasa", "precision": "f64", "mode": "standard"})
        == "zsasa_f64"
    )
    assert (
        batch_column_name({"tool_id": "zsasa", "precision": "f32", "mode": "bitmask"})
        == "zsasa_bitmask_f32"
    )
    assert (
        batch_column_name({"tool_id": "rustsasa", "precision": "f64", "mode": "standard"})
        == "rustsasa"
    )
    assert (
        batch_column_name({"tool_id": "freesasa_batch", "precision": "f64", "mode": "standard"})
        == "freesasa_batch"
    )
    assert (
        batch_column_name({"tool_id": "lahuta", "precision": "f64", "mode": "bitmask"})
        == "lahuta_bitmask"
    )


def test_throughput_per_second() -> None:
    assert throughput_per_second(4370, 4.37) == 1000.0


def test_speedup_rows_uses_one_thread_baseline() -> None:
    rows = [
        {"variant": "zsasa_f64", "threads": 1, "mean_s": 10.0},
        {"variant": "zsasa_f64", "threads": 4, "mean_s": 2.5},
        {"variant": "rustsasa", "threads": 4, "mean_s": 5.0},
    ]

    result = speedup_rows(rows)

    assert result == [
        {"variant": "zsasa_f64", "threads": 1, "speedup": 1.0, "efficiency": 1.0},
        {"variant": "zsasa_f64", "threads": 4, "speedup": 4.0, "efficiency": 1.0},
    ]


def test_memory_summary_mb_reports_mean_and_stddev() -> None:
    mean_mb, stddev_mb = memory_summary_mb([1048576, 3145728])

    assert mean_mb == 2.0
    assert stddev_mb == 1.4142135623730951


def test_cpu_utilization_proxy_uses_user_and_system_over_runtime() -> None:
    from scripts.plot_batch_figures import cpu_utilization_proxy

    assert cpu_utilization_proxy({"mean_s": 2.0, "user_time_s": 3.0, "system_time_s": 1.0}) == 2.0


def test_dataset_slug_and_label_for_human() -> None:
    from scripts.plot_batch_figures import dataset_label, dataset_slug

    assert dataset_slug("UP000005640_9606_HUMAN_v6_pdb") == "human"
    assert dataset_label("UP000005640_9606_HUMAN_v6_pdb") == "Human AFDB"


def test_milliseconds_per_structure() -> None:
    from scripts.plot_batch_figures import milliseconds_per_structure

    assert milliseconds_per_structure(2.0, 1000) == 2.0



def test_batch_comparison_label_style_places_selected_labels() -> None:
    from scripts.plot_batch_figures import batch_comparison_label_style

    assert batch_comparison_label_style("lahuta") == {
        "xytext": (-8, 8),
        "ha": "right",
        "va": "bottom",
        "arrowprops": {"arrowstyle": "-", "color": "0.35", "lw": 0.7},
    }
    assert batch_comparison_label_style("zsasa_f64") == {
        "xytext": (-8, 8),
        "ha": "right",
        "va": "bottom",
        "arrowprops": {"arrowstyle": "-", "color": "0.35", "lw": 0.7},
    }
    assert batch_comparison_label_style("zsasa_bitmask_f64") == {
        "xytext": (-10, 0),
        "ha": "right",
        "va": "center",
        "arrowprops": {"arrowstyle": "-", "color": "0.35", "lw": 0.7},
    }
