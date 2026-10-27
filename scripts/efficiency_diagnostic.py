"""Radiation Efficiency Anomaly Diagnostic for Wire V-Dipole: NEC2 vs MoM.

================================================================================
STEP 1: PRE-DETERMINED INTERPRETATION RULES (RECORDED BEFORE RUNNING)
================================================================================
1. If NEC2 efficiency on a lossless (perfect conductor) sharp bend is below 99%,
   the NEC2 reference has a power-balance error at the junction, so the
   efficiency "FAIL" is not evidence against MoM.
2. If NEC2 lossless efficiency is about 100% but copper efficiency is far below
   99.8%, NEC2 has an unexplained loss mechanism; report it as unexplained.
3. If smoothing the bend restores NEC2 efficiency to about 99.8%, the anomaly is
   tied to NEC2's sharp-junction model.
================================================================================
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

import necpp
from rf_origami.rf.solver.validation_cases import build_v_dipole_discretization
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.materials.material import C_0, ETA_0
from rf_origami.rf.mesh.discretization import EMDiscretization, EMSegment
from scripts.nec2_smooth_bend import build_smooth_polyline, interpolate_reactance_zero

L = 0.05746           # 57.46 mm total length
A = 0.0005           # a = 0.5 mm radius
SIGMA_COPPER = 5.8e7  # Copper conductivity (S/m)
SIGMA_LOSSLESS = 1e14 # Effectively lossless / PEC
FREQS_SWEEP = np.linspace(1.8e9, 3.0e9, 61)


def solve_nec2_sharp(bend_deg: float, nseg: int, f0: float, sigma: float | None, grid_deg: float) -> Tuple[float, float, float]:
    """Solve NEC2 sharp bend: returns (Pin, Prad, Efficiency_pct)."""
    h = L / 2.0
    ang = math.radians(bend_deg) / 2.0
    half = nseg // 2

    n = necpp.nec_create()
    if bend_deg == 0:
        necpp.nec_wire(n, 1, half, 0, 0, -h, 0, 0, 0, A, 1, 1)
        necpp.nec_wire(n, 2, half, 0, 0, 0, 0, 0, h, A, 1, 1)
        tag, seg = 2, 1
    else:
        necpp.nec_wire(n, 1, half, h * math.sin(ang), 0, -h * math.cos(ang), 0, 0, 0, A, 1, 1)
        necpp.nec_wire(n, 2, half, 0, 0, 0, h * math.sin(ang), 0, h * math.cos(ang), A, 1, 1)
        tag, seg = 2, 1

    necpp.nec_geometry_complete(n, 0)
    if sigma is not None:
        necpp.nec_ld_card(n, 5, 0, 0, 0, sigma, 0, 0)
    necpp.nec_ex_card(n, 0, tag, seg, 0, 1.0, 0, 0, 0, 0, 0)
    necpp.nec_fr_card(n, 0, 1, f0 / 1e6, 0)
    necpp.nec_xq_card(n, 0)

    rin = necpp.nec_impedance_real(n, 0)
    xin = necpp.nec_impedance_imag(n, 0)
    pin = 0.5 * rin / (rin**2 + xin**2)

    nth = int(180 / grid_deg) + 1
    nph = int(360 / grid_deg) + 1
    ctx = necpp._contexts[n]
    ctx.rp_card(0, nth, nph, 0, 0, 0, 0, 0.0, 0.0, grid_deg, grid_deg, 0.0, 0.0)
    rp = ctx.get_radiation_pattern(0)
    g_db = rp.get_gain()

    thetas = np.radians(rp.get_theta_angles())
    phis = np.radians(rp.get_phi_angles())
    g_lin = 10.0 ** (g_db / 10.0)

    p_rad_norm = np.trapezoid(np.trapezoid(g_lin * np.sin(thetas)[:, None], thetas, axis=0), phis)
    eff_pct = (p_rad_norm / (4.0 * math.pi)) * 100.0
    prad = pin * (eff_pct / 100.0)

    necpp.nec_delete(n)
    return pin, prad, eff_pct


def solve_mom_sharp(bend_deg: float, nseg: int, f0: float, sigma: float) -> Tuple[float, float, float]:
    """Solve MoM sharp bend: returns (Pin, Prad, Efficiency_pct)."""
    k0 = 2.0 * math.pi * f0 / C_0
    omega = 2.0 * math.pi * f0

    disc = build_v_dipole_discretization(
        bend_deg, num_segments=nseg, total_length_mm=L * 1e3,
        wire_radius_mm=A * 1e3, conductivity=sigma
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

    prad = np.trapezoid(np.trapezoid(U * np.sin(th_grid), thetas, axis=0), phis)
    I_in = I_vec[fi]
    pin = 0.5 * np.real(1.0 * np.conj(I_in))
    eff_pct = (prad / pin) * 100.0

    return pin, prad, eff_pct


def solve_smooth_case(bend_deg: float, K: int, sigma: float | None) -> Tuple[float, float, float, float, float, float]:
    """Solve NEC2 and MoM for smoothed bend polyline at its own f0.

    Returns: (f0, nec_pin, nec_prad, nec_eff, mom_pin, mom_prad, mom_eff)
    """
    nodes, M, K_val = build_smooth_polyline(bend_deg, K, total_segs=81)
    total_segs = 81
    mid_seg = total_segs // 2

    # Frequency sweep to find zero-reactance resonance f0
    out_nec = []
    for f in FREQS_SWEEP:
        n = necpp.nec_create()
        p_start, p_arm1_end = nodes[0], nodes[M]
        necpp.nec_wire(n, 1, M, p_start[0], p_start[1], p_start[2], p_arm1_end[0], p_arm1_end[1], p_arm1_end[2], A, 1.0, 1.0)
        for k in range(K):
            p1, p2 = nodes[M + k], nodes[M + k + 1]
            necpp.nec_wire(n, 2 + k, 1, p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], A, 1.0, 1.0)
        p_arm2_start, p_end = nodes[M + K], nodes[-1]
        necpp.nec_wire(n, K + 2, M, p_arm2_start[0], p_arm2_start[1], p_arm2_start[2], p_end[0], p_end[1], p_end[2], A, 1.0, 1.0)
        necpp.nec_geometry_complete(n, 0)
        if sigma is not None:
            necpp.nec_ld_card(n, 5, 0, 0, 0, sigma, 0, 0)
        center_tag = 2 + (K // 2)
        necpp.nec_ex_card(n, 0, center_tag, 1, 0, 1.0, 0, 0, 0, 0, 0)
        necpp.nec_fr_card(n, 0, 1, f / 1e6, 0)
        necpp.nec_xq_card(n, 0)
        out_nec.append([necpp.nec_impedance_real(n, 0), necpp.nec_impedance_imag(n, 0)])
        necpp.nec_delete(n)

    zin_nec = np.array(out_nec)
    f0_nec, _ = interpolate_reactance_zero(FREQS_SWEEP, zin_nec)

    # Solve NEC2 radiation at f0_nec
    n = necpp.nec_create()
    p_start, p_arm1_end = nodes[0], nodes[M]
    necpp.nec_wire(n, 1, M, p_start[0], p_start[1], p_start[2], p_arm1_end[0], p_arm1_end[1], p_arm1_end[2], A, 1.0, 1.0)
    for k in range(K):
        p1, p2 = nodes[M + k], nodes[M + k + 1]
        necpp.nec_wire(n, 2 + k, 1, p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], A, 1.0, 1.0)
    p_arm2_start, p_end = nodes[M + K], nodes[-1]
    necpp.nec_wire(n, K + 2, M, p_arm2_start[0], p_arm2_start[1], p_arm2_start[2], p_end[0], p_end[1], p_end[2], A, 1.0, 1.0)
    necpp.nec_geometry_complete(n, 0)
    if sigma is not None:
        necpp.nec_ld_card(n, 5, 0, 0, 0, sigma, 0, 0)
    center_tag = 2 + (K // 2)
    necpp.nec_ex_card(n, 0, center_tag, 1, 0, 1.0, 0, 0, 0, 0, 0)
    necpp.nec_fr_card(n, 0, 1, f0_nec / 1e6, 0)
    necpp.nec_xq_card(n, 0)
    rin = necpp.nec_impedance_real(n, 0)
    xin = necpp.nec_impedance_imag(n, 0)
    nec_pin = 0.5 * rin / (rin**2 + xin**2)

    ctx = necpp._contexts[n]
    ctx.rp_card(0, 37, 73, 0, 0, 0, 0, 0.0, 0.0, 5.0, 5.0, 0.0, 0.0)
    rp = ctx.get_radiation_pattern(0)
    g_db = rp.get_gain()
    thetas = np.radians(rp.get_theta_angles())
    phis = np.radians(rp.get_phi_angles())
    g_lin = 10.0 ** (g_db / 10.0)
    p_rad_norm = np.trapezoid(np.trapezoid(g_lin * np.sin(thetas)[:, None], thetas, axis=0), phis)
    nec_eff = (p_rad_norm / (4.0 * math.pi)) * 100.0
    nec_prad = nec_pin * (nec_eff / 100.0)
    necpp.nec_delete(n)

    # Solve MoM on identical smoothed polyline
    segs = []
    sig_val = sigma if sigma is not None else SIGMA_LOSSLESS
    for i in range(len(nodes) - 1):
        segs.append(EMSegment(index=i, p1=nodes[i] * 1e3, p2=nodes[i + 1] * 1e3, radius_mm=A * 1e3, conductivity=sig_val))
    discr = EMDiscretization(segments=segs, port_segment_index=mid_seg)
    solver = MoMSolver(discr)
    k0 = 2.0 * math.pi * f0_nec / C_0
    omega = 2.0 * math.pi * f0_nec
    Z = solver._assemble_impedance_matrix(k=k0, eta=ETA_0, omega=omega, freq=f0_nec)
    V = np.zeros(total_segs - 1, dtype=complex)
    fi = mid_seg - 1
    V[fi] = 1.0
    I_vec = np.linalg.solve(Z, V)
    I_nodes = np.zeros(total_segs + 1, dtype=complex)
    I_nodes[1:total_segs] = I_vec

    p1_arr = np.array([s.p1 for s in segs]) * 1e-3
    p2_arr = np.array([s.p2 for s in segs]) * 1e-3
    dr = p2_arr - p1_arr
    rc = 0.5 * (p1_arr + p2_arr)
    I_bar = 0.5 * (I_nodes[:-1] + I_nodes[1:])

    thetas_m = np.radians(np.linspace(0, 180, 181))
    phis_m = np.radians(np.linspace(0, 360, 361))
    th_grid, ph_grid = np.meshgrid(thetas_m, phis_m, indexing="ij")
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

    mom_prad = np.trapezoid(np.trapezoid(U * np.sin(th_grid), thetas_m, axis=0), phis_m)
    I_in = I_vec[fi]
    mom_pin = 0.5 * np.real(1.0 * np.conj(I_in))
    mom_eff = (mom_prad / mom_pin) * 100.0

    return f0_nec, nec_pin, nec_prad, nec_eff, mom_pin, mom_prad, mom_eff


def run_diagnostics():
    ref_path = os.path.join(os.path.dirname(__file__), "..", "data", "validation", "nec2_reference.json")
    with open(ref_path, "r") as f:
        ref_cases = json.load(f)["cases"]

    print("=" * 140)
    print("STEP 2: RADIATION EFFICIENCY & POWER BUDGET DIAGNOSTIC TABLE")
    print("=" * 140)
    header = (
        f"{'Angle':>5} | {'Model / Condition':>24} | {'N':>2} | {'RP Grid':>7} | "
        f"{'NEC Pin (W)':>11} {'NEC Prad (W)':>12} {'NEC Eff':>8} | "
        f"{'MoM Pin (W)':>11} {'MoM Prad (W)':>12} {'MoM Eff':>8} | "
        f"{'Diff(%)':>7}"
    )
    print(header)
    print("-" * 140)

    # 1. Sharp bend cases across (a, b) and (d) grid resolutions
    angles = [0, 60, 90, 120]
    for grid in [5.0, 1.0]:
        for cond, sig in [("Lossless (PEC)", None), ("Copper", SIGMA_COPPER)]:
            for b in angles:
                f0 = ref_cases[str(b)]["reactance_zero_hz"]
                for nseg in [40, 80]:
                    sig_mom = sig if sig is not None else SIGMA_LOSSLESS
                    nec_pin, nec_prad, nec_eff = solve_nec2_sharp(b, nseg, f0, sig, grid)
                    mom_pin, mom_prad, mom_eff = solve_mom_sharp(b, nseg, f0, sig_mom)
                    diff = abs(mom_eff - nec_eff)
                    desc = f"Sharp, {cond}"
                    grid_str = f"{grid:.1f} deg"
                    line = (
                        f"{b:>5d} | {desc:>24} | {nseg:>2d} | {grid_str:>7} | "
                        f"{nec_pin:>11.5e} {nec_prad:>12.5e} {nec_eff:>7.2f}% | "
                        f"{mom_pin:>11.5e} {mom_prad:>12.5e} {mom_eff:>7.2f}% | "
                        f"{diff:>6.2f}%"
                    )
                    print(line)
        print("-" * 140)

    # 2. Smoothed bend cases (c) at 90 and 120 deg
    for b in [90, 120]:
        for K in [3, 5, 9]:
            for cond, sig in [("Copper", SIGMA_COPPER), ("Lossless (PEC)", None)]:
                f0_nec, nec_pin, nec_prad, nec_eff, mom_pin, mom_prad, mom_eff = solve_smooth_case(b, K, sig)
                diff = abs(mom_eff - nec_eff)
                desc = f"Smooth (K={K}), {cond}"
                line = (
                    f"{b:>5d} | {desc:>24} | {81:>2d} | {'5.0 deg':>7} | "
                    f"{nec_pin:>11.5e} {nec_prad:>12.5e} {nec_eff:>7.2f}% | "
                    f"{mom_pin:>11.5e} {mom_prad:>12.5e} {mom_eff:>7.2f}% | "
                    f"{diff:>6.2f}%"
                )
                print(line)
    print("=" * 140)


if __name__ == "__main__":
    run_diagnostics()
