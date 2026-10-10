"""Unit tests for SurfaceMoMSolver and SurfaceMesh discretization."""

import numpy as np
import pytest

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import MaterialLibrary
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.absorber.surface_solver import SurfaceFacet, SurfaceMesh, RWGBasis, SurfaceMoMSolver
from rf_origami.rf.absorber.fields import evaluate_fields_on_grid, evaluate_surface_loss_density


def test_surface_mesh_generation():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=30.0)

    mesh = SurfaceMesh.from_folded_mesh(folded, ground_backed=True, target_resolution="medium")
    assert mesh.num_facets > 0
    assert mesh.num_basis > 0
    assert mesh.total_area_mm2 > 0.0


def test_surface_mom_single_frequency_solve():
    pattern = MiuraOriPattern.generate(a=25.0, b=25.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=20.0)
    mesh = SurfaceMesh.from_folded_mesh(folded, ground_backed=True)

    solver = SurfaceMoMSolver(
        mesh=mesh,
        conductor_material=MaterialLibrary.get("copper"),
        substrate_material=MaterialLibrary.get("kapton"),
        ground_backed=True,
    )

    pw = PlaneWave.normal_incidence(frequency_hz=2.45e9, polarization=PolarizationType.LINEAR_X)
    res = solver.solve_frequency(pw)

    assert "s11" in res
    assert "reflection" in res
    assert "absorption" in res
    assert 0.0 <= res["reflection"] <= 1.0
    assert 0.0 <= res["absorption"] <= 1.0
    assert res["energy_error"] <= 0.05
    assert "surface_currents" in res
    assert len(res["surface_currents"]["magnitudes"]) == mesh.num_facets


def test_surface_mom_spectrum_solve():
    pattern = MiuraOriPattern.generate(a=25.0, b=25.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=30.0)
    mesh = SurfaceMesh.from_folded_mesh(folded, ground_backed=True)

    solver = SurfaceMoMSolver(mesh=mesh)
    sim_res = solver.solve_spectrum(
        f_start_hz=1.0e9,
        f_stop_hz=5.0e9,
        num_points=11,
        fold_angle_deg=30.0,
    )

    assert len(sim_res.frequencies_hz) == 11
    assert len(sim_res.s11) == 11
    assert len(sim_res.absorption) == 11
    assert sim_res.resonant_frequency_hz > 0.0
    assert sim_res.peak_absorption > 0.0


def test_near_field_evaluation():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=15.0)
    mesh = SurfaceMesh.from_folded_mesh(folded)

    pw = PlaneWave.normal_incidence(frequency_hz=2.45e9)
    fields = evaluate_fields_on_grid(pw, mesh, grid_size_x=5, grid_size_y=5, grid_size_z=3)

    assert len(fields["points"]) == 5 * 5 * 3
    assert len(fields["e_magnitudes"]) == len(fields["points"])
    assert len(fields["electric_energy_density"]) == len(fields["points"])


def test_oblique_and_sheet_resistance_mom_solve():
    pattern = MiuraOriPattern.generate(a=25.0, b=25.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=30.0)
    mesh = SurfaceMesh.from_folded_mesh(folded, ground_backed=True)

    solver = SurfaceMoMSolver(mesh=mesh, sheet_resistance=50.0)
    sim_res = solver.solve_spectrum(
        f_start_hz=2.0e9,
        f_stop_hz=6.0e9,
        num_points=9,
        incidence_angle_deg=30.0,
        azimuth_angle_deg=45.0,
        polarization="te",
        fold_angle_deg=30.0,
    )

    assert len(sim_res.frequencies_hz) == 9
    assert sim_res.peak_absorption > 0.30
    assert sim_res.metadata["sheet_resistance"] == 50.0
    assert sim_res.metadata["incidence_angle_deg"] == 30.0
    assert sim_res.metadata["azimuth_angle_deg"] == 45.0


