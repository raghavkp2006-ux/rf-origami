"""Electromagnetic Absorption and Scattering Metrics for Reconfigurable Metasurfaces.

Implements rigorous Poynting energy balance and S-parameter relationships:
  Reflection:   R(f) = |S11(f)|^2
  Transmission: T(f) = |S21(f)|^2
  Absorption:   A(f) = 1 - R(f) - T(f)
  Conservation: R + T + A == 1.0 within numerical tolerance.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np


def calculate_reflection(s11: Union[complex, float, Sequence[Union[complex, float]]]) -> np.ndarray:
    """Compute power reflection coefficient R = |S11|^2.

    Args:
        s11: Complex S11 reflection parameter or magnitude.

    Returns:
        np.ndarray of reflection values in range [0.0, 1.0].
    """
    arr = np.asarray(s11)
    mag_sq = np.abs(arr) ** 2
    return np.clip(mag_sq, 0.0, 1.0)


def calculate_transmission(s21: Union[complex, float, Sequence[Union[complex, float]]]) -> np.ndarray:
    """Compute power transmission coefficient T = |S21|^2.

    Args:
        s21: Complex S21 transmission parameter or magnitude.

    Returns:
        np.ndarray of transmission values in range [0.0, 1.0].
    """
    arr = np.asarray(s21)
    mag_sq = np.abs(arr) ** 2
    return np.clip(mag_sq, 0.0, 1.0)


def calculate_absorption(
    reflection: Union[float, Sequence[float]],
    transmission: Optional[Union[float, Sequence[float]]] = None,
) -> np.ndarray:
    """Compute electromagnetic power absorption A = 1 - R - T.

    For ground-backed absorbers where S21 = 0, transmission is assumed 0.0.

    Args:
        reflection: Power reflection coefficient R in [0, 1].
        transmission: Optional power transmission coefficient T in [0, 1].

    Returns:
        np.ndarray of absorption values in range [0.0, 1.0].
    """
    r_arr = np.asarray(reflection, dtype=np.float64)
    if transmission is None:
        t_arr = np.zeros_like(r_arr)
    else:
        t_arr = np.asarray(transmission, dtype=np.float64)

    a_arr = 1.0 - r_arr - t_arr
    return np.clip(a_arr, 0.0, 1.0)


def check_energy_conservation(
    reflection: Union[float, Sequence[float]],
    transmission: Union[float, Sequence[float]],
    absorption: Union[float, Sequence[float]],
    tolerance: float = 0.02,
) -> Tuple[bool, float, np.ndarray]:
    """Verify energy conservation R + T + A = 1 across the simulated frequency spectrum.

    Args:
        reflection: Power reflection array.
        transmission: Power transmission array.
        absorption: Power absorption array.
        tolerance: Maximum allowed absolute error (default 2%).

    Returns:
        (is_conserved, max_error, error_array)
    """
    r = np.asarray(reflection, dtype=np.float64)
    t = np.asarray(transmission, dtype=np.float64)
    a = np.asarray(absorption, dtype=np.float64)

    total = r + t + a
    errors = np.abs(1.0 - total)
    max_error = float(np.max(errors)) if len(errors) > 0 else 0.0
    is_conserved = max_error <= tolerance
    return is_conserved, max_error, errors


def s11_to_db(s11: Union[complex, float, Sequence[Union[complex, float]]]) -> np.ndarray:
    """Convert S11 (complex or linear magnitude) to logarithmic decibels (dB).

    S11_dB = 20 * log10(|S11|) = 10 * log10(R)
    """
    arr = np.asarray(s11)
    mag = np.abs(arr)
    mag_safe = np.maximum(mag, 1e-12)
    return 20.0 * np.log10(mag_safe)


def db_to_linear(s_db: Union[float, Sequence[float]]) -> np.ndarray:
    """Convert S-parameter from dB back to linear magnitude."""
    arr = np.asarray(s_db, dtype=np.float64)
    return 10.0 ** (arr / 20.0)


def extract_resonance(
    frequencies_hz: Sequence[float],
    absorption: Sequence[float],
    s11_db: Optional[Sequence[float]] = None,
) -> Tuple[float, float, float]:
    """Find the resonant frequency, peak absorption value, and minimum S11 in dB.

    Args:
        frequencies_hz: Array of simulated frequency points.
        absorption: Power absorption spectrum array [0.0, 1.0].
        s11_db: Optional S11 in dB.

    Returns:
        (f_resonant_hz, peak_absorption, min_s11_db)
    """
    freqs = np.asarray(frequencies_hz, dtype=np.float64)
    abs_arr = np.asarray(absorption, dtype=np.float64)

    if len(freqs) == 0 or len(abs_arr) == 0:
        return 0.0, 0.0, 0.0

    peak_idx = int(np.argmax(abs_arr))
    f_res = float(freqs[peak_idx])
    peak_abs = float(abs_arr[peak_idx])

    if s11_db is not None and len(s11_db) == len(freqs):
        s11_arr = np.asarray(s11_db, dtype=np.float64)
        min_s11 = float(np.min(s11_arr))
    else:
        # Approximate S11 from absorption: R = 1 - A, S11 = sqrt(R)
        r_at_peak = max(1e-12, 1.0 - peak_abs)
        min_s11 = 10.0 * math.log10(r_at_peak)

    return f_res, peak_abs, min_s11


def calculate_absorption_bandwidth(
    frequencies_hz: Sequence[float],
    absorption: Sequence[float],
    threshold: float = 0.9,
) -> Tuple[float, float, float, float]:
    """Calculate the absolute and fractional absorption bandwidth above a threshold (e.g. 90% or 50%).

    Args:
        frequencies_hz: Frequency spectrum.
        absorption: Power absorption array.
        threshold: Required absorption level (default 0.9 for >90% absorption).

    Returns:
        (bandwidth_hz, fractional_bandwidth, f_low_hz, f_high_hz)
    """
    freqs = np.asarray(frequencies_hz, dtype=np.float64)
    abs_arr = np.asarray(absorption, dtype=np.float64)

    if len(freqs) < 2:
        return 0.0, 0.0, 0.0, 0.0

    peak_idx = int(np.argmax(abs_arr))
    f_res = float(freqs[peak_idx])
    peak_val = float(abs_arr[peak_idx])

    if peak_val < threshold:
        # If peak does not reach threshold, return 0 bandwidth
        return 0.0, 0.0, f_res, f_res

    # Find contiguous region around peak where A >= threshold
    left = peak_idx
    while left > 0 and abs_arr[left - 1] >= threshold:
        left -= 1

    right = peak_idx
    while right < len(abs_arr) - 1 and abs_arr[right + 1] >= threshold:
        right += 1

    # Linear interpolation for precise cutoff frequencies
    if left > 0 and abs_arr[left] != abs_arr[left - 1]:
        f_low = freqs[left - 1] + (threshold - abs_arr[left - 1]) * (freqs[left] - freqs[left - 1]) / (abs_arr[left] - abs_arr[left - 1])
    else:
        f_low = freqs[left]

    if right < len(abs_arr) - 1 and abs_arr[right + 1] != abs_arr[right]:
        f_high = freqs[right] + (threshold - abs_arr[right]) * (freqs[right + 1] - freqs[right]) / (abs_arr[right + 1] - abs_arr[right])
    else:
        f_high = freqs[right]

    bw_hz = max(0.0, float(f_high - f_low))
    fbw = bw_hz / f_res if f_res > 0.0 else 0.0

    return float(bw_hz), float(fbw), float(f_low), float(f_high)
