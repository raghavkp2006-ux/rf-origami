import pytest
from rf_origami.generator.design_space import DesignSpace, CandidateDesign
from rf_origami.generator.engine import GenerativeOrigamiEngine


def test_design_space_sampling():
    ds = DesignSpace(
        a_min=15.0, a_max=35.0,
        b_min=10.0, b_max=30.0,
        gamma_min=45.0, gamma_max=75.0,
        num_cells_x_min=2, num_cells_x_max=4,
        num_cells_y_min=2, num_cells_y_max=4,
    )
    samples = ds.sample(count=20, seed=42)
    assert len(samples) == 20

    for s in samples:
        assert 15.0 <= s["a"] <= 35.0
        assert 10.0 <= s["b"] <= 30.0
        assert 45.0 <= s["gamma"] <= 75.0
        assert 2 <= s["num_cells_x"] <= 4
        assert 2 <= s["num_cells_y"] <= 4

    # Test deterministic reproducibility
    samples2 = ds.sample(count=20, seed=42)
    assert samples == samples2

    # Different seed gives different results
    samples_diff = ds.sample(count=20, seed=99)
    assert samples != samples_diff


def test_generative_engine_exploration():
    ds = DesignSpace()
    res = GenerativeOrigamiEngine.explore(design_space=ds, count=15, seed=123)

    assert "summary" in res
    assert res["summary"]["total_generated"] == 15
    assert res["summary"]["seed"] == 123
    assert len(res["candidates"]) == 15
    assert len(res["design_space_scatter"]["points"]) == 15

    # Check candidate structure
    for cand in res["candidates"]:
        assert cand["id"].startswith("CAND-")
        assert "parameters" in cand
        assert "metrics" in cand
        assert "thumbnail_svg" in cand
        assert "<svg" in cand["thumbnail_svg"]

        if cand["is_valid"]:
            assert cand["metrics"]["surface_area_mm2"] > 0
            assert cand["metrics"]["num_faces"] >= 1
            assert cand["metrics"]["compactness_ratio"] > 0


def test_constraint_filter_rejection():
    # Force rejection by demanding impossibly high minimum panel area
    strict_ds = DesignSpace(min_panel_area=500000.0)
    res = GenerativeOrigamiEngine.explore(design_space=strict_ds, count=5, seed=42)

    assert res["summary"]["valid_count"] == 0
    assert res["summary"]["rejected_count"] == 5

    for cand in res["candidates"]:
        assert cand["is_valid"] is False
        assert any("panel area" in r.lower() for r in cand["rejection_reasons"])


def test_waterbomb_and_yoshimura_exploration():
    ds = DesignSpace()
    wb_res = GenerativeOrigamiEngine.explore(design_space=ds, count=5, seed=42, pattern_family="waterbomb")
    assert wb_res["summary"]["total_generated"] == 5

    yo_res = GenerativeOrigamiEngine.explore(design_space=ds, count=5, seed=42, pattern_family="yoshimura")
    assert yo_res["summary"]["total_generated"] == 5


def test_foldability_constraint_rejection():
    # Design space with impossible fold angle (e.g. 95 deg, exceeds 88 deg)
    fold_ds = DesignSpace(fold_angle_min=92.0, fold_angle_max=95.0)
    res = GenerativeOrigamiEngine.explore(design_space=fold_ds, count=3, seed=42)
    for cand in res["candidates"]:
        assert cand["is_valid"] is False
        assert any("fold angle" in r.lower() or "foldability" in r.lower() for r in cand["rejection_reasons"])
