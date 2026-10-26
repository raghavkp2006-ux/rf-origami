"""RF Simulation Result Data Model.

Clean, JSON-serializable representation of full-wave numerical electromagnetic
simulation outputs, antenna metrics, and solver configurations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional


@dataclass
class RFSimulationResult:
    """Encapsulates electromagnetic analysis outputs for an origami antenna design."""

    candidate_id: str
    geometry_id: str
    fold_angle_deg: float
    frequencies_ghz: List[float]
    s11_db: List[float]
    zin_real_ohms: List[float]
    zin_imag_ohms: List[float]
    vswr: List[float]
    resonant_frequency_ghz: float
    min_s11_db: float
    bandwidth_mhz: float
    bandwidth_percent: float
    solver_name: str = "MoM_EFIE_Pocklington"
    is_validated_numerical: bool = False
    port_settings: Dict[str, Any] = field(default_factory=dict)
    materials: Dict[str, Any] = field(default_factory=dict)
    mesh_statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to clean dictionary representation."""
        return {
            "candidate_id": self.candidate_id,
            "geometry_id": self.geometry_id,
            "fold_angle_deg": round(float(self.fold_angle_deg), 1),
            "frequencies_ghz": [round(float(f), 4) for f in self.frequencies_ghz],
            "s11_db": [round(float(s), 2) for s in self.s11_db],
            "zin_real_ohms": [round(float(r), 2) for r in self.zin_real_ohms],
            "zin_imag_ohms": [round(float(x), 2) for x in self.zin_imag_ohms],
            "vswr": [round(float(v), 2) for v in self.vswr],
            "metrics": {
                "resonant_frequency_ghz": round(float(self.resonant_frequency_ghz), 4),
                "min_s11_db": round(float(self.min_s11_db), 2),
                "bandwidth_mhz": round(float(self.bandwidth_mhz), 1),
                "bandwidth_percent": round(float(self.bandwidth_percent), 2),
                "status": "NUMERICAL_EM_VALIDATED" if self.is_validated_numerical else "NUMERICAL_EM_NOT_VALIDATED",
            },
            "solver": {
                "name": self.solver_name,
                "is_numerical": True,
                "is_validated": self.is_validated_numerical,
            },
            "port": self.port_settings,
            "materials": self.materials,
            "mesh": self.mesh_statistics,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RFSimulationResult:
        """Deserialize from dictionary."""
        metrics = data.get("metrics", {})
        solver = data.get("solver", {})
        return cls(
            candidate_id=data.get("candidate_id", ""),
            geometry_id=data.get("geometry_id", ""),
            fold_angle_deg=float(data.get("fold_angle_deg", 0.0)),
            frequencies_ghz=data.get("frequencies_ghz", []),
            s11_db=data.get("s11_db", []),
            zin_real_ohms=data.get("zin_real_ohms", []),
            zin_imag_ohms=data.get("zin_imag_ohms", []),
            vswr=data.get("vswr", []),
            resonant_frequency_ghz=float(metrics.get("resonant_frequency_ghz", 0.0)),
            min_s11_db=float(metrics.get("min_s11_db", 0.0)),
            bandwidth_mhz=float(metrics.get("bandwidth_mhz", 0.0)),
            bandwidth_percent=float(metrics.get("bandwidth_percent", 0.0)),
            solver_name=solver.get("name", "MoM_EFIE_Pocklington"),
            is_validated_numerical=bool(solver.get("is_validated", False)),
            port_settings=data.get("port", {}),
            materials=data.get("materials", {}),
            mesh_statistics=data.get("mesh", {}),
        )
