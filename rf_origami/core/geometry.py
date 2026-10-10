"""Mathematical geometry representations and transformations for origami.

Provides vector math, rigid transformations, and 3D polygon analysis
tailored for computational origami kinematics and RF facet modeling.
"""

from __future__ import annotations
import math
from typing import Sequence, Tuple, Union
import numpy as np


class Vector3D:
    """Immutable 3D vector with arithmetic and geometric operations."""

    __slots__ = ("_data",)

    def __init__(self, x: float, y: float, z: float = 0.0) -> None:
        self._data = np.array([float(x), float(y), float(z)], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: Union[Sequence[float], np.ndarray]) -> Vector3D:
        """Create Vector3D from array-like or sequence."""
        arr_np = np.asarray(arr, dtype=np.float64)
        if arr_np.size == 2:
            return cls(arr_np[0], arr_np[1], 0.0)
        elif arr_np.size == 3:
            return cls(arr_np[0], arr_np[1], arr_np[2])
        raise ValueError(f"Expected 2 or 3 components, got {arr_np.size}")

    @property
    def x(self) -> float:
        return float(self._data[0])

    @property
    def y(self) -> float:
        return float(self._data[1])

    @property
    def z(self) -> float:
        return float(self._data[2])

    def to_numpy(self) -> np.ndarray:
        """Return a copy of the underlying NumPy array."""
        return self._data.copy()

    def __repr__(self) -> str:
        return f"Vector3D(x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Vector3D):
            return bool(np.allclose(self._data, other._data, atol=1e-8))
        return False

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D.from_array(self._data + other._data)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D.from_array(self._data - other._data)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D.from_array(self._data * float(scalar))

    def __rmul__(self, scalar: float) -> Vector3D:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3D:
        if abs(scalar) < 1e-15:
            raise ZeroDivisionError("Division by zero in Vector3D.")
        return Vector3D.from_array(self._data / float(scalar))

    def __neg__(self) -> Vector3D:
        return Vector3D.from_array(-self._data)

    def dot(self, other: Vector3D) -> float:
        """Calculate dot product."""
        return float(np.dot(self._data, other._data))

    def cross(self, other: Vector3D) -> Vector3D:
        """Calculate cross product."""
        return Vector3D.from_array(np.cross(self._data, other._data))

    def norm(self) -> float:
        """Calculate Euclidean L2 norm."""
        return float(np.linalg.norm(self._data))

    def normalize(self) -> Vector3D:
        """Return unit vector. Raises ValueError if length is zero."""
        n = self.norm()
        if n < 1e-14:
            raise ValueError("Cannot normalize zero-length vector.")
        return Vector3D.from_array(self._data / n)

    def angle_to(self, other: Vector3D) -> float:
        """Angle in radians between this vector and another vector in [0, pi]."""
        n1 = self.norm()
        n2 = other.norm()
        if n1 < 1e-14 or n2 < 1e-14:
            raise ValueError("Cannot compute angle with zero vector.")
        cos_theta = self.dot(other) / (n1 * n2)
        cos_theta = max(-1.0, min(1.0, cos_theta))
        return float(math.acos(cos_theta))


class Point3D:
    """3D point coordinate representation."""

    __slots__ = ("_coords",)

    def __init__(self, x: float, y: float, z: float = 0.0) -> None:
        self._coords = np.array([float(x), float(y), float(z)], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: Union[Sequence[float], np.ndarray]) -> Point3D:
        arr_np = np.asarray(arr, dtype=np.float64)
        if arr_np.size == 2:
            return cls(arr_np[0], arr_np[1], 0.0)
        elif arr_np.size == 3:
            return cls(arr_np[0], arr_np[1], arr_np[2])
        raise ValueError(f"Expected 2 or 3 components, got {arr_np.size}")

    @property
    def x(self) -> float:
        return float(self._coords[0])

    @property
    def y(self) -> float:
        return float(self._coords[1])

    @property
    def z(self) -> float:
        return float(self._coords[2])

    def to_numpy(self) -> np.ndarray:
        return self._coords.copy()

    def __repr__(self) -> str:
        return f"Point3D(x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Point3D):
            return bool(np.allclose(self._coords, other._coords, atol=1e-8))
        return False

    def distance_to(self, other: Point3D) -> float:
        """Euclidean distance to another point."""
        return float(np.linalg.norm(self._coords - other._coords))

    def vector_to(self, other: Point3D) -> Vector3D:
        """Vector pointing from self to other."""
        return Vector3D.from_array(other._coords - self._coords)

    def translate(self, vector: Vector3D) -> Point3D:
        """Translate point by a vector."""
        return Point3D.from_array(self._coords + vector.to_numpy())


