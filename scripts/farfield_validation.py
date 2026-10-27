"""Far-field Directivity, Efficiency, Gain, and Radiation Pattern Validation against NEC2.

Evaluates wire V-dipole across bend angles (0, 30, 60, 90, 120 deg) at N=40 and N=80
against NEC2 (RP card integration) at each angle's zero-reactance resonance f0.
"""

from __future__ import annotations
import json
import math
import os
import sys
from typing import Any, Dict, List, Tuple
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import necpp
except ImportError:
    necpp = None
from rf_origami.rf.solver.validation_cases import build_v_dipole_discretization
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.materials.material import C_0, ETA_0

# ==============================================================================
# STEP 2: PRE-DETERMINED ACCEPTANCE GATES (DEFINED BEFORE EVALUATION)
# ==============================================================================
GATE_DIRECTIVITY_DB = 0.5    # Error within 0.5 dB of NEC2
GATE_EFFICIENCY_PCT = 5.0    # Absolute percentage points error within 5.0%
GATE_GAIN_DB = 0.5           # Error within 0.5 dB of NEC2
GATE_PEAK_DIR_DEG = 5.0      # Angular separation within 5.0 degrees of NEC2

# Physical Constants and Geometry
TOTAL_LENGTH_M = 0.05746     # 57.46 mm total length
WIRE_RADIUS_M = 0.0005       # a = 0.5 mm radius
SIGMA_COPPER = 5.8e7         # Copper conductivity 5.8e7 S/m
BEND_ANGLES = [0, 30, 60, 90, 120]
SEGMENT_COUNTS = [40, 80]


def run_sanity_checks() -> Dict[str, Any]:
    """Step 3 Sanity checks (no NEC2 needed):

    Straight dipole in free space:
    1. Directivity should be ~2.15 dBi (textbook ideal half-wave dipole).
    2. Exact null along wire axis (theta = 0 and 180 deg).
    3. Lossless case should yield efficiency ~100%.
    """
    results = {}
    f_ref = 2412447218.6059513  # Resonance of straight dipole
    k0 = 2.0 * math.pi * f_ref / C_0
    omega = 2.0 * math.pi * f_ref

    for nseg in [40, 80]:
        for condition, sigma in [("Lossless", 1e14), ("Copper", SIGMA_COPPER)]:
            disc = build_v_dipole_discretization(
                0.0, num_segments=nseg, total_length_mm=TOTAL_LENGTH_M * 1e3,
                wire_radius_mm=WIRE_RADIUS_M * 1e3, conductivity=sigma
            )
            solver = MoMSolver(disc)
            N = disc.num_segments
            fi = disc.port_segment_index - 1
            Z = solver._assemble_impedance_matrix(k=k0, eta=ETA_0, omega=omega, freq=f_ref)
            V = np.zeros(N - 1, dtype=complex)
            V[fi] = 1.0
            I_vec = np.linalg.solve(Z, V)
            I_nodes = np.zeros(N + 1, dtype=complex)
            I_nodes[1:N] = I_vec

            segs = disc.segments
            p1 = np.array([s.p1 for s in segs]) * 1e-3
            p2 = np.array([s.p2 for s in segs]) * 1e-3
            dr = p2 - p1
            rc = 0.5 * (p1 + p2)
            I_bar = 0.5 * (I_nodes[:-1] + I_nodes[1:])

            thetas = np.radians(np.linspace(0, 180, 181))
            phis = np.radians(np.linspace(0, 360, 361))
            th_grid, ph_grid = np.meshgrid(thetas, phis, indexing="ij")
            rx = np.sin(th_grid) * np.cos(ph_grid)
            ry = np.sin(th_grid) * np.sin(ph_grid)
            rz = np.cos(th_grid)
            r_hat = np.stack([rx, ry, rz], axis=-1)

            phase = np.exp(1j * k0 * np.sum(r_hat[..., None, :] * rc, axis=-1))
            N_vec = np.sum(dr * I_bar[:, None] * phase[..., None], axis=-2)
            theta_hat = np.stack([np.cos(th_grid) * np.cos(ph_grid), np.cos(th_grid) * np.sin(ph_grid), -np.sin(th_grid)], axis=-1)
            phi_hat = np.stack([-np.sin(ph_grid), np.cos(ph_grid), np.zeros_like(ph_grid)], axis=-1)
            N_th = np.sum(N_vec * theta_hat, axis=-1)
            N_ph = np.sum(N_vec * phi_hat, axis=-1)
            U = (k0**2 * ETA_0 / (32.0 * math.pi**2)) * (np.abs(N_th)**2 + np.abs(N_ph)**2)

            P_rad = np.trapezoid(np.trapezoid(U * np.sin(th_grid), thetas, axis=0), phis)
            I_in = I_vec[fi]
            P_in = 0.5 * np.real(1.0 * np.conj(I_in))
            eff_pct = (P_rad / P_in) * 100.0
            D_max = 4.0 * math.pi * np.max(U) / P_rad
            D_dbi = 10.0 * math.log10(D_max)
            U_axis_0 = float(U[0, 0])
            U_axis_180 = float(U[-1, 0])
            U_max = float(np.max(U))

            results[f"N={nseg}_{condition}"] = {
                "directivity_dbi": D_dbi,
                "efficiency_pct": eff_pct,
                "null_0_deg": U_axis_0,
                "null_180_deg": U_axis_180,
                "u_max": U_max,
            }
    return results


