"""Origami folding kinematics and 3D coordinate calculation.

Provides exact closed-form kinematic solvers for standard origami tessellations
(such as Miura-ori) and general rigid origami state evaluation.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple
import numpy as np

from rf_origami.core.mesh import FoldedMesh
from rf_origami.core.parameters import Parameter, ParameterSet, ParameterType
from rf_origami.patterns.miura_ori import MiuraOriPattern


class MiuraKinematics:
    """Exact, closed-form kinematic solver for Miura-ori 3D folding (Schenk & Guest 2013).

    Preserves facet isometry (edge lengths a and b, and facet sector angle gamma)
    to machine precision across all folding states theta in [0, pi/2).
    """

    def __init__(self, a: float = 20.0, b: float = 20.0, gamma_deg: float = 60.0) -> None:
        if a <= 0 or b <= 0:
            raise ValueError("Side lengths a and b must be positive.")
        if not (0.0 < gamma_deg < 90.0):
            raise ValueError("Sector angle gamma must be in (0, 90) degrees.")

        self.a = float(a)
        self.b = float(b)
        self.gamma_deg = float(gamma_deg)
        self.gamma_rad = math.radians(self.gamma_deg)

    @classmethod
    def default_parameters(cls) -> ParameterSet:
        pset = MiuraOriPattern.default_parameters()
        pset.add(
            Parameter(
                name="folding_ratio",
                default=0.3,
                min_val=0.0,
                max_val=0.98,
                unit="",
                category="folding_state",
                description="Folding progression parameter rho: 0 is flat, ~1 is fully folded",
                param_type=ParameterType.FLOAT,
            )
        )
        return pset

    def compute_cell_geometry(self, rho: float) -> Tuple[float, float, float, float]:
        """Compute the 3D unit-cell dimensions (S, V, L, H) for folding progression rho in [0, 1).

        In Schenk & Guest (2013):
        - theta is the dihedral angle between the facet and the xy plane:
          theta = 0 is flat state, theta -> pi/2 is fully folded state.
        - tan(xi) = cos(theta) * tan(gamma)
        - sin(psi) = sin(theta) * sin(gamma)
        - cos(gamma) = cos(xi) * cos(psi)
        - S = b * sin(xi)
        - V = b * cos(xi)
        - L = a * cos(psi)
        - H = a * sin(psi)

        Returns:
            (S, V, L, H)
        """
        rho = max(0.0, min(0.98, float(rho)))
        # Map rho in [0, 1) to facet inclination angle theta in [0, pi/2)
        theta_f = rho * (math.pi / 2.0)

        # Compute auxiliary angles
        tan_xi = math.cos(theta_f) * math.tan(self.gamma_rad)
        xi = math.atan(tan_xi)

        sin_psi = math.sin(theta_f) * math.sin(self.gamma_rad)
        sin_psi = max(-1.0, min(1.0, sin_psi))
        psi = math.asin(sin_psi)

        S = self.b * math.sin(xi)
        V = self.b * math.cos(xi)
        L = self.a * math.cos(psi)
        H = self.a * math.sin(psi)

        return S, V, L, H

    def fold(
        self,
        nx: int = 2,
        ny: int = 2,
        rho: float = 0.3
    ) -> FoldedMesh:
        """Calculate exact 3D coordinates for a folded Miura-ori sheet.

        Args:
            nx: Number of unit cells along x.
            ny: Number of unit cells along y.
            rho: Folding progression parameter in [0, 0.98].

        Returns:
            FoldedMesh instance containing 3D vertex coordinates, faces, and normals.
        """
        S, V, L, H = self.compute_cell_geometry(rho)

        num_cols = 2 * nx + 1
        num_rows = 2 * ny + 1

        vertices_list = []
        vertex_grid = []

        for j in range(num_rows):
            row = []
            # In periodic Miura-ori, rows alternate in height:
            # Row 0, 2, 4... are at z = 0; Row 1, 3, 5... are at z = H
            z = H if (j % 2 == 1) else 0.0

            for i in range(num_cols):
                x = i * S
                # The y-coordinate has base j * L, plus alternating V shift on odd columns
                y_shift = V if (i % 2 == 1) else 0.0
                y = j * L + y_shift

                idx = len(vertices_list)
                vertices_list.append([x, y, z])
                row.append(idx)
            vertex_grid.append(row)

        vertices_np = np.array(vertices_list, dtype=np.float64)

        # Build quad faces
        faces = []
        for j in range(num_rows - 1):
            for i in range(num_cols - 1):
                v0 = vertex_grid[j][i]
                v1 = vertex_grid[j][i + 1]
                v2 = vertex_grid[j + 1][i + 1]
                v3 = vertex_grid[j + 1][i]
                faces.append((v0, v1, v2, v3))

        return FoldedMesh(vertices=vertices_np, faces=faces)
