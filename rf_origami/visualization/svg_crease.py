"""Pure-Python SVG Crease Pattern Exporter & Visualizer.

Generates high-precision, resolution-independent vector SVG graphics for 2D crease patterns
with zero external C-extension or DLL dependencies (guaranteed compatibility on all systems).
"""

from __future__ import annotations
import html
from typing import Optional

from rf_origami.core.crease_pattern import CreasePattern, CreaseType


def export_crease_svg(
    pattern: CreasePattern,
    filepath: Optional[str] = None,
    width: int = 800,
    height: int = 600,
    margin: int = 40,
    show_faces: bool = True,
    show_vertices: bool = True,
    show_labels: bool = False,
    title: str = "RF Origami Crease Pattern",
) -> str:
    """Generate a clean vector SVG representation of an origami crease pattern.

    Args:
        pattern: CreasePattern instance.
        filepath: Optional path to save the .svg file.
        width: Output SVG viewport width in pixels.
        height: Output SVG viewport height in pixels.
        margin: Padding around the pattern.
        show_faces: Whether to fill facets with material shading.
        show_vertices: Whether to draw circle nodes at vertices.
        show_labels: Whether to print vertex index numbers.
        title: Chart title text.

    Returns:
        SVG content string.
    """
    if pattern.num_vertices == 0:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'></svg>"

    verts = pattern.vertices[:, :2]
    min_x, min_y = float(verts[:, 0].min()), float(verts[:, 1].min())
    max_x, max_y = float(verts[:, 0].max()), float(verts[:, 1].max())

    dx = max(1e-6, max_x - min_x)
    dy = max(1e-6, max_y - min_y)

    # Compute scale to fit in (width - 2*margin, height - 2*margin) keeping aspect ratio
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    scale = min(avail_w / dx, avail_h / dy)

    # Offset to center pattern
    offset_x = margin + (avail_w - dx * scale) / 2.0
    offset_y = margin + (avail_h - dy * scale) / 2.0

    def to_svg(x: float, y: float) -> tuple[float, float]:
        # SVG y-axis points downward, so invert y
        sx = offset_x + (x - min_x) * scale
        sy = height - (offset_y + (y - min_y) * scale)
        return sx, sy

    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    svg_lines.append('<defs>')
    svg_lines.append('  <style>')
    svg_lines.append('    .title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 16px; font-weight: bold; fill: #212121; }')
    svg_lines.append('    .legend { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 12px; fill: #424242; }')
    svg_lines.append('    .vlabel { font-family: monospace; font-size: 9px; fill: #616161; }')
    svg_lines.append('    .boundary { stroke: #212121; stroke-width: 2.5; stroke-linecap: round; }')
    svg_lines.append('    .mountain { stroke: #D32F2F; stroke-width: 2.0; stroke-linecap: round; }')
    svg_lines.append('    .valley { stroke: #1976D2; stroke-width: 2.0; stroke-dasharray: 6,4; stroke-linecap: round; }')
    svg_lines.append('    .facet { stroke: #BDBDBD; stroke-width: 1.0; stroke-dasharray: 2,2; }')
    svg_lines.append('  </style>')
    svg_lines.append('</defs>')
    svg_lines.append(f'<rect width="{width}" height="{height}" fill="#FAFAFA" rx="8" />')

    # Title
    svg_lines.append(f'<text x="{margin}" y="{margin - 15}" class="title">{html.escape(title)}</text>')

    # 1. Shaded faces
    if show_faces:
        svg_lines.append('<!-- Faces -->')
        for face in pattern.faces:
            pts_str = " ".join(f"{to_svg(verts[idx][0], verts[idx][1])[0]:.2f},{to_svg(verts[idx][0], verts[idx][1])[1]:.2f}" for idx in face.vertex_indices)
            fill_color = "#FFE082" if "conduct" in face.material_tag.lower() or "copper" in face.material_tag.lower() else "#E1F5FE"
            svg_lines.append(f'<polygon points="{pts_str}" fill="{fill_color}" fill-opacity="0.6" />')

    # 2. Crease lines
    svg_lines.append('<!-- Creases -->')
    for crease in pattern.creases:
        x1, y1 = to_svg(verts[crease.u][0], verts[crease.u][1])
        x2, y2 = to_svg(verts[crease.v][0], verts[crease.v][1])

        if crease.crease_type == CreaseType.BOUNDARY:
            cls_name = "boundary"
        elif crease.crease_type == CreaseType.MOUNTAIN:
            cls_name = "mountain"
        elif crease.crease_type == CreaseType.VALLEY:
            cls_name = "valley"
        else:
            cls_name = "facet"

        svg_lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="{cls_name}" />')

    # 3. Vertices
    if show_vertices:
        svg_lines.append('<!-- Vertices -->')
        for idx in range(pattern.num_vertices):
            vx, vy = to_svg(verts[idx][0], verts[idx][1])
            svg_lines.append(f'<circle cx="{vx:.2f}" cy="{vy:.2f}" r="3.5" fill="#37474F" />')
            if show_labels:
                svg_lines.append(f'<text x="{vx + 5:.2f}" y="{vy - 5:.2f}" class="vlabel">{idx}</text>')

    # 4. Legend
    leg_x = width - 180
    leg_y = margin - 15
    svg_lines.append(f'<g transform="translate({leg_x}, {leg_y})">')
    svg_lines.append('  <line x1="0" y1="0" x2="25" y2="0" class="mountain" />')
    svg_lines.append('  <text x="32" y="4" class="legend">Mountain (M)</text>')
    svg_lines.append('  <line x1="0" y1="16" x2="25" y2="16" class="valley" />')
    svg_lines.append('  <text x="32" y="20" class="legend">Valley (V)</text>')
    svg_lines.append('  <line x1="0" y1="32" x2="25" y2="32" class="boundary" />')
    svg_lines.append('  <text x="32" y="36" class="legend">Boundary</text>')
    svg_lines.append('</g>')

    svg_lines.append('</svg>')
    svg_content = "\n".join(svg_lines)

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)

    return svg_content
