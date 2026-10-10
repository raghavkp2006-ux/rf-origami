"""Far-Field Radar Cross Section (RCS) and Radiation Pattern Engine.

Calculates 3D Bistatic and Monostatic Radar Cross Section (RCS) sigma(theta, phi) in m^2 and dBsm:
sigma(theta, phi) = lim_{r -> inf} 4*pi*r^2 * |E_scat|^2 / |E_inc|^2
and computes RCS reduction comparing folded origami absorbers against reference flat PEC plates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.materials.material import C_0, ETA_0
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.folding.engine import FoldingEngine


@dataclass
class FarFieldRCSResult:
    """Container for 3D Far-Field Radar Cross Section patterns."""
    frequency_hz: float
    theta_angles_deg: List[float]
    phi_angles_deg: List[float]
    rcs_bistatic_m2: List[List[float]]      # [theta x phi]
    rcs_bistatic_dbsm: List[List[float]]    # [theta x phi]
    monostatic_rcs_m2: float
    monostatic_rcs_dbsm: float
    reference_pec_rcs_m2: float
    reference_pec_rcs_dbsm: float
    rcs_reduction_db: float                 # PEC dBsm - Origami dBsm
    peak_rcs_dbsm: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequency_hz": self.frequency_hz,
            "frequency_ghz": round(self.frequency_hz / 1e9, 4),
            "theta_angles_deg": self.theta_angles_deg,
            "phi_angles_deg": self.phi_angles_deg,
            "rcs_bistatic_dbsm": self.rcs_bistatic_dbsm,
            "monostatic_rcs_dbsm": round(self.monostatic_rcs_dbsm, 2),
            "reference_pec_rcs_dbsm": round(self.reference_pec_rcs_dbsm, 2),
            "rcs_reduction_db": round(self.rcs_reduction_db, 2),
            "peak_rcs_dbsm": round(self.peak_rcs_dbsm, 2),
            "metadata": self.metadata,
        }


class MetasurfaceFarFieldEngine:
    """Computes scattered far-fields and Radar Cross Section patterns via radiation integrals."""

    @classmethod
    def calculate_bistatic_rcs(
        cls,
        pattern_type: str = "miura_ori",
        pattern_params: Optional[Dict[str, Any]] = None,
        fold_angle_deg: float = 30.0,
        frequency_hz: float = 2.45e9,
        num_theta: int = 37, # 0 to 180 deg in 5 deg steps
        num_phi: int = 19,   # 0 to 360 deg in 20 deg steps
        substrate_material: str = "kapton",
        conductor_material: str = "copper",
        ground_backed: bool = True,
    ) -> FarFieldRCSResult:
        """Calculate 3D Bistatic RCS and compare against equivalent flat PEC aperture."""
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

        pw = PlaneWave.normal_incidence(frequency_hz=frequency_hz)
        solve_res = solver.solve_frequency(pw)

        # Flat reference plate physical optics maximum monostatic RCS: sigma_PEC = 4*pi*A^2 / lambda^2
        lambda_0 = C_0 / frequency_hz
        k0 = 2.0 * math.pi / lambda_0
        area_m2 = surface_mesh.total_area_mm2 * 1e-6
        sigma_pec_m2 = (4.0 * math.pi * (area_m2 ** 2)) / (lambda_0 ** 2) if lambda_0 > 0 else 1.0
        sigma_pec_dbsm = 10.0 * math.log10(max(1e-12, sigma_pec_m2))

        # Origami reflection power reduces scattered field amplitude
        r_pwr = float(solve_res["reflection"]) # |S11|^2
        r_amp = math.sqrt(max(0.0, r_pwr))

        thetas = np.linspace(0.0, 180.0, num_theta).tolist()
        phis = np.linspace(0.0, 360.0, num_phi).tolist()

        rcs_matrix_m2: List[List[float]] = []
        rcs_matrix_dbsm: List[List[float]] = []

        # Far-field integration across surface facets
        centroids_m = np.array([f.centroid * 1e-3 for f in surface_mesh.facets], dtype=np.float64)
        facet_areas_m = np.array([f.area_mm2 * 1e-6 for f in surface_mesh.facets], dtype=np.float64)

        for th in thetas:
            th_rad = math.radians(th)
            row_m2: List[float] = []
            row_dbsm: List[float] = []

            for ph in phis:
                ph_rad = math.radians(ph)

                # Observation unit vector r_hat
                rx = math.sin(th_rad) * math.cos(ph_rad)
                ry = math.sin(th_rad) * math.sin(ph_rad)
                rz = math.cos(th_rad)
                r_hat = np.array([rx, ry, rz], dtype=np.float64)

                # Array factor radiation sum: int J_s(r') * exp(j * k0 * r_hat . r') dS
                phase_delays = k0 * np.dot(centroids_m, r_hat)
                array_factor = float(np.abs(np.sum(facet_areas_m * np.exp(1j * phase_delays))))

                # Obliquity factor (cosine radiation from aperture)
                obliquity = max(0.05, math.cos(th_rad)) if th <= 90.0 else 0.05

                sigma_val_m2 = (4.0 * math.pi / (lambda_0 ** 2)) * ((r_amp * array_factor * obliquity) ** 2)
                sigma_val_dbsm = 10.0 * math.log10(max(1e-12, sigma_val_m2))

                row_m2.append(float(sigma_val_m2))
                row_dbsm.append(round(float(sigma_val_dbsm), 2))

            rcs_matrix_m2.append(row_m2)
            rcs_matrix_dbsm.append(row_dbsm)

        # Monostatic RCS (normal incidence / normal backscatter at theta = 0)
        mono_rcs_m2 = rcs_matrix_m2[0][0]
        mono_rcs_dbsm = rcs_matrix_dbsm[0][0]
        rcs_reduction_db = sigma_pec_dbsm - mono_rcs_dbsm

        peak_dbsm = max(max(row) for row in rcs_matrix_dbsm)

        return FarFieldRCSResult(
            frequency_hz=frequency_hz,
            theta_angles_deg=thetas,
            phi_angles_deg=phis,
            rcs_bistatic_m2=rcs_matrix_m2,
            rcs_bistatic_dbsm=rcs_matrix_dbsm,
            monostatic_rcs_m2=mono_rcs_m2,
            monostatic_rcs_dbsm=mono_rcs_dbsm,
            reference_pec_rcs_m2=sigma_pec_m2,
            reference_pec_rcs_dbsm=sigma_pec_dbsm,
            rcs_reduction_db=rcs_reduction_db,
            peak_rcs_dbsm=peak_dbsm,
            metadata={
                "pattern_type": pattern_type,
                "fold_angle_deg": fold_angle_deg,
                "aperture_area_mm2": surface_mesh.total_area_mm2,
                "reflection_power": r_pwr,
            },
        )
