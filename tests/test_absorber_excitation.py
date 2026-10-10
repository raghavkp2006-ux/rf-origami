"""Unit tests for PlaneWave electromagnetic excitation module."""

import math
import numpy as np
import pytest

from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.materials.material import ETA_0, C_0


def test_plane_wave_normal_incidence_initialization():
    pw = PlaneWave.normal_incidence(frequency_hz=2.45e9, polarization=PolarizationType.LINEAR_X)
    assert pw.frequency_hz == 2.45e9
    assert np.allclose(pw.propagation_direction, [0.0, 0.0, -1.0])
    assert np.allclose(pw.polarization_vector, [1.0, 0.0, 0.0])
    assert abs(np.dot(pw.propagation_direction, pw.polarization_vector)) < 1e-6
    assert abs(pw.wavelength_m - (C_0 / 2.45e9)) < 1e-6


def test_plane_wave_fields_evaluation():
    pw = PlaneWave.normal_incidence(frequency_hz=3.0e9, electric_field_amplitude=2.0)
    r = np.array([0.0, 0.0, 0.05])
    e_field = pw.e_field_at(r)
    h_field = pw.h_field_at(r)

    # Magnitude check
    assert abs(np.linalg.norm(np.abs(e_field)) - 2.0) < 1e-6
    assert abs(np.linalg.norm(np.abs(h_field)) - (2.0 / ETA_0)) < 1e-6

    # E and H must be orthogonal
    assert abs(np.dot(np.abs(e_field), np.abs(h_field))) < 1e-6


def test_plane_wave_oblique_incidence():
    pw = PlaneWave.oblique_incidence(
        frequency_hz=5.0e9,
        theta_inc_deg=45.0,
        phi_inc_deg=0.0,
        polarization=PolarizationType.TE,
    )
    # TE wave with phi=0 should have E along y-axis
    assert abs(np.dot(pw.propagation_direction, pw.polarization_vector)) < 1e-6
    assert abs(pw.incidence_angle_deg - 45.0) < 1e-6
    assert np.allclose(pw.polarization_vector, [0.0, 1.0, 0.0], atol=1e-5)


def test_plane_wave_poynting_vector():
    pw = PlaneWave.normal_incidence(frequency_hz=2.0e9, electric_field_amplitude=1.0)
    s_vec = pw.poynting_vector
    # Direction along -z
    assert s_vec[2] < 0.0
    expected_s_mag = 1.0 / (2.0 * ETA_0)
    assert abs(np.linalg.norm(s_vec) - expected_s_mag) < 1e-6


def test_plane_wave_serialization():
    pw = PlaneWave.normal_incidence(frequency_hz=2.4e9)
    d = pw.to_dict()
    assert d["frequency_hz"] == 2.4e9
    assert d["frequency_ghz"] == 2.4
    assert len(d["propagation_direction"]) == 3
    assert len(d["polarization_vector"]) == 3
