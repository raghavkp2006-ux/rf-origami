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
    def _fold_miura(cls, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        a = float(params.get("a", 20.0))
        b = float(params.get("b", 20.0))
        gamma = float(params.get("gamma", 60.0))
        nx = int(params.get("num_cells_x", 2))
        ny = int(params.get("num_cells_y", 2))

        # Map fold_angle in [0, 90] degrees to folding_ratio rho in [0, 0.98]
        rho = (fold_angle_deg / 90.0) * 0.96
        solver = MiuraKinematics(a=a, b=b, gamma_deg=gamma)
        return solver.fold(nx=nx, ny=ny, rho=rho)

    @classmethod
    def _fold_degree4(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold an isolated degree-4 vertex in 3D by dihedral angle rotation."""
        verts_2d = pattern.vertices.copy()
        if len(verts_2d) < 5:
            return FoldedMesh(vertices=verts_2d, faces=[f.vertex_indices for f in pattern.faces])

        r = float(params.get("radius", 30.0))
        a1 = float(params.get("alpha1", 70.0))
        theta_rad = math.radians(fold_angle_deg)

        # Center vertex stays at origin
        # The 4 surrounding vertices rotate out of plane:
        # Mountain folds rise, valley fold drops
        v_3d = np.zeros((len(verts_2d), 3), dtype=np.float64)
        v_3d[0] = [0.0, 0.0, 0.0]

        # Calculate height depression of center or wing lift
        h = r * math.sin(theta_rad / 2.0) * 0.7
        compress = math.cos(theta_rad / 2.0)

        for i in range(1, 5):
            x2 = verts_2d[i, 0] * compress
            y2 = verts_2d[i, 1] * compress
            # Odd outer vertices lift up, even stay at baseline
            z = h if (i % 2 == 1) else 0.0
            v_3d[i] = [x2, y2, z]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)

    @classmethod
    def _fold_waterbomb(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold waterbomb tessellation by depressing central vertices."""
        verts = pattern.vertices.copy()
        theta_rad = math.radians(fold_angle_deg)
        cw = float(params.get("cell_width", 30.0))
        ch = float(params.get("cell_height", 30.0))

        # Vertical depression of center vertices
        h = (cw / 2.0) * math.sin(theta_rad) * 0.8
        compress_x = 1.0 - (1.0 - math.cos(theta_rad)) * 0.4

        v_3d = np.zeros_like(verts)
        for i, (x, y, _) in enumerate(verts):
            # Check if vertex is a cell center (odd multiples of cw/2 and ch/2)
            rem_x = (x % cw)
            rem_y = (y % ch)
            is_center = (abs(rem_x - cw / 2.0) < 1e-4) and (abs(rem_y - ch / 2.0) < 1e-4)
            is_horizontal_mid = (abs(rem_y - ch / 2.0) < 1e-4) and not is_center

            new_x = x * compress_x
            new_y = y
            if is_center:
                new_z = -h
            elif is_horizontal_mid:
                new_z = h * 0.3
            else:
                new_z = 0.0

            v_3d[i] = [new_x, new_y, new_z]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)

    @classmethod
    def _fold_yoshimura(cls, pattern: CreasePattern, params: Dict[str, Any], fold_angle_deg: float) -> FoldedMesh:
        """Fold Yoshimura pattern by curving into a cylindrical polygon arc."""
        verts = pattern.vertices.copy()
        if len(verts) == 0:
            return FoldedMesh(vertices=verts, faces=[])

        theta_rad = math.radians(fold_angle_deg)
        w = float(params.get("cell_width", 25.0))
        nx = int(params.get("num_cells_x", 4))
        total_w = nx * w

        # When fold angle increases, sheet curves around a cylinder of radius R
        # Arc angle span: phi_total = total_w / R
        if fold_angle_deg < 0.5:
            # Nearly flat
            return FoldedMesh(
                vertices=verts,
                faces=[f.vertex_indices for f in pattern.faces],
                face_materials=[f.material_tag for f in pattern.faces]
            )

        # Arc span increases with fold angle (up to 2*pi for complete cylinder)
        arc_fraction = (fold_angle_deg / 90.0) * 0.95
        max_angle = 2.0 * math.pi * min(1.0, arc_fraction * (nx / 6.0 + 0.5))
        radius = total_w / max(1e-4, max_angle)

        v_3d = np.zeros_like(verts)
        for idx, (x, y, _) in enumerate(verts):
            frac = x / max(1e-4, total_w)
            phi = frac * max_angle
            # Folded into cylinder along Y
            cx = radius * math.sin(phi)
            cz = radius * (1.0 - math.cos(phi))
            v_3d[idx] = [cx, y, cz]

        faces = [f.vertex_indices for f in pattern.faces]
        mats = [f.material_tag for f in pattern.faces]
        return FoldedMesh(vertices=v_3d, faces=faces, face_materials=mats)
