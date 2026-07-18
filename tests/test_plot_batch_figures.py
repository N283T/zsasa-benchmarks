from __future__ import annotations

from scripts.export_summary_tables import batch_variant_name
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
    versioned_bitmask = {"tool_id": "zsasa_0_9_0", "precision": "f32", "mode": "bitmask"}
    assert batch_column_name(versioned_bitmask) == "zsasa_0_9_0_bitmask_f32"
    assert batch_variant_name(versioned_bitmask) == "zsasa_0_9_0_bitmask_f32"
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


def test_ecoli_comparison_rows_excludes_overcommit_threads() -> None:
    from scripts.plot_batch_figures import ecoli_comparison_rows

    rows = [{"threads": thread} for thread in (1, 4, 8, 10, 20, 40)]

    assert ecoli_comparison_rows(rows) == [
        {"threads": 1},
        {"threads": 4},
        {"threads": 8},
        {"threads": 10},
    ]


def test_ecoli_story_rows_selects_precision_extremes_and_comparators() -> None:
    from scripts.plot_batch_figures import ecoli_story_rows

    rows = [
        {"variant": variant, "threads": threads}
        for variant in (
            "zsasa_f64",
            "zsasa_f32",
            "zsasa_bitmask_f64",
            "zsasa_bitmask_f32",
            "freesasa_batch",
            "rustsasa",
            "lahuta",
            "lahuta_bitmask",
        )
        for threads in (1, 10, 20)
    ]

    assert {(row["variant"], row["threads"]) for row in ecoli_story_rows(rows)} == {
        (variant, threads)
        for variant in (
            "zsasa_f64",
            "zsasa_bitmask_f32",
            "freesasa_batch",
            "rustsasa",
            "lahuta_bitmask",
        )
        for threads in (1, 10)
    }


def test_human_cif_t20_rows_selects_complete_parser_io_matrix() -> None:
    from scripts.plot_batch_figures import human_cif_t20_rows

    rows = [
        {"variant": variant, "threads": threads}
        for variant in (
            "zsasa_generic_read",
            "zsasa_generic_mmap",
            "zsasa_af_fast_read",
            "zsasa_af_fast_mmap",
            "lahuta_bitmask",
        )
        for threads in (10, 20, 40)
    ]

    assert {row["variant"] for row in human_cif_t20_rows(rows)} == {
        "zsasa_generic_read",
        "zsasa_generic_mmap",
        "zsasa_af_fast_read",
        "zsasa_af_fast_mmap",
    }
    assert {row["threads"] for row in human_cif_t20_rows(rows)} == {20}


def test_row_for_selects_variant_and_worker_count() -> None:
    from scripts.plot_batch_figures import row_for

    rows = [
        {"variant": "zsasa_af_fast_read", "threads": 10, "value": "ten"},
        {"variant": "zsasa_af_fast_read", "threads": 40, "value": "forty"},
    ]

    assert row_for(rows, "zsasa_af_fast_read", 40)["value"] == "forty"



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
