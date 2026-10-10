"""Parametric single degree-4 flat-foldable vertex generator.

The canonical unit-cell building block for rigid origami kinematics.
"""

from __future__ import annotations
import math
from typing import Any, Optional

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.parameters import Parameter, ParameterSet, ParameterType
from rf_origami.patterns.base import BasePattern


class Degree4VertexPattern(BasePattern):
    """Generates an isolated degree-4 flat-foldable vertex unit cell."""

    name = "degree4_vertex"
    description = "Isolated parametric degree-4 flat-foldable origami vertex"

    @classmethod
    def default_parameters(cls) -> ParameterSet:
        return ParameterSet([
            Parameter(
                name="alpha1",
                default=70.0,
                min_val=10.0,
                max_val=170.0,
                unit="deg",
                category="vertex_geometry",
                description="Sector angle 1 (alpha3 is automatically 180 - alpha1)",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="alpha2",
                default=110.0,
                min_val=10.0,
                max_val=170.0,
                unit="deg",
                category="vertex_geometry",
                description="Sector angle 2 (alpha4 is automatically 180 - alpha2)",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="radius",
                default=30.0,
                min_val=5.0,
                max_val=200.0,
                unit="mm",
                category="vertex_geometry",
                description="Radial length of crease lines from central vertex",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="valley_index",
                default=3,
                min_val=0,
                max_val=3,
                unit="",
                category="crease_assignment",
                description="Index (0..3) of the unique Valley crease (3M, 1V Maekawa rule)",
                param_type=ParameterType.INT,
            ),
        ])

    def generate(self, params: Optional[ParameterSet] = None, **kwargs: Any) -> CreasePattern:
        p = self.default_parameters() if params is None else params.copy()
        if kwargs:
            p.update(**kwargs)

        a1_deg: float = float(p["alpha1"])
        a2_deg: float = float(p["alpha2"])
        r: float = float(p["radius"])
        valley_idx: int = int(p["valley_index"]) % 4

        # Enforce Kawasaki's theorem: alpha1 + alpha3 = 180, alpha2 + alpha4 = 180
        a3_deg = 180.0 - a1_deg
        a4_deg = 180.0 - a2_deg
        sector_angles = [a1_deg, a2_deg, a3_deg, a4_deg]

        pattern = CreasePattern()
        v_center = pattern.add_vertex(0.0, 0.0, 0.0)

        # Compute cumulative angles for outer vertices
        curr_angle = 0.0
        outer_indices = []
        for ang in sector_angles:
            rad = math.radians(curr_angle)
            x = r * math.cos(rad)
            y = r * math.sin(rad)
            outer_indices.append(pattern.add_vertex(x, y, 0.0))
            curr_angle += ang

        # Add radial interior creases meeting at v_center (3 Mountain, 1 Valley)
        for idx in range(4):
            c_type = CreaseType.VALLEY if (idx == valley_idx) else CreaseType.MOUNTAIN
            pattern.add_crease(v_center, outer_indices[idx], crease_type=c_type, target_length=r)

        # Add outer boundary creases connecting surrounding vertices
        for idx in range(4):
            v_curr = outer_indices[idx]
            v_next = outer_indices[(idx + 1) % 4]
            pattern.add_crease(v_curr, v_next, crease_type=CreaseType.BOUNDARY)

        # Add 4 triangular faces
        for idx in range(4):
            v_curr = outer_indices[idx]
            v_next = outer_indices[(idx + 1) % 4]
            pattern.add_face([v_center, v_curr, v_next], material_tag="substrate")

        return pattern
