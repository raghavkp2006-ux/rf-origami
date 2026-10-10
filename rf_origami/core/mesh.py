"""3D Folded geometry mesh representation.

Stores 3D vertices, polygonal faces, computed surface normals, bounding boxes,
and geometric properties for RF origami designs.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from rf_origami.core.geometry import polygon_normal, polygon_area, polygon_centroid
from rf_origami.core.crease_pattern import Crease


class FoldedMesh:
    """Represents a 3D folded origami surface mesh."""

    def __init__(
        self,
        vertices: Union[np.ndarray, Sequence[Sequence[float]]],
        faces: Sequence[Sequence[int]],
        creases: Optional[Sequence[Crease]] = None,
        face_materials: Optional[Sequence[str]] = None,
    ) -> None:
        self._vertices = np.asarray(vertices, dtype=np.float64)
        if self._vertices.ndim != 2 or self._vertices.shape[1] != 3:
            raise ValueError(f"Vertices must be an (N, 3) array, got {self._vertices.shape}")

        self._faces: List[Tuple[int, ...]] = [tuple(int(i) for i in f) for f in faces]
        self._creases: List[Crease] = list(creases) if creases else []
        self._face_materials: List[str] = (
            list(face_materials) if face_materials else ["substrate"] * len(self._faces)
        )

        if len(self._face_materials) != len(self._faces):
            raise ValueError(
                f"Face materials length ({len(self._face_materials)}) must match faces count ({len(self._faces)})"
            )

    @property
    def vertices(self) -> np.ndarray:
        """(N, 3) vertex coordinates."""
        return self._vertices.copy()

    @property
    def faces(self) -> List[Tuple[int, ...]]:
        return list(self._faces)

    @property
    def creases(self) -> List[Crease]:
        return list(self._creases)

    @property
    def face_materials(self) -> List[str]:
        return list(self._face_materials)

    @property
    def num_vertices(self) -> int:
        return len(self._vertices)

    @property
    def num_faces(self) -> int:
        return len(self._faces)

    def bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (min_xyz, max_xyz) coordinates."""
        if len(self._vertices) == 0:
            return np.zeros(3), np.zeros(3)
        return np.min(self._vertices, axis=0), np.max(self._vertices, axis=0)

    def dimensions(self) -> np.ndarray:
        """Return dimensions [Lx, Ly, Lz] along principal axes."""
        b_min, b_max = self.bounding_box()
        return b_max - b_min

    def compute_face_normals(self) -> np.ndarray:
        """Compute unit normal vector for each polygonal face.

        Returns (num_faces, 3) float array.
        """
        normals = np.zeros((len(self._faces), 3), dtype=np.float64)
        for i, face_v in enumerate(self._faces):
            face_coords = self._vertices[list(face_v)]
            try:
                normals[i] = polygon_normal(face_coords)
            except ValueError:
                # Default degenerate normal to +Z
                normals[i] = np.array([0.0, 0.0, 1.0])
        return normals

    def compute_face_centroids(self) -> np.ndarray:
        """Compute geometric centroid for each face.

        Returns (num_faces, 3) float array.
        """
        centroids = np.zeros((len(self._faces), 3), dtype=np.float64)
        for i, face_v in enumerate(self._faces):
            centroids[i] = polygon_centroid(self._vertices[list(face_v)])
        return centroids

    def compute_total_surface_area(self) -> float:
        """Sum of surface areas across all facets."""
        total = 0.0
        for face_v in self._faces:
            total += polygon_area(self._vertices[list(face_v)])
        return total

    def compute_material_surface_area(self, material_tag: str) -> float:
        """Total area of facets with a specific material (e.g., 'conductor' or 'copper')."""
        total = 0.0
        for face_v, mat in zip(self._faces, self._face_materials):
            if mat.lower() == material_tag.lower():
                total += polygon_area(self._vertices[list(face_v)])
        return total

    def to_triangulated(self) -> FoldedMesh:
        """Convert any n-gon facets into triangles via fan triangulation.

        Essential for export to STL or standard CAD / EM meshes.
        """
        tri_faces: List[Tuple[int, ...]] = []
        tri_materials: List[str] = []

        for face_v, mat in zip(self._faces, self._face_materials):
            if len(face_v) == 3:
                tri_faces.append(face_v)
                tri_materials.append(mat)
            else:
                # Simple fan triangulation from vertex 0
                v0 = face_v[0]
                for k in range(1, len(face_v) - 1):
                    tri_faces.append((v0, face_v[k], face_v[k + 1]))
                    tri_materials.append(mat)

        return FoldedMesh(
            vertices=self._vertices.copy(),
            faces=tri_faces,
            creases=self._creases,
            face_materials=tri_materials,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize folded mesh."""
        return {
            "vertices": self._vertices.tolist(),
            "faces": [list(f) for f in self._faces],
            "face_materials": self._face_materials,
            "dimensions": self.dimensions().tolist(),
            "total_surface_area": self.compute_total_surface_area(),
        }
