"""2D Crease pattern visualization with standard origami line styles.

Conventions:
- Mountain (M): Red line (solid or dashdot)
- Valley (V): Blue dashed line
- Boundary (B): Solid black line
- Facet (F): Thin gray line
"""

from __future__ import annotations
from typing import Any, Optional, Tuple

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.visualization.svg_crease import export_crease_svg


def plot_crease_pattern(
    pattern: CreasePattern,
    show_vertices: bool = True,
    show_vertex_labels: bool = False,
    show_faces: bool = True,
    figsize: Tuple[float, float] = (8.0, 6.0),
    title: Optional[str] = "Origami Crease Pattern",
    save_path: Optional[str] = None,
) -> Any:
    """Plot a 2D crease pattern.

    If Matplotlib is available, generates and returns (fig, ax).
    If Matplotlib DLLs are restricted by OS security policies, automatically
    exports pure-Python vector SVG.
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon

        fig, ax = plt.subplots(figsize=figsize)
        verts = pattern.vertices[:, :2]

        # 1. Draw faces with subtle shading
        if show_faces and pattern.num_faces > 0:
            for face in pattern.faces:
                poly_pts = verts[list(face.vertex_indices)]
                color = "#FFE0B2" if "conduct" in face.material_tag.lower() or "copper" in face.material_tag.lower() else "#E8EAF6"
                poly = Polygon(poly_pts, closed=True, facecolor=color, edgecolor="none", alpha=0.6)
                ax.add_patch(poly)

        # 2. Draw creases by type
        style_map = {
            CreaseType.BOUNDARY: {"color": "#212121", "linewidth": 2.0, "linestyle": "-", "label": "Boundary"},
            CreaseType.MOUNTAIN: {"color": "#D32F2F", "linewidth": 1.5, "linestyle": "-", "label": "Mountain (M)"},
            CreaseType.VALLEY: {"color": "#1976D2", "linewidth": 1.5, "linestyle": "--", "label": "Valley (V)"},
            CreaseType.FACET: {"color": "#9E9E9E", "linewidth": 0.8, "linestyle": ":", "label": "Facet seam"},
        }

        plotted_labels = set()

        for crease in pattern.creases:
            u_pt = verts[crease.u]
            v_pt = verts[crease.v]
            cfg = style_map.get(crease.crease_type, style_map[CreaseType.FACET])

            label = cfg["label"] if cfg["label"] not in plotted_labels else None
            if label:
                plotted_labels.add(cfg["label"])

            ax.plot(
                [u_pt[0], v_pt[0]],
                [u_pt[1], v_pt[1]],
                color=cfg["color"],
                linewidth=cfg["linewidth"],
                linestyle=cfg["linestyle"],
                label=label,
            )

        if show_vertices and len(verts) > 0:
            ax.scatter(verts[:, 0], verts[:, 1], color="#424242", s=20, zorder=5)

        if show_vertex_labels and len(verts) > 0:
            for idx, (x, y) in enumerate(verts):
                ax.annotate(str(idx), (x, y), textcoords="offset points", xytext=(3, 3), fontsize=8, color="#212121")

        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlabel("X (mm)", fontsize=10)
        ax.set_ylabel("Y (mm)", fontsize=10)
        if title:
            ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper right", framealpha=0.9)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig, ax

    except (ImportError, Exception):
        # Fallback to pure-Python SVG generator
        svg_path = save_path if (save_path and save_path.endswith(".svg")) else (save_path + ".svg" if save_path else None)
        return export_crease_svg(
            pattern,
            filepath=svg_path,
            show_faces=show_faces,
            show_vertices=show_vertices,
            show_labels=show_vertex_labels,
            title=title or "Origami Crease Pattern",
        )
