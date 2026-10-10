"""Unit tests for experimental data import, comparison, and digital twin calibration."""

import numpy as np
import pytest

from rf_origami.experiments.importer import MeasurementImporter
from rf_origami.experiments.comparison import ExperimentalComparator
from rf_origami.experiments.calibration import DigitalTwinCalibrator


def test_measurement_importer_csv():
    csv_text = """frequency_hz,reflection_db
1.0e9,-1.2
2.45e9,-22.5
5.0e9,-2.1
"""
    data = MeasurementImporter.import_csv(csv_text)
    assert data["num_points"] == 3
    assert data["frequencies_hz"][1] == 2.45e9
    assert data["s11_db"][1] == -22.5
    assert data["absorption"][1] > 0.95


def test_measurement_importer_touchstone():
    s1p_text = """# GHZ S DB R 50
! VNA Measurement
1.0  -2.0  0.0
2.45 -25.0 0.0
5.0  -3.0  0.0
"""
    data = MeasurementImporter.import_touchstone_s1p(s1p_text)
    assert data["num_points"] == 3
    assert data["frequencies_hz"][1] == 2.45e9
    assert data["s11_db"][1] == -25.0


def test_experimental_comparison():
    sim_f = [1e9, 2.45e9, 4e9]
    sim_s11 = [-2.0, -20.0, -2.0]
    meas_f = [1e9, 2.45e9, 4e9]
    meas_s11 = [-2.1, -19.5, -2.2]

    comp = ExperimentalComparator.compare(sim_f, sim_s11, meas_f, meas_s11)
    assert comp["frequency_error_percent"] == 0.0
    assert comp["s11_rmse_db"] < 1.0
    assert comp["agreement_grade"] in ("EXCELLENT", "GOOD")


def test_digital_twin_calibration():
    # Synthetic measurement with target resonance
    meas_f = np.linspace(2.0e9, 3.0e9, 5).tolist()
    meas_s11 = [-2.0, -8.0, -22.0, -7.0, -2.0]

    calib = DigitalTwinCalibrator.calibrate_material_and_geometry(
        pattern_params={"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        nominal_fold_angle_deg=30.0,
        meas_frequencies_hz=meas_f,
        meas_s11_db=meas_s11,
        nominal_eps_r=3.5,
    )

    assert "calibrated_eps_r" in calib
    assert "calibrated_fold_angle_deg" in calib
    assert calib["calibration_status"] == "CONVERGED"
