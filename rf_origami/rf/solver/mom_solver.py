"""Method of Moments (MoM) Numerical Electromagnetic Solver.

Implements the Electric Field Integral Equation (EFIE) for wire and strip
conductors on 3D folded origami geometries using free-space Green's functions.
No commercial software dependencies (standalone numerical solver).
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from rf_origami.rf.materials.material import (
    EPSILON_0,
    MU_0,
    C_0,
    ETA_0,
    Material,
    MaterialLibrary,
)
from rf_origami.rf.mesh.discretization import EMDiscretization, EMSegment
from rf_origami.rf.ports.lumped_port import LumpedPort
from rf_origami.rf.metrics.antenna_metrics import extract_resonant_frequency, extract_impedance_bandwidth
from rf_origami.rf.solver.rooftop_wire import assemble_rooftop


class MoMSolver:
    """Frequency-domain Method of Moments solver for folded antenna structures."""

    def __init__(
        self,
        discretization: EMDiscretization,
        port: Optional[LumpedPort] = None,
        substrate_material: Optional[Material] = None,
    ) -> None:
        self.discretization = discretization
        self.port = port or LumpedPort()
        self.substrate = substrate_material or MaterialLibrary.get("air")
        self.last_asymmetry: Optional[float] = None
        if not discretization.segments:
            raise ValueError("The solver requires at least one conductor segment.")
        N = discretization.num_segments
        if N < 2:
            raise ValueError("The rooftop wire solver requires at least two conductor segments.")
        p = discretization.port_segment_index
        if not 1 <= p <= N - 1:
            raise ValueError(f"Feed segment index must satisfy 1 <= port_segment_index <= N-1 (got {p} for N={N}).")
        for segment in discretization.segments:
            if (not np.all(np.isfinite([segment.p1, segment.p2])) or
                    segment.length <= 0 or not math.isfinite(segment.radius_mm) or segment.radius_mm <= 0):
                raise ValueError("Conductor segments require finite endpoints, positive length and radius.")
        segs = discretization.segments
        for i in range(len(segs) - 1):
            gap = float(np.linalg.norm(segs[i].p2 - segs[i + 1].p1))
            if gap > 1e-9:
                raise ValueError(
                    f"Segments must form one open consecutive polyline, but segment {i}'s p2 "
                    f"does not match segment {i + 1}'s p1 (gap: {gap:.6e} mm > 1e-9 mm)."
                )
        if not math.isfinite(self.port.impedance) or self.port.impedance <= 0:
            raise ValueError("Port reference impedance must be positive and finite.")

    def solve_frequency(self, frequency_hz: float) -> Dict[str, Any]:
        """Compute the full electrodynamic current distribution and input impedance at frequency f.

        Args:
            frequency_hz: Excitation frequency in Hertz (e.g. 2.4e9).

        Returns:
            Dictionary with Zin, Rin, Xin, reflection coefficient, S11, VSWR, and current vector.
        """
        if not math.isfinite(frequency_hz) or frequency_hz <= 0.0:
            raise ValueError(f"Frequency must be strictly positive (got {frequency_hz}).")

        N = self.discretization.num_segments
        p = self.discretization.port_segment_index
        if not 1 <= p <= N - 1:
            raise ValueError(f"Feed index must satisfy 1 <= port_segment_index <= N-1 (got {p} for N={N}).")

        omega = 2.0 * math.pi * frequency_hz
        k0 = omega / C_0

        # Effective permittivity for microstrip/coplanar substrate loading
        # Semi-infinite ground or dielectric backing lowers resonance by sqrt(eps_eff)
        eps_r = self.substrate.relative_permittivity
        eps_eff = (eps_r + 1.0) / 2.0 if eps_r > 1.0 else 1.0
        k = k0 * math.sqrt(eps_eff)
        eta = ETA_0 / math.sqrt(eps_eff)

        # Assemble Impedance Matrix [Z] (N-1 x N-1 unknowns)
        Z_mat = self._assemble_impedance_matrix(k=k, eta=eta, omega=omega, freq=frequency_hz)

        # Assemble Excitation Vector [V] (Delta-gap port generator on node between p-1 and p)
        fi = p - 1
        V_vec = np.zeros(N - 1, dtype=np.complex128)
        V0 = 1.0  # 1.0 Volt normalized excitation
        V_vec[fi] = complex(V0, 0.0)

        # Solve Linear System [Z] [I] = [V]
        try:
            I_vec = np.linalg.solve(Z_mat, V_vec)
        except np.linalg.LinAlgError:
            # Fallback pseudo-inverse if ill-conditioned
            I_vec = np.linalg.pinv(Z_mat) @ V_vec

        # Input Current at Feed Port
        I_in = I_vec[fi]

        # Input Impedance Zin = V0 / I_in
        if abs(I_in) < 1e-15:
            Z_in = complex(1e6, 0.0)
        else:
            Z_in = V0 / I_in

        R_in = float(Z_in.real)
        X_in = float(Z_in.imag)

        # Reflection Coefficient Γ = (Zin - Z0) / (Zin + Z0)
        Z0 = float(self.port.impedance)
        gamma = (Z_in - Z0) / (Z_in + Z0)
        gamma_mag = float(abs(gamma))

        # Clamp to avoid log(0)
        gamma_mag_safe = max(1e-7, gamma_mag)
        s11_db = 20.0 * math.log10(gamma_mag_safe)

        # VSWR = (1 + |Γ|) / (1 - |Γ|)
        if gamma_mag >= 0.9999:
            vswr = 100.0
        else:
            vswr = float((1.0 + gamma_mag) / (1.0 - gamma_mag))

        return {
            "frequency_hz": frequency_hz,
            "frequency_ghz": frequency_hz * 1e-9,
            "zin_real": R_in,
            "zin_imag": X_in,
            "zin": complex(R_in, X_in),
            "gamma": gamma,
            "gamma_mag": gamma_mag,
            "s11_db": s11_db,
            "vswr": vswr,
            "current_magnitude": np.abs(I_vec).tolist(),
            "port_index": fi,
        }

    def solve_sweep(
        self,
        f_start_hz: float = 1.0e9,
        f_stop_hz: float = 8.0e9,
        num_points: int = 101,
    ) -> Dict[str, Any]:
        """Execute frequency sweep across [f_start, f_stop] with num_points samples."""
        if (not math.isfinite(f_start_hz) or not math.isfinite(f_stop_hz) or
                f_start_hz <= 0 or f_stop_hz <= f_start_hz):
            raise ValueError("Sweep bounds must be finite, positive and increasing.")
        if isinstance(num_points, bool) or not isinstance(num_points, (int, np.integer)) or num_points < 3:
            raise ValueError("A frequency sweep requires at least three integer samples.")
        freqs = np.linspace(f_start_hz, f_stop_hz, num_points)

        s11_list = []
        zin_r_list = []
        zin_x_list = []
        vswr_list = []
        gamma_mag_list = []

        for f in freqs:
            sol = self.solve_frequency(f)
            s11_list.append(sol["s11_db"])
            zin_r_list.append(sol["zin_real"])
            zin_x_list.append(sol["zin_imag"])
            vswr_list.append(sol["vswr"])
            gamma_mag_list.append(sol["gamma_mag"])

        freqs_ghz = [float(f * 1e-9) for f in freqs]

        # Extract Resonant Frequency (where S11 is minimum and/or Xin crosses zero)
        resonance = extract_resonant_frequency(freqs, s11_list, np.array(zin_r_list) + 1j * np.array(zin_x_list))
        f0_s11_ghz = resonance["resonant_frequency_ghz"]
        min_s11_val = resonance["min_s11_db"]

        # Extract -10 dB Impedance Bandwidth
        bandwidth = extract_impedance_bandwidth(freqs, s11_list)

        return {
            "frequencies_ghz": freqs_ghz,
            "s11_db": s11_list,
            "zin_real_ohms": zin_r_list,
            "zin_imag_ohms": zin_x_list,
            "vswr": vswr_list,
            "gamma_mag": gamma_mag_list,
            "resonance": {
                **resonance,
                **bandwidth,
                "resonant_frequency_ghz": f0_s11_ghz,
                "min_s11_db": min_s11_val,
                "zin_at_resonance": [float(np.interp(f0_s11_ghz, freqs_ghz, zin_r_list)), float(np.interp(f0_s11_ghz, freqs_ghz, zin_x_list))],
                "vswr_at_resonance": float(np.interp(f0_s11_ghz, freqs_ghz, vswr_list)),
            },
            "validation_status": "Not validated",
            "dielectric_model": "effective-permittivity approximation" if self.substrate.relative_permittivity > 1 else "free space",
        }

    def _assemble_impedance_matrix(
        self,
        k: float,
        eta: float,
        omega: float,
        freq: float,
    ) -> np.ndarray:
        """Assemble Galerkin rooftop-basis impedance matrix for open polyline wire."""
        segs = self.discretization.segments
        p1 = np.array([s.p1 for s in segs], float) * 1e-3
        p2 = np.array([s.p2 for s in segs], float) * 1e-3
        rad = np.array([s.radius_mm for s in segs], float) * 1e-3
        sig = np.array([s.conductivity for s in segs], float)
        Z, self.last_asymmetry = assemble_rooftop(p1, p2, rad, sig, k, omega)
        return Z
