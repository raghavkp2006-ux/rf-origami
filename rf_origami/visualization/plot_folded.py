"""3D Folded geometry visualization using Matplotlib 3D or pure-Python SVG fallback."""

from __future__ import annotations
from typing import Any, Optional, Tuple

from rf_origami.core.mesh import FoldedMesh
from rf_origami.visualization.svg_folded import export_folded_svg


def plot_folded_mesh(
    mesh: FoldedMesh,
    show_edges: bool = True,
    show_vertices: bool = False,
    figsize: Tuple[float, float] = (9.0, 7.0),
    title: Optional[str] = "3D Folded Origami Geometry",
    save_path: Optional[str] = None,
    elev: float = 30.0,
    azim: float = -60.0,
) -> Any:
    """Render 3D folded origami geometry.

    Uses Matplotlib 3D if available, and gracefully falls back to pure-Python
    vector SVG if C-extension DLLs are restricted by the OS environment.
    """
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import numpy as np

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection="3d")

        verts = mesh.vertices
        poly_list = []
        face_colors = []

        for idx, face_v in enumerate(mesh.faces):
            face_pts = verts[list(face_v)]
            poly_list.append(face_pts)

            mat = mesh.face_materials[idx] if idx < len(mesh.face_materials) else "substrate"
            if "conduct" in mat.lower() or "copper" in mat.lower():
                face_colors.append("#FFB74D")
            else:
                face_colors.append("#90CAF9")

        edge_color = "#212121" if show_edges else "none"
        poly_collection = Poly3DCollection(
            poly_list,
            facecolors=face_colors,
            edgecolors=edge_color,
            linewidths=1.0,
            alpha=0.85,
        )
        ax.add_collection3d(poly_collection)

        if show_vertices:
            ax.scatter(verts[:, 0], verts[:, 1], verts[:, 2], color="#D32F2F", s=25, zorder=10)

        b_min, b_max = mesh.bounding_box()
        max_range = max(b_max - b_min)
        if max_range < 1e-6:
            max_range = 1.0

        mid = (b_max + b_min) / 2.0
        ax.set_xlim(mid[0] - max_range / 2.0, mid[0] + max_range / 2.0)
        ax.set_ylim(mid[1] - max_range / 2.0, mid[1] + max_range / 2.0)
        ax.set_zlim(mid[2] - max_range / 2.0, mid[2] + max_range / 2.0)

        ax.set_xlabel("X (mm)", fontsize=10)
        ax.set_ylabel("Y (mm)", fontsize=10)
        ax.set_zlabel("Z (mm)", fontsize=10)
        ax.view_init(elev=elev, azim=azim)

        if title:
            dims = mesh.dimensions()
            ax.set_title(
                f"{title}\nSize: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm | Area: {mesh.compute_total_surface_area():.1f} mm²",
                fontsize=11,
                fontweight="bold"
            )

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig, ax

    except (ImportError, Exception):
        # Fallback to pure-Python vector SVG
        svg_path = save_path if (save_path and save_path.endswith(".svg")) else (save_path + ".svg" if save_path else None)
        return export_folded_svg(
            mesh,
            filepath=svg_path,
            azim_deg=azim,
            elev_deg=elev,
            title=title or "3D Folded Origami Geometry",
        )
