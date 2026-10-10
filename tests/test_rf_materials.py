import pytest
import math
from rf_origami.rf.materials.material import (
    Material,
    MaterialLibrary,
    EPSILON_0,
    MU_0,
    C_0,
    ETA_0,
)


def test_material_creation_and_validation():
    # Valid dielectric
    mat = Material(
        name="CustomDielectric",
        relative_permittivity=3.5,
        relative_permeability=1.0,
        loss_tangent=0.01,
        thickness_mm=0.8,
    )
    assert mat.name == "CustomDielectric"
    assert mat.relative_permittivity == 3.5
    assert not mat.is_conductor

    # Invalid permittivity <= 0
    with pytest.raises(ValueError, match="Relative permittivity"):
        Material(name="Invalid", relative_permittivity=-1.0)

    # Invalid negative conductivity
    with pytest.raises(ValueError, match="Conductivity"):
        Material(name="Invalid", conductivity=-10.0)


def test_complex_permittivity_and_skin_depth():
    copper = MaterialLibrary.get("copper")
    assert copper.is_conductor
    assert copper.conductivity > 1e7

    f = 2.4e9 # 2.4 GHz
    eps = copper.complex_permittivity(f)
    assert eps.imag < 0.0 # Lossy imaginary part

    delta = copper.skin_depth(f)
    # At 2.4 GHz, copper skin depth is ~1.3 microns (1.3e-6 m)
    assert 1.0e-6 < delta < 2.0e-6


def test_material_library_lookup():
    air = MaterialLibrary.get("air")
    assert air.relative_permittivity == 1.0
    assert air.is_lossless

    kapton = MaterialLibrary.get("kapton")
    assert kapton.relative_permittivity == 3.4
    assert kapton.loss_tangent == 0.002

    fr4 = MaterialLibrary.get("fr4")
    assert fr4.relative_permittivity == 4.4

    with pytest.raises(KeyError):
        MaterialLibrary.get("nonexistent_material_123")


def test_material_serialization():
    mat = Material(
        name="TestMat",
        relative_permittivity=2.2,
        loss_tangent=0.001,
        thickness_mm=1.5,
    )
    d = mat.to_dict()
    assert d["name"] == "TestMat"
    assert d["relative_permittivity"] == 2.2

    mat_loaded = Material.from_dict(d)
    assert mat_loaded.name == mat.name
    assert mat_loaded.relative_permittivity == mat.relative_permittivity
    assert mat_loaded.thickness_mm == mat.thickness_mm
