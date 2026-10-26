"""Numerical regression and truthful validation-state tests."""
import math
import numpy as np
import pytest

from rf_origami.core.mesh import FoldedMesh
from rf_origami.rf.mesh.discretization import EMDiscretization
from rf_origami.rf.mesh.quality import validate_fold_mesh
from rf_origami.rf.metrics.antenna_metrics import extract_resonant_frequency, extract_impedance_bandwidth
from rf_origami.rf.metrics.result import RFSimulationResult
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.solver.quadrature import wire_potential
from rf_origami.rf.solver.rooftop_wire import _inner_moments
from rf_origami.rf.solver.validation_cases import compare_metrics, error_percent
from rf_origami.web.service import OrigamiWebService


def test_parabolic_interpolation_on_nonuniform_grid():
    f = np.array([2.0, 2.3, 2.6, 3.0]) * 1e9
    values = -25 + 40 * (f / 1e9 - 2.45)**2
    result = extract_resonant_frequency(f, values)
    assert result["resonant_frequency_hz"] == pytest.approx(2.45e9)
    assert result["min_s11_db"] == pytest.approx(-25)
    assert result["interpolated"] is True
    assert result["resolution_better_than_one_percent"] is False


def test_sweep_boundary_is_not_resolved_resonance():
    result = extract_resonant_frequency([1e9, 1.001e9, 1.002e9], [-20, -15, -10])
    assert result["at_sweep_boundary"] is True
    assert result["interpolated"] is False
    assert result["resolution_better_than_one_percent"] is False


def test_bandwidth_does_not_bridge_separate_bands():
    result = extract_impedance_bandwidth(np.arange(1, 8) * 1e9, [-5, -15, -5, -5, -25, -15, -5])
    assert result["f_low_ghz"] == pytest.approx(4.25)
    assert result["f_high_ghz"] == pytest.approx(6.5)
    assert result["bandwidth_mhz"] == pytest.approx(2250)
    assert result["truncated"] is False


def test_bandwidth_at_sweep_boundary_is_truncated():
    result = extract_impedance_bandwidth([1e9, 2e9, 3e9], [-25, -15, -5])
    assert result["truncated"] is True
    assert result["f_high_ghz"] == pytest.approx(2.5)


@pytest.mark.parametrize("f,s", [([2, 1], [-5, -6]), ([1, 1], [-5, -6]), ([1, 2], [-5]), ([1, 2], [-5, float('nan')])])
def test_metric_curve_rejects_invalid_input(f, s):
    with pytest.raises(ValueError):
        extract_resonant_frequency(f, s)
    with pytest.raises(ValueError):
        extract_impedance_bandwidth(f, s)


def test_wire_self_static_term_matches_analytic_integral():
    length, radius = 0.01, 1e-6
    value = wire_potential(np.zeros(3), np.zeros(3), length, np.array([0, 1, 0]), radius, 0)
    expected = 2 * math.asinh(length / (2 * radius)) / (4 * math.pi * length)
    assert value == pytest.approx(expected, rel=1e-13)


def test_wire_dynamic_integral_matches_independent_dense_quadrature():
    points, weights = np.polynomial.legendre.leggauss(300)
    length, radius, k = 0.01, 0.0005, 100
    r = np.sqrt((length / 2 * points - 0.001)**2 + radius**2)
    expected = np.dot(weights, np.exp(-1j * k * r) / r) / (8 * math.pi)
    actual = wire_potential(np.array([0, .001, 0]), np.zeros(3), length, np.array([0, 1, 0]), radius, k)
    assert actual == pytest.approx(expected, rel=1e-8)


