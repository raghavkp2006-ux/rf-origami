"""Lumped Port Feed Excitation Model for RF Origami Antennas.

Models 50-Ohm lumped excitation ports with positive/negative terminals,
direction vectors, and geometric physical validation checks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from rf_origami.rf.geometry.rf_object import RFGeometryModel


@dataclass
class LumpedPort:
    """Represents a 50-Ohm lumped port excitation across an antenna gap."""

    port_id: str = "PORT_1"
    impedance: float = 50.0                  # Reference characteristic impedance Z0 [Ohms]
    positive_terminal: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    negative_terminal: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    attached_conductor_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.positive_terminal = np.asarray(self.positive_terminal, dtype=np.float64)
        self.negative_terminal = np.asarray(self.negative_terminal, dtype=np.float64)

    @property
    def position(self) -> np.ndarray:
        """Port center position between positive and negative terminals."""
        return 0.5 * (self.positive_terminal + self.negative_terminal)

    @property
    def gap_length(self) -> float:
        """Physical distance between terminals in millimeters."""
        return float(np.linalg.norm(self.positive_terminal - self.negative_terminal))

    @property
    def direction(self) -> np.ndarray:
        """Normalized direction vector pointing from negative to positive terminal."""
        vec = self.positive_terminal - self.negative_terminal
        norm = np.linalg.norm(vec)
        if norm < 1e-12:
            return np.array([0.0, 0.0, 1.0], dtype=np.float64)
        return vec / norm

    def validate(self, rf_geometry: Optional[RFGeometryModel] = None) -> Tuple[bool, List[str]]:
        """Validate physical correctness of port definition.

        Checks:
        1. Impedance must be strictly positive.
        2. Positive and negative terminals must not be coincident.
        3. Gap length must be within reasonable physical bounds (<= 15 mm).
        4. If RF geometry is provided, terminals must be located near conductor elements.
        """
        errors = []

        if self.impedance <= 0.0:
            errors.append(f"Port reference impedance must be > 0 (got {self.impedance} Ω).")

        gap = self.gap_length
        if gap < 1e-5:
            errors.append(f"Port terminals are coincident (gap = {gap:.3e} mm < 1e-5 mm).")

        if gap > 20.0:
            errors.append(f"Port feed gap ({gap:.2f} mm) is too large for a lumped element assumption.")

        if rf_geometry is not None:
            # Check proximity to conductor surfaces
            conductors = rf_geometry.conductors
            if not conductors:
                errors.append("No conductor surfaces present in RF geometry for port attachment.")
            else:
                # Find minimum distance to any conductor vertex
                min_dist_pos = float("inf")
                min_dist_neg = float("inf")
                for c in conductors:
                    if len(c.vertices) > 0:
                        d_pos = np.min(np.linalg.norm(c.vertices - self.positive_terminal, axis=1))
                        d_neg = np.min(np.linalg.norm(c.vertices - self.negative_terminal, axis=1))
                        min_dist_pos = min(min_dist_pos, d_pos)
                        min_dist_neg = min(min_dist_neg, d_neg)

                # Tolerance of 5 mm proximity to mesh vertices
                if min_dist_pos > 5.0 and min_dist_neg > 5.0:
                    errors.append(f"Port is disconnected: nearest conductor vertex is {min(min_dist_pos, min_dist_neg):.1f} mm away.")

        return (len(errors) == 0), errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize port settings."""
        is_ok, errs = self.validate()
        return {
            "port_id": self.port_id,
            "impedance_ohms": self.impedance,
            "positive_terminal": self.positive_terminal.tolist(),
            "negative_terminal": self.negative_terminal.tolist(),
            "position": self.position.tolist(),
            "direction": self.direction.tolist(),
            "gap_length_mm": round(self.gap_length, 3),
            "is_valid": is_ok,
            "validation_errors": errs,
        }

    @classmethod
    def from_center_and_length(
        cls,
        center: Union[Sequence[float], np.ndarray],
        direction: Union[Sequence[float], np.ndarray],
        gap_length_mm: float = 1.0,
        impedance: float = 50.0,
        port_id: str = "PORT_1",
    ) -> LumpedPort:
        """Construct lumped port by specifying center point and gap length."""
        c = np.asarray(center, dtype=np.float64)
        d = np.asarray(direction, dtype=np.float64)
        norm = np.linalg.norm(d)
        u = d / norm if norm > 1e-12 else np.array([0.0, 1.0, 0.0])

        half = 0.5 * gap_length_mm * u
        pos_term = c + half
        neg_term = c - half

        return cls(
            port_id=port_id,
            impedance=impedance,
            positive_terminal=pos_term,
            negative_terminal=neg_term,
        )
