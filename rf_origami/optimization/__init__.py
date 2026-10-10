"""Optimization and Inverse Design Package for RF Origami Metasurfaces."""

from rf_origami.optimization.objectives import (
    AbsorberOptimizationTarget,
    compute_packed_volume_mm3,
    evaluate_absorber_objectives,
)
from rf_origami.optimization.lhs import (
    CandidateAbsorberDesign,
    AbsorberLHSSampler,
)
from rf_origami.optimization.nsga2 import (
    NSGA2Optimizer,
    fast_non_dominated_sort,
    assign_crowding_distance,
)
from rf_origami.optimization.surrogate import GaussianProcessSurrogate

__all__ = [
    "AbsorberOptimizationTarget",
    "compute_packed_volume_mm3",
    "evaluate_absorber_objectives",
    "CandidateAbsorberDesign",
    "AbsorberLHSSampler",
    "NSGA2Optimizer",
    "fast_non_dominated_sort",
    "assign_crowding_distance",
    "GaussianProcessSurrogate",
]
