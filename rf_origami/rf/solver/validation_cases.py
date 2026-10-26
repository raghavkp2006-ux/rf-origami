"""Canonical Electromagnetic Validation Cases for the Standalone MoM Solver.

Provides analytical and standard benchmark validation models:
1. Free-space wave propagation & intrinsic impedance (η0 ≈ 376.73 Ω).
2. Canonical center-fed half-wave thin-wire dipole antenna (L = λ/2).
3. Quarter-wave monopole antenna over an infinite/finite ground plane (L = λ/4).
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np


def error_percent(project: float, reference: float):
    """Relative error in percent; zero references require an absolute tolerance."""
    if not math.isfinite(project) or not math.isfinite(reference):
        raise ValueError("Comparison values must be finite.")
    return abs(project - reference) / abs(reference) * 100 if reference != 0 else None


def compare_metrics(project, reference, percent_tolerance=5.0, db_tolerance=3.0, reactance_tolerance_ohms=1.0):
    """Compare like-for-like scalar metrics without relative error at zero.

    S11 uses absolute dB error. Zero reactance uses an absolute ohm tolerance.
    Missing measurements fail the comparison; they are never treated as zero.
    """
    if not reference:
        raise ValueError("At least one reference metric is required.")
    rows = {}
    for name, expected in reference.items():
        if name not in project or project[name] is None:
            rows[name] = {"passed": False, "reason": "Missing project metric"}
            continue
        actual = float(project[name])
        expected = float(expected)
        relative = error_percent(actual, expected)
        absolute = abs(actual - expected)
        is_db = name.endswith("_db")
        tolerance = db_tolerance if is_db else (reactance_tolerance_ohms if relative is None else percent_tolerance)
        error = absolute if is_db or relative is None else relative
        rows[name] = {"project": actual, "reference": expected, "error_percent": relative,
                      "absolute_error": absolute, "tolerance": tolerance,
                      "error_unit": "dB" if is_db else ("ohms" if relative is None else "%"),
                      "passed": bool(error <= tolerance)}
    return {"passed": all(row["passed"] for row in rows.values()), "metrics": rows}

from rf_origami.rf.materials.material import (
    C_0,
    ETA_0,
    EPSILON_0,
    MU_0,
    MaterialLibrary,
)
from rf_origami.rf.mesh.discretization import EMDiscretization, EMSegment
from rf_origami.rf.ports.lumped_port import LumpedPort
from rf_origami.rf.solver.mom_solver import MoMSolver


def build_v_dipole_discretization(
    bend_deg: float,
    num_segments: int = 40,
    total_length_mm: float = 57.46,
    wire_radius_mm: float = 0.5,
    conductivity: float = 5.8e7,
) -> EMDiscretization:
    """Build a center-fed V-dipole wire discretization in the x-z plane.

    Total wire length total_length_mm, radius wire_radius_mm, copper conductivity.
    Arms are in the x-z plane, each arm bent bend_deg / 2 from the z-axis.
    num_segments must be even; feed is at apex node (port_segment_index = num_segments // 2).
    """
    if num_segments % 2 != 0:
        raise ValueError(f"num_segments must be an even integer, got {num_segments}")
    if num_segments < 2:
        raise ValueError("num_segments must be at least 2")

    h = total_length_mm / 2.0
    ang = math.radians(bend_deg) / 2.0
    half = num_segments // 2
    segs = []

    # Arm 1: from (h*sin(ang), 0, -h*cos(ang)) to (0, 0, 0)
    p_start = np.array([h * math.sin(ang), 0.0, -h * math.cos(ang)], dtype=float)
    p_apex = np.array([0.0, 0.0, 0.0], dtype=float)
    for i in range(half):
        p1 = p_start + (p_apex - p_start) * (i / half)
        p2 = p_start + (p_apex - p_start) * ((i + 1) / half)
        segs.append(EMSegment(index=i, p1=p1, p2=p2, radius_mm=wire_radius_mm, conductivity=conductivity))

    # Arm 2: from (0, 0, 0) to (h*sin(ang), 0, h*cos(ang))
    p_end = np.array([h * math.sin(ang), 0.0, h * math.cos(ang)], dtype=float)
    for i in range(half):
        p1 = p_apex + (p_end - p_apex) * (i / half)
        p2 = p_apex + (p_end - p_apex) * ((i + 1) / half)
        segs.append(EMSegment(index=half + i, p1=p1, p2=p2, radius_mm=wire_radius_mm, conductivity=conductivity))

    return EMDiscretization(segments=segs, port_segment_index=half)


def interpolate_reactance_zero(freqs_hz: np.ndarray, zin: np.ndarray) -> Tuple[float, float]:
    """Find zero-reactance crossing frequency and interpolated Rin matching the reference linear interpolation."""
    crossings = np.where(np.diff(np.sign(zin[:, 1])) != 0)[0]
    if len(crossings) == 0:
        raise ValueError("No zero-reactance crossing found in frequency sweep.")
    i = crossings[0]
    f0 = freqs_hz[i] - zin[i, 1] * (freqs_hz[i + 1] - freqs_hz[i]) / (zin[i + 1, 1] - zin[i, 1])
    r0 = float(np.interp(f0, freqs_hz, zin[:, 0]))
    return float(f0), float(r0)


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
        num_segments: int = 20,
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

        return {
            "name": "Half-Wave Dipole Benchmark",
            "frequency_ghz": frequency_ghz,
            "total_length_mm": round(resonant_length_mm, 2),
            "wavelength_mm": round(wavelength_mm, 2),
            "num_segments": num_segments,
            "numerical_zin_ohms": [round(r_in, 2), round(x_in, 2)],
            "theoretical_expected_rin": "Approximate screening target: 73.13 ohms (infinitely thin wire)",
            "numerical_s11_db": round(sol["s11_db"], 2),
            "numerical_vswr": round(sol["vswr"], 2),
            "passed": None,
            "status": "Screening value only (0.5 mm radius, 57.46 mm dipole is not an infinitely thin half-wave dipole)",
            "rin_error_percent": error_percent(r_in, 73.13),
            "reactance_absolute_error_ohms": abs(x_in),
            "validation_status": "Not validated",
            "reference_kind": "Approximate textbook screening target, not a matched-geometry reference",
            "notes": "Fixed-frequency screening only. 73.13 ohms is for an idealized infinitely thin half-wave dipole, not a matched-geometry reference for a finite-radius wire.",
        }

    @classmethod
    def run_quarter_wave_monopole_benchmark(
        cls,
        frequency_ghz: float = 2.4,
        num_segments: int = 20,
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

        return {
            "name": "Quarter-Wave Monopole Benchmark",
            "frequency_ghz": frequency_ghz,
            "monopole_length_mm": round(monopole_len_mm, 2),
            "numerical_zin_ohms": [round(r_in, 2), round(x_in, 2)],
            "theoretical_expected_rin": "35 - 38 Ω",
            "passed": None,
            "status": "Screening value only (image-scaled dipole consistency check)",
            "rin_error_percent": error_percent(r_in, 36.565),
            "reactance_absolute_error_ohms": abs(x_in),
            "validation_status": "Not validated",
            "independent_benchmark": False,
            "notes": "Image-scaled dipole consistency check; not a second independent antenna benchmark.",
        }

    @classmethod
    def compare_nec2_reference(
        cls,
        reference_path: str | Path | None = None,
        segment_counts: Tuple[int, ...] = (40, 80),
        fr_gate_percent: float = 5.0,
        rin_gate_percent: float = 5.0,
    ) -> Dict[str, Any]:
        """Compare project solver V-dipole results against independent NEC2 reference data.

        Matches reference:
        - 57.46 mm total length, 0.5 mm radius copper wire (sigma = 5.8e7 S/m), free space.
        - Frequencies: 1.8 - 3.0 GHz (61 points).
        - Bend angles: 0, 30, 60, 90, 120 degrees in x-z plane.
        - Even segment counts (N=40, N=80 convergence check), feed at apex (port_segment_index = N//2).
        - Linear interpolation for reactance-zero frequency and Rin.
        - Gates: fr error < 5% at all angles, Rin error < 5% at each angle.
        - Note: Wire V-dipole benchmark, not an origami patch or surface antenna, and not a measurement.
        """
        if reference_path is None:
            reference_path = Path(__file__).resolve().parents[3] / "data" / "validation" / "nec2_reference.json"
        else:
            reference_path = Path(reference_path)

        if not reference_path.is_file():
            raise FileNotFoundError(f"NEC2 reference data file not found: {reference_path}")

        with open(reference_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)

        freqs_hz = np.array(ref_data["freqs_hz"], dtype=float)
        geom = ref_data.get("geometry", {})
        length_mm = geom.get("length_m", 0.05746) * 1000.0
        radius_mm = geom.get("radius_m", 0.0005) * 1000.0
        sigma = geom.get("sigma_S_per_m", 5.8e7)

        bend_keys = sorted(ref_data["cases"].keys(), key=lambda k: float(k))
        cases_out: Dict[str, Any] = {}

        for b_str in bend_keys:
            bend_deg = float(b_str)
            ref_case = ref_data["cases"][b_str]
            nec_f0 = float(ref_case["reactance_zero_hz"])
            nec_r0 = float(ref_case["rin_at_reactance_zero"])

            by_segments: Dict[str, Any] = {}
            for n_segs in segment_counts:
                discr = build_v_dipole_discretization(
                    bend_deg=bend_deg,
                    num_segments=n_segs,
                    total_length_mm=length_mm,
                    wire_radius_mm=radius_mm,
                    conductivity=sigma,
                )
                solver = MoMSolver(
                    discretization=discr,
                    substrate_material=MaterialLibrary.get("air"),
                )
                zin_list = []
                for f_hz in freqs_hz:
                    sol = solver.solve_frequency(f_hz)
                    zin_list.append([sol["zin_real"], sol["zin_imag"]])
                zin_arr = np.array(zin_list, dtype=float)

                f0, r0 = interpolate_reactance_zero(freqs_hz, zin_arr)
                fr_err = error_percent(f0, nec_f0)
                rin_err = error_percent(r0, nec_r0)

                # Reactance at the NEC2 resonance frequency
                x_at_nec_f0 = float(np.interp(nec_f0, freqs_hz, zin_arr[:, 1]))
                reactance_err_ohms = abs(x_at_nec_f0)

                pass_fr = bool(fr_err is not None and fr_err < fr_gate_percent)
                pass_rin = bool(rin_err is not None and rin_err < rin_gate_percent)

                by_segments[str(n_segs)] = {
                    "num_segments": n_segs,
                    "reactance_zero_hz": f0,
                    "rin_at_reactance_zero": r0,
                    "fr_error_percent": fr_err,
                    "rin_error_percent": rin_err,
                    "reactance_at_nec2_res_ohms": x_at_nec_f0,
                    "reactance_error_ohms": reactance_err_ohms,
                    "passed_fr": pass_fr,
                    "passed_rin": pass_rin,
                    "passed": bool(pass_fr and pass_rin),
                }

            angle_passed = all(seg_data["passed"] for seg_data in by_segments.values())

            cases_out[b_str] = {
                "bend_deg": bend_deg,
                "nec2": {
                    "reactance_zero_hz": nec_f0,
                    "rin_at_reactance_zero": nec_r0,
                },
                "by_segments": by_segments,
                "passed": angle_passed,
                "result": "PASS" if angle_passed else "FAIL",
            }

        straight_case = cases_out.get("0") or cases_out.get("0.0")
        straight_passed = bool(straight_case and straight_case["passed"])
        all_angles_passed = all(c["passed"] for c in cases_out.values())

        return {
            "name": "NEC2 Wire V-Dipole Benchmark Comparison",
            "reference_file": str(reference_path),
            "disclaimer": "Wire V-dipole benchmark, not an origami patch or surface antenna, and not a measurement.",
            "gates": {
                "fr_error_percent_max": fr_gate_percent,
                "rin_error_percent_max": rin_gate_percent,
            },
            "cases": cases_out,
            "straight_dipole_benchmark": {
                "passed": straight_passed,
                "result": "PASS" if straight_passed else "FAIL",
                "details": straight_case,
            },
            "fold_sweep_benchmark": {
                "passed": all_angles_passed,
                "result": "PASS" if all_angles_passed else "FAIL",
                "failed_angles_deg": [c["bend_deg"] for c in cases_out.values() if not c["passed"]],
            },
        }
