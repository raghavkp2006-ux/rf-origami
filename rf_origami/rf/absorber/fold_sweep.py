"""Automated Multi-State Kinematic Fold Angle and Frequency Sweeper for Metasurface Absorbers.

Sweeps origami fold angles theta x frequency f to quantify fold-dependent
electromagnetic tuning, absorption spectra, and 2D absorption heatmaps.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.mesh import FoldedMesh
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import Material, MaterialLibrary
from rf_origami.rf.geometry.converter import RFGeometryConverter
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.absorber.result import AbsorberResult
from rf_origami.rf.absorber.metrics import s11_to_db


@dataclass
class AbsorberFoldSweepResult:
    """Aggregated multi-angle sweep dataset for origami RF absorbers.

    Attributes:
        fold_angles_deg: List of evaluated fold angles [deg].
        frequencies_hz: Frequency spectrum evaluated at each fold angle [Hz].
        results_by_angle: Dictionary mapping fold angle to individual AbsorberResult.
        s11_db_matrix: 2D array of S11 in dB [num_angles, num_freqs].
        absorption_matrix: 2D array of absorption [num_angles, num_freqs] (Heatmap data).
        reflection_matrix: 2D array of reflection [num_angles, num_freqs].
        transmission_matrix: 2D array of transmission [num_angles, num_freqs].
        resonance_vs_fold: List of (fold_angle, resonant_freq_ghz, peak_absorption, bandwidth_mhz).
        tuning_range_ghz: (f_min_resonant, f_max_resonant) across all fold angles.
        tuning_ratio: f_max / f_min tuning capability.
        metadata: Simulation configuration, pattern family, materials, and timestamps.
    """

    fold_angles_deg: List[float]
    frequencies_hz: List[float]
    results_by_angle: Dict[float, AbsorberResult]
    s11_db_matrix: List[List[float]]
    absorption_matrix: List[List[float]]
    reflection_matrix: List[List[float]]
    transmission_matrix: List[List[float]]
    resonance_vs_fold: List[Dict[str, float]]
    tuning_range_ghz: Tuple[float, float] = (0.0, 0.0)
    tuning_ratio: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def frequencies_ghz(self) -> List[float]:
        return [f / 1e9 for f in self.frequencies_hz]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete sweep dataset to JSON-serializable dictionary."""
        results_dict = {
            f"{ang:.1f}": res.to_dict()
            for ang, res in self.results_by_angle.items()
        }

        return {
            "fold_angles_deg": [float(a) for a in self.fold_angles_deg],
            "frequencies_hz": [float(f) for f in self.frequencies_hz],
            "frequencies_ghz": self.frequencies_ghz,
            "results_by_angle": results_dict,
            "s11_db_matrix": self.s11_db_matrix,
            "absorption_matrix": self.absorption_matrix,
            "reflection_matrix": self.reflection_matrix,
            "transmission_matrix": self.transmission_matrix,
            "resonance_vs_fold": self.resonance_vs_fold,
            "tuning_range_ghz": [float(self.tuning_range_ghz[0]), float(self.tuning_range_ghz[1])],
            "tuning_ratio": float(self.tuning_ratio),
            "metadata": self.metadata,
        }


