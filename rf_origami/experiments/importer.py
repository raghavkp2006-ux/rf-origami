"""Laboratory Measurement Data Importer for RF Metasurfaces and Antennas.

Parses experimental vector network analyzer (VNA) and arch reflection data:
  - CSV files (frequency_hz, s11_db / reflection, phase_deg)
  - Touchstone 1-Port (.s1p) and 2-Port (.s2p) files (RI, MA, DB formats)
"""

from __future__ import annotations
import csv
import io
import math
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class MeasurementImporter:
    """Imports and validates experimental electromagnetic measurement data."""

    @classmethod
    def import_csv(
        cls,
        csv_text_or_path: str,
    ) -> Dict[str, Any]:
        """Parse CSV measurement data containing frequency and reflection.

        Supports headers like: 'frequency_hz', 'freq_ghz', 's11_db', 'reflection', 'absorption'.
        """
        if os.path.isfile(csv_text_or_path):
            with open(csv_text_or_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = csv_text_or_path

        reader = csv.DictReader(io.StringIO(content.strip()))
        freqs_hz: List[float] = []
        s11_db: List[float] = []
        absorption: List[float] = []

        for row in reader:
            row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k}

            # Frequency detection
            if "frequency_hz" in row_clean:
                f = float(row_clean["frequency_hz"])
            elif "freq_hz" in row_clean:
                f = float(row_clean["freq_hz"])
            elif "frequency_ghz" in row_clean:
                f = float(row_clean["frequency_ghz"]) * 1e9
            elif "freq_ghz" in row_clean:
                f = float(row_clean["freq_ghz"]) * 1e9
            elif "freq" in row_clean:
                f_val = float(row_clean["freq"])
                f = f_val * 1e9 if f_val < 1000.0 else f_val
            else:
                continue

            # S11 / Reflection detection
            if "s11_db" in row_clean:
                db = float(row_clean["s11_db"])
            elif "reflection_db" in row_clean:
                db = float(row_clean["reflection_db"])
            elif "reflection" in row_clean:
                r_val = max(1e-9, min(1.0, float(row_clean["reflection"])))
                db = 10.0 * math.log10(r_val)
            else:
                db = 0.0

            # Absorption detection
            if "absorption" in row_clean:
                a_val = float(row_clean["absorption"])
            else:
                r_lin = 10.0 ** (db / 10.0)
                a_val = max(0.0, min(1.0, 1.0 - r_lin))

            freqs_hz.append(f)
            s11_db.append(db)
            absorption.append(a_val)

        return {
            "frequencies_hz": freqs_hz,
            "frequencies_ghz": [f / 1e9 for f in freqs_hz],
            "s11_db": s11_db,
            "absorption": absorption,
            "num_points": len(freqs_hz),
        }

    @classmethod
    def import_touchstone_s1p(cls, s1p_text_or_path: str) -> Dict[str, Any]:
        """Parse Touchstone 1-Port (.s1p) file format."""
        if os.path.isfile(s1p_text_or_path):
            with open(s1p_text_or_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = s1p_text_or_path.strip().split("\n")

        freq_multiplier = 1e9  # Default GHz
        format_type = "DB"     # DB, MA, RI

        freqs_hz = []
        s11_db = []
        absorption = []

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("!"):
                continue

            if line_str.startswith("#"):
                tokens = line_str.upper().split()
                if "HZ" in tokens:
                    freq_multiplier = 1.0
                elif "KHZ" in tokens:
                    freq_multiplier = 1e3
                elif "MHZ" in tokens:
                    freq_multiplier = 1e6
                elif "GHZ" in tokens:
                    freq_multiplier = 1e9

                if "MA" in tokens:
                    format_type = "MA"
                elif "RI" in tokens:
                    format_type = "RI"
                elif "DB" in tokens:
                    format_type = "DB"
                continue

            parts = line_str.split()
            if len(parts) >= 2:
                try:
                    f = float(parts[0]) * freq_multiplier
                    v1 = float(parts[1])
                    v2 = float(parts[2]) if len(parts) > 2 else 0.0

                    if format_type == "DB":
                        db = v1
                    elif format_type == "MA":
                        mag = max(1e-9, v1)
                        db = 20.0 * math.log10(mag)
                    elif format_type == "RI":
                        cplx = complex(v1, v2)
                        mag = max(1e-9, abs(cplx))
                        db = 20.0 * math.log10(mag)
                    else:
                        db = v1

                    r_lin = 10.0 ** (db / 10.0)
                    a_val = max(0.0, min(1.0, 1.0 - r_lin))

                    freqs_hz.append(f)
                    s11_db.append(db)
                    absorption.append(a_val)
                except ValueError:
                    continue

        return {
            "frequencies_hz": freqs_hz,
            "frequencies_ghz": [f / 1e9 for f in freqs_hz],
            "s11_db": s11_db,
            "absorption": absorption,
            "num_points": len(freqs_hz),
        }
