"""Absorber Mode Package for Reconfigurable Origami RF Metasurfaces.

Provides plane-wave excitation, surface Method of Moments (RWG) solver,
electromagnetic absorption metrics, automated kinematic fold sweeps,
near-field evaluation, and Level 1-5 validation benchmarks.
"""

from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.absorber.result import AbsorberResult
from rf_origami.rf.absorber.metrics import (
    calculate_reflection,
    calculate_transmission,
    calculate_absorption,
    check_energy_conservation,
    extract_resonance,
    calculate_absorption_bandwidth,
    s11_to_db,
    db_to_linear,
)
from rf_origami.rf.absorber.surface_solver import (
    SurfaceFacet,
    RWGBasis,
    SurfaceMesh,
    SurfaceMoMSolver,
)
from rf_origami.rf.absorber.fields import (
    evaluate_fields_on_grid,
    evaluate_surface_loss_density,
)
from rf_origami.rf.absorber.fold_sweep import (
    AbsorberFoldSweepResult,
    run_absorber_fold_sweep,
)
from rf_origami.rf.absorber.validation_cases import AbsorberValidationSuite

__all__ = [
    "PlaneWave",
    "PolarizationType",
    "AbsorberResult",
    "calculate_reflection",
    "calculate_transmission",
    "calculate_absorption",
    "check_energy_conservation",
    "extract_resonance",
    "calculate_absorption_bandwidth",
    "s11_to_db",
    "db_to_linear",
    "SurfaceFacet",
    "RWGBasis",
    "SurfaceMesh",
    "SurfaceMoMSolver",
    "evaluate_fields_on_grid",
    "evaluate_surface_loss_density",
    "AbsorberFoldSweepResult",
    "run_absorber_fold_sweep",
    "AbsorberValidationSuite",
]
