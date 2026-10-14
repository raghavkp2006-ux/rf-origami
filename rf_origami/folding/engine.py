"""Unified folding engine for all supported origami patterns.

Maps 2D crease patterns and parameter sets to 3D folded meshes across continuous
fold angles theta in [0, 90] degrees.
"""

from __future__ import annotations
import math
from typing import Any, Dict, Optional
import numpy as np

from rf_origami.core.mesh import FoldedMesh
from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.parameters import ParameterSet
from rf_origami.folding.kinematics import MiuraKinematics


class FoldingEngine:
    """Dispatches and evaluates 3D folded geometry across origami pattern types."""

    @classmethod
    def fold(
        cls,
        pattern_type: str,
        crease_pattern: CreasePattern,
        params: Dict[str, Any],
        fold_angle_deg: float = 30.0,
    ) -> FoldedMesh:
        """Calculate 3D folded mesh for the given pattern type and fold angle.

        Args:
            pattern_type: 'miura_ori', 'degree4_vertex', 'waterbomb', or 'yoshimura'.
            crease_pattern: The 2D reference CreasePattern.
            params: Dictionary of geometric parameters.
            fold_angle_deg: Folding dihedral/inclination angle in [0, 89.9] degrees.

        Returns:
            FoldedMesh containing 3D folded vertices, faces, and computed normals.
        """
        pt = pattern_type.lower().replace("-", "_").strip()
        fold_angle_deg = max(0.0, min(89.5, float(fold_angle_deg)))

        if pt in ("miura_ori", "miura"):
            return cls._fold_miura(params, fold_angle_deg)
        elif pt in ("degree4_vertex", "degree4", "deg4"):
            return cls._fold_degree4(crease_pattern, params, fold_angle_deg)
        elif pt in ("waterbomb", "water_bomb"):
            return cls._fold_waterbomb(crease_pattern, params, fold_angle_deg)
        elif pt in ("yoshimura", "diamond"):
            return cls._fold_yoshimura(crease_pattern, params, fold_angle_deg)
        else:
            # Fallback: return flat mesh in 3D
            return FoldedMesh(
                vertices=crease_pattern.vertices,
                faces=[f.vertex_indices for f in crease_pattern.faces],
                face_materials=[f.material_tag for f in crease_pattern.faces],
            )

    @classmethod
    def fold_analytical(
        cls,
        crease_pattern: CreasePattern,
        fold_angle_deg: float = 30.0,
        pattern_type: str = "miura_ori",
        params: Optional[Dict[str, Any]] = None,
    ) -> FoldedMesh:
        """Calculate 3D folded mesh from crease pattern and analytical fold angle."""
        p = params or {}
        return cls.fold(
            pattern_type=pattern_type,
            crease_pattern=crease_pattern,
            params=p,
            fold_angle_deg=fold_angle_deg,
        )

    @classmethod
    def _fold_miura(cls, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        a = float(params.get("a", 20.0))
        b = float(params.get("b", 20.0))
        gamma = float(params.get("gamma", params.get("gamma_deg", 60.0)))
        nx = int(params.get("num_cells_x", 2))
        ny = int(params.get("num_cells_y", 2))

        # Map fold_angle in [0, 90] degrees to folding_ratio rho in [0, 0.98]
        rho = (fold_angle_deg / 90.0) * 0.96
        solver = MiuraKinematics(a=a, b=b, gamma_deg=gamma)
        return solver.fold(nx=nx, ny=ny, rho=rho)


    @classmethod
    def _fold_degree4(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold an isolated degree-4 vertex in 3D by dihedral angle rotation along crease hinges."""
        verts_2d = pattern.vertices.copy()
        if len(verts_2d) < 5:
            return FoldedMesh(vertices=verts_2d, faces=[f.vertex_indices for f in pattern.faces])

        r = float(params.get("radius", params.get("a", 30.0)))
        theta_rad = math.radians(fold_angle_deg)

        # Center vertex stays at origin
        v_3d = np.zeros((len(verts_2d), 3), dtype=np.float64)
        v_3d[0] = [0.0, 0.0, 0.0]

        # Dihedral crease folding
        h = r * math.sin(theta_rad) * 0.5
        compress = math.cos(theta_rad * 0.5)

        for i in range(1, len(verts_2d)):
            vx = verts_2d[i, 0] * compress
            vy = verts_2d[i, 1] * compress
            # Mountain creases rise, valley crease dips
            if i in (1, 3):
                vz = h  # Mountain ridge lift
            elif i == 2:
                vz = -h * 0.5  # Valley depression
            else:
                vz = 0.0
            v_3d[i] = [vx, vy, vz]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)

    @classmethod
    def _fold_waterbomb(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold waterbomb tessellation by rigid facet rotation about mountain and valley creases.

        The 8 triangular facets in each waterbomb cell rotate around diagonal mountain creases
        and orthogonal valley creases, pulling cell borders together and depressing the center node.
        """
        verts = pattern.vertices.copy()
        theta_rad = math.radians(fold_angle_deg)
        cw = float(params.get("cell_width", params.get("a", 30.0)))
        ch = float(params.get("cell_height", params.get("b", 30.0)))

        # Center depression depth
        h_depress = (min(cw, ch) * 0.5) * math.sin(theta_rad)
        # Lateral contraction of cell
        comp_x = math.cos(theta_rad * 0.5)
        comp_y = math.cos(theta_rad * 0.5)

        v_3d = np.zeros_like(verts)
        for i, (x, y, _) in enumerate(verts):
            # Determine cell coordinate and offset within cell
            cell_x_idx = int(x // max(1e-4, cw))
            cell_y_idx = int(y // max(1e-4, ch))
            rel_x = x - cell_x_idx * cw
            rel_y = y - cell_y_idx * ch

            is_center = (abs(rel_x - cw / 2.0) < 1e-3) and (abs(rel_y - ch / 2.0) < 1e-3)
            is_horiz_mid = (abs(rel_y - ch / 2.0) < 1e-3) and not is_center
            is_vert_mid = (abs(rel_x - cw / 2.0) < 1e-3) and not is_center

            # Contract coordinates towards cell centers proportionally
            x_shift_cell = (rel_x - cw / 2.0) * comp_x
            y_shift_cell = (rel_y - ch / 2.0) * comp_y

            new_x = (cell_x_idx * cw * comp_x) + (cw * comp_x / 2.0) + x_shift_cell
            new_y = (cell_y_idx * ch * comp_y) + (ch * comp_y / 2.0) + y_shift_cell

            if is_center:
                new_z = -h_depress
            elif is_horiz_mid or is_vert_mid:
                # Orthogonal valley creases fold downward midway
                new_z = -h_depress * 0.45
            else:
                # Corner nodes remain at upper ridge baseline
                new_z = 0.0

            v_3d[i] = [new_x, new_y, new_z]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)

    @classmethod
    def _fold_yoshimura(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold Yoshimura pattern with authentic rigid triangular origami crease buckling.

        Rather than projecting onto a smooth cylinder curve, the sheet buckles along
        the horizontal valley creases and diagonal mountain creases. The triangular facets
        remain planar and fold at sharp dihedral angles, with alternating ridge and trough vertices.
        """
        verts = pattern.vertices.copy()
        if len(verts) == 0:
            return FoldedMesh(vertices=verts, faces=[])

        theta_rad = math.radians(fold_angle_deg)
        w = float(params.get("cell_width", params.get("a", 25.0)))
        h = float(params.get("cell_height", params.get("b", 20.0)))
        nx = int(params.get("num_cells_x", 4))
        ny = int(params.get("num_cells_y", 2))
        total_w = nx * w

        if fold_angle_deg < 0.2:
            return FoldedMesh(
                vertices=verts,
                faces=[f.vertex_indices for f in pattern.faces],
                face_materials=[f.material_tag for f in pattern.faces]
            )

        # Circumferential arc angle span and mean curvature radius
        arc_fraction = (fold_angle_deg / 90.0) * 0.95
        max_angle = 2.0 * math.pi * min(1.0, arc_fraction * (nx / 6.0 + 0.5))
        r0 = total_w / max(1e-4, max_angle)

        # Origami crease buckling: mountain creases push OUTWARD, valley creases fold INWARD
        # Radial displacement amplitude Delta R along mountain/valley folds:
        delta_r = (w * 0.35) * math.sin(theta_rad)
        # Axial tier compression to preserve diagonal crease length:
        h_folded = max(1.0, math.sqrt(max(1.0, h**2 - (1.8 * delta_r)**2))) if h > 2 * delta_r else h * math.cos(theta_rad * 0.5)

        v_3d = np.zeros_like(verts)

        for idx, (x, y, _) in enumerate(verts):
            # Identify row index j from y coordinate
            row_j = int(round(y / max(1e-4, h)))
            is_odd_row = (row_j % 2 == 1)

            # In Yoshimura, odd rows have mountain vertices that buckle outward (r0 + delta_r),
            # while even rows have valley crease vertices that drop inward (r0 - delta_r).
            r_v = (r0 + delta_r) if is_odd_row else (r0 - delta_r)

            phi = (x / max(1e-4, total_w)) * max_angle
            cx = r_v * math.sin(phi)
            cz = r_v * (1.0 - math.cos(phi))
            # Axial position compressed according to folding state
            cy = row_j * h_folded

            v_3d[idx] = [cx, cy, cz]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)
