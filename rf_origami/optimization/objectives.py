"""Multi-Objective Evaluation for Origami Metasurfaces and Absorbers.

Defines target objectives:
  f1: Frequency targeting error |f_res - f_target| [Hz]
  f2: Peak absorption maximization (min 1 - A_peak)
  f3: Bandwidth maximization (min -BW_90)
  f4: Packed folded volume minimization [mm^3]
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rf_origami.core.mesh import FoldedMesh
from rf_origami.rf.absorber.result import AbsorberResult


@dataclass
class AbsorberOptimizationTarget:
    """Design requirements and target performance specifications for inverse design."""
    target_frequency_ghz: float = 2.45
    min_absorption: float = 0.90
    min_bandwidth_mhz: float = 100.0
    max_packed_volume_cm3: float = 50.0
    allowed_fold_range_deg: Tuple[float, float] = (0.0, 60.0)
    substrate_material: str = "kapton"
    conductor_material: str = "copper"


def compute_packed_volume_mm3(folded_mesh: FoldedMesh, substrate_thickness_mm: float = 0.5) -> float:
    """Calculate 3D bounding box packed volume of the folded structure in mm^3."""
    v = folded_mesh.vertices
    if len(v) == 0:
        return 0.0
    min_xyz = np.min(v, axis=0)
    max_xyz = np.max(v, axis=0)
    dx = max(1.0, max_xyz[0] - min_xyz[0])
    dy = max(1.0, max_xyz[1] - min_xyz[1])
    dz = max(substrate_thickness_mm, max_xyz[2] - min_xyz[2] + substrate_thickness_mm)
    return float(dx * dy * dz)


def evaluate_absorber_objectives(
    sim_result: AbsorberResult,
    folded_mesh: FoldedMesh,
    target: AbsorberOptimizationTarget,
    substrate_thickness_mm: float = 0.5,
) -> Tuple[float, float, float, float]:
    """Compute 4-objective evaluation vector F(x) = [freq_err, 1 - A_peak, -BW_mhz, vol_cm3].

    All objectives are formulated for MINIMIZATION.
    """
    f_res_ghz = sim_result.resonant_frequency_hz / 1e9
    f_err = abs(f_res_ghz - target.target_frequency_ghz)

    # 1.0 - peak absorption (0 is ideal 100% absorption)
    abs_obj = max(0.0, 1.0 - sim_result.peak_absorption)

    # Negative bandwidth in MHz for maximization
    bw_mhz = sim_result.absorption_bandwidth_hz / 1e6
    bw_obj = -bw_mhz

    # Packed volume in cm^3 (mm^3 / 1000)
    vol_mm3 = compute_packed_volume_mm3(folded_mesh, substrate_thickness_mm)
    vol_cm3 = vol_mm3 / 1000.0

    return float(f_err), float(abs_obj), float(bw_obj), float(vol_cm3)
