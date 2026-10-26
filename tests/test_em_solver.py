import pytest
import numpy as np

from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.solver.validation_cases import SolverValidationBenchmarks
from rf_origami.rf.mesh.discretization import EMDiscretization, EMSegment
from rf_origami.rf.ports.lumped_port import LumpedPort


def test_free_space_validation_benchmark():
    res = SolverValidationBenchmarks.validate_free_space_propagation()
    assert res["passed"] is True
    assert res["speed_of_light_m_s"] == pytest.approx(299792458.0, rel=1e-3)
    assert res["wave_impedance_ohms"] == pytest.approx(376.73, rel=1e-3)


def test_half_wave_dipole_benchmark():
    # Canonical resonant dipole at 2.4 GHz (even segment count)
    res = SolverValidationBenchmarks.run_half_wave_dipole_benchmark(
        frequency_ghz=2.4,
        num_segments=20,
    )
    # 73.13 ohm is a screening target for an idealized infinitely thin wire, not a matched pass/fail gate
    assert res["validation_status"] == "Not validated"
    rin = res["numerical_zin_ohms"][0]
    xin = res["numerical_zin_ohms"][1]

    # Theoretical radiation resistance of half-wave dipole is ~65-75 Ohms
    assert 55.0 <= rin <= 90.0
    # Reactance near resonance is small
    assert abs(xin) < 45.0
    # S11 is reasonably matched to 50 Ohms
    assert res["numerical_s11_db"] < -5.0


def test_quarter_wave_monopole_benchmark():
    # Canonical quarter-wave monopole at 2.4 GHz (even segment count)
    res = SolverValidationBenchmarks.run_quarter_wave_monopole_benchmark(
        frequency_ghz=2.4,
        num_segments=20,
    )
    assert res["independent_benchmark"] is False
    rin = res["numerical_zin_ohms"][0]
    # By image theory, Rin,monopole ≈ 0.5 * Rin,dipole ≈ 34-38 Ohms
    assert 25.0 <= rin <= 50.0


