"""Evaluation of smooth bends vs sharp-corner junctions for V-dipole input resistance.

Standalone script: not part of the automated test suite.
Does NOT write into data/validation.

Compares NEC2 and in-house Galerkin rooftop MoM solver for:
  a. Current sharp-corner V-dipole (two straight wires, feed at apex)
  b. Smoothed bend: replacing the corner with 3, 5, and 9 short straight wire pieces
     turning gradually, maintaining the same total length (57.46 mm), wire radius
     (a = 0.5 mm), and copper conductivity (5.8e7 S/m), with feed at the center.

Evaluates total bend angles 90 and 120 degrees over 1.8 - 3.0 GHz (61 points).
"""
import math
import os
import sys
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import necpp
from rf_origami.rf.solver.mom_solver import MoMSolver
from rf_origami.rf.mesh.discretization import EMDiscretization, EMSegment
from rf_origami.rf.solver.validation_cases import build_v_dipole_discretization, interpolate_reactance_zero

L = 57.46e-3
A = 0.5e-3
SIGMA = 5.8e7
FREQS_HZ = np.linspace(1.8e9, 3.0e9, 61)


def run_sharp(bend_deg, nseg=80):
    """Run NEC2 and MoM for the canonical sharp-corner V-dipole (N=80)."""
    ang = math.radians(bend_deg) / 2.0
    h = L / 2.0
    half = nseg // 2

    # NEC2 sharp model: two straight wires meeting at apex, feed on wire 2 seg 1
    out_nec = []
    for f in FREQS_HZ:
        n = necpp.nec_create()
        necpp.nec_wire(n, 1, half, h * math.sin(ang), 0, -h * math.cos(ang), 0, 0, 0, A, 1.0, 1.0)
        necpp.nec_wire(n, 2, half, 0, 0, 0, h * math.sin(ang), 0, h * math.cos(ang), A, 1.0, 1.0)
        necpp.nec_geometry_complete(n, 0)
        necpp.nec_ld_card(n, 5, 0, 0, 0, SIGMA, 0, 0)
        necpp.nec_ex_card(n, 0, 2, 1, 0, 1.0, 0, 0, 0, 0, 0)
        necpp.nec_fr_card(n, 0, 1, f / 1e6, 0)
        necpp.nec_xq_card(n, 0)
        out_nec.append([necpp.nec_impedance_real(n, 0), necpp.nec_impedance_imag(n, 0)])
        necpp.nec_delete(n)

    zin_nec = np.array(out_nec)
    f0_nec, r0_nec = interpolate_reactance_zero(FREQS_HZ, zin_nec)

    # MoM sharp model
    discr = build_v_dipole_discretization(
        bend_deg=bend_deg,
        num_segments=nseg,
        total_length_mm=L * 1000.0,
        wire_radius_mm=A * 1000.0,
        conductivity=SIGMA,
    )
    solver = MoMSolver(discretization=discr)
    sweep = solver.solve_sweep(FREQS_HZ[0], FREQS_HZ[-1], len(FREQS_HZ))
    zin_mom = np.column_stack([sweep["zin_real_ohms"], sweep["zin_imag_ohms"]])
    f0_mom, r0_mom = interpolate_reactance_zero(FREQS_HZ, zin_mom)

    rin_err = abs(r0_mom - r0_nec) / r0_nec * 100.0
    return f0_nec, r0_nec, f0_mom, r0_mom, rin_err


def build_smooth_polyline(bend_deg, K, total_segs=81):
    """Build smoothed polyline geometry replacing the corner with K pieces turning gradually."""
    M = (total_segs - K) // 2
    delta_s = L / total_segs
    ang = math.radians(bend_deg) / 2.0
    delta = (2.0 * ang) / (K + 1)

    # Directions phi relative to z-axis in x-z plane (dx/ds = sin(phi), dz/ds = cos(phi))
    phi_list = []
    for _ in range(M):
        phi_list.append(-ang)
    for k in range(K):
        phi_k = -ang + (k + 1) * delta
        phi_list.append(phi_k)
    for _ in range(M):
        phi_list.append(ang)

    nodes = [np.array([0.0, 0.0, 0.0])]
    for phi in phi_list:
        step = np.array([delta_s * math.sin(phi), 0.0, delta_s * math.cos(phi)])
        nodes.append(nodes[-1] + step)
    nodes = np.array(nodes)

    # Center nodes symmetrically around x=0, z=0
    mid_idx = total_segs // 2
    mid_pt = 0.5 * (nodes[mid_idx] + nodes[mid_idx + 1])
    nodes = nodes - mid_pt

    return nodes, M, K


