"""Tests for far-field directivity, efficiency, gain and pattern against NEC2."""

import json
import os
import pytest

from scripts.farfield_validation import (
    solve_mom,
    compute_angular_separation,
    GATE_DIRECTIVITY_DB,
    GATE_EFFICIENCY_PCT,
    GATE_GAIN_DB,
    GATE_PEAK_DIR_DEG,
)

# Independent NEC2 reference far-field metrics at N=40 computed at each angle's zero-reactance f0
# (via scripts/farfield_validation.py using necpp/RP card integration):
NEC2_FARFIELD_REF = {
    0: {
        "directivity_dbi": 2.135574,
        "peak_theta_deg": 90.0,
        "peak_phi_deg": 0.0,
        "gain_dbi": 2.128032,
        "efficiency_pct": 99.8265,
    },
    30: {
        "directivity_dbi": 2.096055,
        "peak_theta_deg": 90.0,
        "peak_phi_deg": 61.0,
    },
    60: {
        "directivity_dbi": 1.957878,
        "peak_theta_deg": 90.0,
        "peak_phi_deg": 77.0,
    },
    90: {
        "directivity_dbi": 1.755108,
        "peak_theta_deg": 90.0,
        "peak_phi_deg": 83.0,
    },
    120: {
        "directivity_dbi": 1.519114,
        "peak_theta_deg": 90.0,
        "peak_phi_deg": 86.0,
    },
}


@pytest.fixture(scope="module")
def nec2_reference_cases():
    ref_path = os.path.join(os.path.dirname(__file__), "..", "data", "validation", "nec2_reference.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("bend_deg", [0, 30, 60, 90, 120])
def test_farfield_directivity_and_peak_direction_vs_nec2(nec2_reference_cases, bend_deg):
    """Validate far-field directivity and peak direction at N=40 against NEC2 across all 5 angles."""
    f0 = nec2_reference_cases[str(bend_deg)]["reactance_zero_hz"]
    nseg = 40

    mom = solve_mom(bend_deg, nseg, f0)
    ref = NEC2_FARFIELD_REF[bend_deg]

    err_d = abs(mom["directivity_dbi"] - ref["directivity_dbi"])
    err_peak = compute_angular_separation(
        mom["peak_theta_deg"], mom["peak_phi_deg"],
        ref["peak_theta_deg"], ref["peak_phi_deg"],
    )

    # Directivity within 0.5 dB and peak direction within 5.0 deg across all angles
    assert err_d <= GATE_DIRECTIVITY_DB
    assert err_peak <= GATE_PEAK_DIR_DEG


def test_farfield_efficiency_and_gain_vs_nec2_straight_dipole(nec2_reference_cases):
    """Validate far-field efficiency and gain against NEC2 at 0 degrees only.

    At 30, 60, 90, 120 degrees the NEC2 reference suffers internal power-balance loss
    at the sharp junction, so the reference is not reliable for efficiency.
    """
    f0 = nec2_reference_cases["0"]["reactance_zero_hz"]
    nseg = 40

    mom = solve_mom(0, nseg, f0)
    ref = NEC2_FARFIELD_REF[0]

    err_g = abs(mom["gain_dbi"] - ref["gain_dbi"])
    err_eff = abs(mom["efficiency_pct"] - ref["efficiency_pct"])

    assert err_g <= GATE_GAIN_DB
    assert err_eff <= GATE_EFFICIENCY_PCT


@pytest.mark.parametrize("bend_deg", [0, 30, 60, 90, 120])
def test_mom_energy_conservation_lossless(nec2_reference_cases, bend_deg):
    """Verify MoM energy conservation on lossless conductor (P_rad / P_in within 0.1% of 100%)."""
    f0 = nec2_reference_cases[str(bend_deg)]["reactance_zero_hz"]
    nseg = 40

    mom_lossless = solve_mom(bend_deg, nseg, f0, conductivity=1e14)
    eff_pct = (mom_lossless["p_rad"] / mom_lossless["p_in"]) * 100.0
    assert abs(eff_pct - 100.0) <= 0.1


@pytest.mark.parametrize("bend_deg", [0, 30, 60, 90, 120])
def test_mom_radiation_efficiency_copper(nec2_reference_cases, bend_deg):
    """Verify MoM copper radiation efficiency is between 99.4% and 99.9% across all angles."""
    f0 = nec2_reference_cases[str(bend_deg)]["reactance_zero_hz"]
    nseg = 40

    mom_copper = solve_mom(bend_deg, nseg, f0)
    eff_pct = mom_copper["efficiency_pct"]
    assert 99.4 <= eff_pct <= 99.9
