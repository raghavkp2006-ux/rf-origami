import pytest
import numpy as np

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import MaterialLibrary
from rf_origami.rf.geometry.rf_object import (
    ConductorSurface,
    SubstrateSurface,
    GroundPlane,
    RFGeometryModel,
)
from rf_origami.rf.geometry.converter import RFGeometryConverter
from rf_origami.rf.mesh.discretization import EMDiscretization


def test_rf_object_creation_and_metrics():
    # Square 20x20 mm conductor patch
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [20.0, 0.0, 0.0],
        [20.0, 20.0, 0.0],
        [0.0, 20.0, 0.0],
    ])
    faces = [[0, 1, 2, 3]]

    cond = ConductorSurface(
        object_id="patch_1",
        vertices=vertices,
        faces=faces,
        material=MaterialLibrary.get("copper"),
        parent_candidate_id="CAND-001",
        fold_angle_deg=0.0,
    )
    assert cond.surface_area() == pytest.approx(400.0)
    assert cond.object_type.value == "conductor"

    b_min, b_max = cond.bounding_box()
    assert np.allclose(b_min, [0.0, 0.0, 0.0])
    assert np.allclose(b_max, [20.0, 20.0, 0.0])


def test_rf_geometry_converter_from_folded_mesh():
    gen = MiuraOriPattern()
    pattern = gen.generate(a=25.0, b=20.0, gamma=60.0, num_cells_x=1, num_cells_y=1)

    # Tag face 0 as conductor, face 1 as ground, rest substrate
    pattern.faces[0].material_tag = "conductor"
    pattern.faces[1].material_tag = "ground"

    folded = FoldingEngine.fold(
        pattern_type="miura_ori",
        crease_pattern=pattern,
        params={"a": 25.0, "b": 20.0, "gamma": 60.0, "num_cells_x": 1, "num_cells_y": 1},
        fold_angle_deg=35.0,
    )
    folded._face_materials = [f.material_tag for f in pattern.faces]

    rf_model = RFGeometryConverter.from_folded_mesh(
        folded_mesh=folded,
        parent_candidate_id="CAND-TEST",
        fold_angle_deg=35.0,
    )

    assert len(rf_model.conductors) == 1
    assert len(rf_model.ground_planes) == 1
    assert len(rf_model.substrates) == 1
    assert rf_model.total_conductor_area() > 0.0
    assert rf_model.total_ground_area() > 0.0
    assert rf_model.total_substrate_area() > 0.0

    d = rf_model.to_dict()
    assert d["parent_candidate_id"] == "CAND-TEST"
    assert d["fold_angle_deg"] == 35.0
    assert len(d["objects"]) >= 3


def test_em_discretization_generation():
    gen = MiuraOriPattern()
    pattern = gen.generate(a=30.0, b=20.0, gamma=60.0, num_cells_x=2, num_cells_y=1)
    folded = FoldingEngine.fold(
        pattern_type="miura_ori",
        crease_pattern=pattern,
        params={"a": 30.0, "b": 20.0, "gamma": 60.0, "num_cells_x": 2, "num_cells_y": 1},
        fold_angle_deg=30.0,
    )
    rf_model = RFGeometryConverter.from_folded_mesh(folded)

    discretization = EMDiscretization.from_rf_geometry(rf_model, target_segment_length_mm=8.0)
    assert discretization.num_segments > 0
    assert discretization.total_length_mm > 0.0
    assert 0 <= discretization.port_segment_index < discretization.num_segments

    centers = discretization.get_centers()
    assert centers.shape == (discretization.num_segments, 3)
