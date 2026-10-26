"""Radius sweep and NEC2 self-consistency experiment for V-dipole input resistance.

Standalone script: not part of the automated test suite.
Evaluates NEC2 vs in-house Galerkin rooftop MoM solver across wire radii
a in [0.5 mm, 0.25 mm, 0.1 mm] at bend angles [0, 60, 90, 120] deg.
"""
import math
import os
import sys
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import necpp
from rf_origami.rf.solver.validation_cases import build_v_dipole_discretization
from rf_origami.rf.solver.mom_solver import MoMSolver

L = 57.46e-3
SIGMA = 5.8e7
FREQS_HZ = np.linspace(1.8e9, 3.0e9, 61)


def run_nec2(bend_deg, a, nseg):
    """Run NEC2 frequency sweep for given bend angle, wire radius, and segment count."""
    h = L / 2.0
    ang = math.radians(bend_deg) / 2.0
    out = []
    for f in FREQS_HZ:
        n = necpp.nec_create()
        if bend_deg == 0:
            necpp.nec_wire(n, 1, nseg + 1, 0, 0, -h, 0, 0, h, a, 1.0, 1.0)
            tag, seg = 1, (nseg + 1) // 2 + 1
        else:
            half = nseg // 2
            necpp.nec_wire(n, 1, half, h * math.sin(ang), 0, -h * math.cos(ang), 0, 0, 0, a, 1.0, 1.0)
            necpp.nec_wire(n, 2, half, 0, 0, 0, h * math.sin(ang), 0, h * math.cos(ang), a, 1.0, 1.0)
            tag, seg = 2, 1
        necpp.nec_geometry_complete(n, 0)
        necpp.nec_ld_card(n, 5, 0, 0, 0, SIGMA, 0, 0)
        necpp.nec_ex_card(n, 0, tag, seg, 0, 1.0, 0, 0, 0, 0, 0)
        necpp.nec_fr_card(n, 0, 1, f / 1e6, 0)
        necpp.nec_xq_card(n, 0)
        out.append([necpp.nec_impedance_real(n, 0), necpp.nec_impedance_imag(n, 0)])
        necpp.nec_delete(n)
    return np.array(out)


def run_mom(bend_deg, a, nseg):
    """Run rooftop MoM solver frequency sweep for given bend angle, radius, and segment count."""
    discr = build_v_dipole_discretization(
        bend_deg=bend_deg,
        num_segments=nseg,
        total_length_mm=L * 1000.0,
        wire_radius_mm=a * 1000.0,
        conductivity=SIGMA,
    )
    solver = MoMSolver(discretization=discr)
    sweep = solver.solve_sweep(FREQS_HZ[0], FREQS_HZ[-1], len(FREQS_HZ))
    return np.column_stack([sweep["zin_real_ohms"], sweep["zin_imag_ohms"]])


def reactance_zero(z):
    """Linear interpolation of zero-reactance resonance frequency f0 and Rin."""
    crossings = np.where(np.diff(np.sign(z[:, 1])) != 0)[0]
    if len(crossings) == 0:
        return None, None
    i = crossings[0]
    f0 = FREQS_HZ[i] - z[i, 1] * (FREQS_HZ[i + 1] - FREQS_HZ[i]) / (z[i + 1, 1] - z[i, 1])
    r0 = float(np.interp(f0, FREQS_HZ, z[:, 0]))
    return float(f0), float(r0)


def main():
    print("=" * 80)
    print("STEP 1 & 2: RADIUS SWEEP EXPERIMENT (a = 0.5 mm, 0.25 mm, 0.1 mm)")
    print("=" * 80)
    print("Checking whether Rin error at 90/120 deg drops as wire radius a shrinks")
    print("Total wire length: 57.46 mm, Frequency: 1.8 - 3.0 GHz (61 pts)\n")

    # Selected configurations ensuring delta/a >= 2
    # For a = 0.5 mm:  N=40 (delta/a = 2.87); also evaluate N=80 (delta/a = 1.44)
    # For a = 0.25 mm: N=80 (delta/a = 2.87); also evaluate N=40 (delta/a = 5.75)
    # For a = 0.1 mm:  N=80 (delta/a = 7.18), N=160 (delta/a = 3.59); also N=40 (delta/a = 14.36)
    
    sweep_cases = [
        # (bend_deg, radius, [N_list])
        (bend, a, n_list)
        for a, n_list in [
            (0.5e-3, [40, 80]),
            (0.25e-3, [40, 80]),
            (0.1e-3, [40, 80, 160]),
        ]
        for bend in [0, 60, 90, 120]
    ]

    results = []
    for bend, a, n_list in sweep_cases:
        for N in n_list:
            delta = L / N
            delta_over_a = delta / a
            
            # NEC2 reference
            z_nec = run_nec2(bend, a, N)
            f0_nec, r0_nec = reactance_zero(z_nec)
            
            # MoM solve
            z_mom = run_mom(bend, a, N)
            f0_mom, r0_mom = reactance_zero(z_mom)
            
            if f0_nec is not None and f0_mom is not None:
                f0_err = abs(f0_mom - f0_nec) / f0_nec * 100.0
                rin_err = abs(r0_mom - r0_nec) / r0_nec * 100.0
            else:
                f0_err, rin_err = float('nan'), float('nan')
                
            res = {
                "bend": bend,
                "a_mm": a * 1000.0,
                "N": N,
                "delta_over_a": delta_over_a,
                "f0_nec": f0_nec / 1e9 if f0_nec else None,
                "r0_nec": r0_nec,
                "f0_mom": f0_mom / 1e9 if f0_mom else None,
                "r0_mom": r0_mom,
                "f0_err": f0_err,
                "rin_err": rin_err,
            }
            results.append(res)
            print(f"Angle {bend:3d} deg | a = {a*1000:4.2f} mm | N = {N:3d} (d/a={delta_over_a:4.2f}): "
                  f"NEC2=(f0={res['f0_nec']:.4f} GHz, Rin={res['r0_nec']:.2f} ohm) | "
                  f"MoM=(f0={res['f0_mom']:.4f} GHz, Rin={res['r0_mom']:.2f} ohm) | "
                  f"err_f0={f0_err:.2f}%, err_Rin={rin_err:.2f}%")

    print("\n" + "=" * 80)
    print("STEP 3: NEC2 SELF-CONSISTENCY CONVERGENCE CHECK (a = 0.5 mm, N = 20, 40, 80, 160)")
    print("=" * 80)
    print("Checking whether NEC2's own Rin and f0 converge across segment counts at sharp bends\n")

    nec_convergence = []
    for bend in [90, 120]:
        for N in [20, 40, 80, 160]:
            delta = L / N
            delta_over_a = delta / 0.5e-3
            z_nec = run_nec2(bend, 0.5e-3, N)
            f0_nec, r0_nec = reactance_zero(z_nec)
            nec_convergence.append({
                "bend": bend,
                "N": N,
                "delta_over_a": delta_over_a,
                "f0_nec": f0_nec / 1e9 if f0_nec else None,
                "r0_nec": r0_nec,
            })
            print(f"NEC2 Angle {bend:3d} deg | N = {N:3d} (d/a={delta_over_a:4.2f}): "
                  f"f0 = {f0_nec/1e9:.4f} GHz, Rin = {r0_nec:.2f} ohm")

    print("\nSUMMARY COMPLETE.")
    return results, nec_convergence


if __name__ == "__main__":
    main()
