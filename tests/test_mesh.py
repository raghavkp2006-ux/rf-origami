import pytest
import numpy as np

from rf_origami.core.mesh import FoldedMesh


def test_folded_mesh_properties():
    # A single unit square with 2 triangles
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    faces = [
        (0, 1, 2),
        (0, 2, 3),
    ]
    materials = ["copper", "substrate"]

    mesh = FoldedMesh(vertices=vertices, faces=faces, face_materials=materials)

    assert mesh.num_vertices == 4
    assert mesh.num_faces == 2

    # Normals should be +Z
    normals = mesh.compute_face_normals()
    assert np.allclose(normals[0], [0.0, 0.0, 1.0])
    assert np.allclose(normals[1], [0.0, 0.0, 1.0])

    # Area
    assert mesh.compute_total_surface_area() == pytest.approx(1.0)
    assert mesh.compute_material_surface_area("copper") == pytest.approx(0.5)
    assert mesh.compute_material_surface_area("substrate") == pytest.approx(0.5)

    # Dimensions
    dims = mesh.dimensions()
    assert np.allclose(dims, [1.0, 1.0, 0.0])


def test_mesh_triangulation():
    # Quad face
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 2.0, 0.0],
        [0.0, 2.0, 0.0],
    ])
    faces = [(0, 1, 2, 3)]
    materials = ["conductor"]

    mesh = FoldedMesh(vertices=vertices, faces=faces, face_materials=materials)
    tri_mesh = mesh.to_triangulated()

    assert tri_mesh.num_faces == 2
    assert all(len(f) == 3 for f in tri_mesh.faces)
    assert tri_mesh.compute_total_surface_area() == pytest.approx(4.0)
    assert tri_mesh.face_materials == ["conductor", "conductor"]
