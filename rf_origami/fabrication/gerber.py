"""RS-274X Extended Gerber File Exporter for Origami Metasurface Circuit Fabrication.

Generates industry-standard printed circuit board (PCB) lithography files:
  - Top Conductor Layer (.GBR / .GTL)
  - Bottom Ground Layer (.GBR / .GBL)
  - Solder Mask / Coverlay (.GTS)
"""

from __future__ import annotations
import datetime
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.mesh import FoldedMesh


class GerberExporter:
    """Exports 2D uncreased/folded origami conductor geometry to RS-274X Gerber format."""

    @classmethod
    def export_top_copper(
        cls,
        pattern: CreasePattern,
        output_filename: Optional[str] = None,
        scale: float = 1.0,
    ) -> str:
        """Generate RS-274X Gerber format string for the top metallization layer."""
        header = [
            "G04 RF Origami Forge Top Copper Layer*",
            f"G04 Generated: {datetime.datetime.now().isoformat()}*",
            "%FSLAX34Y34*%",          # Format statement: absolute, 3.4 decimal
            "%MOMM*%",                 # Metric millimeters
            "%LPD*%",                  # Layer polarity dark
            "%ADD10C,0.2000*%",        # Aperture D10: 0.2mm round tool
            "%ADD11R,1.000X1.000*%",   # Aperture D11: 1.0mm rectangle
            "G01*",                    # Linear interpolation
            "D10*",                    # Select tool D10
        ]

        commands = list(header)

        # Draw outer perimeter and metallized facets
        for face in pattern.faces:
            face_nodes = face.vertex_indices if hasattr(face, "vertex_indices") else face
            pts = [pattern.vertices[v] for v in face_nodes]
            if len(pts) < 3:
                continue


            # Move to first point
            x0 = int(round(pts[0][0] * scale * 10000))
            y0 = int(round(pts[0][1] * scale * 10000))
            commands.append(f"X{x0:+08d}Y{y0:+08d}D02*")

            # Draw lines around the polygon
            for p in pts[1:]:
                x = int(round(p[0] * scale * 10000))
                y = int(round(p[1] * scale * 10000))
                commands.append(f"X{x:+08d}Y{y:+08d}D01*")

            # Close polygon
            commands.append(f"X{x0:+08d}Y{y0:+08d}D01*")

        commands.append("M02*")  # End of program
        gerber_code = "\n".join(commands) + "\n"

        if output_filename:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(gerber_code)

        return gerber_code

    @classmethod
    def export_ground_plane(
        cls,
        pattern: CreasePattern,
        output_filename: Optional[str] = None,
        scale: float = 1.0,
    ) -> str:
        """Generate RS-274X Gerber format string for solid bottom ground plane."""
        min_xyz, max_xyz = pattern.bounding_box()
        min_x, min_y = float(min_xyz[0]), float(min_xyz[1])
        max_x, max_y = float(max_xyz[0]), float(max_xyz[1])

        x0 = int(round(min_x * scale * 10000))
        y0 = int(round(min_y * scale * 10000))
        x1 = int(round(max_x * scale * 10000))
        y1 = int(round(max_y * scale * 10000))


        lines = [
            "G04 RF Origami Forge Bottom Ground Layer*",
            f"G04 Generated: {datetime.datetime.now().isoformat()}*",
            "%FSLAX34Y34*%",
            "%MOMM*%",
            "%LPD*%",
            "%ADD10C,0.2000*%",
            "G01*",
            "D10*",
            # Filled region
            "G36*",
            f"X{x0:+08d}Y{y0:+08d}D02*",
            f"X{x1:+08d}Y{y0:+08d}D01*",
            f"X{x1:+08d}Y{y1:+08d}D01*",
            f"X{x0:+08d}Y{y1:+08d}D01*",
            f"X{x0:+08d}Y{y0:+08d}D01*",
            "G37*",
            "M02*",
        ]

        gerber_code = "\n".join(lines) + "\n"

        if output_filename:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(gerber_code)

        return gerber_code
