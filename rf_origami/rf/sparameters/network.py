"""S-Parameter Network Analysis and Microwave Formalism.

Provides exact calculations for reflection coefficient (Γ), S11 (dB),
Voltage Standing Wave Ratio (VSWR), and Return Loss.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Sequence, Union
import numpy as np


def reflection_coefficient(zin: complex, z0: float = 50.0) -> complex:
    """Calculate complex reflection coefficient Γ = (Zin - Z0) / (Zin + Z0).

    Args:
        zin: Input impedance (complex: R + jX).
        z0: Reference characteristic impedance (strictly positive real, default: 50.0 Ω).
    """
    if z0 <= 0.0:
        raise ValueError(f"Reference impedance Z0 must be > 0 (got {z0}).")
    denom = zin + z0
    if abs(denom) < 1e-14:
        return complex(1.0, 0.0)
    return (zin - z0) / denom


def s11_db(zin: complex, z0: float = 50.0) -> float:
    """Calculate return loss / S11 parameter in decibels: S11_dB = 20 * log10(|Γ|).

    Returns a negative number (e.g. -15.4 dB). Clamped to -100 dB minimum.
    """
    gamma = reflection_coefficient(zin, z0)
    mag = abs(gamma)
    if mag < 1e-5:
        return -100.0
    if mag >= 1.0:
        return 0.0
    return float(20.0 * math.log10(mag))


def vswr(zin: complex, z0: float = 50.0) -> float:
    """Calculate Voltage Standing Wave Ratio: VSWR = (1 + |Γ|) / (1 - |Γ|).

    Valid range: [1.0, inf). Clamped to 100.0 for near-total reflections.
    """
    gamma = reflection_coefficient(zin, z0)
    mag = abs(gamma)
    if mag >= 0.99:
        return 100.0
    return float((1.0 + mag) / (1.0 - mag))


def return_loss_db(zin: complex, z0: float = 50.0) -> float:
    """Calculate Return Loss in positive decibels: RL = -20 * log10(|Γ|) = -S11_dB."""
    return -s11_db(zin, z0)


class SParameterVector:
    """Vectorized microwave network representation across a frequency sweep."""

    def __init__(
        self,
        frequencies_hz: Sequence[float],
        zin_values: Sequence[complex],
        z0: float = 50.0,
    ) -> None:
        self.frequencies_hz = np.asarray(frequencies_hz, dtype=np.float64)
        self.zin_values = np.asarray(zin_values, dtype=np.complex128)
        self.z0 = float(z0)

        if len(self.frequencies_hz) != len(self.zin_values):
            raise ValueError("Frequencies and Zin vectors must have identical length.")

    @property
    def num_points(self) -> int:
        return len(self.frequencies_hz)

    @property
    def frequencies_ghz(self) -> np.ndarray:
        return self.frequencies_hz * 1e-9

    def gamma(self) -> np.ndarray:
        """Complex reflection coefficient array."""
        return (self.zin_values - self.z0) / (self.zin_values + self.z0)

    def s11_db(self) -> np.ndarray:
        """S11 in decibels array."""
        gam = self.gamma()
        mag = np.abs(gam)
        mag_safe = np.clip(mag, 1e-5, 1.0)
        return 20.0 * np.log10(mag_safe)

    def vswr(self) -> np.ndarray:
        """VSWR array."""
        mag = np.abs(self.gamma())
        mag_clamped = np.clip(mag, 0.0, 0.99)
        return (1.0 + mag_clamped) / (1.0 - mag_clamped)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequencies_ghz": [round(float(f), 4) for f in self.frequencies_ghz],
            "zin_real_ohms": [round(float(z.real), 2) for z in self.zin_values],
            "zin_imag_ohms": [round(float(z.imag), 2) for z in self.zin_values],
            "s11_db": [round(float(s), 2) for s in self.s11_db()],
            "vswr": [round(float(v), 2) for v in self.vswr()],
            "z0_ohms": self.z0,
        }
