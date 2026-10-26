"""Galerkin rooftop-basis wire impedance matrix (drop-in for rf_origami/rf/solver).

Save as rf_origami/rf/solver/rooftop_wire.py

INTEGRATION INTO MoMSolver
--------------------------
1. In mom_solver.py:
       from rf_origami.rf.solver.rooftop_wire import assemble_rooftop

2. Replace the body of MoMSolver._assemble_impedance_matrix with:

       segs = self.discretization.segments
       p1 = np.array([s.p1 for s in segs], float) * 1e-3
       p2 = np.array([s.p2 for s in segs], float) * 1e-3
       rad = np.array([s.radius_mm for s in segs], float) * 1e-3
       sig = np.array([s.conductivity for s in segs], float)
       Z, self.last_asymmetry = assemble_rooftop(p1, p2, rad, sig, k, omega)
       return Z

3. In solve_frequency, the system now has N-1 unknowns (one per node between
   consecutive segments; zero current at both free ends). Replace the V vector part:

       N = self.discretization.num_segments
       p = self.discretization.port_segment_index      # feed node sits between segment p-1 and p
       if not 1 <= p <= N - 1:
           raise ValueError("Feed index must satisfy 1 <= port_segment_index <= N-1.")
       fi = p - 1
       V_vec = np.zeros(N - 1, dtype=np.complex128)
       V_vec[fi] = 1.0
       I_vec = np.linalg.solve(Z_mat, V_vec)
       I_in = I_vec[fi]
       ...and use fi (not p_idx) when indexing I_vec.

4. Mesh requirement: segments must be consecutive along ONE open polyline
   (segment i ends where segment i+1 starts). Use an EVEN segment count for a
   centre-fed dipole (10, 20, 30, 40) so a node exists at the centre; set
   port_segment_index = N // 2. Branched or closed conductors need junction/loop
   basis functions, which this module does not implement.

5. Validation report: reciprocity gate should use self.last_asymmetry (the value
   BEFORE symmetrisation, a quadrature-consistency number) with a relative
   tolerance such as 1e-4. Z is mirrored afterwards, so a post-symmetrisation
   check would always pass and prove nothing.

Status: tested on a standalone script only, not inside your repo. Results are NOT
validated against NEC2/openEMS. Basis: rooftop, testing: Galerkin, kernel: reduced
(thin-wire) kernel with exact asinh static part, delta-gap feed.
"""
import math
import numpy as np

_GO_X, _GO_W = np.polynomial.legendre.leggauss(8)
_GI_X, _GI_W = np.polynomial.legendre.leggauss(16)
MU_0 = 4e-7 * math.pi
C_0 = 299792458.0
EPS_0 = 1.0 / (MU_0 * C_0 ** 2)


def _inner_moments(points, centers, dirs, half, a, k):
    """For each field point and source segment return (M0, M1):
    M0 = int G dt, M1 = int t G dt over t in [-h, h] (t measured from the segment centre).
    Reduced kernel G = exp(-jkR)/(4 pi R), R = sqrt(dist^2 + a^2).
    The static 1/R part is exact (asinh); the smooth remainder uses Gauss quadrature."""
    d = points[:, :, None, :] - centers[None, None, :, :]
    t0 = np.einsum('mgnc,nc->mgn', d, dirs)
    rho2 = np.maximum(np.einsum('mgnc,mgnc->mgn', d, d) - t0 ** 2, 0.0)
    q = np.sqrt(rho2 + a ** 2)
    h = half[None, None, :]
    S0 = np.arcsinh((h - t0) / q) + np.arcsinh((h + t0) / q)
    Rp = np.sqrt((h - t0) ** 2 + q ** 2)
    Rm = np.sqrt((h + t0) ** 2 + q ** 2)
    S1 = (Rp - Rm) + t0 * S0
    t = h[..., None] * _GI_X
    R = np.sqrt((t - t0[..., None]) ** 2 + q[..., None] ** 2)
    g = (np.exp(-1j * k * R) - 1.0) / R
    D0 = (g @ _GI_W) * h
    D1 = ((g * t) @ _GI_W) * h
    return (S0 + D0) / (4 * math.pi), (S1 + D1) / (4 * math.pi)


