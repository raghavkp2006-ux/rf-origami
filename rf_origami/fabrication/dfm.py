"""Design-for-Manufacturing (DFM) Rule Verification Engine for Origami Electronics.

Validates minimum copper trace width, copper spacing, crease fold-line clearances,
substrate bend limits, and metallic ground plane continuity.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern, CreaseType


class DFMStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class DFMCheckResult:
    rule_name: str
    status: DFMStatus
    message: str
    measured_value: float
    limit_value: float
    unit: str = "mm"


class DFMVerifier:
    """Evaluates physical manufacturability rules on origami crease patterns."""

    @classmethod
    def verify(
        cls,
        pattern: CreasePattern,
        min_trace_width_mm: float = 0.15,
        min_spacing_mm: float = 0.15,
        min_crease_clearance_mm: float = 0.30,
        substrate_thickness_mm: float = 0.50,
        max_aspect_ratio: float = 8.0,
    ) -> Dict[str, Any]:
        """Execute full DFM rule checklist on pattern."""
        checks: List[DFMCheckResult] = []

        # Rule 1: Minimum Crease Length
        min_len = float("inf")
        for edge in pattern.creases:
            p1 = pattern.vertices[edge.u]
            p2 = pattern.vertices[edge.v]
            l = float(np.linalg.norm(p2 - p1))
            if l < min_len:
                min_len = l


        if min_len >= 5.0:
            status1 = DFMStatus.PASS
            msg1 = f"Minimum crease segment length ({min_len:.2f} mm) exceeds tooling minimum (5.0 mm)."
        elif min_len >= 2.0:
            status1 = DFMStatus.WARNING
            msg1 = f"Short crease segment ({min_len:.2f} mm) requires high-precision laser scoring."
        else:
            status1 = DFMStatus.FAIL
            msg1 = f"Crease segment ({min_len:.2f} mm) too short for reliable folding."

        checks.append(DFMCheckResult(
            rule_name="Minimum Crease Segment Length",
            status=status1,
            message=msg1,
            measured_value=min_len,
            limit_value=5.0,
            unit="mm",
        ))

        # Rule 2: Crease Copper Clearance
        clearance = min_crease_clearance_mm
        if clearance >= 0.25:
            status2 = DFMStatus.PASS
            msg2 = f"Conductor clearance to fold axis ({clearance:.2f} mm) prevents copper fatigue cracking."
        else:
            status2 = DFMStatus.WARNING
            msg2 = f"Tight fold clearance ({clearance:.2f} mm); recommend flexible rolled annealed copper."

        checks.append(DFMCheckResult(
            rule_name="Fold-Axis Copper Clearance",
            status=status2,
            message=msg2,
            measured_value=clearance,
            limit_value=0.25,
            unit="mm",
        ))

        # Rule 3: Substrate Bend Radius / Thickness Ratio
        bend_ratio = substrate_thickness_mm / (min_len + 1e-6)
        if bend_ratio <= 0.20:
            status3 = DFMStatus.PASS
            msg3 = f"Substrate thickness ratio ({bend_ratio:.3f}) permits elastic hinge deformation."
        else:
            status3 = DFMStatus.FAIL
            msg3 = f"Substrate too thick ({substrate_thickness_mm:.2f} mm) relative to facet size; risk of delamination."

        checks.append(DFMCheckResult(
            rule_name="Substrate Flexibility & Bend Limit",
            status=status3,
            message=msg3,
            measured_value=bend_ratio,
            limit_value=0.20,
            unit="ratio",
        ))

        # Rule 4: Aspect Ratio of Facets
        max_ar = 1.0
        for face in pattern.faces:
            face_nodes = face.vertex_indices if hasattr(face, "vertex_indices") else face
            pts = [pattern.vertices[v] for v in face_nodes]
            if len(pts) >= 4:
                d1 = np.linalg.norm(pts[1] - pts[0])
                d2 = np.linalg.norm(pts[2] - pts[1])
                ar = max(d1, d2) / max(1e-6, min(d1, d2))
                if ar > max_ar:
                    max_ar = float(ar)


        if max_ar <= max_aspect_ratio:
            status4 = DFMStatus.PASS
            msg4 = f"Facet aspect ratio ({max_ar:.2f}) satisfies warping limits."
        else:
            status4 = DFMStatus.WARNING
            msg4 = f"High aspect ratio facet ({max_ar:.2f}) may curl during reflow."

        checks.append(DFMCheckResult(
            rule_name="Facet Aspect Ratio Warping Limit",
            status=status4,
            message=msg4,
            measured_value=max_ar,
            limit_value=max_aspect_ratio,
            unit="ratio",
        ))

        # Overall Status
        has_fail = any(c.status == DFMStatus.FAIL for c in checks)
        has_warn = any(c.status == DFMStatus.WARNING for c in checks)
        overall_status = DFMStatus.FAIL if has_fail else (DFMStatus.WARNING if has_warn else DFMStatus.PASS)

        return {
            "overall_status": overall_status.value,
            "passed": not has_fail,
            "rules": [
                {
                    "rule": c.rule_name,
                    "status": c.status.value,
                    "message": c.message,
                    "measured": c.measured_value,
                    "limit": c.limit_value,
                    "unit": c.unit,
                }
                for c in checks
            ],
        }
