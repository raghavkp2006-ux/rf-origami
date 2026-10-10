import math
import numpy as np
import pytest

from rf_origami.core.geometry import (
    Vector3D,
    Point3D,
    rotation_matrix_axis_angle,
    rotation_matrix_euler,
    create_affine_matrix,
    transform_points,
    polygon_normal,
    polygon_area,
    polygon_centroid,
    is_coplanar,
)


def test_vector3d_basic_arithmetic():
    v1 = Vector3D(1.0, 2.0, 3.0)
    v2 = Vector3D(4.0, 5.0, 6.0)

    # Addition & Subtraction
    v_add = v1 + v2
    assert v_add == Vector3D(5.0, 7.0, 9.0)
    v_sub = v2 - v1
    assert v_sub == Vector3D(3.0, 3.0, 3.0)

    # Scaling
    v_mul = v1 * 2.0
    assert v_mul == Vector3D(2.0, 4.0, 6.0)
    v_div = v1 / 2.0
    assert v_div == Vector3D(0.5, 1.0, 1.5)

    # Negation
    assert -v1 == Vector3D(-1.0, -2.0, -3.0)


def test_vector3d_dot_and_cross():
    # Perpendicular unit vectors
    vx = Vector3D(1.0, 0.0, 0.0)
    vy = Vector3D(0.0, 1.0, 0.0)

    assert vx.dot(vy) == pytest.approx(0.0)
    vz = vx.cross(vy)
    assert vz == Vector3D(0.0, 0.0, 1.0)
    assert vx.angle_to(vy) == pytest.approx(math.pi / 2)


def test_point3d_operations():
    p1 = Point3D(0.0, 0.0, 0.0)
    p2 = Point3D(3.0, 4.0, 0.0)

    assert p1.distance_to(p2) == pytest.approx(5.0)
    vec = p1.vector_to(p2)
    assert vec == Vector3D(3.0, 4.0, 0.0)

    p3 = p1.translate(Vector3D(1.0, 1.0, 1.0))
    assert p3 == Point3D(1.0, 1.0, 1.0)


def test_rotation_matrix_axis_angle():
    # 90 degree rotation about Z axis
    axis = Vector3D(0.0, 0.0, 1.0)
    R = rotation_matrix_axis_angle(axis, math.pi / 2)

    v_x = np.array([1.0, 0.0, 0.0])
    v_rotated = R @ v_x
    assert np.allclose(v_rotated, [0.0, 1.0, 0.0], atol=1e-7)


def test_affine_transformation():
    # Translate by (10, 20, 30)
    T = create_affine_matrix(translation=[10.0, 20.0, 30.0])
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    transformed = transform_points(pts, T)

    assert np.allclose(transformed[0], [10.0, 20.0, 30.0])
    assert np.allclose(transformed[1], [11.0, 22.0, 33.0])


def test_polygon_normal_and_area():
    # Square in XY plane of side 2 (corners: (0,0), (2,0), (2,2), (0,2))
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 2.0, 0.0],
        [0.0, 2.0, 0.0],
    ])

    normal = polygon_normal(vertices)
    assert np.allclose(normal, [0.0, 0.0, 1.0], atol=1e-7)

    area = polygon_area(vertices)
    assert area == pytest.approx(4.0)

    centroid = polygon_centroid(vertices)
    assert np.allclose(centroid, [1.0, 1.0, 0.0])


def test_coplanarity():
    planar_quad = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    assert is_coplanar(planar_quad)

    non_planar_quad = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 1.0],  # out of plane
    ])
    assert not is_coplanar(non_planar_quad)


def test_segments_intersect_2d():
    from rf_origami.core.geometry import segments_intersect_2d
    # Crossing segments (X shape)
    assert segments_intersect_2d([0, 0], [2, 2], [0, 2], [2, 0]) is True

    # Parallel non-intersecting segments
    assert segments_intersect_2d([0, 0], [2, 0], [0, 1], [2, 1]) is False

    # Touching at endpoint only (not interior intersection)
    assert segments_intersect_2d([0, 0], [1, 1], [1, 1], [2, 0]) is False

    # T-junction touching
    assert segments_intersect_2d([0, 0], [2, 0], [1, 0], [1, 1]) is False