def test_adjacent_non_collinear_segment_interaction_matches_dense_quadrature():
    """Verify that adjacent non-collinear wire interaction in rooftop_wire matches independent dense 2D Gauss quadrature."""
    L1, L2 = 1.4365e-3, 1.4365e-3
    h1, h2 = L1 / 2.0, L2 / 2.0
    a = 0.5e-3
    k = 2 * math.pi * 2.5e9 / 299792458.0

    pts_dense, wts_dense = np.polynomial.legendre.leggauss(100)

    for bend_deg in [90.0, 120.0]:
        ang = math.radians(bend_deg) / 2.0
        u1 = np.array([-math.sin(ang), 0.0, math.cos(ang)])
        c1 = -h1 * u1
        u2 = np.array([math.sin(ang), 0.0, math.cos(ang)])
        c2 = h2 * u2

        # 1. Rooftop solver formulation using semi-analytic _inner_moments + 8-pt outer quadrature
        _GO_X, _GO_W = np.polynomial.legendre.leggauss(8)
        pts_outer = c1[None, :] + h1 * _GO_X[:, None] * u1[None, :]
        w_outer = h1 * _GO_W

        M0, _ = _inner_moments(
            pts_outer[None, :, :],
            c2[None, :],
            u2[None, :],
            np.array([h2]),
            np.array([[a]]),
            k,
        )
        W_solver = np.sum(w_outer * M0[0, :, 0])

        # 2. Independent dense 2D Gauss-Legendre quadrature (100 x 100 points)
        s_vals = h1 * pts_dense
        t_vals = h2 * pts_dense
        r1 = c1[None, :] + s_vals[:, None] * u1[None, :]
        r2 = c2[None, :] + t_vals[:, None] * u2[None, :]

        diff = r1[:, None, :] - r2[None, :, :]
        dist2 = np.sum(diff**2, axis=-1)
        R = np.sqrt(dist2 + a**2)
        G_dense = np.exp(-1j * k * R) / (4 * math.pi * R)

        W_dense = (h1 * wts_dense) @ G_dense @ (h2 * wts_dense)

        rel_err = abs(W_solver - W_dense) / abs(W_dense)
        assert rel_err < 1e-6, f"Bend {bend_deg} deg relative error {rel_err} exceeds 1e-6"



def test_fold_geometry_gate_rejects_collapsed_and_stretched_panels():
    reference = FoldedMesh([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 1, 2]])
    assert validate_fold_mesh(reference, reference)["passed"] is True
    collapsed = FoldedMesh([[0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0, 1, 2]])
    stretched = FoldedMesh([[0, 0, 0], [2, 0, 0], [0, 1, 0]], [[0, 1, 2]])
    with pytest.raises(ValueError, match="collapsed"):
        validate_fold_mesh(collapsed)
    with pytest.raises(ValueError, match="edge lengths"):
        validate_fold_mesh(stretched, reference)


def test_percent_error_and_db_tolerance_are_distinct():
    assert error_percent(105, 100) == pytest.approx(5)
    assert error_percent(1, 0) is None
    result = compare_metrics({"fr_hz": 104, "s11_db": -17, "xin_ohms": 0.5},
                             {"fr_hz": 100, "s11_db": -20, "xin_ohms": 0})
    assert result["passed"] is True
    assert result["metrics"]["s11_db"]["absolute_error"] == 3
    assert compare_metrics({}, {"fr_hz": 100})["passed"] is False
    from rf_origami.experiments.comparison import ExperimentalComparator
    with pytest.raises(ValueError, match="overlapping"):
        ExperimentalComparator.compare([1e9, 2e9], [-10, -20], [3e9, 4e9], [-10, -20])
    compared = ExperimentalComparator.compare([1e9, 2e9, 3e9], [-10, -20, -10], [1e9, 2e9, 3e9], [-12, -22, -12])
    assert compared["s11_rmse_db"] == pytest.approx(2.0)


def test_result_deserialization_does_not_confuse_numerical_with_validated():
    result = RFSimulationResult.from_dict({"solver": {"is_numerical": True}})
    assert result.is_validated_numerical is False
    assert result.to_dict()["solver"]["is_numerical"] is True
    assert result.to_dict()["solver"]["is_validated"] is False


def test_saved_report_api_never_claims_physical_validation():
    data = OrigamiWebService.get_validation_report()
    assert data["validation_status"] == "Not validated"
    assert data["model_limitations"]
    assert data["markdown"]


def test_invalid_feed_and_empty_mesh_are_rejected():
    with pytest.raises(ValueError, match="at least one"):
        MoMSolver(EMDiscretization())
    mesh = EMDiscretization.from_wire_line([0, 0, 0], [0, 10, 0], 6)
    mesh.port_segment_index = -1
    with pytest.raises(ValueError, match="Feed segment"):
        MoMSolver(mesh)


@pytest.mark.parametrize("start,stop,count", [(1e9, 1e9, 10), (float('nan'), 2e9, 10), (1e9, 2e9, 1)])
def test_invalid_solver_sweep_is_rejected(start, stop, count):
    mesh = EMDiscretization.from_wire_line([0, 0, 0], [0, 10, 0], 6)
    with pytest.raises(ValueError):
        MoMSolver(mesh).solve_sweep(start, stop, count)
