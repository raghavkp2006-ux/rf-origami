"""Unit tests for MetasurfacePhaseEngine and beam steering."""

import numpy as np
import pytest

from rf_origami.rf.metasurface.phase import MetasurfacePhaseEngine


def test_reflection_phase_calculation():
    s11_sample = [1.0 + 0j, 0.0 + 1.0j, -1.0 + 0j, 0.0 - 1.0j]
    phases = MetasurfacePhaseEngine.calculate_reflection_phase(s11_sample, unwrap=False)
    assert len(phases) == 4
    assert abs(phases[0] - 0.0) < 1e-4
    assert abs(phases[1] - 90.0) < 1e-4
    assert abs(abs(phases[2]) - 180.0) < 1e-4
    assert abs(phases[3] - (-90.0)) < 1e-4


def test_phase_agility_sweep():
    res = MetasurfacePhaseEngine.analyze_phase_agility(
        pattern_type="miura_ori",
        fold_angles_deg=[0.0, 30.0, 60.0],
        f_start_ghz=3.0,
        f_stop_ghz=5.0,
        num_freq_points=5,
    )
    assert len(res.frequencies_hz) == 5
    assert len(res.fold_angles_deg) == 3
    assert len(res.phase_matrix_deg) == 3
    assert res.max_phase_agility_deg >= 0.0


def test_anomalous_reflection_snell_law():
    res_prop = MetasurfacePhaseEngine.calculate_anomalous_reflection(
        frequency_hz=3.0e9,
        theta_inc_deg=0.0,
        phase_gradient_deg_per_m=1800.0,
    )
    assert res_prop["is_propagating"] is True
    assert abs(res_prop["theta_reflected_deg"]) > 0.0

    res_evanescent = MetasurfacePhaseEngine.calculate_anomalous_reflection(
        frequency_hz=3.0e9,
        theta_inc_deg=45.0,
        phase_gradient_deg_per_m=9000.0, # Exceeds k0
    )
    assert res_evanescent["is_propagating"] is False
