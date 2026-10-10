"""Simulation vs. Experimental Measurement Comparison and Error Analytics.

Calculates resonant frequency error percentage, minimum reflection discrepancy,
bandwidth differences, and spectral curve Root-Mean-Square Error (RMSE).
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rf_origami.rf.absorber.metrics import extract_resonance, calculate_absorption_bandwidth


class ExperimentalComparator:
    """Compares simulated electromagnetic predictions against physical measurement data."""

    @classmethod
    def compare(
        cls,
        sim_frequencies_hz: List[float],
        sim_s11_db: List[float],
        meas_frequencies_hz: List[float],
        meas_s11_db: List[float],
        sim_absorption: Optional[List[float]] = None,
        meas_absorption: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive statistical and spectral comparison."""
        f_sim = np.asarray(sim_frequencies_hz, dtype=np.float64)
        s_sim = np.asarray(sim_s11_db, dtype=np.float64)

        f_meas = np.asarray(meas_frequencies_hz, dtype=np.float64)
        s_meas = np.asarray(meas_s11_db, dtype=np.float64)

        if sim_absorption is None:
            r_sim = 10.0 ** (s_sim / 10.0)
            a_sim = np.clip(1.0 - r_sim, 0.0, 1.0)
        else:
            a_sim = np.asarray(sim_absorption, dtype=np.float64)

        if meas_absorption is None:
            r_meas = 10.0 ** (s_meas / 10.0)
            a_meas = np.clip(1.0 - r_meas, 0.0, 1.0)
        else:
            a_meas = np.asarray(meas_absorption, dtype=np.float64)

        # 1. Resonances
        f_res_sim, peak_abs_sim, min_s11_sim = extract_resonance(f_sim, a_sim, s_sim)
        f_res_meas, peak_abs_meas, min_s11_meas = extract_resonance(f_meas, a_meas, s_meas)

        freq_error_hz = abs(f_res_sim - f_res_meas)
        freq_error_percent = (freq_error_hz / f_res_meas * 100.0) if f_res_meas > 0 else 0.0

        peak_abs_diff = abs(peak_abs_sim - peak_abs_meas)
        min_s11_diff_db = abs(min_s11_sim - min_s11_meas)

        # 2. Bandwidths
        bw_sim_hz, _, _, _ = calculate_absorption_bandwidth(f_sim, a_sim, threshold=0.9)
        bw_meas_hz, _, _, _ = calculate_absorption_bandwidth(f_meas, a_meas, threshold=0.9)
        bw_diff_mhz = abs(bw_sim_hz - bw_meas_hz) / 1e6

        # 3. Spectral Curve Interpolation and RMSE
        # Interpolate measured curve onto simulated frequency grid
        f_common_min = max(float(np.min(f_sim)), float(np.min(f_meas)))
        f_common_max = min(float(np.max(f_sim)), float(np.max(f_meas)))

        mask_sim = (f_sim >= f_common_min) & (f_sim <= f_common_max)
        f_eval = f_sim[mask_sim]

        if len(f_eval) >= 2:
            s_meas_interp = np.interp(f_eval, f_meas, s_meas)
            s_sim_eval = s_sim[mask_sim]
            rmse_s11_db = float(np.sqrt(np.mean((s_sim_eval - s_meas_interp) ** 2)))

            a_meas_interp = np.interp(f_eval, f_meas, a_meas)
            a_sim_eval = a_sim[mask_sim]
            rmse_absorption = float(np.sqrt(np.mean((a_sim_eval - a_meas_interp) ** 2)))
        else:
            rmse_s11_db = 0.0
            rmse_absorption = 0.0

        correlation = float(np.corrcoef(s_sim[mask_sim], s_meas_interp)[0, 1]) if len(f_eval) >= 3 else 1.0

        return {
            "predicted_resonance_ghz": float(f_res_sim / 1e9),
            "measured_resonance_ghz": float(f_res_meas / 1e9),
            "frequency_error_percent": float(freq_error_percent),
            "frequency_error_mhz": float(freq_error_hz / 1e6),
            "predicted_peak_absorption": float(peak_abs_sim),
            "measured_peak_absorption": float(peak_abs_meas),
            "peak_absorption_difference": float(peak_abs_diff),
            "predicted_min_s11_db": float(min_s11_sim),
            "measured_min_s11_db": float(min_s11_meas),
            "min_s11_difference_db": float(min_s11_diff_db),
            "predicted_bandwidth_mhz": float(bw_sim_hz / 1e6),
            "measured_bandwidth_mhz": float(bw_meas_hz / 1e6),
            "bandwidth_difference_mhz": float(bw_diff_mhz),
            "s11_rmse_db": float(rmse_s11_db),
            "absorption_rmse": float(rmse_absorption),
            "pearson_correlation": float(correlation),
            "agreement_grade": "EXCELLENT" if freq_error_percent < 3.0 and rmse_s11_db < 2.5 else ("GOOD" if freq_error_percent < 7.0 else "POOR"),
        }