def solve_nec2(bend_deg: float, nseg: int, f0: float) -> Dict[str, Any]:
    """Solve radiation metrics in NEC2 via RP card and spherical integration.

    NEC2 power integration method:
    Since necpp's get_average_power_gain() is not bound reliably across builds,
    we sample the 3D power gain pattern G(theta, phi) in dBi using the RP card:
        rp_card(0, 181, 361, 0, 0, 0, 0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0)
    We convert G_lin = 10^(G_dBi / 10).
    The radiated power is P_rad = P_in * (1 / 4*pi) * int G_lin * sin(theta) dtheta dphi.
    The radiation efficiency is eta_rad = P_rad / P_in = G_avg.
    The directivity is D_dBi = G_max_dBi - 10*log10(eta_rad).
    """
    if necpp is None:
        raise RuntimeError("necpp is not available in the current environment")

    h = TOTAL_LENGTH_M / 2.0
    ang = math.radians(bend_deg) / 2.0
    half = nseg // 2

    n = necpp.nec_create()
    if bend_deg == 0:
        necpp.nec_wire(n, 1, half, 0, 0, -h, 0, 0, 0, WIRE_RADIUS_M, 1, 1)
        necpp.nec_wire(n, 2, half, 0, 0, 0, 0, 0, h, WIRE_RADIUS_M, 1, 1)
        tag, seg = 2, 1
    else:
        necpp.nec_wire(n, 1, half, h * math.sin(ang), 0, -h * math.cos(ang), 0, 0, 0, WIRE_RADIUS_M, 1, 1)
        necpp.nec_wire(n, 2, half, 0, 0, 0, h * math.sin(ang), 0, h * math.cos(ang), WIRE_RADIUS_M, 1, 1)
        tag, seg = 2, 1

    necpp.nec_geometry_complete(n, 0)
    necpp.nec_ld_card(n, 5, 0, 0, 0, SIGMA_COPPER, 0, 0)
    necpp.nec_ex_card(n, 0, tag, seg, 0, 1.0, 0, 0, 0, 0, 0)
    necpp.nec_fr_card(n, 0, 1, f0 / 1e6, 0)

    ctx = necpp._contexts[n]
    ctx.rp_card(0, 181, 361, 0, 0, 0, 0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0)
    rp = ctx.get_radiation_pattern(0)
    g_db = rp.get_gain()

    thetas = np.radians(rp.get_theta_angles())
    phis = np.radians(rp.get_phi_angles())
    g_lin = 10.0 ** (g_db / 10.0)

    p_rad_norm = np.trapezoid(np.trapezoid(g_lin * np.sin(thetas)[:, None], thetas, axis=0), phis)
    eff_pct = (p_rad_norm / (4.0 * math.pi)) * 100.0
    g_max_dbi = float(np.max(g_db))
    d_max_dbi = g_max_dbi - 10.0 * math.log10(eff_pct / 100.0)

    # Restrict peak search to phi in [0, 180] due to exact bilateral y-symmetry
    g_half = g_db[:, :181]
    max_idx = np.unravel_index(np.argmax(g_half), g_half.shape)
    th_peak_deg = float(rp.get_theta_angles()[max_idx[0]])
    ph_peak_deg = float(rp.get_phi_angles()[max_idx[1]])

    necpp.nec_delete(n)

    return {
        "directivity_dbi": d_max_dbi,
        "efficiency_pct": eff_pct,
        "gain_dbi": g_max_dbi,
        "peak_theta_deg": th_peak_deg,
        "peak_phi_deg": ph_peak_deg,
    }


