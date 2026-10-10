"""Unit tests for energy conservation and benchmark physics."""

import pytest
from rf_origami.rf.absorber.validation_cases import AbsorberValidationSuite


def test_level1_pec_plate_benchmark():
    res = AbsorberValidationSuite.benchmark_level1_pec_plate()
    assert res["passed"], f"Level 1 failed: {res}"
    assert res["reflection"] > 0.90
    assert res["transmission"] < 0.01
    assert res["absorption"] < 0.10


def test_level2_dielectric_slab_benchmark():
    res = AbsorberValidationSuite.benchmark_level2_dielectric_slab()
    assert res["passed"], f"Level 2 failed: {res}"
    assert res["energy_error"] <= 0.02


def test_level3_grounded_dielectric_benchmark():
    res = AbsorberValidationSuite.benchmark_level3_grounded_dielectric()
    assert res["passed"], f"Level 3 failed: {res}"
    assert res["transmission"] < 1e-6
    assert res["energy_error"] <= 0.02


def test_level4_flat_resonant_absorber_benchmark():
    res = AbsorberValidationSuite.benchmark_level4_flat_resonant_absorber()
    assert res["passed"], f"Level 4 failed: {res}"
    assert res["peak_absorption"] > 0.80
    assert res["minimum_s11_db"] < -7.0


def test_level5_folded_miura_absorber_benchmark():
    res = AbsorberValidationSuite.benchmark_level5_folded_miura_absorber()
    assert res["passed"], f"Level 5 failed: {res}"
    assert res["tuning_ratio"] >= 1.05