def assemble_rooftop(p1, p2, radius, sigma, k, omega):
    """Galerkin rooftop-basis impedance matrix for an open polyline wire (SI units).
    Segments 0..N-1 are consecutive. Unknown j sits on the node between segment j and j+1,
    so there are N-1 unknowns and zero current at both free ends.
    Returns (Z, asymmetry_before_symmetrisation)."""
    N = len(p1)
    dv = p2 - p1
    L = np.linalg.norm(dv, axis=1)
    u = dv / L[:, None]
    c = 0.5 * (p1 + p2)
    h = 0.5 * L
    a_pq = 0.5 * (radius[:, None] + radius[None, :])
    eps = EPS_0 * (k * C_0 / omega) ** 2

    tg = h[:, None] * _GO_X                                   # (N,G) offsets from centre
    pts = c[:, None, :] + tg[:, :, None] * u[:, None, :]
    w = h[:, None] * _GO_W
    wR = w * (tg + h[:, None]) / L[:, None]                   # rising profile 0 -> 1
    wF = w * (h[:, None] - tg) / L[:, None]                   # falling profile 1 -> 0

    M0, M1 = _inner_moments(pts, c, u, h, a_pq[:, None, :], k)
    hh = h[None, None, :]
    IR = (M1 + hh * M0) / L[None, None, :]                    # int phi_rise * G
    IF = (hh * M0 - M1) / L[None, None, :]                    # int phi_fall * G

    KRR = np.einsum('pg,pgq->pq', wR, IR)
    KRF = np.einsum('pg,pgq->pq', wR, IF)
    KFR = np.einsum('pg,pgq->pq', wF, IR)
    KFF = np.einsum('pg,pgq->pq', wF, IF)
    W = np.einsum('pg,pgq->pq', w, M0)
    UU = u @ u.T

    R_ = np.arange(N - 1)          # segment where basis j rises
    F_ = R_ + 1                    # segment where basis j falls
    ix = np.ix_
    vec = (UU[ix(R_, R_)] * KRR[ix(R_, R_)] + UU[ix(R_, F_)] * KRF[ix(R_, F_)]
           + UU[ix(F_, R_)] * KFR[ix(F_, R_)] + UU[ix(F_, F_)] * KFF[ix(F_, F_)])
    dR, dF = 1.0 / L[R_], -1.0 / L[F_]
    sca = (dR[:, None] * dR[None, :] * W[ix(R_, R_)] + dR[:, None] * dF[None, :] * W[ix(R_, F_)]
           + dF[:, None] * dR[None, :] * W[ix(F_, R_)] + dF[:, None] * dF[None, :] * W[ix(F_, F_)])
    Z = 1j * omega * MU_0 * vec + sca / (1j * omega * eps)

    asym = float(np.max(np.abs(Z - Z.T)) / np.max(np.abs(Z)))
    Z = 0.5 * (Z + Z.T)

    with np.errstate(divide='ignore'):
        delta = np.sqrt(2.0 / (omega * MU_0 * sigma))
        rp = np.where(sigma > 0, 1.0 / (2 * math.pi * radius * sigma * delta), 0.0)   # ohm/m
    diag = rp[R_] * L[R_] / 3.0 + rp[F_] * L[F_] / 3.0
    off = rp[F_[:-1]] * L[F_[:-1]] / 6.0                     # basis j and j+1 share segment j+1
    Z[np.diag_indices(N - 1)] += diag
    Z[np.arange(N - 2), np.arange(1, N - 1)] += off
    Z[np.arange(1, N - 1), np.arange(N - 2)] += off
    return Z, asym
