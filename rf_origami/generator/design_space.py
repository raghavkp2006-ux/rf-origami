"""Design space definition, sampling distributions, and candidate data structures.

Provides parameterized exploration bounds, constraint definitions, and deterministic
random sampling for algorithmic origami design discovery.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class DesignSpace:
    """Defines the multidimensional parameter boundaries and filtering constraints."""

    # Geometric Parameter Bounds
    a_min: float = 12.0
    a_max: float = 50.0
    b_min: float = 12.0
    b_max: float = 50.0
    gamma_min: float = 30.0  # degrees
    gamma_max: float = 75.0  # degrees
    num_cells_x_min: int = 1
    num_cells_x_max: int = 5
    num_cells_y_min: int = 1
    num_cells_y_max: int = 5
    gradient_x_min: float = -0.2
    gradient_x_max: float = 0.2
    gradient_y_min: float = -0.2
    gradient_y_max: float = 0.2
    fold_angle_min: float = 15.0
    fold_angle_max: float = 75.0

    # Physical & Manufacturing Constraints
    flat_foldable_only: bool = True
    min_panel_area: float = 40.0        # mm²
    min_crease_length: float = 8.0      # mm
    max_aperture_width: float = 350.0   # mm
    max_aperture_height: float = 350.0  # mm

    # RF-Aware Target Constraints (EM Solver Pending)
    target_frequency_ghz: float = 2.4   # GHz
    substrate_thickness_mm: float = 0.8 # mm
    crease_keepout_mm: float = 1.0      # mm

    def sample(self, count: int, seed: int = 42) -> List[Dict[str, Any]]:
        """Generate `count` candidate parameter sets using deterministic Latin Hypercube Sampling.

        Args:
            count: Number of candidates to sample (e.g. 10, 50, 100, 500).
            seed: Deterministic integer seed for full reproducibility.

        Returns:
            List of parameter dictionaries.
        """
        rng = np.random.default_rng(seed)
        samples = []

        # Latin Hypercube intervals
        intervals = np.linspace(0.0, 1.0, count + 1)

        for idx in range(count):
            # Uniform jitter within LHS bin
            u = lambda: float(rng.uniform(intervals[idx], intervals[idx + 1]))

            a = self.a_min + u() * (self.a_max - self.a_min)
            b = self.b_min + float(rng.uniform(0.0, 1.0)) * (self.b_max - self.b_min)
            gamma = self.gamma_min + float(rng.uniform(0.0, 1.0)) * (self.gamma_max - self.gamma_min)

            nx = int(rng.integers(self.num_cells_x_min, self.num_cells_x_max + 1))
            ny = int(rng.integers(self.num_cells_y_min, self.num_cells_y_max + 1))

            grad_x = self.gradient_x_min + float(rng.uniform(0.0, 1.0)) * (self.gradient_x_max - self.gradient_x_min)
            grad_y = self.gradient_y_min + float(rng.uniform(0.0, 1.0)) * (self.gradient_y_max - self.gradient_y_min)

            fold_angle = self.fold_angle_min + float(rng.uniform(0.0, 1.0)) * (self.fold_angle_max - self.fold_angle_min)

            # Round parameters to sensible manufacturing precision
            samples.append({
                "candidate_index": idx + 1,
                "a": round(a, 2),
                "b": round(b, 2),
                "gamma": round(gamma, 1),
                "num_cells_x": nx,
                "num_cells_y": ny,
                "gradient_x": round(grad_x, 3),
                "gradient_y": round(grad_y, 3),
                "fold_angle": round(fold_angle, 1),
            })

        # Shuffle deterministically to prevent ordering correlation across variables
        rng.shuffle(samples)
        return samples

    def to_dict(self) -> Dict[str, Any]:
        """Serialize design space bounds and constraint settings."""
        return {
            "a_range": [self.a_min, self.a_max],
            "b_range": [self.b_min, self.b_max],
            "gamma_range": [self.gamma_min, self.gamma_max],
            "num_cells_x_range": [self.num_cells_x_min, self.num_cells_x_max],
            "num_cells_y_range": [self.num_cells_y_min, self.num_cells_y_max],
            "gradient_x_range": [self.gradient_x_min, self.gradient_x_max],
            "gradient_y_range": [self.gradient_y_min, self.gradient_y_max],
            "fold_angle_range": [self.fold_angle_min, self.fold_angle_max],
            "constraints": {
                "flat_foldable_only": self.flat_foldable_only,
                "min_panel_area": self.min_panel_area,
                "min_crease_length": self.min_crease_length,
                "max_aperture_width": self.max_aperture_width,
                "max_aperture_height": self.max_aperture_height,
            },
            "rf_constraints": {
                "target_frequency_ghz": self.target_frequency_ghz,
                "substrate_thickness_mm": self.substrate_thickness_mm,
                "crease_keepout_mm": self.crease_keepout_mm,
            }
        }


@dataclass
class CandidateDesign:
    """Represents a single generated candidate origami design in the exploration space."""

    id: str
    seed: int
    pattern_family: str
    parameters: Dict[str, Any]
    is_valid: bool
    rejection_reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    thumbnail_svg: str = ""

    def get_hash(self) -> str:
        """Deterministic fingerprint of this candidate's parameters."""
        raw = f"{self.pattern_family}_{self.seed}_{json.dumps(self.parameters, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable representation."""
        return {
            "id": self.id,
            "hash": self.get_hash(),
            "seed": self.seed,
            "pattern_family": self.pattern_family,
            "parameters": self.parameters,
            "is_valid": self.is_valid,
            "rejection_reasons": self.rejection_reasons,
            "metrics": self.metrics,
            "validation": self.validation,
            "thumbnail_svg": self.thumbnail_svg,
        }
