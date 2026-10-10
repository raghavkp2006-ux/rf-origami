"""Parametric Miura-ori tessellation crease pattern generator.

Generates the classic herringbone/parallelogram tessellation widely utilized
in deployable aerospace structures and reconfigurable RF antennas/reflectarrays.
"""

from __future__ import annotations
import math
from typing import Any, Optional

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.parameters import Parameter, ParameterSet, ParameterType
from rf_origami.patterns.base import BasePattern


class MiuraOriPattern(BasePattern):
    """Parametric Miura-ori origami pattern generator."""

    name = "miura_ori"
    description = "Parametric Miura-ori parallelogram herringbone tessellation"

    @classmethod
    def default_parameters(cls) -> ParameterSet:
        """Default geometric parameters for Miura-ori."""
        return ParameterSet([
            Parameter(
                name="a",
                default=20.0,
                min_val=1.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Side length along the zig-zag crease lines",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="b",
                default=20.0,
                min_val=1.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Side length along the straight horizontal crease lines",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="gamma",
                default=60.0,
                min_val=15.0,
                max_val=85.0,
                unit="deg",
                category="cell_dimensions",
                description="Acute sector angle of the parallelogram facets",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="num_cells_x",
                default=2,
                min_val=1,
                max_val=50,
                unit="",
                category="tessellation",
                description="Number of repeating unit cells in x-direction",
                param_type=ParameterType.INT,
            ),
            Parameter(
                name="num_cells_y",
                default=2,
                min_val=1,
                max_val=50,
                unit="",
                category="tessellation",
                description="Number of repeating unit cells in y-direction",
                param_type=ParameterType.INT,
            ),
        ])

    @classmethod
    def generate(cls, params: Optional[ParameterSet] = None, **kwargs: Any) -> CreasePattern:
        """Generate the 2D Miura-ori crease pattern.

        Args:
            params: Optional ParameterSet. If omitted, default_parameters() is used.
            **kwargs: Direct parameter overrides (e.g. a=30.0, gamma=55.0, gamma_deg=55.0).
        """
        p = cls.default_parameters() if params is None else params.copy()
        if "gamma_deg" in kwargs and "gamma" not in kwargs:
            kwargs["gamma"] = kwargs["gamma_deg"]
        if kwargs:
            p.update(**kwargs)

        a: float = float(p["a"])
        b: float = float(p["b"])
        gamma_deg: float = float(p["gamma"])
        gamma_rad: float = math.radians(gamma_deg)
        nx: int = int(p["num_cells_x"])
        ny: int = int(p["num_cells_y"])


        # Grid dimensions (each unit cell contains 2x2 facets)
        num_cols = 2 * nx + 1
        num_rows = 2 * ny + 1

        pattern = CreasePattern()
        dx_offset = a * math.cos(gamma_rad)
        dy_step = a * math.sin(gamma_rad)

        # 1. Create vertices
        # vertex_grid[j][i] stores the vertex index at column i, row j
        vertex_grid = []
        for j in range(num_rows):
            row = []
            y = j * dy_step
            # Offset alternates on odd rows to produce the zig-zag
            x_shift = dx_offset if (j % 2 == 1) else 0.0
            for i in range(num_cols):
                x = i * b + x_shift
                v_idx = pattern.add_vertex(x, y, 0.0)
                row.append(v_idx)
            vertex_grid.append(row)

        # 2. Add Horizontal Creases
        for j in range(num_rows):
            is_boundary_row = (j == 0 or j == num_rows - 1)
            # Internal horizontal lines alternate Mountain / Valley by row
            row_fold_type = CreaseType.MOUNTAIN if (j % 2 == 1) else CreaseType.VALLEY

            for i in range(num_cols - 1):
                u = vertex_grid[j][i]
                v = vertex_grid[j][i + 1]
                c_type = CreaseType.BOUNDARY if is_boundary_row else row_fold_type
                pattern.add_crease(u, v, crease_type=c_type, target_length=b)

        # 3. Add Zig-Zag Creases
        for j in range(num_rows - 1):
            for i in range(num_cols):
                is_boundary_col = (i == 0 or i == num_cols - 1)
                # Internal zig-zag lines alternate Mountain / Valley with checkerboard parity
                zz_fold_type = CreaseType.MOUNTAIN if ((i + j) % 2 == 0) else CreaseType.VALLEY

                u = vertex_grid[j][i]
                v = vertex_grid[j + 1][i]
                c_type = CreaseType.BOUNDARY if is_boundary_col else zz_fold_type
                pattern.add_crease(u, v, crease_type=c_type, target_length=a)

        # 4. Add Parallelogram Faces
        for j in range(num_rows - 1):
            for i in range(num_cols - 1):
                v0 = vertex_grid[j][i]
                v1 = vertex_grid[j][i + 1]
                v2 = vertex_grid[j + 1][i + 1]
                v3 = vertex_grid[j + 1][i]
                # Counter-clockwise face
                pattern.add_face([v0, v1, v2, v3], material_tag="substrate")

        return pattern
