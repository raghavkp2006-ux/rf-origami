"""Fold-Angle Sweep and RF Tunability Analysis.

Simulates the electromagnetic response of an origami antenna across multiple
folding angles (0°, 15°, 30°, 45°, 60°, 75°, 85°) to demonstrate frequency tuning.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from rf_origami.folding.engine import FoldingEngine
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.patterns.waterbomb import WaterbombPattern
from rf_origami.patterns.yoshimura import YoshimuraPattern
from rf_origami.rf.geometry.converter import RFGeometryConverter
from rf_origami.rf.mesh.discretization import EMDiscretization
from rf_origami.rf.mesh.quality import validate_fold_mesh
from rf_origami.rf.ports.lumped_port import LumpedPort
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.metrics.result import RFSimulationResult
from rf_origami.rf.materials.material import MaterialLibrary, Material


class FoldAngleSweepRunner:
    """Executes multi-state RF analysis across the folding trajectory."""

    DEFAULT_ANGLES = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 85.0]

    @classmethod
    def run_sweep(
        cls,
        candidate_id: str,
        pattern_type: str,
        params: Dict[str, Any],
        angles_deg: Optional[Sequence[float]] = None,
        f_start_hz: float = 1.0e9,
        f_stop_hz: float = 8.0e9,
        num_points: int = 51,
        substrate_material: Optional[Material] = None,
    ) -> Dict[str, Any]:
        """Simulate RF S-parameters and resonant frequencies across discrete fold angles."""
        angles = list(angles_deg) if angles_deg is not None else cls.DEFAULT_ANGLES
        sub_mat = substrate_material or MaterialLibrary.get("kapton")
        ptype = pattern_type.lower().replace("-", "_").strip()

        # Instantiate pattern generator
        if "waterbomb" in ptype:
            gen = WaterbombPattern()
        elif "yoshimura" in ptype:
            gen = YoshimuraPattern()
        else:
            gen = MiuraOriPattern()

        valid_keys = set(gen.default_parameters().keys())
        clean_params = {k: v for k, v in params.items() if k in valid_keys}
        crease_pattern = gen.generate(**clean_params)
        reference_mesh = FoldingEngine.fold(ptype, crease_pattern, clean_params, fold_angle_deg=0.0)

        results: List[RFSimulationResult] = []
        comparison_table: List[Dict[str, Any]] = []

        for theta in angles:
            # Kinematically fold at angle theta
            folded_mesh = FoldingEngine.fold(
                pattern_type=ptype,
                crease_pattern=crease_pattern,
                params=clean_params,
                fold_angle_deg=float(theta),
            )
            quality = validate_fold_mesh(folded_mesh, reference_mesh)

            # Convert to physical RF model
            rf_geom = RFGeometryConverter.from_folded_mesh(
                folded_mesh=folded_mesh,
                parent_candidate_id=candidate_id,
                fold_angle_deg=float(theta),
                substrate_material=sub_mat,
            )

            # Discretize
            discretization = EMDiscretization.from_rf_geometry(
                rf_geometry=rf_geom,
                target_segment_length_mm=6.0,
            )

            port = LumpedPort(
                port_id=f"FEED_{theta:.0f}",
                impedance=50.0,
            )

            solver = MoMSolver(
                discretization=discretization,
                port=port,
                substrate_material=sub_mat,
            )

            # Run frequency sweep
            sweep_data = solver.solve_sweep(
                f_start_hz=f_start_hz,
                f_stop_hz=f_stop_hz,
                num_points=num_points,
            )

            res_info = sweep_data["resonance"]
            sim_res = RFSimulationResult(
                candidate_id=candidate_id,
                geometry_id=f"{candidate_id}_fold_{theta:.0f}",
                fold_angle_deg=float(theta),
                frequencies_ghz=sweep_data["frequencies_ghz"],
                s11_db=sweep_data["s11_db"],
                zin_real_ohms=sweep_data["zin_real_ohms"],
                zin_imag_ohms=sweep_data["zin_imag_ohms"],
                vswr=sweep_data["vswr"],
                resonant_frequency_ghz=res_info["resonant_frequency_ghz"],
                min_s11_db=res_info["min_s11_db"],
                bandwidth_mhz=res_info["bandwidth_mhz"],
                bandwidth_percent=res_info["bandwidth_percent"],
                materials={"substrate": sub_mat.name, "conductor": "Copper"},
                mesh_statistics={"num_segments": discretization.num_segments},
            )
            results.append(sim_res)

            comparison_table.append({
                "fold_angle_deg": round(float(theta), 1),
                "resonant_frequency_ghz": res_info["resonant_frequency_ghz"],
                "min_s11_db": res_info["min_s11_db"],
                "vswr": res_info["vswr_at_resonance"],
                "bandwidth_mhz": res_info["bandwidth_mhz"],
                "total_length_mm": round(discretization.total_length_mm, 1),
                "mesh_quality": quality,
                "at_sweep_boundary": res_info["at_sweep_boundary"],
            })

        return {
            "candidate_id": candidate_id,
            "pattern_type": ptype,
            "angles_evaluated": angles,
            "comparison_table": comparison_table,
            "results": [r.to_dict() for r in results],
            "validation_status": "Not validated",
            "tuning_ratio": max(r.resonant_frequency_ghz for r in results) / min(r.resonant_frequency_ghz for r in results) if results else None,
            "heatmap": {"angles_deg": angles, "frequencies_ghz": results[0].frequencies_ghz if results else [], "s11_db": [r.s11_db for r in results]},
        }
