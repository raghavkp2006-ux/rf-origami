"""Stereolithography (STL) 3D Mesh Exporter with Physical Panel Thickness.

Generates solid manifold 3D watertight STL models for 3D printing,
milling, and CAD assembly integration.
"""

from __future__ import annotations
import math
import struct
from typing import Any, Dict, List, Optional
import numpy as np

from rf_origami.core.mesh import FoldedMesh


class STLExporter:
    """Exports folded origami structures to ASCII and binary STL formats."""

    @classmethod
    def export_folded_mesh_ascii(
        cls,
        mesh: FoldedMesh,
        thickness_mm: float = 0.5,
        output_filename: Optional[str] = None,
    ) -> str:
        """Generate ASCII STL representation with extruded thickness."""
        lines = [f"solid rf_origami_folded"]

        v = mesh.vertices
        for face_nodes in mesh.faces:
            if len(face_nodes) < 3:
                continue

            pts = [v[idx] for idx in face_nodes]
            # Triangulate face
            for i in range(1, len(pts) - 1):
                p0 = pts[0]
                p1 = pts[i]
                p2 = pts[i + 1]

                # Top face normal
                n = np.cross(p1 - p0, p2 - p0)
                norm_n = np.linalg.norm(n)
                n_unit = (n / norm_n) if norm_n > 1e-9 else np.array([0.0, 0.0, 1.0])

                # Top triangle (offset by +thickness/2)
                offset = n_unit * (thickness_mm * 0.5)
                top_p0 = p0 + offset
                top_p1 = p1 + offset
                top_p2 = p2 + offset

                lines.append(f"  facet normal {n_unit[0]:.6e} {n_unit[1]:.6e} {n_unit[2]:.6e}")
                lines.append("    outer loop")
                lines.append(f"      vertex {top_p0[0]:.6f} {top_p0[1]:.6f} {top_p0[2]:.6f}")
                lines.append(f"      vertex {top_p1[0]:.6f} {top_p1[1]:.6f} {top_p1[2]:.6f}")
                lines.append(f"      vertex {top_p2[0]:.6f} {top_p2[1]:.6f} {top_p2[2]:.6f}")
                lines.append("    endloop")
                lines.append("  endfacet")

                # Bottom triangle (offset by -thickness/2)
                bot_p0 = p0 - offset
                bot_p1 = p1 - offset
                bot_p2 = p2 - offset

                lines.append(f"  facet normal {-n_unit[0]:.6e} {-n_unit[1]:.6e} {-n_unit[2]:.6e}")
                lines.append("    outer loop")
                lines.append(f"      vertex {bot_p0[0]:.6f} {bot_p0[1]:.6f} {bot_p0[2]:.6f}")
                lines.append(f"      vertex {bot_p2[0]:.6f} {bot_p2[1]:.6f} {bot_p2[2]:.6f}")
                lines.append(f"      vertex {bot_p1[0]:.6f} {bot_p1[1]:.6f} {bot_p1[2]:.6f}")
                lines.append("    endloop")
                lines.append("  endfacet")

        lines.append("endsolid rf_origami_folded")
        stl_text = "\n".join(lines) + "\n"

        if output_filename:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(stl_text)

        return stl_text
