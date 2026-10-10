"""Abstract base class and utilities for parametric origami pattern generators."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.parameters import ParameterSet


class BasePattern(ABC):
    """Abstract base class for all procedural origami pattern generators."""

    name: str = "base_pattern"
    description: str = "Base origami pattern generator"

    @classmethod
    @abstractmethod
    def default_parameters(cls) -> ParameterSet:
        """Return the default ParameterSet defining geometric parameters for this pattern."""
        pass

    @abstractmethod
    def generate(self, params: Optional[ParameterSet] = None, **kwargs: Any) -> CreasePattern:
        """Generate and return a populated CreasePattern instance.

        Args:
            params: Optional ParameterSet. If omitted, default_parameters() is used.
            **kwargs: Direct parameter overrides (e.g. a=30.0, num_cells_x=4).
        """
        pass

    def verify_pattern(self, pattern: CreasePattern) -> Dict[str, Any]:
        """Perform topological and foldability verification on a generated pattern.

        Checks:
        - Number of vertices, creases, and faces.
        - Boundary vertex identification.
        - Kawasaki's Theorem on all interior even-degree vertices.
        - Maekawa's Theorem on all interior degree-4 vertices.

        Returns:
            Dictionary containing verification statistics and pass/fail summary.
        """
        interior_v_count = 0
        kawasaki_passes = 0
        maekawa_passes = 0

        for v_idx in range(pattern.num_vertices):
            if pattern.is_boundary_vertex(v_idx):
                continue
            interior_v_count += 1

            k_ok, _, _ = pattern.check_kawasaki_theorem(v_idx)
            if k_ok:
                kawasaki_passes += 1

            m_ok, _, _ = pattern.check_maekawa_theorem(v_idx)
            if m_ok:
                maekawa_passes += 1

        return {
            "num_vertices": pattern.num_vertices,
            "num_creases": pattern.num_creases,
            "num_faces": pattern.num_faces,
            "num_interior_vertices": interior_v_count,
            "kawasaki_passes": kawasaki_passes,
            "maekawa_passes": maekawa_passes,
            "is_valid_flat_foldable": (
                interior_v_count > 0 and
                kawasaki_passes == interior_v_count and
                maekawa_passes == interior_v_count
            ),
        }
