import pytest
import numpy as np

from rf_origami.core.parameters import (
    ParameterType,
    Parameter,
    ParameterSet,
)


def test_parameter_validation():
    # Valid float parameter
    p_len = Parameter(name="length", default=10.0, min_val=1.0, max_val=50.0, unit="mm")
    assert p_len.value == 10.0

    p_len.set_value(25.5)
    assert p_len.value == 25.5

    # Out of bounds
    with pytest.raises(ValueError, match="min_val"):
        p_len.set_value(0.5)

    with pytest.raises(ValueError, match="max_val"):
        p_len.set_value(100.0)

    # Type error
    with pytest.raises(TypeError):
        p_len.set_value("not_a_number")


def test_parameter_int_and_bool():
    p_count = Parameter(name="num_cells", default=3, min_val=1, max_val=10, param_type=ParameterType.INT)
    assert p_count.value == 3
    p_count.set_value(5)
    assert p_count.value == 5

    with pytest.raises(TypeError):
        p_count.set_value(3.5)

    p_bool = Parameter(name="closed", default=False, param_type=ParameterType.BOOL)
    assert p_bool.value is False
    p_bool.set_value(True)
    assert p_bool.value is True


def test_parameter_set_operations():
    p_set = ParameterSet([
        Parameter(name="a", default=20.0, min_val=5.0, max_val=50.0, unit="mm"),
        Parameter(name="b", default=15.0, min_val=5.0, max_val=50.0, unit="mm"),
        Parameter(name="gamma", default=60.0, min_val=30.0, max_val=80.0, unit="deg"),
        Parameter(name="theta", default=45.0, min_val=0.0, max_val=90.0, unit="deg"),
    ])

    assert len(p_set) == 4
    assert p_set["a"] == 20.0

    p_set.update(a=25.0, theta=60.0)
    assert p_set["a"] == 25.0
    assert p_set["theta"] == 60.0

    values = p_set.to_values_dict()
    assert values["a"] == 25.0
    assert values["gamma"] == 60.0


def test_parameter_sampling_and_sweeps():
    p_set = ParameterSet([
        Parameter(name="a", default=10.0, min_val=10.0, max_val=20.0),
        Parameter(name="b", default=5.0, min_val=5.0, max_val=15.0),
    ])

    # Grid sweep: 2 points for 'a' (10, 20), 3 points for 'b' (5, 10, 15) -> 6 candidates
    candidates = p_set.generate_grid_sweep({"a": 2, "b": 3})
    assert len(candidates) == 6
    assert candidates[0]["a"] == 10.0
    assert candidates[0]["b"] == 5.0
    assert candidates[-1]["a"] == 20.0
    assert candidates[-1]["b"] == 15.0

    # Random sampling
    rand_candidates = p_set.generate_random_samples(num_samples=10, seed=42)
    assert len(rand_candidates) == 10
    for cand in rand_candidates:
        assert 10.0 <= cand["a"] <= 20.0
        assert 5.0 <= cand["b"] <= 15.0


def test_parameter_json_serialization():
    p_set = ParameterSet([
        Parameter(name="freq", default=2.4, min_val=1.0, max_val=10.0, unit="GHz", description="Center RF freq"),
    ])

    json_str = p_set.to_json()
    p_loaded = ParameterSet.from_json(json_str)

    assert len(p_loaded) == 1
    assert p_loaded["freq"] == 2.4
    param = p_loaded.get_param("freq")
    assert param.unit == "GHz"
    assert param.description == "Center RF freq"
