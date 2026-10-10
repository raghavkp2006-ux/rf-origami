"""Method of Moments (MoM) Numerical Electromagnetic Solver.

Implements the Electric Field Integral Equation (EFIE) for wire and strip
conductors on 3D folded origami geometries using free-space Green's functions.
No commercial software dependencies (standalone numerical solver).
"""

from __future__ import annotations
import cmath
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
        self.substrate = substrate_material or MaterialLibrary.get("kapton")

    def solve_frequency(self, frequency_hz: float) -> Dict[str, Any]:
        """Compute the full electrodynamic current distribution and input impedance at frequency f.

        Args:
            frequency_hz: Excitation frequency in Hertz (e.g. 2.4e9).

        Returns:
            Dictionary with Zin, Rin, Xin, reflection coefficient, S11, VSWR, and current vector.
        """
        if frequency_hz <= 0.0:
            raise ValueError(f"Frequency must be strictly positive (got {frequency_hz}).")

        omega = 2.0 * math.pi * frequency_hz
        k0 = omega / C_0

        # Effective permittivity for microstrip/coplanar substrate loading
        # Semi-infinite ground or dielectric backing lowers resonance by sqrt(eps_eff)
        eps_r = self.substrate.relative_permittivity
        eps_eff = (eps_r + 1.0) / 2.0 if eps_r > 1.0 else 1.0
        k = k0 * math.sqrt(eps_eff)
        eta = ETA_0 / math.sqrt(eps_eff)

        # Assemble Impedance Matrix [Z]
        Z_mat = self._assemble_impedance_matrix(k=k, eta=eta, omega=omega, freq=frequency_hz)

        # Assemble Excitation Vector [V] (Delta-gap port generator)
        N = self.discretization.num_segments
        V_vec = np.zeros(N, dtype=np.complex128)
        p_idx = min(self.discretization.port_segment_index, N - 1)
        V0 = 1.0  # 1.0 Volt normalized excitation
        V_vec[p_idx] = complex(V0, 0.0)

        # Solve Linear System [Z] [I] = [V]
        try:
            I_vec = np.linalg.solve(Z_mat, V_vec)
        except np.linalg.LinAlgError:
            # Fallback pseudo-inverse if ill-conditioned
            I_vec = np.linalg.pinv(Z_mat) @ V_vec

        # Input Current at Feed Port
        I_in = I_vec[p_idx]

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
        gamma_mag_safe = max(1e-7, min(1.0, gamma_mag))
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
            "port_index": p_idx,
        }

    def solve_sweep(
        self,
        f_start_hz: float = 1.0e9,
        f_stop_hz: float = 8.0e9,
        num_points: int = 101,
    ) -> Dict[str, Any]:
        """Execute frequency sweep across [f_start, f_stop] with num_points samples."""
        freqs = np.linspace(f_start_hz, f_stop_hz, num_points)

        s11_list = []
        zin_r_list = []
        zin_x_list = []
        vswr_list = []
        gamma_mag_list = []

        for f in freqs:
            sol = self.solve_frequency(f)
            s11_list.append(round(sol["s11_db"], 2))
            zin_r_list.append(round(sol["zin_real"], 2))
            zin_x_list.append(round(sol["zin_imag"], 2))
            vswr_list.append(round(sol["vswr"], 2))
            gamma_mag_list.append(round(sol["gamma_mag"], 4))

        freqs_ghz = [round(float(f * 1e-9), 4) for f in freqs]

        # Extract Resonant Frequency (where S11 is minimum and/or Xin crosses zero)
        min_s11_idx = int(np.argmin(s11_list))
        f0_s11_ghz = freqs_ghz[min_s11_idx]
        min_s11_val = s11_list[min_s11_idx]

        # Extract -10 dB Impedance Bandwidth
        in_band_indices = [i for i, s in enumerate(s11_list) if s <= -10.0]
        if in_band_indices:
            f_low = freqs_ghz[in_band_indices[0]]
            f_high = freqs_ghz[in_band_indices[-1]]
            bw_mhz = (f_high - f_low) * 1000.0
            bw_pct = (bw_mhz / (f0_s11_ghz * 1000.0)) * 100.0 if f0_s11_ghz > 0 else 0.0
        else:
            f_low, f_high, bw_mhz, bw_pct = 0.0, 0.0, 0.0, 0.0

        return {
            "frequencies_ghz": freqs_ghz,
            "s11_db": s11_list,
            "zin_real_ohms": zin_r_list,
            "zin_imag_ohms": zin_x_list,
            "vswr": vswr_list,
            "gamma_mag": gamma_mag_list,
            "resonance": {
                "resonant_frequency_ghz": f0_s11_ghz,
                "min_s11_db": min_s11_val,
                "zin_at_resonance": [zin_r_list[min_s11_idx], zin_x_list[min_s11_idx]],
                "vswr_at_resonance": vswr_list[min_s11_idx],
                "bandwidth_mhz": round(bw_mhz, 1),
                "bandwidth_percent": round(bw_pct, 2),
                "f_low_ghz": f_low,
                "f_high_ghz": f_high,
            }
        }

    def _assemble_impedance_matrix(
        self,
        k: float,
        eta: float,
        omega: float,
        freq: float,
    ) -> np.ndarray:
        """Assemble the N x N Pocklington EFIE impedance matrix [Z] using Harrington formulation."""
        segments = self.discretization.segments
        N = len(segments)
        Z = np.zeros((N, N), dtype=np.complex128)

        # Segment geometric parameters in meters
        p1_all = np.array([s.p1 * 1e-3 for s in segments], dtype=np.float64)
        p2_all = np.array([s.p2 * 1e-3 for s in segments], dtype=np.float64)
        pc_all = (p1_all + p2_all) / 2.0
        dl_all = np.array([s.length * 1e-3 for s in segments], dtype=np.float64)
        u_all = np.array([s.direction for s in segments], dtype=np.float64)
        a_all = np.array([s.radius_mm * 1e-3 for s in segments], dtype=np.float64)

        # Gauss-Legendre 3-point quadrature for wire segment potential integrals
        gauss_pts = np.array([-0.7745966692414834, 0.0, 0.7745966692414834], dtype=np.float64)
        gauss_wts = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0], dtype=np.float64)

        def psi_segment(ra: np.ndarray, center: np.ndarray, length: float, direction: np.ndarray, radius: float) -> complex:
            """Compute average Green's function potential from segment to field point ra."""
            val = complex(0.0, 0.0)
            half_l = length / 2.0
            for p, w in zip(gauss_pts, gauss_wts):
                rp = center + (p * half_l) * direction
                dist_sq = float(np.sum((ra - rp) ** 2))
                R = math.sqrt(dist_sq + radius ** 2)
                G = cmath.exp(complex(0.0, -k * R)) / (4.0 * math.pi * R)
                val += w * G * half_l
            return val / max(1e-12, length)

        for m in range(N):
            rm_c = pc_all[m]
            rm_1 = p1_all[m]
            rm_2 = p2_all[m]
            dl_m = dl_all[m]
            u_m = u_all[m]

            for n in range(N):
                rn_c = pc_all[n]
                rn_1 = p1_all[n]
                rn_2 = p2_all[n]
                dl_n = dl_all[n]
                u_n = u_all[n]
                a_n = a_all[n]

                dot_u = float(np.dot(u_m, u_n))

                # Vector potential term: j ω μ Δl_m Δl_n (u_m · u_n) ψ(r_m, segment_n)
                term_A = complex(0.0, omega * MU_0) * dl_m * dl_n * dot_u * psi_segment(
                    ra=rm_c, center=rn_c, length=dl_n, direction=u_n, radius=a_n
                )

                # Scalar potential charge endpoints: 1 / (j ω ε) [ψ(r_m2, r_n2) - ψ(r_m2, r_n1) - ...]
                psi_22 = psi_segment(ra=rm_2, center=rn_2, length=dl_n, direction=u_n, radius=a_n)
                psi_21 = psi_segment(ra=rm_2, center=rn_1, length=dl_n, direction=u_n, radius=a_n)
                psi_12 = psi_segment(ra=rm_1, center=rn_2, length=dl_n, direction=u_n, radius=a_n)
                psi_11 = psi_segment(ra=rm_1, center=rn_1, length=dl_n, direction=u_n, radius=a_n)

                term_Phi = (1.0 / complex(0.0, omega * EPSILON_0)) * (psi_22 - psi_21 - psi_12 + psi_11)

                # Ohmic surface resistance loss on diagonal
                R_ohm = 0.0
                if m == n:
                    sigma = segments[n].conductivity
                    if sigma > 0.0:
                        delta = math.sqrt(2.0 / (omega * MU_0 * sigma))
                        R_ohm = dl_m / (2.0 * math.pi * a_n * sigma * delta)

                Z[m, n] = term_A + term_Phi + complex(R_ohm, 0.0)

        return Z
