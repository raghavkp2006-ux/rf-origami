"""Reconfigurable Metasurface Reflection Phase and Beam Steering Engine.

Calculates reflection phase Phi(f, theta) = arg(S11), dynamic phase agility Delta Phi,
and anomalous reflection angles via generalized Snell's law:
sin(theta_r) - sin(theta_i) = (lambda_0 / (2*pi)) * (dPhi / dx).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.materials.material import C_0
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.folding.engine import FoldingEngine
from rf_origami.patterns.miura_ori import MiuraOriPattern


@dataclass
class PhaseAgilityResult:
    """Container for metasurface reflection phase responses across fold states."""
    frequencies_hz: List[float]
    fold_angles_deg: List[float]
    phase_matrix_deg: List[List[float]]  # [fold_angles x frequencies]
    unwrapped_phase_deg: List[List[float]]
    phase_agility_deg: List[float]        # Max phase shift vs frequency [f]
    center_frequency_hz: float
    max_phase_agility_deg: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequencies_hz": self.frequencies_hz,
            "frequencies_ghz": [round(f / 1e9, 4) for f in self.frequencies_hz],
            "fold_angles_deg": self.fold_angles_deg,
            "phase_matrix_deg": self.phase_matrix_deg,
            "unwrapped_phase_deg": self.unwrapped_phase_deg,
            "phase_agility_deg": self.phase_agility_deg,
            "center_frequency_hz": self.center_frequency_hz,
            "max_phase_agility_deg": round(self.max_phase_agility_deg, 2),
            "metadata": self.metadata,
        }


class MetasurfacePhaseEngine:
    """Analyzes reflection phase characteristics and beam steering across origami fold states."""

    @classmethod
    def calculate_reflection_phase(
        cls,
        s11: Sequence[complex],
        unwrap: bool = True,
    ) -> List[float]:
        """Extract reflection phase in degrees from S11 spectrum."""
        phases_rad = [cmath_phase(c) for c in s11]
        phases_deg = [math.degrees(p) for p in phases_rad]
        if unwrap and len(phases_deg) > 1:
            unwrapped = np.unwrap(phases_rad)
            return [float(math.degrees(p)) for p in unwrapped]
        return phases_deg

    @classmethod
    def analyze_phase_agility(
        cls,
        pattern_type: str = "miura_ori",
        pattern_params: Optional[Dict[str, Any]] = None,
        fold_angles_deg: Optional[List[float]] = None,
        f_start_ghz: float = 2.0,
        f_stop_ghz: float = 6.0,
        num_freq_points: int = 21,
        substrate_material: str = "kapton",
        conductor_material: str = "copper",
        ground_backed: bool = True,
        polarization: PolarizationType = PolarizationType.LINEAR_X,
    ) -> PhaseAgilityResult:
        """Evaluate reflection phase across continuous fold angles and extract phase agility."""
        from rf_origami.rf.materials.material import MaterialLibrary
        from rf_origami.web.service import OrigamiWebService

        if fold_angles_deg is None:
            fold_angles_deg = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0]

        freqs_hz = np.linspace(f_start_ghz * 1e9, f_stop_ghz * 1e9, num_freq_points).tolist()
        pattern = OrigamiWebService._build_pattern(pattern_type, pattern_params)

        raw_phase_matrix: List[List[float]] = []
        unwrap_phase_matrix: List[List[float]] = []

        sub_mat = MaterialLibrary.get(substrate_material)
        cond_mat = MaterialLibrary.get(conductor_material)

        for theta in fold_angles_deg:
            mesh_3d = FoldingEngine.fold_analytical(pattern, fold_angle_deg=theta)
            surface_mesh = SurfaceMesh.from_folded_mesh(
                folded_mesh=mesh_3d,
                ground_backed=ground_backed,
                substrate_thickness_mm=0.5,
            )
            solver = SurfaceMoMSolver(
                mesh=surface_mesh,
                conductor_material=cond_mat,
                substrate_material=sub_mat,
                ground_backed=ground_backed,
            )
            sim_res = solver.solve_spectrum(
                f_start_hz=f_start_ghz * 1e9,
                f_stop_hz=f_stop_ghz * 1e9,
                num_points=num_freq_points,
                polarization=polarization,
                fold_angle_deg=theta,
            )

            raw_phases = [math.degrees(cmath_phase(s)) for s in sim_res.s11]
            unwrapped = [float(math.degrees(p)) for p in np.unwrap([cmath_phase(s) for s in sim_res.s11])]
            raw_phase_matrix.append(raw_phases)
            unwrap_phase_matrix.append(unwrapped)

        # Compute phase agility vs frequency: max(Phi) - min(Phi) across fold angles
        phase_arr = np.array(unwrap_phase_matrix) # (num_angles, num_freqs)
        agility_per_freq = (np.max(phase_arr, axis=0) - np.min(phase_arr, axis=0)).tolist()
        max_agility = float(np.max(agility_per_freq)) if len(agility_per_freq) > 0 else 0.0

        center_freq = float(freqs_hz[len(freqs_hz) // 2])

        return PhaseAgilityResult(
            frequencies_hz=freqs_hz,
            fold_angles_deg=fold_angles_deg,
            phase_matrix_deg=raw_phase_matrix,
            unwrapped_phase_deg=unwrap_phase_matrix,
            phase_agility_deg=[round(float(a), 2) for a in agility_per_freq],
            center_frequency_hz=center_freq,
            max_phase_agility_deg=max_agility,
            metadata={
                "pattern_type": pattern_type,
                "substrate_material": substrate_material,
                "conductor_material": conductor_material,
            },
        )

    @classmethod
    def calculate_anomalous_reflection(
        cls,
        frequency_hz: float,
        theta_inc_deg: float,
        phase_gradient_deg_per_m: float,
    ) -> Dict[str, Any]:
        """Compute anomalous reflection angle using Generalized Snell's Law.

        sin(theta_r) = sin(theta_i) + (lambda_0 / 2pi) * dPhi/dx
        """
        lambda_0 = C_0 / frequency_hz
        k0 = 2.0 * math.pi / lambda_0

        dphi_dx_rad = math.radians(phase_gradient_deg_per_m)
        sin_inc = math.sin(math.radians(theta_inc_deg))

        sin_refl = sin_inc + (dphi_dx_rad / k0)

        if abs(sin_refl) <= 1.0:
            theta_r_deg = math.degrees(math.asin(sin_refl))
            is_propagating = True
        else:
            theta_r_deg = 90.0 if sin_refl > 0 else -90.0
            is_propagating = False  # Surface wave excitation (evanescent)

        return {
            "frequency_hz": frequency_hz,
            "wavelength_m": lambda_0,
            "theta_inc_deg": theta_inc_deg,
            "phase_gradient_deg_per_m": phase_gradient_deg_per_m,
            "sin_reflected": round(sin_refl, 4),
            "theta_reflected_deg": round(theta_r_deg, 2),
            "is_propagating": is_propagating,
            "mode": "Specially Deflected Plane Wave" if is_propagating else "Bound Surface Wave (Evanescent)",
        }


def cmath_phase(c: complex) -> float:
    """Return phase angle in radians of a complex number."""
    return math.atan2(c.imag, c.real)
