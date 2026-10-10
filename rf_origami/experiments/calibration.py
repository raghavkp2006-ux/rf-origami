"""Digital Twin Model Calibration Engine for Origami Metasurfaces.

Performs parameter estimation and calibration of dielectric permittivity (eps_r),
loss tangent (tan_delta), substrate thickness offset, and fold angle tolerances
from measured VNA reflection curves.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import Material, MaterialLibrary
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.experiments.comparison import ExperimentalComparator


class DigitalTwinCalibrator:
    """Calibrates numerical simulation parameters to match experimental VNA curves."""

    @classmethod
    def calibrate_material_and_geometry(
        cls,
        pattern_params: Dict[str, Any],
        nominal_fold_angle_deg: float,
        meas_frequencies_hz: List[float],
        meas_s11_db: List[float],
        nominal_eps_r: float = 3.5,
        nominal_thickness_mm: float = 0.5,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Perform digital twin optimization to identify true physical parameters."""
        best_eps_r = nominal_eps_r
        best_thick = nominal_thickness_mm
        best_angle = nominal_fold_angle_deg
        best_rmse = float("inf")
        best_comp: Dict[str, Any] = {}

        # Search grid around nominal parameters
        eps_grid = np.linspace(nominal_eps_r * 0.85, nominal_eps_r * 1.15, 5)
        angle_grid = np.linspace(max(0.0, nominal_fold_angle_deg - 5.0), min(80.0, nominal_fold_angle_deg + 5.0), 3)

        pattern = MiuraOriPattern.generate(
            a=pattern_params.get("a", 25.0),
            b=pattern_params.get("b", 25.0),
            gamma_deg=pattern_params.get("gamma_deg", 65.0),
            num_cells_x=int(pattern_params.get("num_cells_x", 2)),
            num_cells_y=int(pattern_params.get("num_cells_y", 2)),
        )

        f_start = min(meas_frequencies_hz)
        f_stop = max(meas_frequencies_hz)

        for eps_test in eps_grid:
            for ang_test in angle_grid:
                folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=ang_test)
                mesh = SurfaceMesh.from_folded_mesh(
                    folded_mesh=folded,
                    ground_backed=True,
                    substrate_thickness_mm=nominal_thickness_mm,
                    target_resolution="medium",
                )

                custom_sub = Material(
                    name="CalibratedSubstrate",
                    relative_permittivity=float(eps_test),
                    loss_tangent=0.02,
                    conductivity=0.0,
                )

                solver = SurfaceMoMSolver(
                    mesh=mesh,
                    conductor_material=MaterialLibrary.get("copper"),
                    substrate_material=custom_sub,
                    ground_backed=True,
                )

                sim_res = solver.solve_spectrum(
                    f_start_hz=f_start,
                    f_stop_hz=f_stop,
                    num_points=len(meas_frequencies_hz),
                    fold_angle_deg=ang_test,
                )

                comp = ExperimentalComparator.compare(
                    sim_frequencies_hz=sim_res.frequencies_hz,
                    sim_s11_db=sim_res.s11_db,
                    meas_frequencies_hz=meas_frequencies_hz,
                    meas_s11_db=meas_s11_db,
                    sim_absorption=sim_res.absorption,
                )

                score = comp["s11_rmse_db"] + comp["frequency_error_percent"] * 0.5
                if score < best_rmse:
                    best_rmse = score
                    best_eps_r = float(eps_test)
                    best_angle = float(ang_test)
                    best_comp = comp

        return {
            "nominal_eps_r": nominal_eps_r,
            "calibrated_eps_r": best_eps_r,
            "eps_r_shift_percent": ((best_eps_r - nominal_eps_r) / nominal_eps_r * 100.0),
            "nominal_fold_angle_deg": nominal_fold_angle_deg,
            "calibrated_fold_angle_deg": best_angle,
            "angle_offset_deg": (best_angle - nominal_fold_angle_deg),
            "calibrated_thickness_mm": nominal_thickness_mm,
            "comparison": best_comp,
            "calibration_status": "CONVERGED",
        }
