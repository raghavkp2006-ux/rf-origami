"""RF Materials System for standalone electromagnetic analysis.

Defines dielectric, conductor, and substrate constitutive parameters
(εr, μr, σ, tanδ, thickness) without commercial software dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, Optional


# Physical Constants in SI units
EPSILON_0 = 8.8541878128e-12  # F/m (Permittivity of free space)
MU_0 = 1.25663706212e-6       # H/m (Permeability of free space)
C_0 = 299792458.0             # m/s (Speed of light in vacuum)
ETA_0 = 376.730313668         # Ohms (Intrinsic wave impedance of free space)


@dataclass
class Material:
    """Constitutive electromagnetic material definition."""

    name: str
    relative_permittivity: float = 1.0  # εr (real part)
    relative_permeability: float = 1.0  # μr (real part)
    conductivity: float = 0.0           # σ [S/m]
    loss_tangent: float = 0.0           # tan δ (dielectric loss)
    thickness_mm: float = 0.0           # Physical layer thickness in mm
    color_hex: str = "#38bdf8"
    description: str = ""

    def __post_init__(self) -> None:
        if self.relative_permittivity <= 0.0:
            raise ValueError(f"Relative permittivity εr must be > 0 (got {self.relative_permittivity})")
        if self.relative_permeability <= 0.0:
            raise ValueError(f"Relative permeability μr must be > 0 (got {self.relative_permeability})")
        if self.conductivity < 0.0:
            raise ValueError(f"Conductivity σ must be >= 0 (got {self.conductivity})")
        if self.loss_tangent < 0.0:
            raise ValueError(f"Loss tangent tanδ must be >= 0 (got {self.loss_tangent})")

    @property
    def is_conductor(self) -> bool:
        """Return True if conductivity is high enough to be treated as a conductor."""
        return self.conductivity > 1e4 or "pec" in self.name.lower() or "copper" in self.name.lower()

    @property
    def is_lossless(self) -> bool:
        """Return True if material has zero dielectric and ohmic losses."""
        return self.loss_tangent == 0.0 and self.conductivity == 0.0

    def complex_permittivity(self, frequency_hz: float) -> complex:
        """Compute complex permittivity ε = ε' - j ε'' at frequency f.

        ε' = ε_0 * ε_r
        ε'' = ε_0 * ε_r * tan δ + σ / (2π f)
        """
        if frequency_hz <= 0.0:
            raise ValueError("Frequency must be positive.")
        omega = 2.0 * math.pi * frequency_hz
        eps_prime = EPSILON_0 * self.relative_permittivity
        eps_double_prime = eps_prime * self.loss_tangent + (self.conductivity / omega)
        return complex(eps_prime, -eps_double_prime)

    def skin_depth(self, frequency_hz: float) -> float:
        """Calculate conductor skin depth δ = sqrt(2 / (ω μ σ)) in meters.

        Returns float('inf') if conductivity is zero.
        """
        if self.conductivity <= 0.0 or frequency_hz <= 0.0:
            return float("inf")
        omega = 2.0 * math.pi * frequency_hz
        mu = MU_0 * self.relative_permeability
        return math.sqrt(2.0 / (omega * mu * self.conductivity))

    def wave_impedance(self, frequency_hz: float) -> complex:
        """Calculate intrinsic wave impedance η = sqrt(μ / ε) in Ohms."""
        eps = self.complex_permittivity(frequency_hz)
        mu = MU_0 * self.relative_permeability
        # complex sqrt with branch cut on negative real axis
        import cmath
        return cmath.sqrt(mu / eps)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize material parameters to dictionary."""
        return {
            "name": self.name,
            "relative_permittivity": self.relative_permittivity,
            "relative_permeability": self.relative_permeability,
            "conductivity": self.conductivity,
            "loss_tangent": self.loss_tangent,
            "thickness_mm": self.thickness_mm,
            "color_hex": self.color_hex,
            "is_conductor": self.is_conductor,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Material:
        """Deserialize material from dictionary."""
        return cls(
            name=d.get("name", "Custom"),
            relative_permittivity=float(d.get("relative_permittivity", 1.0)),
            relative_permeability=float(d.get("relative_permeability", 1.0)),
            conductivity=float(d.get("conductivity", 0.0)),
            loss_tangent=float(d.get("loss_tangent", 0.0)),
            thickness_mm=float(d.get("thickness_mm", 0.0)),
            color_hex=d.get("color_hex", "#38bdf8"),
            description=d.get("description", ""),
        )


class MaterialLibrary:
    """Catalog of standard RF materials used in origami antennas and substrates."""

    _MATERIALS: Dict[str, Material] = {
        "air": Material(
            name="Air",
            relative_permittivity=1.0,
            relative_permeability=1.0,
            conductivity=0.0,
            loss_tangent=0.0,
            thickness_mm=0.0,
            color_hex="#0f172a",
            description="Vacuum / Free Space",
        ),
        "pec": Material(
            name="PEC",
            relative_permittivity=1.0,
            relative_permeability=1.0,
            conductivity=1e8,
            loss_tangent=0.0,
            thickness_mm=0.035,
            color_hex="#94a3b8",
            description="Perfect Electric Conductor (Ideal)",
        ),
        "copper": Material(
            name="Copper",
            relative_permittivity=1.0,
            relative_permeability=0.999994,
            conductivity=5.8e7,
            loss_tangent=0.0,
            thickness_mm=0.035,
            color_hex="#f59e0b",
            description="Standard Annealed Copper Foil (1 oz / 35 um)",
        ),
        "generic_dielectric": Material(
            name="Generic Dielectric",
            relative_permittivity=3.0,
            relative_permeability=1.0,
            conductivity=0.0,
            loss_tangent=0.005,
            thickness_mm=0.8,
            color_hex="#38bdf8",
            description="Generic folding dielectric substrate",
        ),
        "kapton": Material(
            name="Kapton / Polyimide",
            relative_permittivity=3.4,
            relative_permeability=1.0,
            conductivity=0.0,
            loss_tangent=0.002,
            thickness_mm=0.125,
            color_hex="#f97316",
            description="Flexible Polyimide Substrate for Deployable Origami Antennas",
        ),
        "fr4": Material(
            name="FR-4",
            relative_permittivity=4.4,
            relative_permeability=1.0,
            conductivity=0.0,
            loss_tangent=0.02,
            thickness_mm=1.6,
            color_hex="#10b981",
            description="Standard Glass-Reinforced Epoxy Substrate",
        ),
        "rogers_ro4003c": Material(
            name="Rogers RO4003C",
            relative_permittivity=3.55,
            relative_permeability=1.0,
            conductivity=0.0,
            loss_tangent=0.0027,
            thickness_mm=0.813,
            color_hex="#8b5cf6",
            description="High-Frequency Hydrocarbon Ceramic Laminate",
        ),
    }

    @classmethod
    def get(cls, key: str) -> Material:
        """Retrieve material by key name (case-insensitive)."""
        norm = key.lower().replace("-", "_").replace(" ", "_").strip()
        if norm not in cls._MATERIALS:
            raise KeyError(f"Material '{key}' not found in library. Available: {list(cls._MATERIALS.keys())}")
        return cls._MATERIALS[norm]

    @classmethod
    def register(cls, key: str, material: Material) -> None:
        """Register custom material in the library."""
        norm = key.lower().replace("-", "_").replace(" ", "_").strip()
        cls._MATERIALS[norm] = material

    @classmethod
    def all(cls) -> List[Material]:
        """Return list of all registered materials."""
        return list(cls._MATERIALS.values())

    @classmethod
    def list_materials(cls) -> Dict[str, Dict[str, Any]]:
        """Return serialized list of all available materials."""
        return {k: m.to_dict() for k, m in cls._MATERIALS.items()}
