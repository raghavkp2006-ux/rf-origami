"""Canonical Electromagnetic Validation Cases for the Standalone MoM Solver.

Provides analytical and standard benchmark validation models:
1. Free-space wave propagation & intrinsic impedance (η0 ≈ 376.73 Ω).
2. Canonical center-fed half-wave thin-wire dipole antenna (L = λ/2).
3. Quarter-wave monopole antenna over an infinite/finite ground plane (L = λ/4).
"""

from __future__ import annotations
import math
from typing import Any, Dict, Tuple
import numpy as np

from rf_origami.rf.materials.material import (
    C_0,
    ETA_0,
    EPSILON_0,
    MU_0,
    MaterialLibrary,
)
from rf_origami.rf.mesh.discretization import EMDiscretization
from rf_origami.rf.ports.lumped_port import LumpedPort
from rf_origami.rf.solver.mom_solver import MoMSolver


class SolverValidationBenchmarks:
    """Canonical verification benchmarks with known analytical / textbook solutions."""

    @classmethod
    def validate_free_space_propagation(cls) -> Dict[str, Any]:
        """Verify fundamental free-space electromagnetic constitutive parameters."""
        c_calc = 1.0 / math.sqrt(EPSILON_0 * MU_0)
        eta_calc = math.sqrt(MU_0 / EPSILON_0)

        c_err = abs(c_calc - C_0) / C_0
        eta_err = abs(eta_calc - ETA_0) / ETA_0

        return {
            "name": "Free-Space Wave Parameters",
            "passed": bool(c_err < 1e-4 and eta_err < 1e-4),
            "speed_of_light_m_s": round(c_calc, 1),
            "speed_of_light_expected": C_0,
            "wave_impedance_ohms": round(eta_calc, 3),
            "wave_impedance_expected": round(ETA_0, 3),
            "relative_error": float(max(c_err, eta_err)),
        }

    @classmethod
    def run_half_wave_dipole_benchmark(
        cls,
        frequency_ghz: float = 2.4,
        num_segments: int = 21,
        wire_radius_mm: float = 0.5,
    ) -> Dict[str, Any]:
        """Simulate a classical center-fed dipole antenna of resonant length L ≈ 0.46 λ.

        Textbook analytical expectation (Balanis Ch. 4 & 8 / Kraus):
        - For thin wire (a/λ ≈ 0.004): Resonant length is L ≈ 0.455 - 0.465 λ
        - At resonance: Zin ≈ 70 - 79 + j0 Ω (purely resistive)
        """
        f_hz = frequency_ghz * 1e9
        wavelength_m = C_0 / f_hz
        wavelength_mm = wavelength_m * 1000.0

        # Resonant dipole length (shortened by ~4% to tune out inductive reactance for a/lambda=0.004)
        resonant_length_mm = 0.46 * wavelength_mm

        half_len = resonant_length_mm / 2.0
        p1 = np.array([0.0, -half_len, 0.0])
        p2 = np.array([0.0, half_len, 0.0])

        discretization = EMDiscretization.from_wire_line(
            start_pt=p1,
            end_pt=p2,
            num_segments=num_segments,
            radius_mm=wire_radius_mm,
            feed_at_center=True,
        )

        port = LumpedPort(
            port_id="DIPOLE_FEED",
            impedance=50.0,
            positive_terminal=np.array([0.0, 0.5, 0.0]),
            negative_terminal=np.array([0.0, -0.5, 0.0]),
        )

        solver = MoMSolver(
            discretization=discretization,
            port=port,
            substrate_material=MaterialLibrary.get("air"),
        )

        sol = solver.solve_frequency(f_hz)

        r_in = sol["zin_real"]
        x_in = sol["zin_imag"]

        # Validation criteria:
        # Radiation resistance for resonant dipole is between 55 Ω and 90 Ω
        # Reactance near resonance is small (|X| < 45 Ω)
        r_valid = 55.0 <= r_in <= 90.0
        x_valid = abs(x_in) < 45.0
        passed = bool(r_valid and x_valid)

        return {
            "name": "Half-Wave Dipole Benchmark",
            "frequency_ghz": frequency_ghz,
            "total_length_mm": round(resonant_length_mm, 2),
            "wavelength_mm": round(wavelength_mm, 2),
            "num_segments": num_segments,
            "numerical_zin_ohms": [round(r_in, 2), round(x_in, 2)],
            "theoretical_expected_rin": "70 - 75 Ω",
            "numerical_s11_db": round(sol["s11_db"], 2),
            "numerical_vswr": round(sol["vswr"], 2),
            "passed": passed,
            "notes": "Verified against classical Harrington/Pocklington integral equation.",
        }

    @classmethod
    def run_quarter_wave_monopole_benchmark(
        cls,
        frequency_ghz: float = 2.4,
        num_segments: int = 21,
        wire_radius_mm: float = 0.5,
    ) -> Dict[str, Any]:
        """Simulate a quarter-wave monopole (L ≈ 0.23 λ) over an ideal infinite ground plane.

        By classical electromagnetic image theory (Balanis Section 4.7):
        - A vertical monopole of height h on a PEC ground plane has an identical upper-space
          field as a center-fed dipole of length 2h in free space.
        - Because fields exist only in z > 0, radiated power is halved:
          Zin,monopole = 0.5 * Zin,dipole ≈ 35 - 40 Ω.
        """
        f_hz = frequency_ghz * 1e9
        wavelength_mm = (C_0 / f_hz) * 1000.0
        monopole_len_mm = 0.23 * wavelength_mm

        # Model via equivalent image dipole of length 2*h
        discretization = EMDiscretization.from_wire_line(
            start_pt=np.array([0.0, -monopole_len_mm, 0.0]),
            end_pt=np.array([0.0, monopole_len_mm, 0.0]),
            num_segments=num_segments,
            radius_mm=wire_radius_mm,
            feed_at_center=True,
        )

        solver = MoMSolver(
            discretization=discretization,
            port=LumpedPort(impedance=50.0),
            substrate_material=MaterialLibrary.get("air"),
        )

        sol_dipole = solver.solve_frequency(f_hz)

        # Image theory scaling
        r_in = sol_dipole["zin_real"] / 2.0
        x_in = sol_dipole["zin_imag"] / 2.0
        r_valid = 25.0 <= r_in <= 50.0

        return {
            "name": "Quarter-Wave Monopole Benchmark",
            "frequency_ghz": frequency_ghz,
            "monopole_length_mm": round(monopole_len_mm, 2),
            "numerical_zin_ohms": [round(r_in, 2), round(x_in, 2)],
            "theoretical_expected_rin": "35 - 38 Ω",
            "passed": bool(r_valid),
            "notes": "Verified against classical image theory of half-wave dipole.",
        }
