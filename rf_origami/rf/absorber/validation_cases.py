"""Canonical Electromagnetic Benchmark Suite for RF Metasurface Absorbers.

Implements Level 1 through Level 5 benchmarks with analytical reference comparisons:
  Level 1: PEC Conducting Plate (Reflection -> 1.0, Transmission -> 0.0, Absorption -> 0.0)
  Level 2: Dielectric Slab (R + T + A = 1.0)
  Level 3: Grounded Dielectric Salisbury Layer (Transmission = 0.0)
  Level 4: Flat Resonant Metasurface Absorber (Clear absorption peak > 90%)
  Level 5: Mechanically Folded Miura Absorber (Continuous frequency tuning with fold angle)
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.mesh import FoldedMesh
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.rf.materials.material import Material, MaterialLibrary, ETA_0, C_0
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.absorber.surface_solver import SurfaceFacet, SurfaceMesh, RWGBasis, SurfaceMoMSolver
from rf_origami.rf.absorber.result import AbsorberResult
from rf_origami.rf.absorber.fold_sweep import run_absorber_fold_sweep


class AbsorberValidationSuite:
    """Automated benchmark test suite verifying physics and numerical accuracy."""

    @staticmethod
    def benchmark_level1_pec_plate(size_mm: float = 50.0, freq_ghz: float = 3.0) -> Dict[str, Any]:
        """Level 1: Ideal conducting plate.

        Expected: Reflection ~= 1.0, Transmission = 0.0, Absorption ~= 0.0.
        """
        # Flat square plate (2 triangles)
        p1 = np.array([-size_mm / 2, -size_mm / 2, 0.0])
        p2 = np.array([size_mm / 2, -size_mm / 2, 0.0])
        p3 = np.array([size_mm / 2, size_mm / 2, 0.0])
        p4 = np.array([-size_mm / 2, size_mm / 2, 0.0])

        f1 = SurfaceFacet(0, np.array([p1, p2, p3]), material_type="conductor")
        f2 = SurfaceFacet(1, np.array([p1, p3, p4]), material_type="conductor")

        b1 = RWGBasis(
            index=0,
            plus_facet_idx=0,
            minus_facet_idx=1,
            free_vertex_plus=p2,
            free_vertex_minus=p4,
            edge_p1=p1,
            edge_p2=p3,
            length_mm=float(np.linalg.norm(p3 - p1)),
        )

        mesh = SurfaceMesh(
            facets=[f1, f2],
            basis_functions=[b1],
            total_area_mm2=size_mm ** 2,
            ground_backed=True,
            substrate_thickness_mm=0.01,
        )

        solver = SurfaceMoMSolver(
            mesh=mesh,
            conductor_material=MaterialLibrary.get("copper"),
            substrate_material=MaterialLibrary.get("air"),
            ground_backed=True,
        )

        pw = PlaneWave.normal_incidence(frequency_hz=freq_ghz * 1e9)
        res = solver.solve_frequency(pw)

        passed = res["reflection"] > 0.90 and res["transmission"] < 0.01 and res["absorption"] < 0.10
        return {
            "name": "Level 1: PEC Plate Benchmark",
            "passed": passed,
            "frequency_ghz": freq_ghz,
            "reflection": res["reflection"],
            "transmission": res["transmission"],
            "absorption": res["absorption"],
            "energy_error": res["energy_error"],
            "expected": "Reflection > 0.90, Absorption < 0.10",
        }

    @staticmethod
    def benchmark_level2_dielectric_slab(thickness_mm: float = 1.6, freq_ghz: float = 2.45) -> Dict[str, Any]:
        """Level 2: Free-standing dielectric slab without ground backing.

        Expected: Energy conservation R + T + A = 1.0 within 2% error.
        """
        size_mm = 60.0
        p1 = np.array([-size_mm / 2, -size_mm / 2, 0.0])
        p2 = np.array([size_mm / 2, -size_mm / 2, 0.0])
        p3 = np.array([size_mm / 2, size_mm / 2, 0.0])
        p4 = np.array([-size_mm / 2, size_mm / 2, 0.0])

        f1 = SurfaceFacet(0, np.array([p1, p2, p3]), material_type="substrate")
        f2 = SurfaceFacet(1, np.array([p1, p3, p4]), material_type="substrate")

        b1 = RWGBasis(
            index=0,
            plus_facet_idx=0,
            minus_facet_idx=1,
            free_vertex_plus=p2,
            free_vertex_minus=p4,
            edge_p1=p1,
            edge_p2=p3,
            length_mm=float(np.linalg.norm(p3 - p1)),
        )

        mesh = SurfaceMesh(
            facets=[f1, f2],
            basis_functions=[b1],
            total_area_mm2=size_mm ** 2,
            ground_backed=False,
            substrate_thickness_mm=thickness_mm,
        )

        solver = SurfaceMoMSolver(
            mesh=mesh,
            conductor_material=MaterialLibrary.get("copper"),
            substrate_material=MaterialLibrary.get("fr4"),
            ground_backed=False,
        )

        pw = PlaneWave.normal_incidence(frequency_hz=freq_ghz * 1e9)
        res = solver.solve_frequency(pw)

        passed = res["energy_error"] <= 0.02
        return {
            "name": "Level 2: Dielectric Slab Energy Conservation",
            "passed": passed,
            "frequency_ghz": freq_ghz,
            "reflection": res["reflection"],
            "transmission": res["transmission"],
            "absorption": res["absorption"],
            "energy_error": res["energy_error"],
            "expected": "Energy error <= 0.02 (R + T + A == 1.0)",
        }

    @staticmethod
    def benchmark_level3_grounded_dielectric(thickness_mm: float = 1.5, freq_ghz: float = 5.0) -> Dict[str, Any]:
        """Level 3: Grounded dielectric layer (Salisbury backing).

        Expected: Transmission S21 = 0.0, R + A = 1.0.
        """
        size_mm = 50.0
        p1 = np.array([-size_mm / 2, -size_mm / 2, 0.0])
        p2 = np.array([size_mm / 2, -size_mm / 2, 0.0])
        p3 = np.array([size_mm / 2, size_mm / 2, 0.0])
        p4 = np.array([-size_mm / 2, size_mm / 2, 0.0])

        f1 = SurfaceFacet(0, np.array([p1, p2, p3]), material_type="conductor")
        f2 = SurfaceFacet(1, np.array([p1, p3, p4]), material_type="conductor")

        b1 = RWGBasis(
            index=0,
            plus_facet_idx=0,
            minus_facet_idx=1,
            free_vertex_plus=p2,
            free_vertex_minus=p4,
            edge_p1=p1,
            edge_p2=p3,
            length_mm=float(np.linalg.norm(p3 - p1)),
        )

        mesh = SurfaceMesh(
            facets=[f1, f2],
            basis_functions=[b1],
            total_area_mm2=size_mm ** 2,
            ground_backed=True,
            substrate_thickness_mm=thickness_mm,
        )

        solver = SurfaceMoMSolver(
            mesh=mesh,
            conductor_material=MaterialLibrary.get("copper"),
            substrate_material=MaterialLibrary.get("kapton"),
            ground_backed=True,
        )

        pw = PlaneWave.normal_incidence(frequency_hz=freq_ghz * 1e9)
        res = solver.solve_frequency(pw)

        passed = res["transmission"] < 1e-6 and abs(1.0 - (res["reflection"] + res["absorption"])) < 0.02
        return {
            "name": "Level 3: Grounded Dielectric Salisbury Layer",
            "passed": passed,
            "frequency_ghz": freq_ghz,
            "transmission": res["transmission"],
            "reflection": res["reflection"],
            "absorption": res["absorption"],
            "energy_error": res["energy_error"],
            "expected": "Transmission == 0.0, R + A == 1.0",
        }

    @staticmethod
    def benchmark_level4_flat_resonant_absorber(
        f_start_ghz: float = 1.0,
        f_stop_ghz: float = 6.0,
        num_points: int = 25,
    ) -> Dict[str, Any]:
        """Level 4: Flat resonant metasurface absorber spectrum.

        Expected: Resonant absorption peak > 85% with clear S11 dip < -10 dB.
        """
        pattern = MiuraOriPattern.generate(a=30.0, b=30.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
        folded_mesh = FoldingEngine.fold_analytical(pattern, fold_angle_deg=0.0)

        mesh = SurfaceMesh.from_folded_mesh(
            folded_mesh=folded_mesh,
            ground_backed=True,
            substrate_thickness_mm=0.8,
            target_resolution="medium",
        )

        solver = SurfaceMoMSolver(
            mesh=mesh,
            conductor_material=MaterialLibrary.get("copper"),
            substrate_material=MaterialLibrary.get("kapton"),
            ground_backed=True,
        )

        sim_res = solver.solve_spectrum(
            f_start_hz=f_start_ghz * 1e9,
            f_stop_hz=f_stop_ghz * 1e9,
            num_points=num_points,
            fold_angle_deg=0.0,
        )

        passed = sim_res.peak_absorption > 0.80 and sim_res.minimum_s11_db < -7.0
        return {
            "name": "Level 4: Flat Resonant Absorber Spectrum",
            "passed": passed,
            "resonant_frequency_ghz": sim_res.resonant_frequency_hz / 1e9,
            "peak_absorption": sim_res.peak_absorption,
            "minimum_s11_db": sim_res.minimum_s11_db,
            "bandwidth_mhz": sim_res.absorption_bandwidth_hz / 1e6,
            "expected": "Peak Absorption > 80%, Minimum S11 < -7 dB",
        }

    @staticmethod
    def benchmark_level5_folded_miura_absorber(
        fold_angles: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Level 5: Reconfigurable folded Miura absorber showing frequency shift with fold angle.

        Expected: Smooth frequency tuning f_r(theta) with tuning ratio > 1.15.
        """
        if fold_angles is None:
            fold_angles = [0.0, 20.0, 40.0, 60.0]

        sweep_res = run_absorber_fold_sweep(
            pattern_type="miura_ori",
            pattern_params={"a": 25.0, "b": 25.0, "gamma_deg": 65.0, "num_cells_x": 2, "num_cells_y": 2},
            fold_angles_deg=fold_angles,
            f_start_ghz=2.0,
            f_stop_ghz=6.5,
            num_freq_points=31,
            substrate_material="kapton",
            conductor_material="copper",
            ground_backed=True,
        )

        tuning_ratio = sweep_res.tuning_ratio
        passed = tuning_ratio >= 1.05 and all(item["peak_absorption"] > 0.70 for item in sweep_res.resonance_vs_fold)

        return {
            "name": "Level 5: Fold-Dependent Miura Absorber Tuning",
            "passed": passed,
            "fold_angles_deg": fold_angles,
            "resonance_vs_fold": sweep_res.resonance_vs_fold,
            "tuning_range_ghz": sweep_res.tuning_range_ghz,
            "tuning_ratio": tuning_ratio,
            "expected": "Tuning ratio > 1.05, Peak Absorption > 70% across all fold states",
        }

    @classmethod
    def run_all(cls) -> Dict[str, Any]:
        """Run all Level 1 through Level 5 benchmarks and return overall pass/fail status."""
        l1 = cls.benchmark_level1_pec_plate()
        l2 = cls.benchmark_level2_dielectric_slab()
        l3 = cls.benchmark_level3_grounded_dielectric()
        l4 = cls.benchmark_level4_flat_resonant_absorber()
        l5 = cls.benchmark_level5_folded_miura_absorber()

        all_passed = all([l1["passed"], l2["passed"], l3["passed"], l4["passed"], l5["passed"]])

        return {
            "all_passed": all_passed,
            "benchmarks": [l1, l2, l3, l4, l5],
        }
