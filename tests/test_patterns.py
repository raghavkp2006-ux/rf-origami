import pytest
import numpy as np

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.patterns.degree4_vertex import Degree4VertexPattern
from rf_origami.patterns.waterbomb import WaterbombPattern
from rf_origami.patterns.yoshimura import YoshimuraPattern
from rf_origami.core.crease_pattern import CreaseType


def test_miura_ori_generation():
    generator = MiuraOriPattern()
    # Default is num_cells_x=2, num_cells_y=2
    # Vertices: (2*2+1) * (2*2+1) = 5 * 5 = 25
    # Faces: (2*2) * (2*2) = 16
    # Creases: 5*4 (horiz) + 4*5 (vert) = 40
    pattern = generator.generate()

    assert pattern.num_vertices == 25
    assert pattern.num_faces == 16
    assert pattern.num_creases == 40

    # Verify Kawasaki and Maekawa across all interior vertices
    verification = generator.verify_pattern(pattern)
    assert verification["num_interior_vertices"] == 9  # 3x3 interior grid
    assert verification["kawasaki_passes"] == 9
    assert verification["maekawa_passes"] == 9
    assert verification["is_valid_flat_foldable"] is True


def test_miura_ori_edge_lengths():
    generator = MiuraOriPattern()
    pattern = generator.generate(a=25.0, b=15.0, gamma=60.0)

    # Check rest edge lengths
    for crease in pattern.creases:
        actual_len = pattern.edge_length(crease.u, crease.v)
        if crease.target_length is not None:
            assert actual_len == pytest.approx(crease.target_length, rel=1e-5)


def test_degree4_vertex_generation():
    generator = Degree4VertexPattern()
    pattern = generator.generate(alpha1=65.0, alpha2=115.0, radius=40.0)

    assert pattern.num_vertices == 5  # 1 center + 4 outer
    assert pattern.num_faces == 4
    assert pattern.num_creases == 8  # 4 radial + 4 boundary

    # Center vertex must satisfy Kawasaki and Maekawa
    k_ok, s_even, s_odd = pattern.check_kawasaki_theorem(0)
    assert k_ok
    assert s_even == pytest.approx(180.0, abs=1.0)
    assert s_odd == pytest.approx(180.0, abs=1.0)

    m_ok, m_count, v_count = pattern.check_maekawa_theorem(0)
    assert m_ok
    assert abs(m_count - v_count) == 2


def test_waterbomb_generation():
    generator = WaterbombPattern()
    pattern = generator.generate(num_cells_x=1, num_cells_y=1, cell_width=30.0, cell_height=30.0)

    assert pattern.num_vertices == 9
    assert pattern.num_faces == 8
    # 8 outer boundary + 4 diagonals + 4 cross = 16 creases
    assert pattern.num_creases == 16

    # Verify center vertex has degree 8 (4 diagonals + 4 cross)
    # Center vertex is at (15, 15), index 8
    creases_at_center = pattern.get_creases_at_vertex(8)
    assert len(creases_at_center) == 8


def test_yoshimura_generation():
    generator = YoshimuraPattern()
    pattern = generator.generate(num_cells_x=3, num_cells_y=2, cell_width=20.0, cell_height=15.0)

    assert pattern.num_vertices > 0
    assert pattern.num_faces > 0
    assert pattern.num_creases > 0

    # Check bounding box
    b_min, b_max = pattern.bounding_box()
    assert b_min[0] == pytest.approx(0.0)
    assert b_min[1] == pytest.approx(0.0)
    assert b_max[1] == pytest.approx(30.0)  # 2 rows * 15.0
