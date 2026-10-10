"""Unit tests for MetasurfacePolarizationEngine and PCR analysis."""

import numpy as np
import pytest

from rf_origami.rf.metasurface.polarization import MetasurfacePolarizationEngine


def test_polarization_matrix_evaluation():
    res = MetasurfacePolarizationEngine.evaluate_polarization_matrix(
        pattern_type="miura_ori",
        fold_angle_deg=30.0,
        f_start_ghz=3.0,
        f_stop_ghz=5.0,
        num_freq_points=5,
        anisotropic_axis_deg=45.0,
    )
    assert len(res.frequencies_hz) == 5
    assert len(res.r_xx) == 5
    assert len(res.r_yx) == 5
    assert len(res.pcr_linear) == 5
    assert len(res.axial_ratio_db) == 5
    assert 0.0 <= res.peak_pcr <= 1.0
    assert res.peak_pcr_freq_hz > 0.0
