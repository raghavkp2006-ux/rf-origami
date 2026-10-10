"""Unit tests for electromagnetic absorption and scattering metrics."""

import math
import numpy as np
import pytest

from rf_origami.rf.absorber.metrics import (
    calculate_reflection,
    calculate_transmission,
    calculate_absorption,
    check_energy_conservation,
    extract_resonance,
    calculate_absorption_bandwidth,
    s11_to_db,
    db_to_linear,
)


def test_reflection_and_transmission_calculation():
    # S11 = 0.5 -> R = 0.25
    r = calculate_reflection(0.5)
    assert abs(r - 0.25) < 1e-6

    # Complex S11: 0.3 + 0.4j -> |S11|^2 = 0.09 + 0.16 = 0.25
    r_cplx = calculate_reflection(complex(0.3, 0.4))
    assert abs(r_cplx - 0.25) < 1e-6

    t = calculate_transmission(0.6)
    assert abs(t - 0.36) < 1e-6


def test_absorption_calculation():
    # R = 0.2, T = 0.1 -> A = 1 - 0.2 - 0.1 = 0.7
    a = calculate_absorption(0.2, 0.1)
    assert abs(a - 0.7) < 1e-6

    # Ground-backed (T = 0)
    a_gnd = calculate_absorption(0.15)
    assert abs(a_gnd - 0.85) < 1e-6


def test_energy_conservation_check():
    r = np.array([0.2, 0.5, 0.1])
    t = np.array([0.1, 0.2, 0.0])
    a = np.array([0.7, 0.3, 0.9])

    is_cons, max_err, errs = check_energy_conservation(r, t, a, tolerance=1e-4)
    assert is_cons
    assert max_err < 1e-6

    # Invalid energy violation test
    a_bad = np.array([0.8, 0.3, 0.9])
    is_cons_bad, max_err_bad, _ = check_energy_conservation(r, t, a_bad, tolerance=1e-4)
    assert not is_cons_bad
    assert max_err_bad > 0.05


def test_s11_db_conversion():
    # S11 = 1.0 -> 0 dB
    assert abs(s11_to_db(1.0) - 0.0) < 1e-6
    # S11 = 0.1 -> -20 dB
    assert abs(s11_to_db(0.1) - (-20.0)) < 1e-4

    lin = db_to_linear(-20.0)
    assert abs(lin - 0.1) < 1e-4


def test_resonance_extraction():
    freqs = [1e9, 2e9, 2.45e9, 3e9, 4e9]
    abs_vals = [0.1, 0.4, 0.98, 0.5, 0.2]
    f_res, peak_a, min_db = extract_resonance(freqs, abs_vals)

    assert f_res == 2.45e9
    assert peak_a == 0.98
    # 1 - 0.98 = 0.02 -> 10 * log10(0.02) ~= -16.98 dB
    assert min_db < -15.0


def test_absorption_bandwidth():
    freqs = np.linspace(1.0e9, 4.0e9, 301)
    # Gaussian absorption peak around 2.45 GHz with width
    f0 = 2.45e9
    sigma = 0.15e9
    abs_vals = 0.99 * np.exp(-0.5 * ((freqs - f0) / sigma) ** 2)

    bw_hz, fbw, f_low, f_high = calculate_absorption_bandwidth(freqs, abs_vals, threshold=0.90)
    assert bw_hz > 0.0
    assert f_low < f0 < f_high
    assert abs((f_low + f_high) / 2.0 - f0) < 0.05e9