def solve_mom(bend_deg: float, nseg: int, f0: float, conductivity: float = SIGMA_COPPER) -> Dict[str, Any]:
    """Solve radiation metrics in Method of Moments using solved rooftop currents.

    Vector potential radiation integral:
        N(r_hat) = sum_{i=1}^N Delta r_i * I_bar_i * exp(j * k0 * r_hat . r_c,i)
        U(theta, phi) = (k0^2 * eta0 / (32 * pi^2)) * (|N_theta|^2 + |N_phi|^2)
        P_rad = int int U(theta, phi) sin(theta) dtheta dphi
        P_in = 0.5 * Re(V0 * I_in^*)
        eta_rad = P_rad / P_in
        D = 4 * pi * U_max / P_rad
        G = 4 * pi * U_max / P_in
    """
    k0 = 2.0 * math.pi * f0 / C_0
    omega = 2.0 * math.pi * f0

    disc = build_v_dipole_discretization(
        bend_deg, num_segments=nseg, total_length_mm=TOTAL_LENGTH_M * 1e3,
        wire_radius_mm=WIRE_RADIUS_M * 1e3, conductivity=conductivity
    )
    solver = MoMSolver(disc)
    N = disc.num_segments
    fi = disc.port_segment_index - 1
    Z = solver._assemble_impedance_matrix(k=k0, eta=ETA_0, omega=omega, freq=f0)
    V = np.zeros(N - 1, dtype=complex)
    V[fi] = 1.0
    I_vec = np.linalg.solve(Z, V)
    I_nodes = np.zeros(N + 1, dtype=complex)
    I_nodes[1:N] = I_vec

    segs = disc.segments
    p1 = np.array([s.p1 for s in segs]) * 1e-3
    p2 = np.array([s.p2 for s in segs]) * 1e-3
    dr = p2 - p1
    rc = 0.5 * (p1 + p2)
    I_bar = 0.5 * (I_nodes[:-1] + I_nodes[1:])

    thetas = np.radians(np.linspace(0, 180, 181))
    phis = np.radians(np.linspace(0, 360, 361))
    th_grid, ph_grid = np.meshgrid(thetas, phis, indexing="ij")
    rx = np.sin(th_grid) * np.cos(ph_grid)
    ry = np.sin(th_grid) * np.sin(ph_grid)
    rz = np.cos(th_grid)
    r_hat = np.stack([rx, ry, rz], axis=-1)

    phase = np.exp(1j * k0 * np.sum(r_hat[..., None, :] * rc, axis=-1))
    N_vec = np.sum(dr * I_bar[:, None] * phase[..., None], axis=-2)
    theta_hat = np.stack([np.cos(th_grid) * np.cos(ph_grid), np.cos(th_grid) * np.sin(ph_grid), -np.sin(th_grid)], axis=-1)
    phi_hat = np.stack([-np.sin(ph_grid), np.cos(ph_grid), np.zeros_like(ph_grid)], axis=-1)
    N_th = np.sum(N_vec * theta_hat, axis=-1)
    N_ph = np.sum(N_vec * phi_hat, axis=-1)
    U = (k0**2 * ETA_0 / (32.0 * math.pi**2)) * (np.abs(N_th)**2 + np.abs(N_ph)**2)

    P_rad = np.trapezoid(np.trapezoid(U * np.sin(th_grid), thetas, axis=0), phis)
    I_in = I_vec[fi]
    P_in = 0.5 * np.real(1.0 * np.conj(I_in))
    eff_pct = (P_rad / P_in) * 100.0

    U_max = np.max(U)
    D_max = 4.0 * math.pi * U_max / P_rad
    D_dbi = 10.0 * math.log10(D_max)
    G_max = 4.0 * math.pi * U_max / P_in
    G_dbi = 10.0 * math.log10(G_max)

    # Restrict peak search to phi in [0, 180] for bilateral symmetry matching
    U_half = U[:, :181]
    max_idx = np.unravel_index(np.argmax(U_half), U_half.shape)
    th_peak_deg = float(np.degrees(thetas[max_idx[0]]))
    ph_peak_deg = float(np.degrees(phis[max_idx[1]]))

    return {
        "directivity_dbi": D_dbi,
        "efficiency_pct": eff_pct,
        "gain_dbi": G_dbi,
        "peak_theta_deg": th_peak_deg,
        "peak_phi_deg": ph_peak_deg,
        "p_rad": P_rad,
        "p_in": P_in,
    }


