"""Parametric Yoshimura (diamond/triangular) origami pattern generator.

Widely utilized in foldable cylindrical antennas, conical horns, and deployable mast reflectors.
"""

from __future__ import annotations
from typing import Any, Optional

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.parameters import Parameter, ParameterSet, ParameterType
from rf_origami.patterns.base import BasePattern


class YoshimuraPattern(BasePattern):
    """Parametric Yoshimura triangular origami pattern generator."""

    name = "yoshimura"
    description = "Parametric Yoshimura triangular/diamond cylinder pattern"

    @classmethod
    def default_parameters(cls) -> ParameterSet:
        return ParameterSet([
            Parameter(
                name="cell_width",
                default=25.0,
                min_val=5.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Width of each triangular unit cell",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="cell_height",
                default=20.0,
                min_val=5.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Axial height of each tier",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="num_cells_x",
                default=4,
                min_val=2,
                max_val=30,
                unit="",
                category="tessellation",
                description="Number of circumferential divisions (columns)",
                param_type=ParameterType.INT,
            ),
            Parameter(
                name="num_cells_y",
                default=2,
                min_val=1,
                max_val=30,
                unit="",
                category="tessellation",
                description="Number of axial tiers (rows)",
                param_type=ParameterType.INT,
            ),
        ])

    def generate(self, params: Optional[ParameterSet] = None, **kwargs: Any) -> CreasePattern:
        p = self.default_parameters() if params is None else params.copy()
        if kwargs:
            p.update(**kwargs)

        w: float = float(p["cell_width"])
        h: float = float(p["cell_height"])
        nx: int = int(p["num_cells_x"])
        ny: int = int(p["num_cells_y"])

        pattern = CreasePattern()
        num_rows = ny + 1
        half_w = w / 2.0

        # Build vertices: alternating staggered rows
        vertex_grid = []
        for j in range(num_rows):
            row = []
            y = j * h
            shift = half_w if (j % 2 == 1) else 0.0
            # Rows alternate between nx+1 and nx vertices
            count = nx if (j % 2 == 1) else (nx + 1)
            for i in range(count):
                x = i * w + shift
                v_idx = pattern.add_vertex(x, y, 0.0)
                row.append(v_idx)
            vertex_grid.append(row)

        # Horizontal Creases
        for j in range(num_rows):
            is_outer = (j == 0 or j == num_rows - 1)
            c_type = CreaseType.BOUNDARY if is_outer else CreaseType.VALLEY
            row = vertex_grid[j]
            for i in range(len(row) - 1):
                pattern.add_crease(row[i], row[i + 1], crease_type=c_type)

        # Diagonal Mountain Creases & Triangular Faces
        for j in range(ny):
            curr_row = vertex_grid[j]
            next_row = vertex_grid[j + 1]

            if j % 2 == 0:
                # Even row (nx+1 vertices) to odd row (nx vertices)
                for i in range(nx):
                    v_bl = curr_row[i]
                    v_br = curr_row[i + 1]
                    v_top = next_row[i]

                    # Upward pointing triangle
                    pattern.add_crease(v_bl, v_top, crease_type=CreaseType.MOUNTAIN)
                    pattern.add_crease(v_br, v_top, crease_type=CreaseType.MOUNTAIN)
                    pattern.add_face([v_bl, v_br, v_top], material_tag="substrate")

                    # Downward pointing triangle (if next top exists)
                    if i < nx - 1:
                        v_top_next = next_row[i + 1]
                        pattern.add_face([v_top, v_br, v_top_next], material_tag="substrate")
            else:
                # Odd row (nx vertices) to even row (nx+1 vertices)
                for i in range(nx):
                    v_bot = curr_row[i]
                    v_tl = next_row[i]
                    v_tr = next_row[i + 1]

                    pattern.add_crease(v_bot, v_tl, crease_type=CreaseType.MOUNTAIN)
                    pattern.add_crease(v_bot, v_tr, crease_type=CreaseType.MOUNTAIN)
                    pattern.add_face([v_bot, v_tr, v_tl], material_tag="substrate")

                    if i < nx - 1:
                        v_bot_next = curr_row[i + 1]
                        pattern.add_face([v_bot, v_bot_next, v_tr], material_tag="substrate")

        # Mark left and right boundaries as BOUNDARY
        for j in range(num_rows - 1):
            v_l1 = vertex_grid[j][0]
            v_l2 = vertex_grid[j + 1][0]
            c_left = pattern.get_crease(v_l1, v_l2)
            if c_left:
                c_left.crease_type = CreaseType.BOUNDARY

            v_r1 = vertex_grid[j][-1]
            v_r2 = vertex_grid[j + 1][-1]
            c_right = pattern.get_crease(v_r1, v_r2)
            if c_right:
                c_right.crease_type = CreaseType.BOUNDARY

        return pattern
