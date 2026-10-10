import pytest
import numpy as np

from rf_origami.core.crease_pattern import (
    CreaseType,
    Crease,
    Face,
    CreasePattern,
)


def test_crease_type_parsing():
    assert CreaseType.from_str("M") == CreaseType.MOUNTAIN
    assert CreaseType.from_str("valley") == CreaseType.VALLEY
    assert CreaseType.from_str("B") == CreaseType.BOUNDARY
    assert CreaseType.from_str("f") == CreaseType.FACET


def test_crease_canonical_key():
    c1 = Crease(u=5, v=2, crease_type=CreaseType.MOUNTAIN)
    assert c1.u == 2
    assert c1.v == 5
    assert c1.key == (2, 5)


def test_crease_pattern_construction():
    cp = CreasePattern()
    # Create 4 vertices of a square
    v0 = cp.add_vertex(0.0, 0.0)
    v1 = cp.add_vertex(1.0, 0.0)
    v2 = cp.add_vertex(1.0, 1.0)
    v3 = cp.add_vertex(0.0, 1.0)

    assert cp.num_vertices == 4

    # Add boundary edges
    cp.add_crease(v0, v1, CreaseType.BOUNDARY)
    cp.add_crease(v1, v2, CreaseType.BOUNDARY)
    cp.add_crease(v2, v3, CreaseType.BOUNDARY)
    cp.add_crease(v3, v0, CreaseType.BOUNDARY)
    # Add diagonal crease
    cp.add_crease(v0, v2, CreaseType.MOUNTAIN, fold_angle=0.5)

    assert cp.num_creases == 5
    assert cp.edge_length(v0, v2) == pytest.approx(np.sqrt(2.0))

    # Add faces
    f1 = cp.add_face([v0, v1, v2], material_tag="conductor")
    f2 = cp.add_face([v0, v2, v3], material_tag="substrate")

    assert cp.num_faces == 2
    assert f1.material_tag == "conductor"
    assert f2.material_tag == "substrate"


def test_kawasaki_and_maekawa_theorems():
    # Construct a classic degree-4 flat-foldable vertex at the origin
    # Angles: 60, 120, 60, 120 (sum: 60+60=120? No: 60+120=180 and 120+60=180!)
    # Vectors at angles: 0 deg, 60 deg, 180 deg, 240 deg:
    # Sector 1 (0 to 60) = 60 deg
    # Sector 2 (60 to 180) = 120 deg
    # Sector 3 (180 to 240) = 60 deg
    # Sector 4 (240 to 360) = 120 deg
    # Alternating sums: 60 + 60 = 120 (Wait: sector 1 + sector 3 = 60 + 60 = 120 != 180).
    # For Kawasaki: sector 1 + sector 3 = 180!
    # Let's choose:
    # Sector 1 = 80 deg (0 to 80)
    # Sector 2 = 100 deg (80 to 180)
    # Sector 3 = 100 deg (180 to 280)
    # Sector 4 = 80 deg (280 to 360)
    # Alternating sums:
    # sector 1 + sector 3 = 80 + 100 = 180 deg!
    # sector 2 + sector 4 = 100 + 80 = 180 deg!

    cp = CreasePattern()
    v_center = cp.add_vertex(0.0, 0.0)

    # Rays
    angles_deg = [0.0, 80.0, 180.0, 280.0]
    ray_indices = []
    for deg in angles_deg:
        rad = np.radians(deg)
        ray_indices.append(cp.add_vertex(np.cos(rad), np.sin(rad)))

    # Maekawa: 3 Mountain, 1 Valley -> |3 - 1| = 2
    cp.add_crease(v_center, ray_indices[0], CreaseType.MOUNTAIN)
    cp.add_crease(v_center, ray_indices[1], CreaseType.MOUNTAIN)
    cp.add_crease(v_center, ray_indices[2], CreaseType.MOUNTAIN)
    cp.add_crease(v_center, ray_indices[3], CreaseType.VALLEY)

    # Verify Kawasaki's theorem
    k_valid, s_even, s_odd = cp.check_kawasaki_theorem(v_center)
    assert k_valid
    assert s_even == pytest.approx(180.0, abs=1.0)
    assert s_odd == pytest.approx(180.0, abs=1.0)

    # Verify Maekawa's theorem
    m_valid, m_count, v_count = cp.check_maekawa_theorem(v_center)
    assert m_valid
    assert m_count == 3
    assert v_count == 1


def test_serialization():
    cp = CreasePattern()
    v0 = cp.add_vertex(0.0, 0.0)
    v1 = cp.add_vertex(10.0, 0.0)
    v2 = cp.add_vertex(10.0, 10.0)
    cp.add_crease(v0, v1, CreaseType.BOUNDARY)
    cp.add_crease(v1, v2, CreaseType.MOUNTAIN, fold_angle=0.8)
    cp.add_face([v0, v1, v2], material_tag="copper")

    data = cp.to_dict()
    cp_loaded = CreasePattern.from_dict(data)

    assert cp_loaded.num_vertices == 3
    assert cp_loaded.num_creases == 2
    assert cp_loaded.num_faces == 1
    assert cp_loaded.faces[0].material_tag == "copper"
    assert cp_loaded.get_crease(v1, v2).fold_angle == pytest.approx(0.8)