def test_mom_solver_frequency_sweep():
    # Straight wire of 60 mm (dipole) with even segment count
    discr = EMDiscretization.from_wire_line(
        start_pt=[0, -30, 0],
        end_pt=[0, 30, 0],
        num_segments=16,
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


def test_reciprocity_random_bent_unequal_polyline():
    # Irregularly bent polyline with unequal segments and varying radii
    nodes = np.array([
        [0.0, 0.0, 0.0],
        [1.5, 4.2, -0.8],
        [3.0, 7.8, 1.5],
        [0.5, 11.0, 3.2],
        [4.5, 13.5, 0.0],
        [6.0, 16.0, -2.5],
    ])
    radii = [0.2, 0.35, 0.25, 0.4, 0.3]
    segments = []
    for i in range(len(nodes) - 1):
        segments.append(EMSegment(
            index=i,
            p1=nodes[i],
            p2=nodes[i + 1],
            radius_mm=radii[i],
            conductivity=5.8e7,
        ))
    discr = EMDiscretization(segments=segments, port_segment_index=2)
    solver = MoMSolver(discretization=discr)
    omega = 2.0 * np.pi * 2.4e9
    k = omega / 299792458.0
    eta = 376.730313668
    solver._assemble_impedance_matrix(k=k, eta=eta, omega=omega, freq=2.4e9)
    assert solver.last_asymmetry is not None
    assert solver.last_asymmetry <= 1e-4


def test_mesh_convergence_dipole():
    # Mesh convergence on dipole between 30 and 40 segments must be < 1%
    length_mm = 57.46
    d30 = MoMSolver(EMDiscretization.from_wire_line([0, -length_mm / 2, 0], [0, length_mm / 2, 0], 30))
    d40 = MoMSolver(EMDiscretization.from_wire_line([0, -length_mm / 2, 0], [0, length_mm / 2, 0], 40))
    sweep30 = d30.solve_sweep(1.8e9, 3.0e9, 61)
    sweep40 = d40.solve_sweep(1.8e9, 3.0e9, 61)
    f0_30 = sweep30["resonance"]["zero_reactance_f0_ghz"]
    f0_40 = sweep40["resonance"]["zero_reactance_f0_ghz"]
    assert f0_30 is not None and f0_40 is not None
    pct_change = abs(f0_30 - f0_40) / abs(f0_40) * 100.0
    assert pct_change < 1.0


def test_invalid_feed_index_raises():
    mesh = EMDiscretization.from_wire_line([0, -25, 0], [0, 25, 0], 10)
    # For N=10 segments, valid feed indices are 1 <= p <= 9
    for invalid_p in [0, 10, -1, 15]:
        mesh.port_segment_index = invalid_p
        with pytest.raises(ValueError, match="Feed.*index"):
            MoMSolver(mesh)

    valid_mesh = EMDiscretization.from_wire_line([0, -25, 0], [0, 25, 0], 10)
    solver = MoMSolver(valid_mesh)
    for invalid_p in [0, 10, -1, 15]:
        solver.discretization.port_segment_index = invalid_p
        with pytest.raises(ValueError, match="Feed.*index"):
            solver.solve_frequency(2.4e9)


def test_non_consecutive_segments_raise():
    # Discontinuous segments: segment 0 ends at (0, 5, 0), segment 1 starts at (0, 5.01, 0)
    segs = [
        EMSegment(0, np.array([0, 0, 0]), np.array([0, 5, 0]), 0.5),
        EMSegment(1, np.array([0, 5.01, 0]), np.array([0, 10, 0]), 0.5),
    ]
    discr = EMDiscretization(segments=segs, port_segment_index=1)
    with pytest.raises(ValueError, match="open consecutive polyline"):
        MoMSolver(discretization=discr)


def test_nec2_reference_file_missing_raises(tmp_path):
    missing_path = tmp_path / "nonexistent_nec2_reference.json"
    with pytest.raises(FileNotFoundError, match="NEC2 reference.*not found"):
        SolverValidationBenchmarks.compare_nec2_reference(reference_path=missing_path)


def test_nec2_reference_file_exists_and_valid():
    from pathlib import Path
    import json
    ref_path = Path(__file__).resolve().parents[1] / "data" / "validation" / "nec2_reference.json"
    assert ref_path.is_file(), f"NEC2 reference file missing at {ref_path}"
    data = json.loads(ref_path.read_text(encoding="utf-8"))
    assert "cases" in data
    assert set(data["cases"].keys()) == {"0", "30", "60", "90", "120"}
    assert len(data["freqs_hz"]) == 61
    assert data["freqs_hz"][0] == 1.8e9
    assert data["freqs_hz"][-1] == 3.0e9


@pytest.fixture(scope="module")
def nec2_benchmark_data():
    return SolverValidationBenchmarks.compare_nec2_reference(
        segment_counts=(40, 80),
        fr_gate_percent=5.0,
        rin_gate_percent=5.0,
    )


def test_nec2_independent_reference_straight_dipole_benchmark(nec2_benchmark_data):
    # Test N=40 and N=80 on 0 deg bend (straight dipole)
    res = nec2_benchmark_data
    case0 = res["cases"]["0"]
    assert case0["passed"] is True
    assert res["straight_dipole_benchmark"]["passed"] is True

    # N=40 checks: fr err < 5%, Rin err < 5%
    s40 = case0["by_segments"]["40"]
    assert s40["fr_error_percent"] < 5.0
    assert s40["rin_error_percent"] < 5.0
    assert s40["fr_error_percent"] == pytest.approx(0.91, abs=0.1)
    assert s40["rin_error_percent"] == pytest.approx(0.10, abs=0.1)
    assert s40["reactance_error_ohms"] == pytest.approx(5.34, abs=0.2)

    # N=80 checks: fr err < 5%, Rin err < 5%
    s80 = case0["by_segments"]["80"]
    assert s80["fr_error_percent"] < 5.0
    assert s80["rin_error_percent"] < 5.0
    assert s80["fr_error_percent"] == pytest.approx(1.01, abs=0.1)
    assert s80["rin_error_percent"] == pytest.approx(2.12, abs=0.1)
    assert s80["reactance_error_ohms"] == pytest.approx(5.73, abs=0.2)


@pytest.mark.parametrize("bend_str", [
    "0",
    "30",
    "60",
    pytest.param("90", marks=pytest.mark.xfail(strict=True, reason="Rin gate not met; see docs/STATUS.md")),
    pytest.param("120", marks=pytest.mark.xfail(strict=True, reason="Rin gate not met; see docs/STATUS.md")),
])
def test_nec2_v_dipole_fold_sweep_strict_gates(nec2_benchmark_data, bend_str):
    # Verify strict gates without relaxing tolerances:
    # 0, 30, 60 pass < 5%; 90 and 120 xfail because Rin gate is not met
    case = nec2_benchmark_data["cases"][bend_str]
    for n_str in ["40", "80"]:
        assert case["by_segments"][n_str]["passed_fr"] is True
        assert case["by_segments"][n_str]["passed_rin"] is True
    assert case["passed"] is True