# =====================================================================
# Transformations & Kinematics
# =====================================================================

def rotation_matrix_axis_angle(axis: Union[Vector3D, np.ndarray, Sequence[float]], angle_rad: float) -> np.ndarray:
    """Generate 3x3 rotation matrix using Rodrigues' rotation formula.

    Rotates a vector around the specified unit axis by angle_rad (radians).
    """
    if isinstance(axis, Vector3D):
        u = axis.normalize().to_numpy()
    else:
        u_arr = np.asarray(axis, dtype=np.float64)
        n = np.linalg.norm(u_arr)
        if n < 1e-14:
            raise ValueError("Rotation axis cannot be zero.")
        u = u_arr / n

    cos_t = math.cos(angle_rad)
    sin_t = math.sin(angle_rad)
    ux, uy, uz = u

    # Rodrigues formula in matrix form: R = I + sin(t)*K + (1-cos(t))*K^2
    R = np.array([
        [cos_t + ux * ux * (1.0 - cos_t), ux * uy * (1.0 - cos_t) - uz * sin_t, ux * uz * (1.0 - cos_t) + uy * sin_t],
        [uy * ux * (1.0 - cos_t) + uz * sin_t, cos_t + uy * uy * (1.0 - cos_t), uy * uz * (1.0 - cos_t) - ux * sin_t],
        [uz * ux * (1.0 - cos_t) - uy * sin_t, uz * uy * (1.0 - cos_t) + ux * sin_t, cos_t + uz * uz * (1.0 - cos_t)],
    ], dtype=np.float64)
    return R


def rotation_matrix_euler(roll: float, pitch: float, yaw: float, degrees: bool = False) -> np.ndarray:
    """Generate 3x3 rotation matrix from Tait-Bryan Euler angles (ZYX convention: roll=X, pitch=Y, yaw=Z)."""
    if degrees:
        roll = math.radians(roll)
        pitch = math.radians(pitch)
        yaw = math.radians(yaw)

    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(roll), -math.sin(roll)],
        [0, math.sin(roll), math.cos(roll)]
    ], dtype=np.float64)

    Ry = np.array([
        [math.cos(pitch), 0, math.sin(pitch)],
        [0, 1, 0],
        [-math.sin(pitch), 0, math.cos(pitch)]
    ], dtype=np.float64)

    Rz = np.array([
        [math.cos(yaw), -math.sin(yaw), 0],
        [math.sin(yaw), math.cos(yaw), 0],
        [0, 0, 1]
    ], dtype=np.float64)

    return Rz @ Ry @ Rx


def create_affine_matrix(
    rotation: np.ndarray = np.eye(3),
    translation: Union[np.ndarray, Sequence[float], Vector3D] = (0.0, 0.0, 0.0)
) -> np.ndarray:
    """Create 4x4 homogeneous transformation matrix."""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = rotation
    if isinstance(translation, Vector3D):
        T[:3, 3] = translation.to_numpy()
    else:
        T[:3, 3] = np.asarray(translation, dtype=np.float64)
    return T


def transform_points(points: np.ndarray, matrix_4x4: np.ndarray) -> np.ndarray:
    """Apply 4x4 affine transformation to (N, 3) or (3,) points."""
    pts = np.asarray(points, dtype=np.float64)
    single = pts.ndim == 1
    if single:
        pts = pts.reshape(1, 3)

    num_pts = pts.shape[0]
    # Homogeneous coordinates (N, 4)
    homo = np.hstack([pts, np.ones((num_pts, 1), dtype=np.float64)])
    transformed = (matrix_4x4 @ homo.T).T[:, :3]

    return transformed[0] if single else transformed


# =====================================================================
# Polygon & Facet Operations
# =====================================================================

