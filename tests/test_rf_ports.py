import pytest
import numpy as np

from rf_origami.rf.ports.lumped_port import LumpedPort


def test_lumped_port_geometry_and_properties():
    port = LumpedPort(
        port_id="TEST_PORT",
        impedance=50.0,
        positive_terminal=np.array([0.0, 1.0, 0.0]),
        negative_terminal=np.array([0.0, -1.0, 0.0]),
    )
    assert port.port_id == "TEST_PORT"
    assert port.impedance == 50.0
    assert port.gap_length == pytest.approx(2.0)
    assert np.allclose(port.position, [0.0, 0.0, 0.0])
    assert np.allclose(port.direction, [0.0, 1.0, 0.0])


def test_lumped_port_validation():
    # Valid port
    p_valid = LumpedPort(
        positive_terminal=np.array([0.0, 0.5, 0.0]),
        negative_terminal=np.array([0.0, -0.5, 0.0]),
    )
    is_ok, errs = p_valid.validate()
    assert is_ok is True
    assert len(errs) == 0

    # Coincident terminals
    p_coincident = LumpedPort(
        positive_terminal=np.array([0.0, 0.0, 0.0]),
        negative_terminal=np.array([0.0, 0.0, 0.0]),
    )
    is_ok, errs = p_coincident.validate()
    assert is_ok is False
    assert any("coincident" in e.lower() for e in errs)

    # Invalid non-positive impedance
    p_bad_z = LumpedPort(
        impedance=-50.0,
        positive_terminal=np.array([0.0, 1.0, 0.0]),
        negative_terminal=np.array([0.0, 0.0, 0.0]),
    )
    is_ok, errs = p_bad_z.validate()
    assert is_ok is False
    assert any("impedance" in e.lower() for e in errs)


def test_lumped_port_factory_and_serialization():
    port = LumpedPort.from_center_and_length(
        center=[10.0, 20.0, 0.0],
        direction=[1.0, 0.0, 0.0],
        gap_length_mm=1.5,
        impedance=75.0,
    )
    assert port.impedance == 75.0
    assert port.gap_length == pytest.approx(1.5)
    assert np.allclose(port.position, [10.0, 20.0, 0.0])

    d = port.to_dict()
    assert d["impedance_ohms"] == 75.0
    assert d["gap_length_mm"] == 1.5
    assert d["is_valid"] is True
