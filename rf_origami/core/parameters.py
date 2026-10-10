"""Parameter definition, validation, and design-space sampling.

Provides strongly-typed parameters with range validation, engineering units,
and grid/random sampling generators for origami candidate designs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import itertools
import json
from typing import Any, Dict, ItemsView, Iterator, KeysView, List, Optional, Sequence, Tuple, Union, ValuesView
import numpy as np


class ParameterType(str, Enum):
    """Supported parameter types."""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"


@dataclass
class Parameter:
    """A typed, bounded parameter for origami design generation."""
    name: str
    default: Any
    value: Any = None
    min_val: Optional[Union[float, int]] = None
    max_val: Optional[Union[float, int]] = None
    step: Optional[Union[float, int]] = None
    unit: str = ""
    category: str = "general"
    description: str = ""
    param_type: ParameterType = ParameterType.FLOAT

    def __post_init__(self) -> None:
        if isinstance(self.param_type, str):
            self.param_type = ParameterType(self.param_type)
        if self.value is None:
            self.value = self.default
        self.validate(self.value)

    def validate(self, val: Any) -> None:
        """Verify that value conforms to parameter type and boundary constraints."""
        if val is None:
            raise ValueError(f"Parameter '{self.name}' value cannot be None.")

        if self.param_type == ParameterType.FLOAT:
            if not isinstance(val, (int, float, np.floating, np.integer)):
                raise TypeError(f"Parameter '{self.name}' must be float/number, got {type(val).__name__}")
            v = float(val)
            if self.min_val is not None and v < self.min_val:
                raise ValueError(f"Parameter '{self.name}' value {v} < min_val {self.min_val}")
            if self.max_val is not None and v > self.max_val:
                raise ValueError(f"Parameter '{self.name}' value {v} > max_val {self.max_val}")

        elif self.param_type == ParameterType.INT:
            if not isinstance(val, (int, np.integer)) or isinstance(val, bool):
                raise TypeError(f"Parameter '{self.name}' must be int, got {type(val).__name__}")
            v_int = int(val)
            if self.min_val is not None and v_int < self.min_val:
                raise ValueError(f"Parameter '{self.name}' value {v_int} < min_val {self.min_val}")
            if self.max_val is not None and v_int > self.max_val:
                raise ValueError(f"Parameter '{self.name}' value {v_int} > max_val {self.max_val}")

        elif self.param_type == ParameterType.BOOL:
            if not isinstance(val, (bool, np.bool_)):
                raise TypeError(f"Parameter '{self.name}' must be bool, got {type(val).__name__}")

        elif self.param_type == ParameterType.STRING:
            if not isinstance(val, str):
                raise TypeError(f"Parameter '{self.name}' must be string, got {type(val).__name__}")

    def set_value(self, new_val: Any) -> None:
        """Validate and update the parameter value."""
        self.validate(new_val)
        if self.param_type == ParameterType.FLOAT:
            self.value = float(new_val)
        elif self.param_type == ParameterType.INT:
            self.value = int(new_val)
        else:
            self.value = new_val

    def get_grid(self, num_points: int) -> np.ndarray:
        """Generate evenly spaced values across [min_val, max_val]."""
        if self.min_val is None or self.max_val is None:
            raise ValueError(f"Cannot generate grid for '{self.name}': bounds not set.")
        if self.param_type == ParameterType.INT:
            pts = np.linspace(self.min_val, self.max_val, num_points)
            return np.unique(np.round(pts).astype(int))
        return np.linspace(self.min_val, self.max_val, num_points)

    def sample_uniform(self, rng: Optional[np.random.Generator] = None) -> Union[float, int, bool, str]:
        """Sample a uniform random valid value."""
        if rng is None:
            rng = np.random.default_rng()
        if self.min_val is None or self.max_val is None:
            return self.value

        if self.param_type == ParameterType.FLOAT:
            return float(rng.uniform(self.min_val, self.max_val))
        elif self.param_type == ParameterType.INT:
            return int(rng.integers(int(self.min_val), int(self.max_val) + 1))
        elif self.param_type == ParameterType.BOOL:
            return bool(rng.choice([True, False]))
        return self.value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize parameter definition."""
        return {
            "name": self.name,
            "value": self.value,
            "default": self.default,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "step": self.step,
            "unit": self.unit,
            "category": self.category,
            "description": self.description,
            "param_type": self.param_type.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Parameter:
        return cls(
            name=data["name"],
            default=data["default"],
            value=data.get("value"),
            min_val=data.get("min_val"),
            max_val=data.get("max_val"),
            step=data.get("step"),
            unit=data.get("unit", ""),
            category=data.get("category", "general"),
            description=data.get("description", ""),
            param_type=ParameterType(data.get("param_type", "float")),
        )


class ParameterSet:
    """A collection of validated parameters defining an origami configuration."""

    def __init__(self, parameters: Optional[Sequence[Parameter]] = None) -> None:
        self._params: Dict[str, Parameter] = {}
        if parameters:
            for p in parameters:
                self.add(p)

    def add(self, param: Parameter) -> None:
        """Register a parameter in the set."""
        self._params[param.name] = param

    def get(self, name: str, default: Any = None) -> Any:
        """Retrieve a parameter's current value."""
        if name in self._params:
            return self._params[name].value
        return default

    def get_param(self, name: str) -> Parameter:
        """Retrieve the Parameter object."""
        if name not in self._params:
            raise KeyError(f"Parameter '{name}' not found in ParameterSet.")
        return self._params[name]

    def set_value(self, name: str, val: Any) -> None:
        """Update value for existing parameter."""
        if name not in self._params:
            raise KeyError(f"Parameter '{name}' not found in ParameterSet.")
        self._params[name].set_value(val)

    def update(self, **kwargs: Any) -> None:
        """Update multiple parameter values, ignoring keys not defined in the set."""
        for k, v in kwargs.items():
            if k in self._params:
                self.set_value(k, v)

    def __getitem__(self, name: str) -> Any:
        return self._params[name].value

    def __setitem__(self, name: str, val: Any) -> None:
        self.set_value(name, val)

    def __contains__(self, name: str) -> bool:
        return name in self._params

    def __iter__(self) -> Iterator[str]:
        return iter(self._params)

    def keys(self) -> KeysView[str]:
        """Return view of parameter names."""
        return self._params.keys()

    def values(self) -> ValuesView[Parameter]:
        """Return view of Parameter objects."""
        return self._params.values()

    def items(self) -> ItemsView[str, Parameter]:
        """Return view of (name, Parameter) pairs."""
        return self._params.items()

    def __len__(self) -> int:
        return len(self._params)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v.value}{v.unit}" for k, v in self._params.items())
        return f"ParameterSet({items})"

    def to_values_dict(self) -> Dict[str, Any]:
        """Return simple dictionary of parameter name -> current value."""
        return {k: p.value for k, p in self._params.items()}

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization of all parameter definitions."""
        return {k: p.to_dict() for k, p in self._params.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ParameterSet:
        pset = cls()
        for k, p_data in data.items():
            pset.add(Parameter.from_dict(p_data))
        return pset

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> ParameterSet:
        data = json.loads(json_str)
        return cls.from_dict(data)

    def copy(self) -> ParameterSet:
        """Return a deep copy of this parameter set."""
        return ParameterSet([
            Parameter.from_dict(p.to_dict()) for p in self._params.values()
        ])

    # -----------------------------------------------------------------
    # Design Space Sweeps & Candidate Generation
    # -----------------------------------------------------------------

    def generate_grid_sweep(
        self,
        grid_specs: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Generate Cartesian product candidate values for selected parameters.

        Args:
            grid_specs: Dict mapping parameter names to number of grid evaluation points.
                        Example: {'fold_angle': 5, 'a': 3}

        Returns:
            List of dictionaries containing full parameter sets for each candidate.
        """
        keys = list(grid_specs.keys())
        grids = []
        for k in keys:
            if k not in self._params:
                raise KeyError(f"Parameter '{k}' not found.")
            grids.append(self._params[k].get_grid(grid_specs[k]))

        candidates = []
        base_values = self.to_values_dict()
        for combination in itertools.product(*grids):
            candidate = dict(base_values)
            for k, val in zip(keys, combination):
                candidate[k] = val
            candidates.append(candidate)
        return candidates

    def generate_random_samples(
        self,
        num_samples: int,
        param_names: Optional[Sequence[str]] = None,
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate random candidate parameter dictionaries within bounds.

        Args:
            num_samples: Number of sample configurations to generate.
            param_names: Specific parameters to vary; if None, all bounded parameters are varied.
            seed: Random seed for reproducibility.
        """
        rng = np.random.default_rng(seed)
        if param_names is None:
            active_keys = [
                k for k, p in self._params.items()
                if p.min_val is not None and p.max_val is not None
            ]
        else:
            active_keys = list(param_names)

        candidates = []
        base_values = self.to_values_dict()

        for _ in range(num_samples):
            candidate = dict(base_values)
            for k in active_keys:
                candidate[k] = self._params[k].sample_uniform(rng)
            candidates.append(candidate)

        return candidates