def compute_angular_separation(th1_deg: float, ph1_deg: float, th2_deg: float, ph2_deg: float) -> float:
    """Compute 3D angular separation between two spherical direction vectors in degrees."""
    th1, ph1 = math.radians(th1_deg), math.radians(ph1_deg)
    th2, ph2 = math.radians(th2_deg), math.radians(ph2_deg)
    u1 = np.array([math.sin(th1) * math.cos(ph1), math.sin(th1) * math.sin(ph1), math.cos(th1)])
    u2 = np.array([math.sin(th2) * math.cos(ph2), math.sin(th2) * math.sin(ph2), math.cos(th2)])
    dot = np.clip(np.dot(u1, u2), -1.0, 1.0)
    return float(math.degrees(math.acos(dot)))


def run_validation_sweep() -> List[Dict[str, Any]]:
    """Run full validation sweep across all angles and segment counts."""
    ref_path = os.path.join(os.path.dirname(__file__), "..", "data", "validation", "nec2_reference.json")
    with open(ref_path, "r") as f:
        ref_data = json.load(f)["cases"]

    rows = []
    for bend in BEND_ANGLES:
        f0 = ref_data[str(bend)]["reactance_zero_hz"]
        for nseg in SEGMENT_COUNTS:
            nec = solve_nec2(bend, nseg, f0)
            mom = solve_mom(bend, nseg, f0)

            err_d = abs(mom["directivity_dbi"] - nec["directivity_dbi"])
            err_eff = abs(mom["efficiency_pct"] - nec["efficiency_pct"])
            err_g = abs(mom["gain_dbi"] - nec["gain_dbi"])
            err_peak = compute_angular_separation(
                mom["peak_theta_deg"], mom["peak_phi_deg"],
                nec["peak_theta_deg"], nec["peak_phi_deg"]
            )

            pass_d = err_d <= GATE_DIRECTIVITY_DB
            pass_eff = err_eff <= GATE_EFFICIENCY_PCT
            pass_g = err_g <= GATE_GAIN_DB
            pass_peak = err_peak <= GATE_PEAK_DIR_DEG
            all_pass = pass_d and pass_eff and pass_g and pass_peak

            row = {
                "bend_deg": bend,
                "nseg": nseg,
                "f0_ghz": f0 * 1e-9,
                "nec_d_dbi": nec["directivity_dbi"],
                "mom_d_dbi": mom["directivity_dbi"],
                "err_d_db": err_d,
                "pass_d": pass_d,
                "nec_eff_pct": nec["efficiency_pct"],
                "mom_eff_pct": mom["efficiency_pct"],
                "err_eff_pct": err_eff,
                "pass_eff": pass_eff,
                "nec_g_dbi": nec["gain_dbi"],
                "mom_g_dbi": mom["gain_dbi"],
                "err_g_db": err_g,
                "pass_g": pass_g,
                "nec_peak": (nec["peak_theta_deg"], nec["peak_phi_deg"]),
                "mom_peak": (mom["peak_theta_deg"], mom["peak_phi_deg"]),
                "err_peak_deg": err_peak,
                "pass_peak": pass_peak,
                "all_pass": all_pass,
            }
            rows.append(row)
    return rows


