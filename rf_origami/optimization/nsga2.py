"""Non-Dominated Sorting Genetic Algorithm II (NSGA-II) for Multi-Objective Absorber Optimization.

Discovers the Pareto frontier balancing frequency accuracy, peak absorption,
bandwidth, and compact folded volume.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import MaterialLibrary
from rf_origami.rf.absorber.surface_solver import SurfaceMesh, SurfaceMoMSolver
from rf_origami.optimization.objectives import AbsorberOptimizationTarget, evaluate_absorber_objectives
from rf_origami.optimization.lhs import CandidateAbsorberDesign


def dominates(obj_a: Tuple[float, ...], obj_b: Tuple[float, ...]) -> bool:
    """Return True if objective vector A dominates vector B (minimization)."""
    better_in_any = False
    for a, b in zip(obj_a, obj_b):
        if a > b:
            return False
        if a < b:
            better_in_any = True
    return better_in_any


def fast_non_dominated_sort(candidates: List[CandidateAbsorberDesign]) -> List[List[CandidateAbsorberDesign]]:
    """Sort population into non-dominated Pareto fronts F_1, F_2, ..."""
    fronts: List[List[CandidateAbsorberDesign]] = [[]]
    domination_counts = {c.candidate_id: 0 for c in candidates}
    dominated_sets = {c.candidate_id: [] for c in candidates}

    cand_map = {c.candidate_id: c for c in candidates}

    for p in candidates:
        if p.objectives is None:
            continue
        for q in candidates:
            if q.objectives is None:
                continue
            if dominates(p.objectives, q.objectives):
                dominated_sets[p.candidate_id].append(q.candidate_id)
            elif dominates(q.objectives, p.objectives):
                domination_counts[p.candidate_id] += 1

        if domination_counts[p.candidate_id] == 0:
            p.rank = 1
            fronts[0].append(p)

    i = 0
    while len(fronts[i]) > 0:
        next_front = []
        for p in fronts[i]:
            for q_id in dominated_sets[p.candidate_id]:
                domination_counts[q_id] -= 1
                if domination_counts[q_id] == 0:
                    q = cand_map[q_id]
                    q.rank = i + 2
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    if not fronts[-1]:
        fronts.pop()

    return fronts


def assign_crowding_distance(front: List[CandidateAbsorberDesign]) -> None:
    """Calculate crowding distance for diversity preservation on the Pareto front."""
    n = len(front)
    if n == 0:
        return
    for c in front:
        c.crowding_distance = 0.0

    if n <= 2:
        for c in front:
            c.crowding_distance = float("inf")
        return

    num_objectives = len(front[0].objectives) if front[0].objectives else 0

    for m in range(num_objectives):
        front.sort(key=lambda c: c.objectives[m] if c.objectives else 0.0)
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")

        f_min = front[0].objectives[m]
        f_max = front[-1].objectives[m]
        diff = max(1e-9, f_max - f_min)

        for i in range(1, n - 1):
            if math.isinf(front[i].crowding_distance):
                continue
            prev_val = front[i - 1].objectives[m]
            next_val = front[i + 1].objectives[m]
            front[i].crowding_distance += (next_val - prev_val) / diff


class NSGA2Optimizer:
    """Multi-objective evolutionary optimizer for origami absorber metasurfaces."""

    @classmethod
    def optimize(
        cls,
        target: Optional[AbsorberOptimizationTarget] = None,
        population_size: int = 20,
        generations: int = 3,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Execute NSGA-II search and return the Pareto frontier."""
        from rf_origami.optimization.lhs import AbsorberLHSSampler

        tgt = target or AbsorberOptimizationTarget()
        rng = np.random.default_rng(seed)

        # Initial population from Latin Hypercube Sampling
        population = AbsorberLHSSampler.sample_design_space(
            num_samples=population_size,
            seed=seed,
            target=tgt,
        )

        # Evaluate initial population
        population = AbsorberLHSSampler.run_screening_pipeline(
            candidates=population,
            target=tgt,
            max_em_evaluations=population_size,
            freq_points=15,
        )

        fronts = fast_non_dominated_sort(population)
        for f in fronts:
            assign_crowding_distance(f)

        # Main generational loop (lightweight for fast response)
        for gen in range(generations):
            # Selection & Genetic Operators
            offspring: List[CandidateAbsorberDesign] = []
            for k in range(population_size // 2):
                p1 = population[rng.integers(0, len(population))]
                p2 = population[rng.integers(0, len(population))]

                # Simulated Binary Crossover (SBX) on continuous parameters
                child_params = {}
                for param_key in ["a", "b", "gamma_deg"]:
                    v1 = p1.params[param_key]
                    v2 = p2.params[param_key]
                    beta = rng.uniform(0.7, 1.3)
                    child_params[param_key] = float(np.clip(0.5 * ((1 + beta) * v1 + (1 - beta) * v2), 10.0, 50.0))

                child_params["num_cells_x"] = p1.params["num_cells_x"]
                child_params["num_cells_y"] = p1.params["num_cells_y"]

                fold_ang = float(np.clip(0.5 * (p1.fold_angle_deg + p2.fold_angle_deg) + rng.normal(0, 3.0), 0.0, 60.0))
                thick = float(np.clip(0.5 * (p1.substrate_thickness_mm + p2.substrate_thickness_mm), 0.2, 1.6))

                offspring.append(CandidateAbsorberDesign(
                    candidate_id=f"GEN{gen+1}-OFF-{k+1:02d}",
                    params=child_params,
                    fold_angle_deg=fold_ang,
                    substrate_material=tgt.substrate_material,
                    conductor_material=tgt.conductor_material,
                    substrate_thickness_mm=thick,
                ))

            # Screen and evaluate offspring
            evaluated_offspring = AbsorberLHSSampler.run_screening_pipeline(
                candidates=offspring,
                target=tgt,
                max_em_evaluations=len(offspring),
                freq_points=15,
            )

            # Combine and non-dominated sort
            combined = population + evaluated_offspring
            fronts = fast_non_dominated_sort(combined)
            for f in fronts:
                assign_crowding_distance(f)

            # Select next generation
            next_pop = []
            for f in fronts:
                if len(next_pop) + len(f) <= population_size:
                    next_pop.extend(f)
                else:
                    f.sort(key=lambda c: c.crowding_distance, reverse=True)
                    next_pop.extend(f[:(population_size - len(next_pop))])
                    break
            population = next_pop

        pareto_front = fronts[0] if fronts else population
        pareto_candidates = [c.to_dict() for c in pareto_front]

        return {
            "target": {
                "target_frequency_ghz": tgt.target_frequency_ghz,
                "min_absorption": tgt.min_absorption,
                "min_bandwidth_mhz": tgt.min_bandwidth_mhz,
            },
            "generations": generations,
            "pareto_count": len(pareto_candidates),
            "pareto_front": pareto_candidates,
            "best_candidate": pareto_candidates[0] if pareto_candidates else None,
        }
