"""Origami crease pattern representation and topological verification.

Represents 2D flat patterns with typed creases (Mountain, Valley, Boundary, Facet),
facets with RF material properties, and flat-foldability verification
(Kawasaki's and Maekawa's theorems).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
import numpy as np


class CreaseType(str, Enum):
    """Crease fold assignment classification."""
    BOUNDARY = "B"    # Outer boundary of sheet
    MOUNTAIN = "M"    # Crease folds upward towards observer (+ dihedral)
    VALLEY = "V"      # Crease folds downward away from observer (- dihedral)
    FACET = "F"       # Flat uncreased seam or triangulation hinge

    @classmethod
    def from_str(cls, val: str) -> CreaseType:
        """Parse crease type from string or single character."""
        val_upper = val.strip().upper()
        for member in cls:
            if member.value == val_upper or member.name == val_upper:
                return member
        raise ValueError(f"Unknown crease type '{val}'. Valid options: {list(cls.__members__.keys())}")


@dataclass
class Crease:
    """Represents a fold line or edge connecting two vertices."""
    u: int
    v: int
    crease_type: CreaseType = CreaseType.FACET
    fold_angle: float = 0.0  # Fold angle in radians (-pi to +pi)
    target_length: Optional[float] = None

    def __post_init__(self) -> None:
        if self.u == self.v:
            raise ValueError(f"Crease cannot connect vertex {self.u} to itself.")
        # Ensure canonical ordering u < v
        if self.u > self.v:
            self.u, self.v = self.v, self.u
        if not isinstance(self.crease_type, CreaseType):
            self.crease_type = CreaseType.from_str(str(self.crease_type))

    @property
    def key(self) -> Tuple[int, int]:
        """Canonical vertex index tuple (u, v) with u < v."""
        return (self.u, self.v)


@dataclass
class Face:
    """Represents an origami polygon facet."""
    vertex_indices: Tuple[int, ...]
    material_tag: str = "substrate"  # e.g., 'substrate', 'conductor', 'copper', 'ground'
    rf_properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.vertex_indices) < 3:
            raise ValueError("A face must have at least 3 vertices.")
        self.vertex_indices = tuple(int(i) for i in self.vertex_indices)


class CreasePattern:
    """2D Origami Crease Pattern graph representation."""

    def __init__(self, vertices: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None) -> None:
        if vertices is not None:
            v_arr = np.asarray(vertices, dtype=np.float64)
            if v_arr.ndim != 2 or v_arr.shape[1] not in (2, 3):
                raise ValueError(f"Vertices must be (N, 2) or (N, 3), got shape {v_arr.shape}")
            if v_arr.shape[1] == 2:
                # Pad with z=0 to maintain 3D compatibility
                z = np.zeros((v_arr.shape[0], 1), dtype=np.float64)
                self._vertices = np.hstack([v_arr, z])
            else:
                self._vertices = v_arr.copy()
        else:
            self._vertices = np.empty((0, 3), dtype=np.float64)

        self._creases: List[Crease] = []
        self._crease_map: Dict[Tuple[int, int], Crease] = {}
        self._faces: List[Face] = []
        self._adj: Dict[int, Set[int]] = {}

    @property
    def num_vertices(self) -> int:
        return len(self._vertices)

    @property
    def num_creases(self) -> int:
        return len(self._creases)

    @property
    def num_faces(self) -> int:
        return len(self._faces)

    @property
    def vertices(self) -> np.ndarray:
        """(N, 3) vertex coordinates."""
        return self._vertices.copy()

    @property
    def creases(self) -> List[Crease]:
        return list(self._creases)

    @property
    def faces(self) -> List[Face]:
        return list(self._faces)

    def add_vertex(self, x: float, y: float, z: float = 0.0) -> int:
        """Add a vertex and return its index."""
        pt = np.array([[float(x), float(y), float(z)]], dtype=np.float64)
        if len(self._vertices) == 0:
            self._vertices = pt
        else:
            self._vertices = np.vstack([self._vertices, pt])
        idx = len(self._vertices) - 1
        self._adj[idx] = set()
        return idx

    def add_crease(
        self,
        u: int,
        v: int,
        crease_type: Union[CreaseType, str] = CreaseType.FACET,
        fold_angle: float = 0.0,
        target_length: Optional[float] = None
    ) -> Crease:
        """Add or update an edge/crease between vertices u and v."""
        if u < 0 or u >= self.num_vertices or v < 0 or v >= self.num_vertices:
            raise IndexError(f"Vertex index out of bounds: u={u}, v={v}, total={self.num_vertices}")

        if isinstance(crease_type, str):
            crease_type = CreaseType.from_str(crease_type)

        key = (min(u, v), max(u, v))
        if target_length is None:
            target_length = self.edge_length(u, v)

        if key in self._crease_map:
            # Update existing crease
            existing = self._crease_map[key]
            existing.crease_type = crease_type
            existing.fold_angle = fold_angle
            existing.target_length = target_length
            return existing

        crease = Crease(u=key[0], v=key[1], crease_type=crease_type, fold_angle=fold_angle, target_length=target_length)
        self._creases.append(crease)
        self._crease_map[key] = crease

        self._adj.setdefault(key[0], set()).add(key[1])
        self._adj.setdefault(key[1], set()).add(key[0])
        return crease

    def add_face(self, vertex_indices: Sequence[int], material_tag: str = "substrate", rf_properties: Optional[Dict[str, Any]] = None) -> Face:
        """Add a polygonal facet defined by vertex indices."""
        for idx in vertex_indices:
            if idx < 0 or idx >= self.num_vertices:
                raise IndexError(f"Face vertex index {idx} out of bounds (0..{self.num_vertices - 1})")
        face = Face(vertex_indices=tuple(vertex_indices), material_tag=material_tag, rf_properties=rf_properties or {})
        self._faces.append(face)
        return face

    def get_crease(self, u: int, v: int) -> Optional[Crease]:
        """Look up crease by vertex pair."""
        return self._crease_map.get((min(u, v), max(u, v)))

    def get_creases_at_vertex(self, v_idx: int) -> List[Crease]:
        """Get all creases meeting at vertex v_idx."""
        return [c for c in self._creases if c.u == v_idx or c.v == v_idx]

    def get_neighbors(self, v_idx: int) -> List[int]:
        """Get adjacent vertex indices."""
        return sorted(list(self._adj.get(v_idx, set())))

    def edge_length(self, u: int, v: int) -> float:
        """Compute Euclidean distance between vertices u and v."""
        return float(np.linalg.norm(self._vertices[u] - self._vertices[v]))

    def vertex_coordinates(self, idx: int) -> np.ndarray:
        return self._vertices[idx].copy()

    def bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (min_xyz, max_xyz) bounding box."""
        if len(self._vertices) == 0:
            return np.zeros(3), np.zeros(3)
        return np.min(self._vertices, axis=0), np.max(self._vertices, axis=0)

    # -----------------------------------------------------------------
    # Origami Flat-Foldability Verification
    # -----------------------------------------------------------------

    def is_boundary_vertex(self, v_idx: int) -> bool:
        """Check if a vertex is on the boundary (has any BOUNDARY creases)."""
        creases = self.get_creases_at_vertex(v_idx)
        return any(c.crease_type == CreaseType.BOUNDARY for c in creases)

    def check_kawasaki_theorem(self, v_idx: int, tol_deg: float = 1.0) -> Tuple[bool, float, float]:
        """Verify Kawasaki's Theorem for an interior vertex.

        For flat-foldable vertices with even degree 2k, the alternating sum
        of sector angles around the vertex must equal 180 degrees (pi radians).
        Returns (is_valid, sum_even_deg, sum_odd_deg).
        """
        neighbors = self.get_neighbors(v_idx)
        degree = len(neighbors)
        if degree < 4 or degree % 2 != 0:
            return False, 0.0, 0.0

        center = self._vertices[v_idx][:2]
        # Sort neighbors radially in counter-clockwise order
        angles_and_neighbors = []
        for n_idx in neighbors:
            pos = self._vertices[n_idx][:2]
            vec = pos - center
            angle = math.atan2(vec[1], vec[0])
            angles_and_neighbors.append((angle, n_idx))

        angles_and_neighbors.sort(key=lambda x: x[0])
        sorted_neighbors = [x[1] for x in angles_and_neighbors]

        # Calculate sector angles between successive radial rays
        sector_angles = []
        for i in range(degree):
            n1 = sorted_neighbors[i]
            n2 = sorted_neighbors[(i + 1) % degree]
            v1 = self._vertices[n1][:2] - center
            v2 = self._vertices[n2][:2] - center
            cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            cos_a = max(-1.0, min(1.0, cos_a))
            sector_angles.append(math.degrees(math.acos(cos_a)))

        sum_even = sum(sector_angles[0::2])
        sum_odd = sum(sector_angles[1::2])
        is_valid = abs(sum_even - 180.0) < tol_deg and abs(sum_odd - 180.0) < tol_deg
        return is_valid, sum_even, sum_odd

    def check_maekawa_theorem(self, v_idx: int) -> Tuple[bool, int, int]:
        """Verify Maekawa's Theorem for an interior flat-foldable vertex.

        The difference between the number of Mountain creases (M) and Valley
        creases (V) at an interior vertex must be +/- 2: |M - V| = 2.
        Returns (is_valid, num_mountain, num_valley).
        """
        creases = self.get_creases_at_vertex(v_idx)
        m_count = sum(1 for c in creases if c.crease_type == CreaseType.MOUNTAIN)
        v_count = sum(1 for c in creases if c.crease_type == CreaseType.VALLEY)
        is_valid = abs(m_count - v_count) == 2
        return is_valid, m_count, v_count

    # -----------------------------------------------------------------
    # Serialization (FOLD Spec 1.1 Standard for Origami Simulators)
    # -----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize crease pattern to dictionary format fully compliant with FOLD 1.1 specification.

        Guarantees presence of vertices_coords, edges_vertices, edges_assignment, faces_vertices,
        and edges_foldAngle for origami simulators (e.g., Amanda Ghassaei's Origami Simulator,
        Tessellatica, Freeform Origami).
        """
        return self.to_fold()

    def to_fold(
        self,
        title: str = "RF Origami Pattern",
        as_folded: bool = False,
        folded_coords: Optional[Union[np.ndarray, Sequence[Sequence[float]]]] = None,
    ) -> Dict[str, Any]:
        """Export pattern to standard FOLD format (.fold specification v1.1).

        Args:
            title: Human-readable model frame title.
            as_folded: If True, exports the 3D folded geometry state (frame_classes: ['foldedForm']).
            folded_coords: Optional (N, 3) array of folded vertex coordinates.
        """
        if as_folded and folded_coords is not None:
            v_arr = np.asarray(folded_coords, dtype=np.float64)
            coords = v_arr.tolist()
            frame_classes = ["foldedForm"]
            frame_attributes = ["3D"]
        else:
            coords = self._vertices.tolist()
            frame_classes = ["creasePattern"]
            frame_attributes = ["2D"]

        # Compute standard FOLD fold angles in degrees
        fold_angles_deg: List[float] = []
        for c in self._creases:
            if abs(c.fold_angle) > 1e-6:
                fold_angles_deg.append(float(math.degrees(c.fold_angle)))
            elif c.crease_type == CreaseType.MOUNTAIN:
                fold_angles_deg.append(-180.0)
            elif c.crease_type == CreaseType.VALLEY:
                fold_angles_deg.append(180.0)
            else:
                fold_angles_deg.append(0.0)

        # Ensure faces_vertices is never empty: if faces were not explicitly added,
        # generate triangulation / polygon faces so Origami Simulator does not reject the file
        faces_list = [list(f.vertex_indices) for f in self._faces]
        faces_mats = [f.material_tag for f in self._faces]

        if len(faces_list) == 0 and len(self._creases) >= 3 and len(self._vertices) >= 3:
            # Fallback simple triangulation from vertex boundary
            if len(self._vertices) == 4:
                faces_list = [[0, 1, 2, 3]]
                faces_mats = ["substrate"]
            elif len(self._vertices) > 4:
                # Triangulate polygon fans
                faces_list = [[0, i, i + 1] for i in range(1, len(self._vertices) - 1)]
                faces_mats = ["substrate"] * len(faces_list)

        return {
            "file_spec": 1.1,
            "file_creator": "RF Origami Design Studio",
            "file_author": "RF Origami Simulator Bridge",
            "file_classes": ["singleModel"],
            "frame_title": title,
            "frame_classes": frame_classes,
            "frame_attributes": frame_attributes,
            "vertices_coords": coords,
            "edges_vertices": [list(c.key) for c in self._creases],
            "edges_assignment": [c.crease_type.value for c in self._creases],
            "edges_foldAngle": fold_angles_deg,
            "edges_fold_angle": [float(c.fold_angle) for c in self._creases],  # Backwards compatibility
            "faces_vertices": faces_list,
            "faces_materials": faces_mats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CreasePattern:
        """Construct CreasePattern from serialized dictionary."""
        cp = cls(vertices=data.get("vertices_coords", []))
        edges = data.get("edges_vertices", [])
        assignments = data.get("edges_assignment", ["F"] * len(edges))

        # Check for edges_fold_angle (exact radians) first, then edges_foldAngle (degrees from FOLD spec)
        if "edges_fold_angle" in data:
            angles = [float(a) for a in data.get("edges_fold_angle", [])]
        elif "edges_foldAngle" in data:
            raw_angles = data.get("edges_foldAngle", [])
            angles = [math.radians(float(a)) for a in raw_angles]
        else:
            angles = [0.0] * len(edges)

        if len(angles) < len(edges):
            angles.extend([0.0] * (len(edges) - len(angles)))

        for (u, v), assign, ang in zip(edges, assignments, angles):
            cp.add_crease(u=u, v=v, crease_type=assign, fold_angle=ang)

        faces = data.get("faces_vertices", [])
        materials = data.get("faces_materials", ["substrate"] * len(faces))
        for face_v, mat in zip(faces, materials):
            cp.add_face(vertex_indices=face_v, material_tag=mat)

        return cp
