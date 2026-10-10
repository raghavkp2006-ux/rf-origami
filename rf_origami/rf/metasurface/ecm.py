"""Analytical Equivalent Circuit Model (ECM) Engine for Folded Metasurfaces.

Extracts lumped surface impedance parameters (grid inductance L_g, patch capacitance C_g,
surface resistance R_s) and computes real-time transmission line impedance Z_in(f).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import cmath
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.materials.material import EPSILON_0, MU_0, C_0, ETA_0


@dataclass
class EquivalentCircuitResult:
    """Container for analytical ECM impedance and frequency response."""
    frequencies_hz: List[float]
    grid_inductance_nh: float
    grid_capacitance_pf: float
    surface_resistance_ohms: float
    z_in_real: List[float]
    z_in_imag: List[float]
    s11_db: List[float]
    absorption: List[float]
    resonant_frequency_hz: float
    peak_absorption: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequencies_hz": self.frequencies_hz,
            "frequencies_ghz": [round(f / 1e9, 4) for f in self.frequencies_hz],
            "grid_inductance_nh": round(self.grid_inductance_nh, 4),
            "grid_capacitance_pf": round(self.grid_capacitance_pf, 4),
            "surface_resistance_ohms": round(self.surface_resistance_ohms, 4),
            "s11_db": [round(s, 2) for s in self.s11_db],
            "absorption": [round(a, 4) for a in self.absorption],
            "resonant_frequency_ghz": round(self.resonant_frequency_hz / 1e9, 4),
            "peak_absorption": round(self.peak_absorption, 4),
            "metadata": self.metadata,
        }


class MetasurfaceECMEngine:
    """Computes lumped Equivalent Circuit Model parameters and fast spectrum responses."""

    @classmethod
    def evaluate_circuit(
        cls,
        facet_length_mm: float = 25.0,
        fold_angle_deg: float = 30.0,
        substrate_thickness_mm: float = 0.5,
        relative_permittivity: float = 3.4,
        loss_tangent: float = 0.002,
        sheet_resistance_ohms: float = 0.0,
        f_start_ghz: float = 1.0,
        f_stop_ghz: float = 6.0,
        num_points: int = 31,
    ) -> EquivalentCircuitResult:
        """Extract equivalent L_g, C_g and solve S11 / Absorption analytically."""
        theta_rad = math.radians(fold_angle_deg)
        # Kinematic projected period and gap
        proj_length_mm = facet_length_mm * math.cos(theta_rad / 2.0)
        p_m = max(1e-4, proj_length_mm * 1e-3)
        g_m = max(1e-5, (facet_length_mm * 0.1) * 1e-3) # Crease gap
        w_m = p_m - g_m

        eps_eff = (relative_permittivity + 1.0) / 2.0
        h_m = substrate_thickness_mm * 1e-3

        # Analytical wire mesh / loop inductance: L_g = mu_0 * (p / (2*pi)) * ln(1 / sin(pi*g / (2*p)))
        arg_sin = max(1e-4, min(1.0, (math.pi * g_m) / (2.0 * p_m)))
        L_g_h = MU_0 * (p_m / (2.0 * math.pi)) * math.log(1.0 / math.sin(arg_sin))

        # Analytical patch gap capacitance: C_g = eps_0 * eps_eff * (2*w / pi) * ln(2*p / (pi*g))
        arg_log = max(1.1, (2.0 * p_m) / (math.pi * g_m))
        C_g_f = EPSILON_0 * eps_eff * (2.0 * w_m / math.pi) * math.log(arg_log)

        freqs_hz = np.linspace(f_start_ghz * 1e9, f_stop_ghz * 1e9, num_points).tolist()

        z_real: List[float] = []
        z_imag: List[float] = []
        s11_list: List[float] = []
        abs_list: List[float] = []

        # Complex substrate properties
        eps_c = complex(relative_permittivity, -relative_permittivity * loss_tangent)
        eta_sub = complex(ETA_0, 0.0) / np.sqrt(eps_c)

        for f in freqs_hz:
            omega = 2.0 * math.pi * f
            k_sub = omega * np.sqrt(complex(MU_0, 0.0) * complex(EPSILON_0, 0.0) * eps_c)

            # Grid series impedance: Z_g = R_s + j*(omega*L - 1/(omega*C))
            z_ind = 1j * omega * L_g_h
            z_cap = 1.0 / (1j * omega * C_g_f) if C_g_f > 0 else 0.0
            z_grid = complex(sheet_resistance_ohms, 0.0) + z_ind + z_cap

            # Dielectric ground-backed transmission line input impedance: Z_d = j * eta_sub * tan(k_sub * h)
            tan_kh = np.tan(k_sub * h_m)
            z_dielectric = 1j * eta_sub * tan_kh

            # Total surface input impedance (parallel combination): Z_in = (Z_g * Z_d) / (Z_g + Z_d)
            if abs(z_grid + z_dielectric) > 1e-12:
                z_in = (z_grid * z_dielectric) / (z_grid + z_dielectric)
            else:
                z_in = z_dielectric

            # Reflection coefficient Gamma = (Z_in - ETA_0) / (Z_in + ETA_0)
            gamma = (z_in - ETA_0) / (z_in + ETA_0)
            refl_pwr = abs(gamma) ** 2
            s11_db = 20.0 * math.log10(max(1e-6, abs(gamma)))
            absorption = max(0.0, min(1.0, 1.0 - refl_pwr))

            z_real.append(float(z_in.real))
            z_imag.append(float(z_in.imag))
            s11_list.append(float(s11_db))
            abs_list.append(float(absorption))

        peak_abs = max(abs_list) if abs_list else 0.0
        peak_idx = abs_list.index(peak_abs) if abs_list else 0
        res_freq = freqs_hz[peak_idx]

        return EquivalentCircuitResult(
            frequencies_hz=freqs_hz,
            grid_inductance_nh=float(L_g_h * 1e9),
            grid_capacitance_pf=float(C_g_f * 1e12),
            surface_resistance_ohms=sheet_resistance_ohms,
            z_in_real=z_real,
            z_in_imag=z_imag,
            s11_db=s11_list,
            absorption=abs_list,
            resonant_frequency_hz=res_freq,
            peak_absorption=peak_abs,
            metadata={
                "facet_length_mm": facet_length_mm,
                "fold_angle_deg": fold_angle_deg,
                "relative_permittivity": relative_permittivity,
            },
        )