def run_absorber_fold_sweep(
    pattern: Optional[CreasePattern] = None,
    pattern_type: str = "miura_ori",
    pattern_params: Optional[Dict[str, Any]] = None,
    fold_angles_deg: Optional[Sequence[float]] = None,
    f_start_ghz: float = 1.0,
    f_stop_ghz: float = 6.0,
    num_freq_points: int = 31,
    substrate_material: str = "kapton",
    conductor_material: str = "copper",
    ground_backed: bool = True,
    substrate_thickness_mm: float = 0.5,
    polarization: PolarizationType = PolarizationType.LINEAR_X,
    material_tags: Optional[List[str]] = None,
) -> AbsorberFoldSweepResult:
    """Execute automated fold angle sweep x frequency spectrum for an origami absorber.

    Args:
        pattern: Optional pre-constructed CreasePattern.
        pattern_type: Name of pattern if generating procedurally ("miura_ori", etc.).
        pattern_params: Parameter dictionary for procedural generator.
        fold_angles_deg: List of fold angles to evaluate (default: 0 to 60 deg).
        f_start_ghz: Sweep start frequency in GHz.
        f_stop_ghz: Sweep stop frequency in GHz.
        num_freq_points: Number of spectral evaluation points.
        substrate_material: Name of dielectric substrate.
        conductor_material: Name of conductive layer.
        ground_backed: Whether structure is backed by a continuous ground plane.
        substrate_thickness_mm: Thickness of substrate layer in mm.
        polarization: Polarization of incident plane wave.
        material_tags: Optional explicit face material assignments.

    Returns:
        AbsorberFoldSweepResult with S11 curves, absorption curves, heatmap matrix, and resonance tuning.
    """
    if fold_angles_deg is None:
        fold_angles_deg = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0]

    # Generate baseline crease pattern if not provided
    if pattern is None:
        if pattern_type == "miura_ori":
            p_args = pattern_params or {"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2}
            pattern = MiuraOriPattern.generate(**p_args)
        else:
            # Fallback to default Miura-Ori
            pattern = MiuraOriPattern.generate(a=25.0, b=25.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)

    sub_mat = MaterialLibrary.get(substrate_material)
    cond_mat = MaterialLibrary.get(conductor_material)

    f_start_hz = f_start_ghz * 1e9
    f_stop_hz = f_stop_ghz * 1e9
    freqs_hz = np.linspace(f_start_hz, f_stop_hz, num_freq_points).tolist()

    results_by_angle: Dict[float, AbsorberResult] = {}
    s11_matrix: List[List[float]] = []
    abs_matrix: List[List[float]] = []
    ref_matrix: List[List[float]] = []
    trn_matrix: List[List[float]] = []
    res_list: List[Dict[str, float]] = []

    for angle in fold_angles_deg:
        # 1. Fold geometry at current angle
        folded_mesh = FoldingEngine.fold_analytical(pattern, fold_angle_deg=angle)

        if material_tags and len(material_tags) == len(folded_mesh.faces):
            folded_mesh.face_materials = list(material_tags)

        # 2. Build triangular surface mesh
        surface_mesh = SurfaceMesh.from_folded_mesh(
            folded_mesh=folded_mesh,
            ground_backed=ground_backed,
            substrate_thickness_mm=substrate_thickness_mm,
            target_resolution="medium",
        )

        # 3. Solve frequency spectrum
        solver = SurfaceMoMSolver(
            mesh=surface_mesh,
            conductor_material=cond_mat,
            substrate_material=sub_mat,
            ground_backed=ground_backed,
        )

        sim_res = solver.solve_spectrum(
            f_start_hz=f_start_hz,
            f_stop_hz=f_stop_hz,
            num_points=num_freq_points,
            polarization=polarization,
            fold_angle_deg=angle,
        )

        results_by_angle[float(angle)] = sim_res
        s11_matrix.append(sim_res.s11_db)
        abs_matrix.append(sim_res.absorption)
        ref_matrix.append(sim_res.reflection)
        trn_matrix.append(sim_res.transmission)

        res_list.append({
            "fold_angle_deg": float(angle),
            "resonant_frequency_hz": float(sim_res.resonant_frequency_hz),
            "resonant_frequency_ghz": float(sim_res.resonant_frequency_hz / 1e9),
            "minimum_s11_db": float(sim_res.minimum_s11_db),
            "peak_absorption": float(sim_res.peak_absorption),
            "absorption_bandwidth_hz": float(sim_res.absorption_bandwidth_hz),
            "absorption_bandwidth_mhz": float(sim_res.absorption_bandwidth_hz / 1e6),
            "fractional_bandwidth": float(sim_res.fractional_bandwidth),
        })

    # Compute tuning bounds
    res_freqs_ghz = [item["resonant_frequency_ghz"] for item in res_list if item["resonant_frequency_ghz"] > 0]
    if res_freqs_ghz:
        f_min = min(res_freqs_ghz)
        f_max = max(res_freqs_ghz)
        tuning_ratio = (f_max / f_min) if f_min > 0 else 1.0
        tuning_range = (f_min, f_max)
    else:
        tuning_range = (0.0, 0.0)
        tuning_ratio = 1.0

    return AbsorberFoldSweepResult(
        fold_angles_deg=[float(a) for a in fold_angles_deg],
        frequencies_hz=freqs_hz,
        results_by_angle=results_by_angle,
        s11_db_matrix=s11_matrix,
        absorption_matrix=abs_matrix,
        reflection_matrix=ref_matrix,
        transmission_matrix=trn_matrix,
        resonance_vs_fold=res_list,
        tuning_range_ghz=tuning_range,
        tuning_ratio=float(tuning_ratio),
        metadata={
            "pattern_type": pattern_type,
            "substrate": substrate_material,
            "conductor": conductor_material,
            "ground_backed": ground_backed,
            "substrate_thickness_mm": substrate_thickness_mm,
            "polarization": polarization.value,
            "timestamp": datetime.datetime.now().isoformat(),
        },
    )
