"""Unit tests for automated multi-angle fold sweeps and heatmaps."""

import numpy as np
import pytest

from rf_origami.rf.absorber.fold_sweep import run_absorber_fold_sweep, AbsorberFoldSweepResult


def test_absorber_fold_sweep_execution():
    angles = [0.0, 20.0, 40.0]
    sweep_res = run_absorber_fold_sweep(
        pattern_type="miura_ori",
        pattern_params={"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angles_deg=angles,
        f_start_ghz=1.0,
        f_stop_ghz=5.0,
        num_freq_points=9,
        substrate_material="kapton",
        conductor_material="copper",
        ground_backed=True,
    )

    assert isinstance(sweep_res, AbsorberFoldSweepResult)
    assert len(sweep_res.fold_angles_deg) == 3
    assert len(sweep_res.frequencies_hz) == 9
    assert len(sweep_res.absorption_matrix) == 3
    assert len(sweep_res.absorption_matrix[0]) == 9
    assert len(sweep_res.s11_db_matrix) == 3
    assert len(sweep_res.resonance_vs_fold) == 3
    assert sweep_res.tuning_ratio >= 1.0


def test_absorber_fold_sweep_serialization():
    sweep_res = run_absorber_fold_sweep(
        pattern_type="miura_ori",
        pattern_params={"a": 20.0, "b": 20.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angles_deg=[10.0, 30.0],
        f_start_ghz=2.0,
        f_stop_ghz=4.0,
        num_freq_points=5,
    )

    d = sweep_res.to_dict()
    assert "fold_angles_deg" in d
    assert "frequencies_ghz" in d
    assert "absorption_matrix" in d
    assert "results_by_angle" in d
    assert "tuning_range_ghz" in d
