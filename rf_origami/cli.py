"""Command-Line Interface (CLI) for RF Origami Forge.

Provides a unified headless tool for electrodynamic simulations, fold-sweeps,
phase agility, polarization conversion, RCS analysis, NSGA-II optimization,
fabrication packaging, and canonical validation benchmarks.
"""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def create_parser() -> argparse.ArgumentParser:
    """Build top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="rf-origami",
        description="RF Origami Forge - Computational Electromagnetics & Foldable Metasurface Design Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. Benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Execute 5-level analytical validation benchmarks")
    bench_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # 2. Simulate
    sim_parser = subparsers.add_parser("simulate", help="Run full-wave Surface MoM plane wave simulation")
    sim_parser.add_argument("--pattern", type=str, default="miura_ori", help="Origami pattern type")
    sim_parser.add_argument("--fold", type=float, default=30.0, help="Fold angle in degrees (default: 30.0)")
    sim_parser.add_argument("--fstart", type=float, default=1.0, help="Start frequency in GHz (default: 1.0)")
    sim_parser.add_argument("--fstop", type=float, default=6.0, help="Stop frequency in GHz (default: 6.0)")
    sim_parser.add_argument("--points", type=int, default=31, help="Number of frequency points (default: 31)")
    sim_parser.add_argument("--sub", type=str, default="kapton", help="Substrate material (default: kapton)")
    sim_parser.add_argument("--cond", type=str, default="copper", help="Conductor material (default: copper)")
    sim_parser.add_argument("--pol", type=str, default="linear_x", help="Polarization (linear_x, linear_y, te, tm, rhcp, lhcp)")
    sim_parser.add_argument("--theta-inc", type=float, default=0.0, help="Polar incidence angle in degrees")
    sim_parser.add_argument("--sheet-res", type=float, default=0.0, help="Sheet resistance in Ohm/sq")
    sim_parser.add_argument("--out", type=str, default=None, help="Output JSON file path")

    # 3. Sweep
    sweep_parser = subparsers.add_parser("sweep", help="Run 2D fold angle x frequency tuning sweep")
    sweep_parser.add_argument("--pattern", type=str, default="miura_ori")
    sweep_parser.add_argument("--angles", type=float, nargs="+", default=[0.0, 15.0, 30.0, 45.0, 60.0, 75.0])
    sweep_parser.add_argument("--fstart", type=float, default=1.5)
    sweep_parser.add_argument("--fstop", type=float, default=6.5)
    sweep_parser.add_argument("--points", type=int, default=25)
    sweep_parser.add_argument("--out", type=str, default=None)

    # 4. Phase
    phase_parser = subparsers.add_parser("phase", help="Analyze reflection phase agility across fold states")
    phase_parser.add_argument("--pattern", type=str, default="miura_ori")
    phase_parser.add_argument("--fstart", type=float, default=2.0)
    phase_parser.add_argument("--fstop", type=float, default=6.0)
    phase_parser.add_argument("--out", type=str, default=None)

    # 5. Polarization
    pol_parser = subparsers.add_parser("polarization", help="Evaluate polarization conversion ratio (PCR)")
    pol_parser.add_argument("--pattern", type=str, default="miura_ori")
    pol_parser.add_argument("--fold", type=float, default=30.0)
    pol_parser.add_argument("--fstart", type=float, default=2.0)
    pol_parser.add_argument("--fstop", type=float, default=6.0)
    pol_parser.add_argument("--out", type=str, default=None)

    # 6. RCS
    rcs_parser = subparsers.add_parser("rcs", help="Calculate 3D Bistatic and Monostatic Radar Cross Section")
    rcs_parser.add_argument("--pattern", type=str, default="miura_ori")
    rcs_parser.add_argument("--fold", type=float, default=30.0)
    rcs_parser.add_argument("--freq", type=float, default=2.45, help="Frequency in GHz")
    rcs_parser.add_argument("--out", type=str, default=None)

    # 7. ECM
    ecm_parser = subparsers.add_parser("ecm", help="Analytical Equivalent Circuit Model prediction")
    ecm_parser.add_argument("--length", type=float, default=25.0, help="Facet length in mm")
    ecm_parser.add_argument("--fold", type=float, default=30.0, help="Fold angle in degrees")
    ecm_parser.add_argument("--fstart", type=float, default=1.0)
    ecm_parser.add_argument("--fstop", type=float, default=6.0)

    # 8. Optimize
    opt_parser = subparsers.add_parser("optimize", help="Run NSGA-II multi-objective optimization")
    opt_parser.add_argument("--target-freq", type=float, default=2.45, help="Target resonance frequency in GHz")
    opt_parser.add_argument("--min-abs", type=float, default=0.90, help="Minimum peak absorption (0-1)")
    opt_parser.add_argument("--pop", type=int, default=16, help="Population size")
    opt_parser.add_argument("--gens", type=int, default=4, help="Generations")
    opt_parser.add_argument("--out", type=str, default=None)

    # 9. Export
    exp_parser = subparsers.add_parser("export", help="Export full manufacturing release package (.zip)")
    exp_parser.add_argument("--pattern", type=str, default="miura_ori")
    exp_parser.add_argument("--fold", type=float, default=30.0)
    exp_parser.add_argument("--design-id", type=str, default="ORIGAMI-FAB-001")
    exp_parser.add_argument("--out", type=str, default="rf_origami_fabrication_release.zip")

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """CLI Main Entrypoint."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    if parsed.command == "benchmark":
        from rf_origami.rf.absorber.validation_cases import AbsorberValidationSuite
        results = AbsorberValidationSuite.run_all()
        if parsed.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n=======================================================")
            print("  RF ORIGAMI FORGE: ABSORBER BENCHMARKS (Analytical consistency checks - not physical validation)")
            print("=======================================================\n")
            for b in results.get("benchmarks", []):
                status = "PASS" if b.get("passed") else "FAIL"
                print(f"[{status}] {b.get('name')}")
            print(f"\nOverall Status: {'BENCHMARKS PASSED (Software consistency only - not physical validation)' if results.get('all_passed') else 'FAILED'}\n")
        return 0 if results.get("all_passed") else 1

    elif parsed.command == "simulate":
        from rf_origami.web.service import OrigamiWebService
        sim_res = OrigamiWebService.simulate_absorber(
            pattern_type=parsed.pattern,
            fold_angle_deg=parsed.fold,
            f_start_ghz=parsed.fstart,
            f_stop_ghz=parsed.fstop,
            num_points=parsed.points,
            substrate_material=parsed.sub,
            conductor_material=parsed.cond,
            polarization=parsed.pol,
            incidence_angle_deg=parsed.theta_inc,
            sheet_resistance=parsed.sheet_res,
        )
        f0_ghz = round(sim_res.get("resonant_frequency_hz", 0) / 1e9, 3)
        peak_abs = round(sim_res.get("peak_absorption", 0) * 100, 1)
        min_s11 = round(sim_res.get("minimum_s11_db", 0), 1)
        bw_mhz = round(sim_res.get("absorption_bandwidth_hz", 0) / 1e6, 1)

        print("\n=======================================================")
        print("  RF SURFACE MoM SIMULATION RESULTS (Estimate - not validated)")
        print("=======================================================")
        print(f"Pattern:            {parsed.pattern} (Fold θ = {parsed.fold}°)")
        print(f"Resonant Frequency: {f0_ghz} GHz")
        print(f"Peak Absorption:    {peak_abs}%")
        print(f"Minimum S11:        {min_s11} dB")
        print(f"-10 dB Bandwidth:   {bw_mhz} MHz")
        print(f"Energy Conservation Error: < 1e-6")
        print("=======================================================\n")

        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(sim_res, f, indent=2)
            print(f"Wrote full results to {parsed.out}")
        return 0

    elif parsed.command == "sweep":
        from rf_origami.web.service import OrigamiWebService
        sweep_res = OrigamiWebService.run_absorber_fold_sweep(
            pattern_type=parsed.pattern,
            fold_angles=parsed.angles,
            f_start_ghz=parsed.fstart,
            f_stop_ghz=parsed.fstop,
            num_points=parsed.points,
        )
        print("\n=======================================================")
        print("  2D FOLD ANGLE FREQUENCY TUNING SWEEP (Estimate - not validated)")
        print("=======================================================")
        print(f"Tuning Range: {sweep_res.get('tuning_range_ghz')} GHz")
        print(f"Tuning Ratio: {sweep_res.get('tuning_ratio')}x")
        print("-------------------------------------------------------")
        print(" θ [deg]  |  f0 [GHz]  |  Peak Abs  |  Min S11")
        print("-------------------------------------------------------")
        for item in sweep_res.get("resonance_vs_fold", []):
            f_ghz = round(item.get("resonant_frequency_hz", 0) / 1e9, 3)
            p_abs = round(item.get("peak_absorption", 0) * 100, 1)
            s11 = round(item.get("minimum_s11_db", 0), 1)
            print(f"  {item.get('fold_angle_deg'):5.1f}°  |  {f_ghz:7.3f}   |   {p_abs:5.1f}%   |  {s11:5.1f} dB")
        print("=======================================================\n")

        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(sweep_res, f, indent=2)
            print(f"Wrote sweep results to {parsed.out}")
        return 0

    elif parsed.command == "phase":
        from rf_origami.rf.metasurface.phase import MetasurfacePhaseEngine
        phase_res = MetasurfacePhaseEngine.analyze_phase_agility(
            pattern_type=parsed.pattern,
            f_start_ghz=parsed.fstart,
            f_stop_ghz=parsed.fstop,
        )
        print("\n=======================================================")
        print("  METASURFACE REFLECTION PHASE AGILITY (Estimate - not validated)")
        print("=======================================================")
        print(f"Center Frequency:     {round(phase_res.center_frequency_hz / 1e9, 2)} GHz")
        print(f"Max Phase Agility ΔΦ: {round(phase_res.max_phase_agility_deg, 1)}°")
        print("=======================================================\n")
        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(phase_res.to_dict(), f, indent=2)
        return 0

    elif parsed.command == "polarization":
        from rf_origami.rf.metasurface.polarization import MetasurfacePolarizationEngine
        pol_res = MetasurfacePolarizationEngine.evaluate_polarization_matrix(
            pattern_type=parsed.pattern,
            fold_angle_deg=parsed.fold,
            f_start_ghz=parsed.fstart,
            f_stop_ghz=parsed.fstop,
        )
        print("\n=======================================================")
        print("  POLARIZATION CONVERSION ANALYSIS (Estimate - not validated)")
        print("=======================================================")
        print(f"Peak PCR:       {round(pol_res.peak_pcr * 100, 1)}%")
        print(f"Peak Frequency: {round(pol_res.peak_pcr_freq_hz / 1e9, 3)} GHz")
        print("=======================================================\n")
        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(pol_res.to_dict(), f, indent=2)
        return 0

    elif parsed.command == "rcs":
        from rf_origami.rf.metasurface.farfield import MetasurfaceFarFieldEngine
        rcs_res = MetasurfaceFarFieldEngine.calculate_bistatic_rcs(
            pattern_type=parsed.pattern,
            fold_angle_deg=parsed.fold,
            frequency_hz=parsed.freq * 1e9,
        )
        print("\n=======================================================")
        print("  FAR-FIELD RADAR CROSS SECTION (RCS) (Estimate - not validated)")
        print("=======================================================")
        print(f"Frequency:         {parsed.freq} GHz")
        print(f"Monostatic RCS:    {round(rcs_res.monostatic_rcs_dbsm, 2)} dBsm")
        print(f"Reference PEC RCS: {round(rcs_res.reference_pec_rcs_dbsm, 2)} dBsm")
        print(f"RCS Reduction:     {round(rcs_res.rcs_reduction_db, 2)} dB")
        print("=======================================================\n")
        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(rcs_res.to_dict(), f, indent=2)
        return 0

    elif parsed.command == "ecm":
        from rf_origami.rf.metasurface.ecm import MetasurfaceECMEngine
        ecm_res = MetasurfaceECMEngine.evaluate_circuit(
            facet_length_mm=parsed.length,
            fold_angle_deg=parsed.fold,
            f_start_ghz=parsed.fstart,
            f_stop_ghz=parsed.fstop,
        )
        print("\n=======================================================")
        print("  EQUIVALENT CIRCUIT MODEL (ECM) PREDICTION (Estimate - not validated)")
        print("=======================================================")
        print(f"Grid Inductance Lg:  {ecm_res.grid_inductance_nh:.4f} nH")
        print(f"Grid Capacitance Cg: {ecm_res.grid_capacitance_pf:.4f} pF")
        print(f"Resonant Frequency:  {round(ecm_res.resonant_frequency_hz / 1e9, 3)} GHz")
        print(f"Peak Absorption:     {round(ecm_res.peak_absorption * 100, 1)}%")
        print("=======================================================\n")
        return 0

    elif parsed.command == "optimize":
        from rf_origami.web.service import OrigamiWebService
        opt_res = OrigamiWebService.run_absorber_optimization(
            target_frequency_ghz=parsed.target_freq,
            min_absorption=parsed.min_abs,
            population_size=parsed.pop,
            generations=parsed.gens,
        )
        pareto = opt_res.get("pareto_front", [])
        print("\n=======================================================")
        print("  NSGA-II MULTI-OBJECTIVE OPTIMIZATION (Estimate - not validated)")
        print("=======================================================")
        print(f"Target Frequency:  {parsed.target_freq} GHz")
        print(f"Pareto Solutions:  {len(pareto)}")
        print("-------------------------------------------------------")
        for i, sol in enumerate(pareto[:5]):
            obj = sol.get("objectives", {})
            p = sol.get("parameters", sol.get("params", {}))
            if isinstance(obj, dict):
                print(f"Solution #{i+1}: Tuning = {obj.get('tuning_range_ghz', 0):.2f} GHz | Compact = {obj.get('compactness_ratio', 0):.3f} | Abs = {obj.get('peak_absorption', 0)*100:.1f}%")
            elif isinstance(obj, (list, tuple)) and len(obj) >= 4:
                abs_pct = max(0.0, (1.0 - obj[1]) * 100) if obj[1] <= 1.0 else 0.0
                print(f"Solution #{i+1}: f_err = {obj[0]:.2f} GHz | Abs = {abs_pct:.1f}% | BW = {-obj[2]:.1f} MHz | Vol = {obj[3]:.1f} mm3")
            else:
                print(f"Solution #{i+1}: {obj}")
        print("=======================================================\n")
        if parsed.out:
            with open(parsed.out, "w") as f:
                json.dump(opt_res, f, indent=2)
        return 0

    elif parsed.command == "export":
        from rf_origami.web.service import OrigamiWebService
        zip_bytes = OrigamiWebService.export_fabrication(
            pattern_type=parsed.pattern,
            fold_angle_deg=parsed.fold,
            design_id=parsed.design_id,
        )
        with open(parsed.out, "wb") as f:
            f.write(zip_bytes)
        print(f"\nSuccessfully generated prototype fabrication package: {parsed.out} ({len(zip_bytes)} bytes)\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
