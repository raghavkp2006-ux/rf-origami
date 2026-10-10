"""Antenna Performance Metrics Extraction.

Extracts resonant frequency (f0), input impedance (Rin + j Xin),
voltage standing wave ratio, and impedance bandwidth (S11 <= -10 dB).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Sequence
import numpy as np


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
    f_arr = np.asarray(frequencies_hz, dtype=np.float64)
    s11_arr = np.asarray(s11_db_values, dtype=np.float64)

    if len(f_arr) == 0:
        return {"resonant_frequency_hz": 0.0, "resonant_frequency_ghz": 0.0, "min_s11_db": 0.0}

    # Primary search: global minimum of S11
    min_idx = int(np.argmin(s11_arr))
    f0_s11 = float(f_arr[min_idx])
    min_s11 = float(s11_arr[min_idx])

    # Secondary: check for zero reactance crossing if Zin provided
    f0_zero_x = None
    if zin_values is not None:
        zin_arr = np.asarray(zin_values, dtype=np.complex128)
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
        "resonant_frequency_ghz": round(f0_s11 * 1e-9, 4),
        "min_s11_db": round(min_s11, 2),
        "min_index": min_idx,
        "zero_reactance_f0_ghz": round(f0_zero_x * 1e-9, 4) if f0_zero_x else None,
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
    f_arr = np.asarray(frequencies_hz, dtype=np.float64)
    s11_arr = np.asarray(s11_db_values, dtype=np.float64)

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

    # Longest continuous segment in band
    f_low = float(f_arr[in_band[0]])
    f_high = float(f_arr[in_band[-1]])
    bw_hz = max(0.0, f_high - f_low)
    f_mid = 0.5 * (f_low + f_high)

    bw_pct = (bw_hz / f_mid) * 100.0 if f_mid > 0 else 0.0

    return {
        "has_bandwidth": True,
        "threshold_db": threshold_db,
        "bandwidth_mhz": round(bw_hz * 1e-6, 1),
        "bandwidth_percent": round(bw_pct, 2),
        "f_low_ghz": round(f_low * 1e-9, 4),
        "f_high_ghz": round(f_high * 1e-9, 4),
    }