def run_smooth(bend_deg, K, total_segs=81):
    """Run NEC2 and MoM on the identical smoothed polyline."""
    nodes, M, K_val = build_smooth_polyline(bend_deg, K, total_segs=total_segs)
    mid_seg = total_segs // 2

    # NEC2: Arm 1 (M segs) + K bend wires (1 seg each) + Arm 2 (M segs)
    out_nec = []
    for f in FREQS_HZ:
        n = necpp.nec_create()
        # Wire 1: Arm 1
        p_start = nodes[0]
        p_arm1_end = nodes[M]
        necpp.nec_wire(n, 1, M, p_start[0], p_start[1], p_start[2],
                       p_arm1_end[0], p_arm1_end[1], p_arm1_end[2], A, 1.0, 1.0)

        # Wires 2 to K+1: K bend pieces
        for k in range(K):
            tag = 2 + k
            p1 = nodes[M + k]
            p2 = nodes[M + k + 1]
            necpp.nec_wire(n, tag, 1, p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], A, 1.0, 1.0)

        # Wire K+2: Arm 2
        p_arm2_start = nodes[M + K]
        p_end = nodes[-1]
        necpp.nec_wire(n, K + 2, M, p_arm2_start[0], p_arm2_start[1], p_arm2_start[2],
                       p_end[0], p_end[1], p_end[2], A, 1.0, 1.0)

        necpp.nec_geometry_complete(n, 0)
        necpp.nec_ld_card(n, 5, 0, 0, 0, SIGMA, 0, 0)

        # Feed on the center segment of the bend
        center_tag = 2 + (K // 2)
        necpp.nec_ex_card(n, 0, center_tag, 1, 0, 1.0, 0, 0, 0, 0, 0)
        necpp.nec_fr_card(n, 0, 1, f / 1e6, 0)
        necpp.nec_xq_card(n, 0)
        out_nec.append([necpp.nec_impedance_real(n, 0), necpp.nec_impedance_imag(n, 0)])
        necpp.nec_delete(n)

    zin_nec = np.array(out_nec)
    f0_nec, r0_nec = interpolate_reactance_zero(FREQS_HZ, zin_nec)

    # MoM on the same polyline
    segs = []
    for i in range(total_segs):
        segs.append(EMSegment(
            index=i,
            p1=nodes[i] * 1000.0,
            p2=nodes[i + 1] * 1000.0,
            radius_mm=A * 1000.0,
            conductivity=SIGMA,
        ))

    discr = EMDiscretization(segments=segs, port_segment_index=mid_seg)
    solver = MoMSolver(discretization=discr)
    sweep = solver.solve_sweep(FREQS_HZ[0], FREQS_HZ[-1], len(FREQS_HZ))
    zin_mom = np.column_stack([sweep["zin_real_ohms"], sweep["zin_imag_ohms"]])
    f0_mom, r0_mom = interpolate_reactance_zero(FREQS_HZ, zin_mom)

    rin_err = abs(r0_mom - r0_nec) / r0_nec * 100.0
    return f0_nec, r0_nec, f0_mom, r0_mom, rin_err


def main():
    print("=" * 95)
    print("  SMOOTHED BEND VS SHARP JUNCTION V-DIPOLE COMPARISON (NEC2 vs MoM)")
    print("  Total length: 57.46 mm, Radius: 0.5 mm, Copper sigma: 5.8e7 S/m, 1.8-3.0 GHz (61 pts)")
    print("=" * 95)

    cases = [
        (90, "sharp", None),
        (90, "smooth 3 pieces", 3),
        (90, "smooth 5 pieces", 5),
        (90, "smooth 9 pieces", 9),
        (120, "sharp", None),
        (120, "smooth 3 pieces", 3),
        (120, "smooth 5 pieces", 5),
        (120, "smooth 9 pieces", 9),
    ]

    results = []
    for bend, model, K in cases:
        if model == "sharp":
            f0_nec, r0_nec, f0_mom, r0_mom, err = run_sharp(bend)
        else:
            f0_nec, r0_nec, f0_mom, r0_mom, err = run_smooth(bend, K)

        results.append({
            "angle": bend,
            "model": model,
            "f0_nec": f0_nec,
            "r0_nec": r0_nec,
            "f0_mom": f0_mom,
            "r0_mom": r0_mom,
            "rin_err": err,
        })

    # Print Table
    print(f"\n{'Angle':>6} | {'Model':<16} | {'NEC2 f0 [GHz]':>13} | {'NEC2 Rin [Ohm]':>14} | {'MoM f0 [GHz]':>12} | {'MoM Rin [Ohm]':>13} | {'Rin Error %':>11}")
    print("-" * 97)
    for r in results:
        f0_n = f"{r['f0_nec'] / 1e9:.4f}"
        r0_n = f"{r['r0_nec']:.2f}"
        f0_m = f"{r['f0_mom'] / 1e9:.4f}"
        r0_m = f"{r['r0_mom']:.2f}"
        err = f"{r['rin_err']:.2f}%"
        print(f"{r['angle']:>4} deg | {r['model']:<16} | {f0_n:>13} | {r0_n:>14} | {f0_m:>12} | {r0_m:>13} | {err:>11}")
    print("-" * 97)

    # Interpretation using only the table
    print("\nInterpretation:")
    sharp_errs = [r["rin_err"] for r in results if r["model"] == "sharp"]
    smooth_errs = [r["rin_err"] for r in results if r["model"] != "sharp"]
    max_smooth_err = max(smooth_errs)
    min_smooth_err = min(smooth_errs)

    if max_smooth_err < 5.0:
        print(f"The Rin error drops from {min(sharp_errs):.2f}%-{max(sharp_errs):.2f}% (sharp corner) to "
              f"{min_smooth_err:.2f}%-{max_smooth_err:.2f}% (all strictly under 5%) as the bend is smoothed "
              f"across 3, 5, and 9 pieces at both 90 deg and 120 deg.")
        print("Conclusion: The Rin gap is tied to the sharp junction treatment rather than solver formulation on continuous curved wires.")
    else:
        print(f"The Rin error persists at {min_smooth_err:.2f}%-{max_smooth_err:.2f}% (5-11% range) as the bend is smoothed.")
        print("Conclusion: The Rin gap is not tied to the sharp junction.")


if __name__ == "__main__":
    main()
