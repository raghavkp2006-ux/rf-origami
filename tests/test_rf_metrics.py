import pytest
import numpy as np

from rf_origami.rf.sparameters.network import (
    reflection_coefficient,
    s11_db,
    vswr,
    return_loss_db,
    SParameterVector,
)
from rf_origami.rf.metrics.antenna_metrics import (
    extract_resonant_frequency,
    extract_impedance_bandwidth,
)
from rf_origami.rf.metrics.result import RFSimulationResult
from rf_origami.rf.solver.fold_sweep import FoldAngleSweepRunner


def test_sparameter_calculations():
    # Perfect match: Zin = 50 Ohms -> Gamma = 0, S11 = -inf (clamped to -100), VSWR = 1.0
    gamma = reflection_coefficient(50.0 + 0j, z0=50.0)
    assert abs(gamma) == pytest.approx(0.0)
    assert s11_db(50.0 + 0j, z0=50.0) == -100.0
    assert vswr(50.0 + 0j, z0=50.0) == 1.0

    # 2:1 mismatch: Zin = 100 Ohms -> Gamma = (100-50)/(100+50) = 1/3
    # S11 = 20 * log10(1/3) ≈ -9.54 dB, VSWR = (1 + 1/3) / (1 - 1/3) = 2.0
    gamma_2 = reflection_coefficient(100.0 + 0j, z0=50.0)
    assert abs(gamma_2) == pytest.approx(1.0 / 3.0)
    assert s11_db(100.0 + 0j, z0=50.0) == pytest.approx(-9.542, abs=0.01)
    assert vswr(100.0 + 0j, z0=50.0) == pytest.approx(2.0, abs=0.01)

    # Total reflection: Open circuit Zin = 1e6 -> Gamma ≈ 1, S11 ≈ 0 dB
    assert s11_db(1e6 + 0j, z0=50.0) == pytest.approx(0.0, abs=0.1)


def test_resonance_and_bandwidth_extraction():
    freqs = np.linspace(2.0e9, 3.0e9, 101)
    # Synthetic dip at 2.45 GHz
    f0_target = 2.45e9
    s11_vals = -5.0 - 20.0 * np.exp(-((freqs - f0_target) / 50e6)**2)

    res_info = extract_resonant_frequency(freqs, s11_vals)
    assert res_info["resonant_frequency_ghz"] == pytest.approx(2.45, abs=0.02)
    assert res_info["min_s11_db"] < -20.0

    bw_info = extract_impedance_bandwidth(freqs, s11_vals, threshold_db=-10.0)
    assert bw_info["has_bandwidth"] is True
    assert bw_info["bandwidth_mhz"] > 0.0


def test_simulation_result_serialization():
    res = RFSimulationResult(
        candidate_id="CAND-042",
        geometry_id="GEOM-01",
        fold_angle_deg=45.0,
        frequencies_ghz=[2.4, 2.5, 2.6],
        s11_db=[-12.0, -22.5, -9.0],
        zin_real_ohms=[48.0, 50.2, 55.0],
        zin_imag_ohms=[-5.0, 0.1, 8.0],
        vswr=[1.6, 1.15, 2.1],
        resonant_frequency_ghz=2.5,
        min_s11_db=-22.5,
        bandwidth_mhz=120.0,
        bandwidth_percent=4.8,
    )
    d = res.to_dict()
    assert d["candidate_id"] == "CAND-042"
    assert d["fold_angle_deg"] == 45.0
    assert d["metrics"]["resonant_frequency_ghz"] == 2.5

    json_str = res.to_json()
    assert "CAND-042" in json_str

    res_back = RFSimulationResult.from_dict(d)
    assert res_back.candidate_id == res.candidate_id
    assert res_back.min_s11_db == res.min_s11_db


def test_fold_angle_sweep_runner():
    # Sweep across 3 angles for fast test
    sweep_res = FoldAngleSweepRunner.run_sweep(
        candidate_id="CAND-TEST",
        pattern_type="miura_ori",
        params={"a": 25.0, "b": 20.0, "gamma": 60.0, "num_cells_x": 1, "num_cells_y": 1},
        angles_deg=[15.0, 45.0, 75.0],
        f_start_hz=2.0e9,
        f_stop_hz=4.0e9,
        num_points=11,
    )

    assert sweep_res["candidate_id"] == "CAND-TEST"
    assert len(sweep_res["angles_evaluated"]) == 3
    assert len(sweep_res["comparison_table"]) == 3
    for entry in sweep_res["comparison_table"]:
        assert "fold_angle_deg" in entry
        assert "resonant_frequency_ghz" in entry
        assert "min_s11_db" in entry
