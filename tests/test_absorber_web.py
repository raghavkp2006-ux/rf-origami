"""Integration tests for web services and REST endpoints supporting Absorber mode."""

import json
import pytest

from rf_origami.web.service import OrigamiWebService


def test_web_service_simulate_absorber():
    res = OrigamiWebService.simulate_absorber(
        pattern_type="miura_ori",
        params={"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angle_deg=30.0,
        f_start_ghz=1.5,
        f_stop_ghz=5.0,
        num_points=9,
        substrate_material="kapton",
        conductor_material="copper",
        ground_backed=True,
    )

    assert "frequencies_ghz" in res
    assert "absorption" in res
    assert "s11_db" in res
    assert "resonant_frequency_ghz" in res
    assert "peak_absorption" in res
    assert len(res["frequencies_ghz"]) == 9


def test_web_service_run_absorber_fold_sweep():
    res = OrigamiWebService.run_absorber_fold_sweep(
        pattern_type="miura_ori",
        params={"a": 20.0, "b": 20.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angles=[0.0, 30.0],
        f_start_ghz=2.0,
        f_stop_ghz=4.0,
        num_points=5,
    )

    assert "absorption_matrix" in res
    assert len(res["absorption_matrix"]) == 2
    assert "resonance_vs_fold" in res


def test_web_service_get_absorber_benchmarks():
    res = OrigamiWebService.get_absorber_benchmarks()
    assert "all_passed" in res
    assert "benchmarks" in res
    assert len(res["benchmarks"]) == 5
    assert res["all_passed"] is True


def test_web_service_export_fabrication():
    zip_bytes = OrigamiWebService.export_fabrication(
        pattern_type="miura_ori",
        params={"a": 20.0, "b": 20.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angle_deg=25.0,
        design_id="TEST-ABS-PKG",
    )

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 500  # Non-trivial ZIP archive


def test_web_service_compare_measurement():
    csv_sample = """frequency_hz,reflection_db,absorption
2.0e9,-3.0,0.50
2.5e9,-18.0,0.98
3.0e9,-4.0,0.60
"""
    res = OrigamiWebService.compare_measurement(
        csv_data=csv_sample,
        pattern_type="miura_ori",
        params={"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angle_deg=20.0,
    )

    assert "measurement" in res
    assert "simulation" in res
    assert "comparison" in res
    assert "frequency_error_percent" in res["comparison"]
