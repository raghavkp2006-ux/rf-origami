"""Unit tests for MetasurfaceFarFieldEngine and ECM."""

import numpy as np
import pytest

from rf_origami.rf.metasurface.farfield import MetasurfaceFarFieldEngine
from rf_origami.rf.metasurface.ecm import MetasurfaceECMEngine


def test_farfield_rcs_calculation():
    res = MetasurfaceFarFieldEngine.calculate_bistatic_rcs(
        pattern_type="miura_ori",
        fold_angle_deg=30.0,
        frequency_hz=3.0e9,
        num_theta=9,
        num_phi=5,
    )
    assert len(res.theta_angles_deg) == 9
    assert len(res.phi_angles_deg) == 5
    assert len(res.rcs_bistatic_dbsm) == 9
    assert len(res.rcs_bistatic_dbsm[0]) == 5
    assert res.reference_pec_rcs_m2 > 0.0
    assert res.monostatic_rcs_m2 >= 0.0


def test_equivalent_circuit_model():
    res = MetasurfaceECMEngine.evaluate_circuit(
        facet_length_mm=25.0,
        fold_angle_deg=30.0,
        f_start_ghz=2.0,
        f_stop_ghz=6.0,
        num_points=11,
    )
    assert res.grid_inductance_nh > 0.0
    assert res.grid_capacitance_pf > 0.0
    assert len(res.s11_db) == 11
    assert len(res.absorption) == 11
    assert 0.0 <= res.peak_absorption <= 1.0