def print_step5_table(rows: List[Dict[str, Any]]):
    """Print the formatted validation table specified in Step 5."""
    print("=" * 135)
    print("STEP 5: FAR-FIELD VALIDATION TABLE (WIRE V-DIPOLE, FREE SPACE, VS NEC2)")
    print(f"Gates: Directivity <= {GATE_DIRECTIVITY_DB} dB | Efficiency <= {GATE_EFFICIENCY_PCT}% | Gain <= {GATE_GAIN_DB} dB | Peak Dir <= {GATE_PEAK_DIR_DEG} deg")
    print("=" * 135)
    header = (
        f"{'Angle':>5} | {'N':>2} | "
        f"{'NEC D':>6} {'MoM D':>6} {'dD(dB)':>6} {'PassD':>5} | "
        f"{'NEC eff':>7} {'MoM eff':>7} {'deff(%)':>7} {'PassE':>5} | "
        f"{'NEC G':>6} {'MoM G':>6} {'dG(dB)':>6} {'PassG':>5} | "
        f"{'NEC Pk':>9} {'MoM Pk':>9} {'dPk(d)':>6} {'PassPk':>6} | "
        f"{'OVERALL':>7}"
    )
    print(header)
    print("-" * 135)

    for r in rows:
        nec_pk_str = f"({r['nec_peak'][0]:.0f},{r['nec_peak'][1]:.0f})"
        mom_pk_str = f"({r['mom_peak'][0]:.0f},{r['mom_peak'][1]:.0f})"
        status_str = "PASS" if r["all_pass"] else "FAIL"

        line = (
            f"{r['bend_deg']:>5d} | {r['nseg']:>2d} | "
            f"{r['nec_d_dbi']:>6.3f} {r['mom_d_dbi']:>6.3f} {r['err_d_db']:>6.4f} {'PASS' if r['pass_d'] else 'FAIL':>5} | "
            f"{r['nec_eff_pct']:>6.2f}% {r['mom_eff_pct']:>6.2f}% {r['err_eff_pct']:>6.2f}% {'PASS' if r['pass_eff'] else 'FAIL':>5} | "
            f"{r['nec_g_dbi']:>6.3f} {r['mom_g_dbi']:>6.3f} {r['err_g_db']:>6.4f} {'PASS' if r['pass_g'] else 'FAIL':>5} | "
            f"{nec_pk_str:>9} {mom_pk_str:>9} {r['err_peak_deg']:>6.2f} {'PASS' if r['pass_peak'] else 'FAIL':>6} | "
            f"{status_str:>7}"
        )
        print(line)
    print("=" * 135)


if __name__ == "__main__":
    print("\n--- STEP 3: SANITY CHECKS ---")
    sanity = run_sanity_checks()
    for k, v in sanity.items():
        print(f"[{k}] Directivity: {v['directivity_dbi']:.3f} dBi | Efficiency: {v['efficiency_pct']:.2f}% | "
              f"Null at theta=0: {v['null_0_deg']:.2e} W/sr | Null at theta=180: {v['null_180_deg']:.2e} W/sr | "
              f"Peak intensity: {v['u_max']:.6e} W/sr")

    print("\n--- STEP 4 & 5: RUNNING VALIDATION SWEEP ---")
    rows = run_validation_sweep()
    print_step5_table(rows)
