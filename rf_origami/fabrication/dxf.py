"""AutoCAD DXF Exporter for Laser Cutting and CNC Routing of Origami Substrates.

Separates geometry into standardized CAD layers:
  - MOUNTAIN_CREASE: Red (Color 1), Dashed score cut
  - VALLEY_CREASE:   Blue (Color 5), Dash-dot score cut
  - SUBSTRATE_CUT:   Green (Color 3), Full through-cut
  - COPPER_TRACES:   Yellow (Color 2), Conductor mask
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern, CreaseType


class DXFExporter:
    """Exports CreasePattern to standard AutoCAD R12 / R2000 compliant DXF format."""

    @classmethod
    def export_crease_pattern(
        cls,
        pattern: CreasePattern,
        output_filename: Optional[str] = None,
    ) -> str:
        """Generate complete DXF file text with layered lines."""
        header = [
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER",
            "1", "AC1009",  # AutoCAD R12 ASCII compatibility
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "TABLES",
            "0", "TABLE",
            "2", "LAYER",
            # Layer: MOUNTAIN (Red = 1)
            "0", "LAYER", "2", "MOUNTAIN_CREASE", "70", "0", "62", "1", "6", "DASHED",
            # Layer: VALLEY (Blue = 5)
            "0", "LAYER", "2", "VALLEY_CREASE", "70", "0", "62", "5", "6", "DASHDOT",
            # Layer: BOUNDARY (Green = 3)
            "0", "LAYER", "2", "SUBSTRATE_CUT", "70", "0", "62", "3", "6", "CONTINUOUS",
            # Layer: COPPER (Yellow = 2)
            "0", "LAYER", "2", "COPPER_TRACES", "70", "0", "62", "2", "6", "CONTINUOUS",
            "0", "ENDTAB",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "ENTITIES",
        ]

        entities = list(header)

        for edge in pattern.creases:
            p1 = pattern.vertices[edge.u]
            p2 = pattern.vertices[edge.v]


            if edge.crease_type == CreaseType.MOUNTAIN:
                layer = "MOUNTAIN_CREASE"
            elif edge.crease_type == CreaseType.VALLEY:
                layer = "VALLEY_CREASE"
            elif edge.crease_type == CreaseType.BOUNDARY:
                layer = "SUBSTRATE_CUT"
            else:
                layer = "COPPER_TRACES"

            entities.extend([
                "0", "LINE",
                "8", layer,
                "10", f"{p1[0]:.4f}",  # X1
                "20", f"{p1[1]:.4f}",  # Y1
                "30", "0.0000",        # Z1
                "11", f"{p2[0]:.4f}",  # X2
                "21", f"{p2[1]:.4f}",  # Y2
                "31", "0.0000",        # Z2
            ])

        entities.extend([
            "0", "ENDSEC",
            "0", "EOF",
        ])

        dxf_text = "\n".join(entities) + "\n"

        if output_filename:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(dxf_text)

        return dxf_text
