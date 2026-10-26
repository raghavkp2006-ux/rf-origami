"""Electromagnetic Discretization for Conductor Surfaces and Origami Antenna Geometry.

Discretizes 3D folded conductor paths and facet boundaries into electrodynamic
segments with equivalent radius (Hallén equivalence for flat strips: a = w/4).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.geometry.rf_object import RFGeometryModel, ConductorSurface
from rf_origami.rf.ports.lumped_port import LumpedPort


@dataclass
class EMSegment:
    """A 1D/2D equivalent conductor segment for Method of Moments analysis."""

    index: int
    p1: np.ndarray             # (3,) Start point [mm]
    p2: np.ndarray             # (3,) End point [mm]
    radius_mm: float = 0.5     # Equivalent wire/strip radius [mm]
    conductivity: float = 5.8e7 # S/m (Copper)
    parent_facet_id: int = -1

    def __post_init__(self) -> None:
        self.p1 = np.asarray(self.p1, dtype=np.float64)
        self.p2 = np.asarray(self.p2, dtype=np.float64)

    @property
    def center(self) -> np.ndarray:
        return 0.5 * (self.p1 + self.p2)

    @property
    def vector(self) -> np.ndarray:
        return self.p2 - self.p1

    @property
    def length(self) -> float:
        return float(np.linalg.norm(self.vector))

    @property
    def direction(self) -> np.ndarray:
        l = self.length
        if l < 1e-12:
            return np.array([0.0, 0.0, 1.0])
        return self.vector / l


@dataclass
class EMDiscretization:
    """Collection of discretized segments representing the active RF structure."""

    segments: List[EMSegment] = field(default_factory=list)
    port_segment_index: int = 0
    total_length_mm: float = 0.0

    @property
    def num_segments(self) -> int:
        return len(self.segments)

    def get_centers(self) -> np.ndarray:
        """Return (N, 3) matrix of segment centers in meters."""
        if not self.segments:
            return np.zeros((0, 3))
        # convert mm to meters
        return np.array([s.center * 1e-3 for s in self.segments], dtype=np.float64)

    def get_lengths_m(self) -> np.ndarray:
        """Return (N,) vector of segment lengths in meters."""
        return np.array([s.length * 1e-3 for s in self.segments], dtype=np.float64)

    def get_directions(self) -> np.ndarray:
        """Return (N, 3) unit direction vectors."""
        return np.array([s.direction for s in self.segments], dtype=np.float64)

    def get_radii_m(self) -> np.ndarray:
        """Return (N,) vector of equivalent radii in meters."""
        return np.array([s.radius_mm * 1e-3 for s in self.segments], dtype=np.float64)

    @classmethod
    def from_wire_line(
        cls,
        start_pt: Sequence[float],
        end_pt: Sequence[float],
        num_segments: int = 20,
        radius_mm: float = 0.5,
        feed_at_center: bool = True,
    ) -> EMDiscretization:
        """Create a straight thin-wire discretization for validation benchmarks."""
        p1 = np.asarray(start_pt, dtype=np.float64)
        p2 = np.asarray(end_pt, dtype=np.float64)

        t = np.linspace(0.0, 1.0, num_segments + 1)
        nodes = np.array([(1.0 - s) * p1 + s * p2 for s in t])

        segments = []
        for i in range(num_segments):
            segments.append(EMSegment(
                index=i,
                p1=nodes[i],
                p2=nodes[i + 1],
                radius_mm=radius_mm,
            ))

        port_idx = num_segments // 2 if feed_at_center else 1
        total_len = float(np.linalg.norm(p2 - p1))

        return cls(
            segments=segments,
            port_segment_index=port_idx,
            total_length_mm=total_len,
        )

    @classmethod
    def from_rf_geometry(
        cls,
        rf_geometry: RFGeometryModel,
        port: Optional[LumpedPort] = None,
        target_segment_length_mm: float = 5.0,
    ) -> EMDiscretization:
        """Discretize conductor paths/strips across 3D folded origami facets."""
        conductors = rf_geometry.conductors
        if not conductors:
            # Fallback: if no conductors defined, use entire substrate geometry as wire trace
            conductors = [ConductorSurface(
                object_id="fallback_cond",
                vertices=rf_geometry.substrates[0].vertices if rf_geometry.substrates else np.zeros((4, 3)),
                faces=rf_geometry.substrates[0].faces if rf_geometry.substrates else [[0, 1, 2, 3]],
            )]

        # Collect unique conductor boundary/fold edges
        v_3d = conductors[0].vertices
        faces = conductors[0].faces

        # Extract centerline or boundary graph across folded panels
        all_edges = set()
        for f in faces:
            n_v = len(f)
            for i in range(n_v):
                u = f[i]
                v = f[(i + 1) % n_v]
                edge = (min(u, v), max(u, v))
                all_edges.add(edge)

        # Build connected ordered path along primary axis (longest dimension)
        # Find vertices with maximum spatial separation
        dims = rf_geometry.dimensions()
        primary_axis = int(np.argmax(dims)) if len(dims) == 3 else 0

        # Sort vertices along primary axis
        sorted_v_indices = sorted(range(len(v_3d)), key=lambda idx: v_3d[idx, primary_axis])

        # Subdivide segments so each segment length <= target_segment_length_mm
        segments: List[EMSegment] = []
        seg_idx = 0

        for i in range(len(sorted_v_indices) - 1):
            u_idx = sorted_v_indices[i]
            v_idx = sorted_v_indices[i + 1]
            p_u = v_3d[u_idx]
            p_v = v_3d[v_idx]
            span = np.linalg.norm(p_v - p_u)
            if span < 1e-3:
                continue

            n_sub = max(1, int(np.ceil(span / max(1.0, target_segment_length_mm))))
            t = np.linspace(0.0, 1.0, n_sub + 1)
            pts = [(1.0 - s) * p_u + s * p_v for s in t]

            for s_i in range(n_sub):
                segments.append(EMSegment(
                    index=seg_idx,
                    p1=pts[s_i],
                    p2=pts[s_i + 1],
                    radius_mm=0.6, # ~2.4 mm width strip equivalent
                ))
                seg_idx += 1

        if not segments:
            # Degenerate safeguard
            segments = [EMSegment(0, np.array([0, 0, 0]), np.array([0, 20, 0]), 0.5)]

        # Find closest segment to port position
        port_idx = len(segments) // 2 # default center
        if port is not None:
            port_pos = port.position
            dists = [np.linalg.norm(s.center - port_pos) for s in segments]
            port_idx = int(np.argmin(dists))

        total_len = sum(s.length for s in segments)

        return cls(
            segments=segments,
            port_segment_index=port_idx,
            total_length_mm=total_len,
        )
