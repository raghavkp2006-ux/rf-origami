"""Geometry gates for antenna fold sweeps (coordinates in millimetres)."""
import numpy as np


def validate_fold_mesh(mesh, reference=None, relative_edge_tolerance=1e-6):
    vertices = mesh.vertices
    if not len(vertices) or not mesh.faces or not np.all(np.isfinite(vertices)):
        raise ValueError("Fold mesh requires finite vertices and nonempty faces.")
    edges = set()
    minimum_area = float("inf")
    for face in mesh.faces:
        if len(face) < 3 or len(set(face)) != len(face) or any(i < 0 or i >= len(vertices) for i in face):
            raise ValueError("Fold mesh contains invalid face indices.")
        for i, j in zip(face, face[1:] + face[:1]):
            edges.add(tuple(sorted((i, j))))
        for i in range(1, len(face) - 1):
            a, b, c = vertices[[face[0], face[i], face[i + 1]]]
            area = float(np.linalg.norm(np.cross(b - a, c - a)) / 2)
            minimum_area = min(minimum_area, area)
    lengths = np.array([np.linalg.norm(vertices[i] - vertices[j]) for i, j in sorted(edges)])
    if np.any(lengths <= 1e-9) or minimum_area <= 1e-12:
        raise ValueError("Fold mesh contains collapsed edges or triangles.")
    drift = 0.0
    if reference is not None:
        if reference.faces != mesh.faces or reference.vertices.shape != vertices.shape:
            raise ValueError("Fold mesh topology changed relative to the reference.")
        ref = reference.vertices
        original = np.array([np.linalg.norm(ref[i] - ref[j]) for i, j in sorted(edges)])
        if np.any(original <= 1e-9):
            raise ValueError("Reference mesh contains collapsed edges.")
        drift = float(np.max(np.abs(lengths - original) / original))
        if drift > relative_edge_tolerance:
            raise ValueError(f"Fold mesh changes panel edge lengths by {drift:.3%}.")
    return {"passed": True, "minimum_triangle_area_mm2": minimum_area,
            "minimum_edge_length_mm": float(lengths.min()), "max_relative_edge_drift": drift}
