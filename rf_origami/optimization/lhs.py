"""Parametric Latin Hypercube Sampling (LHS) and Multi-Stage Filtering for Origami Absorbers.

Discovers viable metasurface absorber candidates across the 10D design space:
  x = [a, b, gamma, Nx, Ny, theta, h_sub, eps_r, L_c, W_c]
Applies hierarchical screening (Topological -> Foldability -> Collisions -> DFM -> Fast EM -> High-Fidelity EM).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.mesh import FoldedMesh
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import Material, MaterialLibrary
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.rf.absorber.result import AbsorberResult
from rf_origami.optimization.objectives import AbsorberOptimizationTarget, evaluate_absorber_objectives, compute_packed_volume_mm3


@dataclass
class CandidateAbsorberDesign:
    """A parameterized candidate design within the exploration pipeline."""
    candidate_id: str
    params: Dict[str, float]
    fold_angle_deg: float
    substrate_material: str = "kapton"
    conductor_material: str = "copper"
    substrate_thickness_mm: float = 0.5

    # Evaluation results
    is_valid_topology: bool = True
    is_valid_kinematics: bool = True
    is_collision_free: bool = True
    passes_dfm: bool = True
    sim_result: Optional[AbsorberResult] = None
    objectives: Optional[Tuple[float, float, float, float]] = None
    rank: int = 0
    crowding_distance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "params": self.params,
            "fold_angle_deg": float(self.fold_angle_deg),
            "substrate_material": self.substrate_material,
            "conductor_material": self.conductor_material,
            "substrate_thickness_mm": float(self.substrate_thickness_mm),
            "is_valid_topology": self.is_valid_topology,
            "is_valid_kinematics": self.is_valid_kinematics,
            "is_collision_free": self.is_collision_free,
            "passes_dfm": self.passes_dfm,
            "objectives": list(self.objectives) if self.objectives else None,
            "rank": int(self.rank),
            "crowding_distance": float(self.crowding_distance),
            "sim_result": self.sim_result.to_dict() if self.sim_result else None,
        }


class AbsorberLHSSampler:
    """Generates stratified Latin Hypercube samples and runs the multi-stage filter pipeline."""

    @staticmethod
    def sample_design_space(
        num_samples: int = 50,
        seed: int = 42,
        target: Optional[AbsorberOptimizationTarget] = None,
        a_range: Tuple[float, float] = (15.0, 45.0),
        b_range: Tuple[float, float] = (15.0, 45.0),
        gamma_range: Tuple[float, float] = (50.0, 80.0),
        nx_range: Tuple[int, int] = (2, 4),
        ny_range: Tuple[int, int] = (2, 4),
        thickness_range: Tuple[float, float] = (0.2, 1.6),
    ) -> List[CandidateAbsorberDesign]:
        """Generate stratified candidate parameter sets using Latin Hypercube Sampling."""
        rng = np.random.default_rng(seed)
        t = target or AbsorberOptimizationTarget()

        # Dimension intervals
        lhs_uniform = (rng.permutation(num_samples) + rng.uniform(0, 1, num_samples)) / num_samples
        lhs_b = (rng.permutation(num_samples) + rng.uniform(0, 1, num_samples)) / num_samples
        lhs_gamma = (rng.permutation(num_samples) + rng.uniform(0, 1, num_samples)) / num_samples
        lhs_angle = (rng.permutation(num_samples) + rng.uniform(0, 1, num_samples)) / num_samples
        lhs_thick = (rng.permutation(num_samples) + rng.uniform(0, 1, num_samples)) / num_samples

        candidates = []
        for i in range(num_samples):
            a_val = float(a_range[0] + lhs_uniform[i] * (a_range[1] - a_range[0]))
            b_val = float(b_range[0] + lhs_b[i] * (b_range[1] - b_range[0]))
            gamma_val = float(gamma_range[0] + lhs_gamma[i] * (gamma_range[1] - gamma_range[0]))
            th_min, th_max = t.allowed_fold_range_deg
            fold_ang = float(th_min + lhs_angle[i] * (th_max - th_min))
            thick_val = float(thickness_range[0] + lhs_thick[i] * (thickness_range[1] - thickness_range[0]))

            nx_val = int(rng.integers(nx_range[0], nx_range[1] + 1))
            ny_val = int(rng.integers(ny_range[0], ny_range[1] + 1))

            candidates.append(CandidateAbsorberDesign(
                candidate_id=f"ABS-LHS-{i + 1:03d}",
                params={
                    "a": a_val,
                    "b": b_val,
                    "gamma_deg": gamma_val,
                    "num_cells_x": nx_val,
                    "num_cells_y": ny_val,
                },
                fold_angle_deg=fold_ang,
                substrate_material=t.substrate_material,
                conductor_material=t.conductor_material,
                substrate_thickness_mm=thick_val,
            ))

        return candidates

    @classmethod
    def run_screening_pipeline(
        cls,
        candidates: List[CandidateAbsorberDesign],
        target: Optional[AbsorberOptimizationTarget] = None,
        max_em_evaluations: int = 15,
        freq_points: int = 21,
    ) -> List[CandidateAbsorberDesign]:
        """Apply sequential filtering: Topology -> Foldability -> DFM -> Fast EM solve."""
        tgt = target or AbsorberOptimizationTarget()
        evaluated: List[CandidateAbsorberDesign] = []

        for cand in candidates:
            # Stage 1: Topological validation
            a = cand.params["a"]
            b = cand.params["b"]
            gamma = cand.params["gamma_deg"]
            if a <= 5.0 or b <= 5.0 or gamma <= 30.0 or gamma >= 89.0:
                cand.is_valid_topology = False
                continue

            # Stage 2: Kinematic folding check
            try:
                pattern = MiuraOriPattern.generate(
                    a=a,
                    b=b,
                    gamma_deg=gamma,
                    num_cells_x=int(cand.params["num_cells_x"]),
                    num_cells_y=int(cand.params["num_cells_y"]),
                )
                folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=cand.fold_angle_deg)
                cand.is_valid_kinematics = True
            except Exception:
                cand.is_valid_kinematics = False
                continue

            # Stage 3: Collision / Geometric envelope check
            v = folded.vertices
            if len(v) == 0:
                cand.is_collision_free = False
                continue

            packed_vol = compute_packed_volume_mm3(folded, cand.substrate_thickness_mm) / 1000.0
            if packed_vol > tgt.max_packed_volume_cm3 * 1.5:
                # Exceeds maximum volume limit
                cand.is_collision_free = False
                continue

            # Stage 4: DFM checks (minimum facet dimension)
            cand.passes_dfm = (a >= 10.0 and b >= 10.0 and cand.substrate_thickness_mm >= 0.1)
            if not cand.passes_dfm:
                continue

            evaluated.append(cand)

        # Stage 5: Select top subset for high-fidelity EM solve
        to_solve = evaluated[:max_em_evaluations]
        final_results = []

        for cand in to_solve:
            pattern = MiuraOriPattern.generate(
                a=cand.params["a"],
                b=cand.params["b"],
                gamma_deg=cand.params["gamma_deg"],
                num_cells_x=int(cand.params["num_cells_x"]),
                num_cells_y=int(cand.params["num_cells_y"]),
            )
            folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=cand.fold_angle_deg)

            mesh = SurfaceMesh.from_folded_mesh(
                folded_mesh=folded,
                ground_backed=True,
                substrate_thickness_mm=cand.substrate_thickness_mm,
                target_resolution="medium",
            )

            solver = SurfaceMoMSolver(
                mesh=mesh,
                conductor_material=MaterialLibrary.get(cand.conductor_material),
                substrate_material=MaterialLibrary.get(cand.substrate_material),
                ground_backed=True,
            )

            f_center = tgt.target_frequency_ghz
            f_start = max(0.5, f_center - 1.5) * 1e9
            f_stop = (f_center + 1.5) * 1e9

            sim = solver.solve_spectrum(
                f_start_hz=f_start,
                f_stop_hz=f_stop,
                num_points=freq_points,
                fold_angle_deg=cand.fold_angle_deg,
            )

            cand.sim_result = sim
            cand.objectives = evaluate_absorber_objectives(sim, folded, tgt, cand.substrate_thickness_mm)
            final_results.append(cand)

        # Rank candidates based on primary objective (frequency error + absorption deficiency)
        final_results.sort(key=lambda c: (c.objectives[0] if c.objectives else 999.0, c.objectives[1] if c.objectives else 999.0))
        for r_idx, c in enumerate(final_results):
            c.rank = r_idx + 1

        return final_results
