"""Pure-Python 3D Folded Geometry SVG & HTML Exporter.

Renders 3D folded origami meshes using axonometric projection with Painter's depth sorting
and Lambertian diffuse surface shading. Completely self-contained with zero DLL dependencies.
"""

from __future__ import annotations
import html
import math
from typing import Optional, Tuple
import numpy as np

from rf_origami.core.mesh import FoldedMesh


def export_folded_svg(
    mesh: FoldedMesh,
    filepath: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    margin: int = 50,
    azim_deg: float = -45.0,
    elev_deg: float = 30.0,
    title: str = "3D Folded Origami Geometry",
) -> str:
    """Render a 3D folded mesh to a pure vector SVG file with depth sorting and lighting.

    Args:
        mesh: FoldedMesh instance.
        filepath: Optional path to save the .svg file.
        width: Viewport width.
        height: Viewport height.
        margin: Padding in pixels.
        azim_deg: Azimuth view angle in degrees.
        elev_deg: Elevation view angle in degrees.
        title: Plot title.

    Returns:
        SVG content string.
    """
    if mesh.num_vertices == 0 or mesh.num_faces == 0:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'></svg>"

    verts = mesh.vertices
    azim = math.radians(azim_deg)
    elev = math.radians(elev_deg)

    # Center vertices at origin
    b_min, b_max = mesh.bounding_box()
    center = (b_min + b_max) / 2.0
    centered_verts = verts - center

    # 3D View rotation:
    # 1. Rotate by azim around Z
    cos_a, sin_a = math.cos(azim), math.sin(azim)
    rot_z = np.array([
        [cos_a, -sin_a, 0.0],
        [sin_a,  cos_a, 0.0],
        [0.0,    0.0,   1.0]
    ])
    # 2. Tilt by elev around X'
    cos_e, sin_e = math.cos(elev), math.sin(elev)
    rot_x = np.array([
        [1.0,   0.0,    0.0],
        [0.0,  cos_e, -sin_e],
        [0.0,  sin_e,  cos_e]
    ])

    view_rot = rot_x @ rot_z
    transformed = (view_rot @ centered_verts.T).T

    # Projected 2D coordinates: x_proj = transformed[:, 0], y_proj = transformed[:, 1]
    # Depth for Painter's algorithm: depth = transformed[:, 2] (larger depth drawn later)
    px = transformed[:, 0]
    py = transformed[:, 1]

    min_px, max_px = float(px.min()), float(px.max())
    min_py, max_py = float(py.min()), float(py.max())

    span_x = max(1e-6, max_px - min_px)
    span_y = max(1e-6, max_py - min_py)

    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    scale = min(avail_w / span_x, avail_h / span_y)

    mid_px = (min_px + max_px) / 2.0
    mid_py = (min_py + max_py) / 2.0

    def to_screen(i: int) -> Tuple[float, float]:
        sx = width / 2.0 + (px[i] - mid_px) * scale
        sy = height / 2.0 - (py[i] - mid_py) * scale
        return sx, sy

    # Light direction for diffuse shading (from top-front-right)
    light_dir = np.array([0.4, 0.4, 0.82], dtype=np.float64)
    light_dir /= np.linalg.norm(light_dir)

    face_normals = mesh.compute_face_normals()

    # Prepare polygon elements with average depth
    polygon_data = []
    for idx, face_v in enumerate(mesh.faces):
        avg_depth = float(np.mean(transformed[list(face_v), 2]))
        norm = face_normals[idx]
        intensity = max(0.35, min(1.0, float(abs(np.dot(norm, light_dir)))))

        # Base color
        mat = mesh.face_materials[idx] if idx < len(mesh.face_materials) else "substrate"
        if "conduct" in mat.lower() or "copper" in mat.lower():
            # Copper tones
            r = int(255 * intensity)
            g = int(160 * intensity)
            b = int(70 * intensity)
        else:
            # Substrate tones
            r = int(140 * intensity)
            g = int(190 * intensity)
            b = int(240 * intensity)

        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        pts_str = " ".join(f"{to_screen(v)[0]:.1f},{to_screen(v)[1]:.1f}" for v in face_v)
        polygon_data.append((avg_depth, pts_str, hex_color))

    # Sort from furthest (smallest depth) to closest (largest depth)
    polygon_data.sort(key=lambda item: item[0])

    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    svg_lines.append('<defs>')
    svg_lines.append('  <style>')
    svg_lines.append('    .title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 16px; font-weight: bold; fill: #212121; }')
    svg_lines.append('    .subtitle { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 11px; fill: #616161; }')
    svg_lines.append('    .face-poly { stroke: #263238; stroke-width: 0.8; stroke-linejoin: round; }')
    svg_lines.append('  </style>')
    svg_lines.append('</defs>')
    svg_lines.append(f'<rect width="{width}" height="{height}" fill="#ECEFF1" rx="8" />')

    dims = mesh.dimensions()
    sub_title = f"Dimensions: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm | Total Surface Area: {mesh.compute_total_surface_area():.1f} mm²"
    svg_lines.append(f'<text x="{margin}" y="{margin - 20}" class="title">{html.escape(title)}</text>')
    svg_lines.append(f'<text x="{margin}" y="{margin - 5}" class="subtitle">{html.escape(sub_title)}</text>')

    # Draw sorted polygons
    for _, pts_str, hex_color in polygon_data:
        svg_lines.append(f'<polygon points="{pts_str}" fill="{hex_color}" class="face-poly" />')

    svg_lines.append('</svg>')
    svg_content = "\n".join(svg_lines)

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)

    return svg_content
