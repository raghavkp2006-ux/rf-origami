"""Absorber Simulation Result Container with S-Parameters, Energy Balance and Metadata.

Represents frequency-swept reflection, transmission, and absorption spectra,
resonant properties, bandwidth, surface current field maps, and solver provenance.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np

from rf_origami.rf.absorber.metrics import (
    calculate_reflection,
    calculate_transmission,
    calculate_absorption,
    check_energy_conservation,
    extract_resonance,
    calculate_absorption_bandwidth,
    s11_to_db,
)


@dataclass
class AbsorberResult:
    """Complete simulation result for an electromagnetic origami absorber.

    Attributes:
        frequencies_hz: List of excitation frequencies [Hz].
        s11: Complex reflection coefficient array S11(f).
        s21: Complex transmission coefficient array S21(f).
        reflection: Power reflection coefficient R(f) = |S11|^2.
        transmission: Power transmission coefficient T(f) = |S21|^2.
        absorption: Power absorption spectrum A(f) = 1 - R - T.
        energy_errors: Energy conservation error |1 - (R + T + A)| at each frequency.
        resonant_frequency_hz: Resonant frequency with maximum absorption [Hz].
        minimum_s11_db: Reflection dip at resonance in dB.
        peak_absorption: Maximum absorption value in range [0.0, 1.0].
        absorption_bandwidth_hz: -10 dB (90% absorption) bandwidth in Hz.
        fractional_bandwidth: Fractional absorption bandwidth (Delta_f / f_0).
        fold_angle_deg: Origami kinematic fold angle [deg].
        surface_currents: Optional dictionary of current density vector maps on facets.
        validation_status: "CONVERGED", "VALID", or "WARNING".
        metadata: Solver metadata (mesh unknowns, solver type, version, timestamp).
    """

    frequencies_hz: List[float]
    s11: List[complex] = field(default_factory=list)
    s21: List[complex] = field(default_factory=list)
    reflection: List[float] = field(default_factory=list)
    transmission: List[float] = field(default_factory=list)
    absorption: List[float] = field(default_factory=list)
    energy_errors: List[float] = field(default_factory=list)

    resonant_frequency_hz: float = 0.0
    minimum_s11_db: float = 0.0
    peak_absorption: float = 0.0
    absorption_bandwidth_hz: float = 0.0
    fractional_bandwidth: float = 0.0
    fold_angle_deg: float = 0.0

    surface_currents: Optional[Dict[str, Any]] = None
    validation_status: str = "VALID"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        freqs = np.asarray(self.frequencies_hz, dtype=np.float64)
        n_pts = len(freqs)

        if n_pts == 0:
            return

        # Initialize S11 if empty
        if len(self.s11) == 0:
            self.s11 = [complex(1.0, 0.0)] * n_pts
        if len(self.s21) == 0:
            self.s21 = [complex(0.0, 0.0)] * n_pts

        # Calculate power reflection and transmission if not supplied
        if len(self.reflection) == 0:
            self.reflection = calculate_reflection(self.s11).tolist()
        if len(self.transmission) == 0:
            self.transmission = calculate_transmission(self.s21).tolist()
        if len(self.absorption) == 0:
            self.absorption = calculate_absorption(self.reflection, self.transmission).tolist()

        # Compute energy errors
        if len(self.energy_errors) == 0:
            _, _, errs = check_energy_conservation(self.reflection, self.transmission, self.absorption)
            self.energy_errors = errs.tolist()

        # Extract resonance metrics
        if self.resonant_frequency_hz == 0.0 and len(self.absorption) > 0:
            s11_db = s11_to_db(self.s11)
            f_res, peak_abs, min_db = extract_resonance(self.frequencies_hz, self.absorption, s11_db)
            self.resonant_frequency_hz = f_res
            self.peak_absorption = peak_abs
            self.minimum_s11_db = min_db

            bw_hz, fbw, _, _ = calculate_absorption_bandwidth(self.frequencies_hz, self.absorption, threshold=0.9)
            if bw_hz == 0.0:
                # Fallback to 50% absorption (-3 dB) bandwidth if 90% is not reached
                bw_hz, fbw, _, _ = calculate_absorption_bandwidth(self.frequencies_hz, self.absorption, threshold=0.5)
            self.absorption_bandwidth_hz = bw_hz
            self.fractional_bandwidth = fbw

        if not self.metadata:
            self.metadata = {
                "solver_type": "surface_mom_absorber",
                "solver_version": "1.0.0",
                "timestamp": datetime.datetime.now().isoformat(),
            }

    @property
    def frequencies_ghz(self) -> List[float]:
        return [f / 1e9 for f in self.frequencies_hz]

    @property
    def s11_db(self) -> List[float]:
        return s11_to_db(self.s11).tolist()

    @property
    def is_energy_conserved(self) -> bool:
        max_err = max(self.energy_errors) if self.energy_errors else 0.0
        return max_err <= 0.05

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a complete, JSON-serializable dictionary."""
        s11_re_im = [{"re": float(val.real), "im": float(val.imag)} for val in self.s11]
        s21_re_im = [{"re": float(val.real), "im": float(val.imag)} for val in self.s21]

        return {
            "frequencies_hz": [float(f) for f in self.frequencies_hz],
            "frequencies_ghz": self.frequencies_ghz,
            "s11": s11_re_im,
            "s21": s21_re_im,
            "s11_db": self.s11_db,
            "reflection": [float(r) for r in self.reflection],
            "transmission": [float(t) for t in self.transmission],
            "absorption": [float(a) for a in self.absorption],
            "energy_errors": [float(e) for e in self.energy_errors],
            "resonant_frequency_hz": float(self.resonant_frequency_hz),
            "resonant_frequency_ghz": float(self.resonant_frequency_hz / 1e9),
            "minimum_s11_db": float(self.minimum_s11_db),
            "peak_absorption": float(self.peak_absorption),
            "absorption_bandwidth_hz": float(self.absorption_bandwidth_hz),
            "absorption_bandwidth_mhz": float(self.absorption_bandwidth_hz / 1e6),
            "fractional_bandwidth": float(self.fractional_bandwidth),
            "fold_angle_deg": float(self.fold_angle_deg),
            "validation_status": self.validation_status,
            "surface_currents": self.surface_currents,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AbsorberResult:
        """Construct AbsorberResult from serialized dictionary."""
        s11_raw = data.get("s11", [])
        s11_cplx = [complex(item["re"], item["im"]) if isinstance(item, dict) else complex(item) for item in s11_raw]
        s21_raw = data.get("s21", [])
        s21_cplx = [complex(item["re"], item["im"]) if isinstance(item, dict) else complex(item) for item in s21_raw]

        return cls(
            frequencies_hz=data["frequencies_hz"],
            s11=s11_cplx,
            s21=s21_cplx,
            reflection=data.get("reflection", []),
            transmission=data.get("transmission", []),
            absorption=data.get("absorption", []),
            energy_errors=data.get("energy_errors", []),
            resonant_frequency_hz=data.get("resonant_frequency_hz", 0.0),
            minimum_s11_db=data.get("minimum_s11_db", 0.0),
            peak_absorption=data.get("peak_absorption", 0.0),
            absorption_bandwidth_hz=data.get("absorption_bandwidth_hz", 0.0),
            fractional_bandwidth=data.get("fractional_bandwidth", 0.0),
            fold_angle_deg=data.get("fold_angle_deg", 0.0),
            surface_currents=data.get("surface_currents"),
            validation_status=data.get("validation_status", "VALID"),
            metadata=data.get("metadata", {}),
        )
