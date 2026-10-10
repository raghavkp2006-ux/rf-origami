"""Unit tests for optimization and inverse design modules."""

import numpy as np
import pytest

from rf_origami.optimization.objectives import AbsorberOptimizationTarget, compute_packed_volume_mm3, evaluate_absorber_objectives
from rf_origami.optimization.lhs import AbsorberLHSSampler, CandidateAbsorberDesign
from rf_origami.optimization.nsga2 import NSGA2Optimizer, fast_non_dominated_sort, assign_crowding_distance, dominates
from rf_origami.optimization.surrogate import GaussianProcessSurrogate
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine


def test_packed_volume_calculation():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=60.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=45.0)
    vol = compute_packed_volume_mm3(folded, substrate_thickness_mm=0.5)
    assert vol > 0.0


def test_latin_hypercube_sampling_and_screening():
    target = AbsorberOptimizationTarget(target_frequency_ghz=2.45)
    samples = AbsorberLHSSampler.sample_design_space(num_samples=10, seed=42, target=target)
    assert len(samples) == 10

    screened = AbsorberLHSSampler.run_screening_pipeline(
        candidates=samples,
        target=target,
        max_em_evaluations=3,
        freq_points=5,
    )
    assert len(screened) > 0
    assert screened[0].sim_result is not None
    assert screened[0].objectives is not None


def test_domination_and_pareto_sorting():
    c1 = CandidateAbsorberDesign("C1", {}, 20.0)
    c1.objectives = (0.1, 0.05, -150.0, 10.0)

    c2 = CandidateAbsorberDesign("C2", {}, 30.0)
    c2.objectives = (0.2, 0.10, -100.0, 15.0)  # Dominated by C1

    assert dominates(c1.objectives, c2.objectives)
    assert not dominates(c2.objectives, c1.objectives)

    fronts = fast_non_dominated_sort([c1, c2])
    assert len(fronts) == 2
    assert fronts[0][0].candidate_id == "C1"


def test_gaussian_process_surrogate():
    # Fit y = x^2
    X = np.array([[1.0], [2.0], [3.0], [4.0]])
    y = np.array([1.0, 4.0, 9.0, 16.0])

    gp = GaussianProcessSurrogate(length_scale=1.5, noise_variance=1e-5)
    gp.fit(X, y)

    X_test = np.array([[2.5]])
    mu, sigma = gp.predict(X_test)
    assert abs(mu[0] - 6.25) < 1.0
    assert sigma[0] >= 0.0
