"""RF Metasurface Subpackage.

Provides specialized engines for:
1. Reflection phase agility and beam steering (MetasurfacePhaseEngine).
2. Polarization conversion and Jones scattering matrices (MetasurfacePolarizationEngine).
3. 3D Bistatic and Monostatic Radar Cross Section (MetasurfaceFarFieldEngine).
4. Analytical Equivalent Circuit Models (MetasurfaceECMEngine).
"""

from rf_origami.rf.metasurface.phase import MetasurfacePhaseEngine, PhaseAgilityResult
from rf_origami.rf.metasurface.polarization import MetasurfacePolarizationEngine, PolarizationScatteringResult
from rf_origami.rf.metasurface.farfield import MetasurfaceFarFieldEngine, FarFieldRCSResult
from rf_origami.rf.metasurface.ecm import MetasurfaceECMEngine, EquivalentCircuitResult

__all__ = [
    "MetasurfacePhaseEngine",
    "PhaseAgilityResult",
    "MetasurfacePolarizationEngine",
    "PolarizationScatteringResult",
    "MetasurfaceFarFieldEngine",
    "FarFieldRCSResult",
    "MetasurfaceECMEngine",
    "EquivalentCircuitResult",
]
