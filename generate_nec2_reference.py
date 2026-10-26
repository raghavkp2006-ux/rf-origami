"""Generate independent NEC2 reference data for the wire dipole / V-dipole.

Requires:  pip install necpp
Run:       python generate_nec2_reference.py
Output:    nec2_reference.json  (commit it with this script; never edit values by hand)

Geometry: total wire length 57.46 mm, radius 0.5 mm, copper (sigma = 5.8e7 S/m),
free space, 1.8-3.0 GHz, 61 samples, 1 V delta-gap feed at the centre/apex.
bend_deg = 0 is a straight dipole; larger values bend each arm by bend_deg/2 from the axis
(arms stay in the x-z plane, feed at the apex).
NEC2 uses 80 segments (converged: R changes < 1% between 80 and 120 segments at 90 deg).
"""
import json, math
import numpy as np
import necpp

L, A, SIGMA = 57.46e-3, 0.5e-3, 5.8e7
FREQS_HZ = np.linspace(1.8e9, 3.0e9, 61)
NSEG = 80
BENDS = [0, 30, 60, 90, 120]


def run(bend_deg, nseg=NSEG):
    out = []
    h = L / 2
    ang = math.radians(bend_deg) / 2
    for f in FREQS_HZ:
        n = necpp.nec_create()
        if bend_deg == 0:
            necpp.nec_wire(n, 1, nseg + 1, 0, 0, -h, 0, 0, h, A, 1, 1)   # odd count -> centre segment
            tag, seg = 1, (nseg + 1) // 2 + 1
        else:
            half = nseg // 2
            necpp.nec_wire(n, 1, half, h * math.sin(ang), 0, -h * math.cos(ang), 0, 0, 0, A, 1, 1)
            necpp.nec_wire(n, 2, half, 0, 0, 0, h * math.sin(ang), 0, h * math.cos(ang), A, 1, 1)
            tag, seg = 2, 1
        necpp.nec_geometry_complete(n, 0)
        necpp.nec_ld_card(n, 5, 0, 0, 0, SIGMA, 0, 0)
        necpp.nec_ex_card(n, 0, tag, seg, 0, 1.0, 0, 0, 0, 0, 0)
        necpp.nec_fr_card(n, 0, 1, f / 1e6, 0)
        necpp.nec_xq_card(n, 0)
        out.append([necpp.nec_impedance_real(n, 0), necpp.nec_impedance_imag(n, 0)])
        necpp.nec_delete(n)
    return np.array(out)


def reactance_zero(z):
    i = np.where(np.diff(np.sign(z[:, 1])) != 0)[0][0]
    f0 = FREQS_HZ[i] - z[i, 1] * (FREQS_HZ[i + 1] - FREQS_HZ[i]) / (z[i + 1, 1] - z[i, 1])
    return float(f0), float(np.interp(f0, FREQS_HZ, z[:, 0]))


data = {"geometry": {"length_m": L, "radius_m": A, "sigma_S_per_m": SIGMA, "nec_segments": NSEG},
        "freqs_hz": FREQS_HZ.tolist(), "cases": {}}
for b in BENDS:
    z = run(b)
    f0, r0 = reactance_zero(z)
    data["cases"][str(b)] = {"zin_real": z[:, 0].tolist(), "zin_imag": z[:, 1].tolist(),
                             "reactance_zero_hz": f0, "rin_at_reactance_zero": r0}
    print(f"bend {b:3d} deg: fX0 = {f0/1e9:.4f} GHz, R = {r0:.2f} ohm")
json.dump(data, open("nec2_reference.json", "w"), indent=1)
print("wrote nec2_reference.json")