def polygon_normal(vertices: Union[Sequence[Point3D], np.ndarray]) -> np.ndarray:
    """Compute normalized surface normal of a 3D polygon using Newell's method.

    Works robustly for arbitrary non-degenerate planar or near-planar polygons.
    """
    if isinstance(vertices, np.ndarray):
        pts = vertices
    else:
        pts = np.array([p.to_numpy() if isinstance(p, Point3D) else p for p in vertices], dtype=np.float64)

    n_pts = len(pts)
    if n_pts < 3:
        raise ValueError("Polygon must contain at least 3 vertices.")

    normal = np.zeros(3, dtype=np.float64)
    for i in range(n_pts):
        curr = pts[i]
        nxt = pts[(i + 1) % n_pts]
        normal[0] += (curr[1] - nxt[1]) * (curr[2] + nxt[2])
        normal[1] += (curr[2] - nxt[2]) * (curr[0] + nxt[0])
        normal[2] += (curr[0] - nxt[0]) * (curr[1] + nxt[1])

    norm_mag = np.linalg.norm(normal)
    if norm_mag < 1e-14:
        raise ValueError("Degenerate collinear polygon vertices; cannot determine normal.")
    return normal / norm_mag


def polygon_area(vertices: Union[Sequence[Point3D], np.ndarray]) -> float:
    """Compute exact surface area of a 3D planar polygon.

    Uses the projected cross product formula.
    """
    if isinstance(vertices, np.ndarray):
        pts = vertices
    else:
        pts = np.array([p.to_numpy() if isinstance(p, Point3D) else p for p in vertices], dtype=np.float64)

    n_pts = len(pts)
    if n_pts < 3:
        return 0.0

    normal_unnorm = np.zeros(3, dtype=np.float64)
    for i in range(n_pts):
        curr = pts[i]
        nxt = pts[(i + 1) % n_pts]
        normal_unnorm[0] += (curr[1] - nxt[1]) * (curr[2] + nxt[2])
        normal_unnorm[1] += (curr[2] - nxt[2]) * (curr[0] + nxt[0])
        normal_unnorm[2] += (curr[0] - nxt[0]) * (curr[1] + nxt[1])

    return 0.5 * float(np.linalg.norm(normal_unnorm))


def polygon_centroid(vertices: Union[Sequence[Point3D], np.ndarray]) -> np.ndarray:
    """Calculate the arithmetic mean centroid of polygon vertices."""
    if isinstance(vertices, np.ndarray):
        pts = vertices
    else:
        pts = np.array([p.to_numpy() if isinstance(p, Point3D) else p for p in vertices], dtype=np.float64)
    return np.mean(pts, axis=0)


def is_coplanar(vertices: Union[Sequence[Point3D], np.ndarray], tol: float = 1e-5) -> bool:
    """Check if all vertices of a polygon lie on the same plane within tolerance."""
    if isinstance(vertices, np.ndarray):
        pts = vertices
    else:
        pts = np.array([p.to_numpy() if isinstance(p, Point3D) else p for p in vertices], dtype=np.float64)

    if len(pts) <= 3:
        return True

    try:
        norm = polygon_normal(pts)
    except ValueError:
        return True  # Collinear points are trivially coplanar

    p0 = pts[0]
    displacements = pts[1:] - p0
    distances = np.abs(np.dot(displacements, norm))
    return bool(np.all(distances < tol))


def segments_intersect_2d(
    p1: Union[Sequence[float], np.ndarray],
    p2: Union[Sequence[float], np.ndarray],
    p3: Union[Sequence[float], np.ndarray],
    p4: Union[Sequence[float], np.ndarray],
    tol: float = 1e-8,
) -> bool:
    """Test if two 2D line segments strictly cross each other at an interior point.

    Returns False if they only touch at an endpoint or are disjoint.
    """
    p1_a = np.asarray(p1[:2], dtype=np.float64)
    p2_a = np.asarray(p2[:2], dtype=np.float64)
    p3_a = np.asarray(p3[:2], dtype=np.float64)
    p4_a = np.asarray(p4[:2], dtype=np.float64)

    def cross_2d(v1: np.ndarray, v2: np.ndarray) -> float:
        return float(v1[0] * v2[1] - v1[1] * v2[0])

    d1 = cross_2d(p3_a - p1_a, p2_a - p1_a)
    d2 = cross_2d(p4_a - p1_a, p2_a - p1_a)
    d3 = cross_2d(p1_a - p3_a, p4_a - p3_a)
    d4 = cross_2d(p2_a - p3_a, p4_a - p3_a)

    # Strictly opposite signs indicates crossing
    if ((d1 > tol and d2 < -tol) or (d1 < -tol and d2 > tol)) and \
       ((d3 > tol and d4 < -tol) or (d3 < -tol and d4 > tol)):
        return True

    return False
