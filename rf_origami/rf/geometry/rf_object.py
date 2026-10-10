"""Physically meaningful RF geometrical objects for folded origami antennas.

Represents conductor surfaces, ground planes, substrate facets, feed locations,
and keep-out boundaries linked to their origami parent candidate and fold state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rf_origami.rf.materials.material import Material, MaterialLibrary
from rf_origami.core.geometry import polygon_area, polygon_normal, is_coplanar


class RFObjectType(str, Enum):
    """Categorization of physical RF objects."""
    CONDUCTOR = "conductor"
    SUBSTRATE = "substrate"
    GROUND_PLANE = "ground_plane"
    DIELECTRIC = "dielectric"
    FEED = "feed"
    KEEPOUT = "keepout"


@dataclass
class RFObject:
    """Base class for physical components in the RF domain."""

    object_id: str
    object_type: RFObjectType
    material: Material
    vertices: np.ndarray             # (N, 3) float64
    faces: List[List[int]]           # List of vertex index sequences
    parent_candidate_id: str = ""
    fold_angle_deg: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.vertices = np.asarray(self.vertices, dtype=np.float64)

    @property
    def num_vertices(self) -> int:
        return len(self.vertices)

    @property
    def num_faces(self) -> int:
        return len(self.faces)

    def surface_area(self) -> float:
        """Compute total surface area of this object."""
        total = 0.0
        for f in self.faces:
            pts = self.vertices[list(f)]
            total += polygon_area(pts)
        return total

    def bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute axis-aligned [min_xyz, max_xyz] bounds."""
        if len(self.vertices) == 0:
            return np.zeros(3), np.zeros(3)
        return np.min(self.vertices, axis=0), np.max(self.vertices, axis=0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize RF object metadata and statistics."""
        b_min, b_max = self.bounding_box()
        return {
            "object_id": self.object_id,
            "object_type": self.object_type.value,
            "material": self.material.to_dict(),
            "parent_candidate_id": self.parent_candidate_id,
            "fold_angle_deg": self.fold_angle_deg,
            "num_vertices": self.num_vertices,
            "num_faces": self.num_faces,
            "surface_area_mm2": round(self.surface_area(), 2),
            "bounds": {
                "min": b_min.tolist(),
                "max": b_max.tolist(),
            },
            "metadata": self.metadata,
        }


@dataclass
class ConductorSurface(RFObject):
    """Conductive surface/patch on the origami structure."""

    def __init__(
        self,
        object_id: str,
        vertices: np.ndarray,
        faces: List[List[int]],
        material: Optional[Material] = None,
        parent_candidate_id: str = "",
        fold_angle_deg: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        mat = material if material is not None else MaterialLibrary.get("copper")
        super().__init__(
            object_id=object_id,
            object_type=RFObjectType.CONDUCTOR,
            material=mat,
            vertices=vertices,
            faces=faces,
            parent_candidate_id=parent_candidate_id,
            fold_angle_deg=fold_angle_deg,
            metadata=metadata or {},
        )


@dataclass
class SubstrateSurface(RFObject):
    """Dielectric substrate facet on the origami structure."""

    def __init__(
        self,
        object_id: str,
        vertices: np.ndarray,
        faces: List[List[int]],
        material: Optional[Material] = None,
        parent_candidate_id: str = "",
        fold_angle_deg: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        mat = material if material is not None else MaterialLibrary.get("kapton")
        super().__init__(
            object_id=object_id,
            object_type=RFObjectType.SUBSTRATE,
            material=mat,
            vertices=vertices,
            faces=faces,
            parent_candidate_id=parent_candidate_id,
            fold_angle_deg=fold_angle_deg,
            metadata=metadata or {},
        )


@dataclass
class GroundPlane(RFObject):
    """Ground plane surface or backing sheet."""

    def __init__(
        self,
        object_id: str,
        vertices: np.ndarray,
        faces: List[List[int]],
        material: Optional[Material] = None,
        parent_candidate_id: str = "",
        fold_angle_deg: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        mat = material if material is not None else MaterialLibrary.get("copper")
        super().__init__(
            object_id=object_id,
            object_type=RFObjectType.GROUND_PLANE,
            material=mat,
            vertices=vertices,
            faces=faces,
            parent_candidate_id=parent_candidate_id,
            fold_angle_deg=fold_angle_deg,
            metadata=metadata or {},
        )


@dataclass
class RFGeometryModel:
    """Complete physical RF domain model assembling all components."""

    parent_candidate_id: str
    fold_angle_deg: float
    conductors: List[ConductorSurface] = field(default_factory=list)
    substrates: List[SubstrateSurface] = field(default_factory=list)
    ground_planes: List[GroundPlane] = field(default_factory=list)
    keepouts: List[RFObject] = field(default_factory=list)

    @property
    def all_objects(self) -> List[RFObject]:
        return [*self.conductors, *self.substrates, *self.ground_planes, *self.keepouts]

    def total_conductor_area(self) -> float:
        return sum(c.surface_area() for c in self.conductors)

    def total_substrate_area(self) -> float:
        return sum(s.surface_area() for s in self.substrates)

    def total_ground_area(self) -> float:
        return sum(g.surface_area() for g in self.ground_planes)

    def bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute overall envelope of the entire RF structure."""
        all_v = [obj.vertices for obj in self.all_objects if len(obj.vertices) > 0]
        if not all_v:
            return np.zeros(3), np.zeros(3)
        stacked = np.vstack(all_v)
        return np.min(stacked, axis=0), np.max(stacked, axis=0)

    def dimensions(self) -> np.ndarray:
        b_min, b_max = self.bounding_box()
        return b_max - b_min

    def to_dict(self) -> Dict[str, Any]:
        b_min, b_max = self.bounding_box()
        dims = self.dimensions()
        return {
            "parent_candidate_id": self.parent_candidate_id,
            "fold_angle_deg": self.fold_angle_deg,
            "dimensions_mm": [round(float(d), 2) for d in dims],
            "total_conductor_area_mm2": round(self.total_conductor_area(), 2),
            "total_substrate_area_mm2": round(self.total_substrate_area(), 2),
            "total_ground_area_mm2": round(self.total_ground_area(), 2),
            "objects": [obj.to_dict() for obj in self.all_objects],
        }
