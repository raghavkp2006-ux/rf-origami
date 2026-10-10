"""RF and Electromagnetic Analysis Engine for RF Origami.

Provides standalone, self-contained materials, geometry conversion,
lumped feed ports, Method of Moments (MoM) numerical EM solving,
S-parameter analysis, and antenna performance metrics.
"""

from rf_origami.rf.materials.material import (
    Material,
    MaterialLibrary,
    EPSILON_0,
    MU_0,
    C_0,
    ETA_0,
)
from rf_origami.rf.geometry.rf_object import (
    RFObjectType,
    RFObject,
    ConductorSurface,
    SubstrateSurface,
    GroundPlane,
    RFGeometryModel,
)
from rf_origami.rf.geometry.converter import RFGeometryConverter
from rf_origami.rf.ports.lumped_port import LumpedPort
from rf_origami.rf.mesh.discretization import EMSegment, EMDiscretization
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.solver.validation_cases import SolverValidationBenchmarks
from rf_origami.rf.solver.fold_sweep import FoldAngleSweepRunner
from rf_origami.rf.sparameters.network import (
    reflection_coefficient,
    s11_db,
    vswr,
    return_loss_db,
    SParameterVector,
)
from rf_origami.rf.metrics.antenna_metrics import (
    extract_resonant_frequency,
    extract_impedance_bandwidth,
)
from rf_origami.rf.metrics.result import RFSimulationResult

__all__ = [
    # Materials
    "Material",
    "MaterialLibrary",
    "EPSILON_0",
    "MU_0",
    "C_0",
    "ETA_0",
    # Geometry
    "RFObjectType",
    "RFObject",
    "ConductorSurface",
    "SubstrateSurface",
    "GroundPlane",
    "RFGeometryModel",
    "RFGeometryConverter",
    # Ports
    "LumpedPort",
    # Discretization
    "EMSegment",
    "EMDiscretization",
    # Solvers
    "MoMSolver",
    "SolverValidationBenchmarks",
    "FoldAngleSweepRunner",
    # S-Parameters
    "reflection_coefficient",
    "s11_db",
    "vswr",
    "return_loss_db",
    "SParameterVector",
    # Metrics
    "extract_resonant_frequency",
    "extract_impedance_bandwidth",
    "RFSimulationResult",
]
