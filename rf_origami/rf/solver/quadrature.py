"""Source-line Green-function integration for the radius-regularized wire kernel.

This is not triangle/RWG singular quadrature. The static part of the existing
wire kernel is integrated analytically; only its smooth dynamic remainder is
sampled. Lengths and coordinates are in metres.
"""
import math
import numpy as np

_POINTS, _WEIGHTS = np.polynomial.legendre.leggauss(32)


def wire_potential(field_point, center, length, direction, radius, k):
    """Return the average exp(-jkR)/(4 pi R) over one straight segment."""
    displacement = np.asarray(field_point) - np.asarray(center)
    projection = float(np.dot(displacement, direction))
    perpendicular = displacement - projection * np.asarray(direction)
    rho = math.sqrt(float(np.dot(perpendicular, perpendicular)) + radius**2)
    half = length / 2
    static = math.asinh((half - projection) / rho) + math.asinh((half + projection) / rho)
    # Split at the nearest axial projection. Subdivide nearby intervals on a
    # geometric scale set by rho so even very thin wires resolve the remainder.
    nearest = min(half, max(-half, projection))
    cuts = {-half, half, nearest}
    offset = rho
    while offset < length:
        for value in (nearest - offset, nearest + offset):
            if -half < value < half:
                cuts.add(value)
        offset *= 2
    cuts = sorted(cuts)
    remainder = 0j
    for start, stop in zip(cuts, cuts[1:]):
        midpoint, scale = (start + stop) / 2, (stop - start) / 2
        distances = np.sqrt((midpoint + scale * _POINTS - projection)**2 + rho**2)
        remainder += scale * np.dot(_WEIGHTS, np.expm1(-1j * k * distances) / distances)
    return (static + remainder) / (4 * math.pi * length)
