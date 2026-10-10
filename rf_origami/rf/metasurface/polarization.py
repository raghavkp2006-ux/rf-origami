"""Metasurface Polarization Conversion and Jones Matrix Scattering Engine.

Calculates full co- and cross-polarization reflection matrices:
[E_r_x; E_r_y] = [R_xx, R_xy; R_yx, R_yy] * [E_i_x; E_i_y]
and polarization conversion ratio (PCR) for linear-to-linear and linear-to-circular converters.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.folding.engine import FoldingEngine


@dataclass
class PolarizationScatteringResult:
    """Container for full 2x2 polarization reflection scattering parameters."""
    frequencies_hz: List[float]
    r_xx: List[complex] # Co-pol X
    r_yy: List[complex] # Co-pol Y
    r_xy: List[complex] # Cross-pol X from Y
    r_yx: List[complex] # Cross-pol Y from X
    pcr_linear: List[float] # Polarization Conversion Ratio: |R_yx|^2 / (|R_xx|^2 + |R_yx|^2)
    axial_ratio_db: List[float] # Axial Ratio in dB for circular polarization conversion
    peak_pcr: float
    peak_pcr_freq_hz: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequencies_hz": self.frequencies_hz,
            "frequencies_ghz": [round(f / 1e9, 4) for f in self.frequencies_hz],
            "r_xx_mag": [round(abs(c), 4) for c in self.r_xx],
            "r_yy_mag": [round(abs(c), 4) for c in self.r_yy],
            "r_xy_mag": [round(abs(c), 4) for c in self.r_xy],
            "r_yx_mag": [round(abs(c), 4) for c in self.r_yx],
            "pcr_linear": [round(p, 4) for p in self.pcr_linear],
            "axial_ratio_db": [round(ar, 2) for ar in self.axial_ratio_db],
            "peak_pcr": round(self.peak_pcr, 4),
            "peak_pcr_freq_hz": self.peak_pcr_freq_hz,
            "peak_pcr_freq_ghz": round(self.peak_pcr_freq_hz / 1e9, 4),
            "metadata": self.metadata,
        }


class MetasurfacePolarizationEngine:
    """Evaluates anisotropic metasurface polarization manipulation and conversion."""

    @classmethod
    def evaluate_polarization_matrix(
        cls,
        pattern_type: str = "miura_ori",
        pattern_params: Optional[Dict[str, Any]] = None,
        fold_angle_deg: float = 30.0,
        f_start_ghz: float = 2.0,
        f_stop_ghz: float = 6.0,
        num_freq_points: int = 21,
        substrate_material: str = "kapton",
        conductor_material: str = "copper",
        ground_backed: bool = True,
        anisotropic_axis_deg: float = 45.0,
    ) -> PolarizationScatteringResult:
        """Calculate full 2x2 Jones reflection scattering matrix and PCR spectrum."""
        from rf_origami.rf.materials.material import MaterialLibrary
        from rf_origami.web.service import OrigamiWebService

        pattern = OrigamiWebService._build_pattern(pattern_type, pattern_params)
        mesh_3d = FoldingEngine.fold_analytical(pattern, fold_angle_deg=fold_angle_deg)
        surface_mesh = SurfaceMesh.from_folded_mesh(
            folded_mesh=mesh_3d,
            ground_backed=ground_backed,
            substrate_thickness_mm=0.5,
        )

        sub_mat = MaterialLibrary.get(substrate_material)
        cond_mat = MaterialLibrary.get(conductor_material)

        solver = SurfaceMoMSolver(
            mesh=surface_mesh,
            conductor_material=cond_mat,
            substrate_material=sub_mat,
            ground_backed=ground_backed,
        )

        freqs = np.linspace(f_start_ghz * 1e9, f_stop_ghz * 1e9, num_freq_points).tolist()

        res_x = solver.solve_spectrum(
            f_start_hz=f_start_ghz * 1e9,
            f_stop_hz=f_stop_ghz * 1e9,
            num_points=num_freq_points,
            polarization=PolarizationType.LINEAR_X,
            fold_angle_deg=fold_angle_deg,
        )

        res_y = solver.solve_spectrum(
            f_start_hz=f_start_ghz * 1e9,
            f_stop_hz=f_stop_ghz * 1e9,
            num_points=num_freq_points,
            polarization=PolarizationType.LINEAR_Y,
            fold_angle_deg=fold_angle_deg,
        )

        # In anisotropic origami coordinates tilted at angle alpha:
        alpha_rad = math.radians(anisotropic_axis_deg)
        cos_a = math.cos(alpha_rad)
        sin_a = math.sin(alpha_rad)

        r_xx_list: List[complex] = []
        r_yy_list: List[complex] = []
        r_xy_list: List[complex] = []
        r_yx_list: List[complex] = []
        pcr_list: List[float] = []
        ar_list: List[float] = []

        for i in range(num_freq_points):
            # Eigen-reflection components along principal symmetry axes
            r_u = res_x.s11[i]
            r_v = res_y.s11[i]

            # Coordinate transformation for 45-degree cross-polarizer
            r_xx = (r_u * (cos_a ** 2) + r_v * (sin_a ** 2))
            r_yy = (r_u * (sin_a ** 2) + r_v * (cos_a ** 2))
            r_yx = ((r_u - r_v) * sin_a * cos_a)
            r_xy = r_yx

            p_xx = abs(r_xx) ** 2
            p_yx = abs(r_yx) ** 2
            total_p = p_xx + p_yx
            pcr = (p_yx / total_p) if total_p > 1e-12 else 0.0

            # Axial ratio in dB = 20 * log10( (|R_xx| + |R_yx|) / abs(|R_xx| - |R_yx| + 1e-6) )
            mag_diff = abs(abs(r_xx) - abs(r_yx))
            ar = 20.0 * math.log10(max(1e-3, (abs(r_xx) + abs(r_yx)) / max(1e-6, mag_diff)))
            ar_clamped = min(40.0, max(0.0, ar))

            r_xx_list.append(r_xx)
            r_yy_list.append(r_yy)
            r_xy_list.append(r_xy)
            r_yx_list.append(r_yx)
            pcr_list.append(float(pcr))
            ar_list.append(float(ar_clamped))

        max_pcr = max(pcr_list) if pcr_list else 0.0
        max_pcr_idx = pcr_list.index(max_pcr) if pcr_list else 0
        peak_freq = freqs[max_pcr_idx]

        return PolarizationScatteringResult(
            frequencies_hz=freqs,
            r_xx=r_xx_list,
            r_yy=r_yy_list,
            r_xy=r_xy_list,
            r_yx=r_yx_list,
            pcr_linear=pcr_list,
            axial_ratio_db=ar_list,
            peak_pcr=max_pcr,
            peak_pcr_freq_hz=peak_freq,
            metadata={
                "pattern_type": pattern_type,
                "fold_angle_deg": fold_angle_deg,
                "anisotropic_axis_deg": anisotropic_axis_deg,
            },
        )
