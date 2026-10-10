"""Parametric Waterbomb origami pattern generator.

Generates the classic Waterbomb base tessellation utilized in origami horn antennas,
expanding cylindrical shells, and reconfigurable deployable reflectors.
"""

from __future__ import annotations
from typing import Any, Optional

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.parameters import Parameter, ParameterSet, ParameterType
from rf_origami.patterns.base import BasePattern


class WaterbombPattern(BasePattern):
    """Parametric Waterbomb origami pattern generator."""

    name = "waterbomb"
    description = "Parametric Waterbomb base and tessellation"

    @classmethod
    def default_parameters(cls) -> ParameterSet:
        return ParameterSet([
            Parameter(
                name="cell_width",
                default=30.0,
                min_val=5.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Width of each waterbomb unit cell",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="cell_height",
                default=30.0,
                min_val=5.0,
                max_val=200.0,
                unit="mm",
                category="cell_dimensions",
                description="Height of each waterbomb unit cell",
                param_type=ParameterType.FLOAT,
            ),
            Parameter(
                name="num_cells_x",
                default=1,
                min_val=1,
                max_val=20,
                unit="",
                category="tessellation",
                description="Number of waterbomb cells along x",
                param_type=ParameterType.INT,
            ),
            Parameter(
                name="num_cells_y",
                default=1,
                min_val=1,
                max_val=20,
                unit="",
                category="tessellation",
                description="Number of waterbomb cells along y",
                param_type=ParameterType.INT,
            ),
        ])

    def generate(self, params: Optional[ParameterSet] = None, **kwargs: Any) -> CreasePattern:
        p = self.default_parameters() if params is None else params.copy()
        if kwargs:
            p.update(**kwargs)

        cw: float = float(p["cell_width"])
        ch: float = float(p["cell_height"])
        nx: int = int(p["num_cells_x"])
        ny: int = int(p["num_cells_y"])

        pattern = CreasePattern()

        # Vertex lookup by coordinate tuple (rounded to 6 decimals)
        v_cache = {}

        def get_or_add_v(x: float, y: float) -> int:
            key = (round(x, 6), round(y, 6))
            if key not in v_cache:
                v_cache[key] = pattern.add_vertex(x, y, 0.0)
            return v_cache[key]

        total_w = nx * cw
        total_h = ny * ch

        def is_outer_boundary(x1: float, y1: float, x2: float, y2: float) -> bool:
            # Check if edge lies along the boundary rectangle
            on_bottom = (abs(y1) < 1e-6 and abs(y2) < 1e-6)
            on_top = (abs(y1 - total_h) < 1e-6 and abs(y2 - total_h) < 1e-6)
            on_left = (abs(x1) < 1e-6 and abs(x2) < 1e-6)
            on_right = (abs(x1 - total_w) < 1e-6 and abs(x2 - total_w) < 1e-6)
            return on_bottom or on_top or on_left or on_right

        # Build each waterbomb cell
        for cy in range(ny):
            for cx in range(nx):
                x0, y0 = cx * cw, cy * ch
                x1, y1 = x0 + cw, y0 + ch
                xm, ym = x0 + cw / 2.0, y0 + ch / 2.0

                # 9 vertices per cell
                v_bl = get_or_add_v(x0, y0)
                v_br = get_or_add_v(x1, y0)
                v_tr = get_or_add_v(x1, y1)
                v_tl = get_or_add_v(x0, y1)

                v_bm = get_or_add_v(xm, y0)
                v_mr = get_or_add_v(x1, ym)
                v_tm = get_or_add_v(xm, y1)
                v_ml = get_or_add_v(x0, ym)

                v_c = get_or_add_v(xm, ym)

                # Boundary edges of unit cell (or internal boundary between cells)
                cell_boundary_edges = [
                    (v_bl, v_bm, x0, y0, xm, y0),
                    (v_bm, v_br, xm, y0, x1, y0),
                    (v_br, v_mr, x1, y0, x1, ym),
                    (v_mr, v_tr, x1, ym, x1, y1),
                    (v_tr, v_tm, x1, y1, xm, y1),
                    (v_tm, v_tl, xm, y1, x0, y1),
                    (v_tl, v_ml, x0, y1, x0, ym),
                    (v_ml, v_bl, x0, ym, x0, y0),
                ]

                for u, v, ex1, ey1, ex2, ey2 in cell_boundary_edges:
                    c_type = CreaseType.BOUNDARY if is_outer_boundary(ex1, ey1, ex2, ey2) else CreaseType.MOUNTAIN
                    pattern.add_crease(u, v, crease_type=c_type)

                # Internal diagonals from center (Mountain)
                pattern.add_crease(v_c, v_bl, crease_type=CreaseType.MOUNTAIN)
                pattern.add_crease(v_c, v_br, crease_type=CreaseType.MOUNTAIN)
                pattern.add_crease(v_c, v_tr, crease_type=CreaseType.MOUNTAIN)
                pattern.add_crease(v_c, v_tl, crease_type=CreaseType.MOUNTAIN)

                # Internal horizontal creases (Valley)
                pattern.add_crease(v_c, v_ml, crease_type=CreaseType.VALLEY)
                pattern.add_crease(v_c, v_mr, crease_type=CreaseType.VALLEY)

                # Internal vertical creases (Valley)
                pattern.add_crease(v_c, v_bm, crease_type=CreaseType.VALLEY)
                pattern.add_crease(v_c, v_tm, crease_type=CreaseType.VALLEY)

                # 8 triangular facets per unit cell
                pattern.add_face([v_c, v_bl, v_bm], material_tag="substrate")
                pattern.add_face([v_c, v_bm, v_br], material_tag="substrate")
                pattern.add_face([v_c, v_br, v_mr], material_tag="substrate")
                pattern.add_face([v_c, v_mr, v_tr], material_tag="substrate")
                pattern.add_face([v_c, v_tr, v_tm], material_tag="substrate")
                pattern.add_face([v_c, v_tm, v_tl], material_tag="substrate")
                pattern.add_face([v_c, v_tl, v_ml], material_tag="substrate")
                pattern.add_face([v_c, v_ml, v_bl], material_tag="substrate")

        return pattern
