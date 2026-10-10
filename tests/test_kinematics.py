import math
import pytest
import numpy as np

from rf_origami.folding.kinematics import MiuraKinematics
from rf_origami.core.geometry import is_coplanar, polygon_area


def test_miura_kinematics_flat_state():
    solver = MiuraKinematics(a=20.0, b=20.0, gamma_deg=60.0)
    mesh = solver.fold(nx=1, ny=1, rho=0.0)

    # In flat state, max z must be 0
    b_min, b_max = mesh.bounding_box()
    assert b_max[2] == pytest.approx(0.0, abs=1e-6)
    assert b_min[2] == pytest.approx(0.0, abs=1e-6)


def test_miura_kinematics_isometry():
    """Verify rigid origami isometry: all edge lengths, face planarity, and areas are strictly preserved."""
    a = 25.0
    b = 18.0
    gamma = 65.0
    solver = MiuraKinematics(a=a, b=b, gamma_deg=gamma)

    expected_facet_area = a * b * math.sin(math.radians(gamma))

    # Test at multiple intermediate folding ratios
    for rho in [0.1, 0.3, 0.5, 0.7, 0.85]:
        mesh = solver.fold(nx=2, ny=2, rho=rho)
        vertices = mesh.vertices

        # 1. Height should increase with rho
        b_min, b_max = mesh.bounding_box()
        assert b_max[2] > 0.0

        # 2. Every facet must be planar and have exact area
        for face_v in mesh.faces:
            face_pts = vertices[list(face_v)]
            assert is_coplanar(face_pts, tol=1e-5)
            area = polygon_area(face_pts)
            assert area == pytest.approx(expected_facet_area, rel=1e-4)

        # 3. Total surface area must equal exactly 16 * facet_area
        total_area = mesh.compute_total_surface_area()
        assert total_area == pytest.approx(16 * expected_facet_area, rel=1e-4)


def test_miura_kinematics_edge_lengths():
    """Test that individual edge lengths match a and b across folding states."""
    a = 30.0
    b = 20.0
    solver = MiuraKinematics(a=a, b=b, gamma_deg=60.0)

    for rho in [0.2, 0.6]:
        mesh = solver.fold(nx=1, ny=1, rho=rho)
        verts = mesh.vertices

        # Facet 0 vertices: (v0, v1, v2, v3)
        f0 = mesh.faces[0]
        # v0 to v1 is horizontal edge (length b)
        len_b = np.linalg.norm(verts[f0[1]] - verts[f0[0]])
        assert len_b == pytest.approx(b, rel=1e-5)

        # v0 to v3 is zig-zag edge (length a)
        len_a = np.linalg.norm(verts[f0[3]] - verts[f0[0]])
        assert len_a == pytest.approx(a, rel=1e-5)
