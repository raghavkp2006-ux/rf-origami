"""Antenna Performance Metrics Extraction.

Extracts resonant frequency (f0), input impedance (Rin + j Xin),
voltage standing wave ratio, and impedance bandwidth (S11 <= -10 dB).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Sequence
import numpy as np


def _validated_curve(frequencies_hz, s11_db_values):
    f = np.asarray(frequencies_hz, dtype=float)
    s = np.asarray(s11_db_values, dtype=float)
    if f.ndim != 1 or s.ndim != 1 or f.shape != s.shape:
        raise ValueError("Frequency and S11 arrays must be matching one-dimensional arrays.")
    if not np.all(np.isfinite(f)) or not np.all(np.isfinite(s)):
        raise ValueError("Frequency and S11 samples must be finite.")
    if np.any(f <= 0) or np.any(np.diff(f) <= 0):
        raise ValueError("Frequencies must be positive and strictly increasing.")
    return f, s


def extract_resonant_frequency(
    frequencies_hz: Sequence[float],
    s11_db_values: Sequence[float],
    zin_values: Optional[Sequence[complex]] = None,
) -> Dict[str, Any]:
    """Find resonance frequency where S11 is minimized and/or reactance crosses zero.

    Args:
        frequencies_hz: Array of frequency points in Hertz.
        s11_db_values: S11 values in decibels.
        zin_values: Optional array of complex input impedances.

    Returns:
        Dictionary containing resonant frequency f0 (Hz & GHz), min S11, and index.
    """
    f_arr, s11_arr = _validated_curve(frequencies_hz, s11_db_values)

    if len(f_arr) == 0:
        return {"resonant_frequency_hz": 0.0, "resonant_frequency_ghz": 0.0, "min_s11_db": 0.0}

    # Primary search: global minimum of S11
    min_idx = int(np.argmin(s11_arr))
    f0_s11 = float(f_arr[min_idx])
    min_s11 = float(s11_arr[min_idx])
    interpolated = False
    at_boundary = min_idx in (0, len(f_arr) - 1)
    if not at_boundary:
        # Fit in local, scaled coordinates to avoid conditioning problems in Hz.
        scale = max(f_arr[min_idx] - f_arr[min_idx - 1], f_arr[min_idx + 1] - f_arr[min_idx])
        x = (f_arr[min_idx - 1:min_idx + 2] - f_arr[min_idx]) / scale
        a, b, c = np.polyfit(x, s11_arr[min_idx - 1:min_idx + 2], 2)
        vertex = -b / (2 * a) if a > 0 else float("inf")
        if x[0] <= vertex <= x[-1]:
            f0_s11 = float(f_arr[min_idx] + vertex * scale)
            min_s11 = float(a * vertex**2 + b * vertex + c)
            interpolated = True

    # Secondary: check for zero reactance crossing if Zin provided
    f0_zero_x = None
    if zin_values is not None:
        zin_arr = np.asarray(zin_values, dtype=np.complex128)
        if zin_arr.shape != f_arr.shape or not np.all(np.isfinite(zin_arr)):
            raise ValueError("Impedance samples must be finite and match the frequency array.")
        x_vals = zin_arr.imag
        # Find zero crossings of X(f)
        crossings = []
        for i in range(len(x_vals) - 1):
            if x_vals[i] * x_vals[i + 1] <= 0.0:
                # Linear interpolation for zero crossing
                denom = x_vals[i + 1] - x_vals[i]
                if abs(denom) > 1e-12:
                    t = -x_vals[i] / denom
                    f_cross = f_arr[i] + t * (f_arr[i + 1] - f_arr[i])
                    crossings.append(float(f_cross))

        if crossings:
            # Pick crossing closest to S11 dip
            dists = [abs(c - f0_s11) for c in crossings]
            f0_zero_x = crossings[int(np.argmin(dists))]

    return {
        "resonant_frequency_hz": f0_s11,
        "resonant_frequency_ghz": f0_s11 * 1e-9,
        "min_s11_db": min_s11,
        "min_index": min_idx,
        "interpolated": interpolated,
        "at_sweep_boundary": at_boundary,
        "frequency_step_percent": float(np.max(np.diff(f_arr)) / f0_s11 * 100) if len(f_arr) > 1 else None,
        "resolution_better_than_one_percent": bool(len(f_arr) > 1 and not at_boundary and np.max(np.diff(f_arr)) / f0_s11 < 0.01),
        "zero_reactance_f0_ghz": f0_zero_x * 1e-9 if f0_zero_x is not None else None,
    }


def extract_impedance_bandwidth(
    frequencies_hz: Sequence[float],
    s11_db_values: Sequence[float],
    threshold_db: float = -10.0,
) -> Dict[str, Any]:
    """Calculate operational frequency bandwidth where S11 <= threshold_db.

    Args:
        frequencies_hz: Frequency array in Hz.
        s11_db_values: S11 array in dB.
        threshold_db: Target threshold (default -10 dB, corresponding to VSWR <= 2.0).

    Returns:
        Dictionary with f_low, f_high, bandwidth_mhz, and bandwidth_percent.
    """
    f_arr, s11_arr = _validated_curve(frequencies_hz, s11_db_values)
    if not np.isfinite(threshold_db):
        raise ValueError("Bandwidth threshold must be finite.")

    in_band = np.where(s11_arr <= threshold_db)[0]

    if len(in_band) == 0:
        return {
            "has_bandwidth": False,
            "threshold_db": threshold_db,
            "bandwidth_mhz": 0.0,
            "bandwidth_percent": 0.0,
            "f_low_ghz": 0.0,
            "f_high_ghz": 0.0,
        }

    # Select the contiguous band containing the deepest S11 minimum. Do not
    # bridge unmatched gaps between separate resonances.
    peak = int(np.argmin(s11_arr))
    left = right = peak
    while left > 0 and s11_arr[left - 1] <= threshold_db:
        left -= 1
    while right < len(f_arr) - 1 and s11_arr[right + 1] <= threshold_db:
        right += 1

    def crossing(i, j):
        t = (threshold_db - s11_arr[i]) / (s11_arr[j] - s11_arr[i])
        return float(f_arr[i] + t * (f_arr[j] - f_arr[i]))

    f_low = crossing(left - 1, left) if left > 0 else float(f_arr[left])
    f_high = crossing(right, right + 1) if right < len(f_arr) - 1 else float(f_arr[right])
    bw_hz = max(0.0, f_high - f_low)
    f_mid = 0.5 * (f_low + f_high)

    bw_pct = (bw_hz / f_mid) * 100.0 if f_mid > 0 else 0.0

    return {
        "has_bandwidth": True,
        "truncated": left == 0 or right == len(f_arr) - 1,
        "threshold_db": threshold_db,
        "bandwidth_mhz": bw_hz * 1e-6,
        "bandwidth_percent": bw_pct,
        "f_low_ghz": f_low * 1e-9,
        "f_high_ghz": f_high * 1e-9,
    }
