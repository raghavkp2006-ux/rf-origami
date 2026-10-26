import pytest
from rf_origami.web.service import OrigamiWebService


def test_web_catalog():
    catalog = OrigamiWebService.get_pattern_catalog()
    assert "miura_ori" in catalog
    assert "degree4_vertex" in catalog
    assert "waterbomb" in catalog
    assert "yoshimura" in catalog

    miura = catalog["miura_ori"]
    assert miura["name"] == "Miura-Ori"
    param_names = [p["name"] for p in miura["parameters"]]
    assert "a" in param_names
    assert "b" in param_names
    assert "gamma" in param_names


def test_web_generate_miura():
    res = OrigamiWebService.generate_and_fold(
        pattern_type="miura_ori",
        params={"a": 25.0, "b": 18.0, "gamma": 65.0, "num_cells_x": 2, "num_cells_y": 2},
        fold_angle_deg=35.0,
    )

    assert res["pattern_type"] == "miura_ori"
    assert res["metrics"]["num_vertices"] == 25
    assert res["metrics"]["num_faces"] == 16
    assert len(res["folded_mesh_3d"]["vertices"]) == 25
    assert res["folded_mesh_3d"]["dimensions"][2] > 0.0  # Folded height > 0

    # Verification must be genuine
    assert res["validation"]["kawasaki"]["passed"] is True
    assert res["validation"]["maekawa"]["passed"] is True
    assert res["validation"]["edge_conservation"]["passed"] is True
    assert res["validation"]["area_conservation"]["passed"] is True


def test_web_generate_degree4():
    res = OrigamiWebService.generate_and_fold(
        pattern_type="degree4_vertex",
        params={"alpha1": 70.0, "alpha2": 110.0, "radius": 30.0},
        fold_angle_deg=25.0,
    )
    assert res["metrics"]["num_vertices"] == 5
    assert res["metrics"]["num_faces"] == 4
    assert res["validation"]["kawasaki"]["passed"] is True
    assert res["validation"]["maekawa"]["passed"] is True


def test_web_material_tagging():
    res = OrigamiWebService.generate_and_fold(
        pattern_type="miura_ori",
        params={"a": 20.0, "b": 20.0, "gamma": 60.0, "num_cells_x": 1, "num_cells_y": 1},
        fold_angle_deg=20.0,
        material_tags={"0": "conductor", "1": "ground"},
    )
    mat_areas = res["metrics"]["material_areas_mm2"]
    assert mat_areas["conductor"] > 0.0
    assert mat_areas["ground"] > 0.0


def test_web_design_space():
    ds_info = OrigamiWebService.get_default_design_space()
    assert "a_range" in ds_info
    assert "constraints" in ds_info
    assert "rf_constraints" in ds_info


def test_web_exploration():
    res = OrigamiWebService.run_exploration({
        "count": 10,
        "seed": 77,
        "pattern_family": "modulated_miura",
    })
    assert res["summary"]["total_generated"] == 10
    assert len(res["candidates"]) == 10
    assert len(res["design_space_scatter"]["points"]) == 10


def test_web_rf_materials():
    mats = OrigamiWebService.get_available_materials()
    assert len(mats) >= 5
    names = [m["name"].lower() for m in mats]
    assert any("copper" in n for n in names)
    assert any("kapton" in n for n in names)
    assert any("fr4" in n or "fr-4" in n for n in names)


def test_web_rf_benchmarks():
    benchmarks = OrigamiWebService.get_validation_benchmarks()
    assert "free_space" in benchmarks
    assert "half_wave_dipole" in benchmarks
    assert "quarter_wave_monopole" in benchmarks
    assert benchmarks["free_space"]["passed"] is True
    assert benchmarks["half_wave_dipole"]["validation_status"] == "Not validated"
    assert benchmarks["quarter_wave_monopole"]["independent_benchmark"] is False


def test_web_rf_simulate():
    res = OrigamiWebService.simulate_rf(
        pattern_type="miura_ori",
        params={"a": 30.0, "b": 20.0, "gamma": 65.0, "num_cells_x": 1, "num_cells_y": 1},
        fold_angle_deg=35.0,
        f_start_ghz=1.5,
        f_stop_ghz=4.5,
        num_points=7,
        substrate_material="kapton",
        conductor_material="copper",
    )
    assert res["simulation_type"] == "mom_solver"
    assert res["is_numerical"] is True
    assert res["commercial_software_used"] is False
    assert res["discretization"]["num_segments"] > 0
    assert len(res["frequency_sweep"]["frequencies_ghz"]) == 7
    assert len(res["frequency_sweep"]["s11_db"]) == 7
    assert "resonance" in res
    assert 1.5 <= res["resonance"]["resonant_frequency_ghz"] <= 4.5
