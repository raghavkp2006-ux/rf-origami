import pytest
import numpy as np

from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.solver.validation_cases import SolverValidationBenchmarks
from rf_origami.rf.mesh.discretization import EMDiscretization
from rf_origami.rf.ports.lumped_port import LumpedPort


def test_free_space_validation_benchmark():
    res = SolverValidationBenchmarks.validate_free_space_propagation()
    assert res["passed"] is True
    assert res["speed_of_light_m_s"] == pytest.approx(299792458.0, rel=1e-3)
    assert res["wave_impedance_ohms"] == pytest.approx(376.73, rel=1e-3)


def test_half_wave_dipole_benchmark():
    # Canonical resonant dipole at 2.4 GHz
    res = SolverValidationBenchmarks.run_half_wave_dipole_benchmark(
        frequency_ghz=2.4,
        num_segments=21,
    )
    assert res["passed"] is True
    rin = res["numerical_zin_ohms"][0]
    xin = res["numerical_zin_ohms"][1]

    # Theoretical radiation resistance of half-wave dipole is ~73 Ohms
    assert 55.0 <= rin <= 90.0
    # Reactance near resonance is small
    assert abs(xin) < 45.0
    # S11 is reasonably matched to 50 or 75 Ohms
    assert res["numerical_s11_db"] < -5.0


def test_quarter_wave_monopole_benchmark():
    # Canonical quarter-wave monopole at 2.4 GHz
    res = SolverValidationBenchmarks.run_quarter_wave_monopole_benchmark(
        frequency_ghz=2.4,
        num_segments=15,
    )
    assert res["passed"] is True
    rin = res["numerical_zin_ohms"][0]
    # By image theory, Rin,monopole ≈ 0.5 * Rin,dipole ≈ 36.5 Ohms
    assert 25.0 <= rin <= 50.0


def test_mom_solver_frequency_sweep():
    # Straight wire of 60 mm (dipole)
    discr = EMDiscretization.from_wire_line(
        start_pt=[0, -30, 0],
        end_pt=[0, 30, 0],
        num_segments=15,
        radius_mm=0.5,
    )
    solver = MoMSolver(discretization=discr)

    sweep = solver.solve_sweep(
        f_start_hz=1.0e9,
        f_stop_hz=5.0e9,
        num_points=21,
    )

    assert len(sweep["frequencies_ghz"]) == 21
    assert len(sweep["s11_db"]) == 21
    assert len(sweep["zin_real_ohms"]) == 21
    assert len(sweep["vswr"]) == 21

    # Check that resonance is identified
    res = sweep["resonance"]
    assert 1.0 <= res["resonant_frequency_ghz"] <= 5.0
    assert res["min_s11_db"] < 0.0
