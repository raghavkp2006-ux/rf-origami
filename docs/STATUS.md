# Research status and repository audit

Status date: 2026-10-26. **Research prototype.** Physical antenna validation is incomplete.
The target of >95% agreement has not been demonstrated. Status applies to a specific
metric and model; software tests are not measurement validation.

| Metric / capability | Status | Evidence or limitation |
| --- | --- | --- |
| Fold angle parameter | Validated (software only) | Kinematics and parameter tests; no physical angle calibration |
| Dimensions and bounding box | Validated (software only) | Hand-computed mesh tests |
| Surface area | Validated (software only) | Mesh and geometry tests |
| Bounding volume and compactness | Validated (software only) | Geometry/objective tests; an AABB is not material volume |
| Vertex, facet, crease and cell counts | Not validated as a dashboard set | Individual representations exist; no complete cross-pattern dashboard acceptance test |
| Folded size reduction | Not validated as a dashboard set | Compactness exists; definition depends on reference dimensions |
| Conductor path length | Not validated | Panel-to-wire path is inferred by sorting spatial coordinates |
| S11 and return loss | Not validated | Algebra tested; physical results require independent references |
| VSWR | Not validated | Algebra tested; physical input impedance is not validated |
| Input impedance, R, X | Validated (wire dipole only; V-dipole fold fails) | Straight wire dipole Rin error is 0.10% (N=40) / 2.12% (N=80) vs NEC2 (<5% gate). Bent V-dipole Rin fails 5% gate at 90° (5.08%) and 120° (6.72%). Wire V-dipole benchmark, not an origami patch or surface antenna, and not a measurement. |
| Resonant frequency | Validated (wire V-dipole only) | Reactance-zero fr error < 1.02% across all bend angles 0°–120° vs NEC2 (<5% gate). Wire V-dipole benchmark, not an origami patch or surface antenna, and not a measurement. |
| −10 dB bandwidth and S11 depth | Not validated | Contiguous crossings tested; no matched antenna reference |
| Quality factor | Not validated | No independent antenna comparison |
| Fold-dependent resonance, bandwidth and tuning ratio | Not validated (partially benchmarked on wire V-dipole) | Wire V-dipole fr(theta) tracks within 1% of NEC2 across 0°–120°, but Rin fails 5% gate at 90° and 120°. Not an origami surface patch, not an experimental measurement. |
| S11(f, theta) heat map | Not validated | Visualizes estimated solver output |
| Mesh non-degeneracy and edge conservation | Validated (software only) | Reject collapsed triangles and non-isometric folds before antenna solves |
| Dielectric-loaded patch resonance | Not implemented | Effective-permittivity loading is not a substrate-aware patch solver |
| RWG surface antenna basis | Not implemented | Antenna solver uses a Galerkin rooftop wire basis with reduced kernel; not an RWG surface basis |
| Surface singular quadrature | Not implemented | Wire kernel uses exact asinh static part with Gauss-Legendre quadrature for smooth dynamic remainder; surface singular quadrature is not implemented |
| Antenna far-field integral from RWG currents | Not implemented | Separate metasurface pattern estimates exist |
| Far-field pattern, radiated power, directivity and HPBW | Directivity & peak direction agree with NEC2 (wire V-dipole, free space, computed by scripts/farfield_validation.py); HPBW & patch not validated | Directivity agrees within 0.006 dB (gate 0.5 dB) and peak direction within 0.00° (gate 5.0°, agreement limited by the angular grid) across 0°–120°. Patch far field not validated. |
| Gain, efficiency and axial ratio | Validated against NEC2 at 0° only; unvalidated at 30°, 60°, 90°, 120° (NEC2 reference not reliable for efficiency; CLI/web use stand-in) | Radiation efficiency and gain are validated against NEC2 at 0° only. At 30°, 60°, 90°, 120°, the NEC2 reference is not reliable for efficiency (internal power-balance loss up to 10.8% on lossless wire), so they are unvalidated. CLI and Web studio retain Estimate - not validated badge. |
| Absorber S11, S21, absorption and bandwidth | Not validated physically | Separate surface solver and consistency tests; no measured reference establishes general accuracy |
| Metasurface phase, RCS and polarization | Not validated physically | Existing approximate models and software tests |

## Repository reality check

- Current test suite: 149 automated tests (147 passed, 2 xfailed on strict Rin gates at 90° and 120°).
  Test counts refer to software behavior and regression checks, not physical benchmark passes.
- The antenna solver is `rf_origami/rf/solver/mom_solver.py`. It uses a Galerkin rooftop wire basis with a reduced kernel (`rooftop_wire.py`), not an RWG surface basis. A separate absorber surface solver exists and must be assessed independently.
- Feed model: 1 V delta-gap generator at the node between segment p-1 and p (p = port_segment_index); solve `Z I = V`, then `Zin = 1/I_feed`. The solver rejects out-of-range feeds (requires 1 <= port_segment_index <= N-1) and verifies segments form one open consecutive polyline. Port terminals do not create a physical gap in the mesh.
- Wire kernel and basis: Galerkin rooftop wire basis with reduced (thin-wire) kernel, exact asinh static part, and Gauss-Legendre quadrature of the smooth dynamic remainder.
- Reciprocity is evaluated on bent, unequal segments using the pre-symmetrization matrix asymmetry with a relative tolerance of 1e-4, which passes (~2.3e-5). Mesh convergence (<1% change in resonant frequency $f_r$ between 30 and 40 segments) also passes (~0.068%).
- Independent NEC2 reference comparison:
  - Bundled matched-geometry NEC2 reference: 57.46 mm, 0.5 mm radius copper wire in free space, 1.8–3.0 GHz (61 points).
  - Straight wire dipole (0° bend) passes the 5% gate: fr error = 0.91% (N=40) / 1.01% (N=80); Rin error = 0.10% (N=40) / 2.12% (N=80); |X(f0)| = 5.34 Ω (N=40) / 5.73 Ω (N=80).
  - Wire V-dipole fold sweep (0°, 30°, 60°, 90°, 120°): fr error < 1.02% across all angles (<5% gate met). Rin error: 0° (0.10%/2.12% PASS), 30° (0.99%/1.16% PASS), 60° (3.49%/1.57% PASS), 90° (6.69%/5.08% FAIL >5%), 120° (8.00%/6.72% FAIL >5%). The 5% Rin gate fails at 90° and 120°.
  - MoM N=40 and N=80 are both compared against the NEC2 reference at N=80. For matched-N comparison at N=40 against NEC2 N=40, $R_{\text{in}}$ error is 1.05% (0°), 2.68% (60°), 6.81% (90°), and 10.68% (120°).
  - Say plainly: this is a wire V-dipole benchmark, not an origami patch or surface antenna, and not a measurement.
- The default standalone wire solve uses air. Explicit dielectric selection retains the legacy effective-permittivity approximation and is labelled as such.
- The report's textbook dipole and image-scaled monopole checks are screening diagnostics. The monopole is not an independent second benchmark.

## Plan progress and remaining acceptance gates

- [x] Audit actual solver basis, excitation and quadrature.
- [x] Correct README status and test counts; document real dependencies.
- [x] Generate Markdown and JSON diagnostics, including failures and missing references.
- [x] Add percent error comparisons, absolute dB tolerances and zero-reference handling.
- [x] Centralize interpolated resonance and contiguous-bandwidth extraction.
- [x] Flag unresolved frequency grids, boundary minima and truncated bands.
- [x] Gate antenna fold geometry for degeneracy and edge conservation.
- [x] Expose estimated fold-sweep heat-map data and draw it in the studio.
- [x] Show validation report and model limitations; remove unconditional pass badges.
- [x] Add packaging metadata and Python 3.10–3.12 test CI with diagnostic artifacts.
- [x] Replace/correct the antenna formulation until reciprocity and mesh convergence pass (Galerkin rooftop wire basis with reduced kernel).
- [x] Independently validate dipole resonance and Rin within 5% using identical geometry/feed/radius (NEC2 straight dipole benchmark: fr err 0.91% N=40 / 1.01% N=80; Rin err 0.10% N=40 / 2.12% N=80; |X| <= 5.73 Ω. Note: wire benchmark, not origami patch or measurement).
- [ ] Add a genuinely independent second antenna benchmark within 5%.
- [ ] Add a matched-geometry length sweep against NEC2 or another reference.
- [ ] Preserve a user-defined physical conductor path and feed through folding.
- [ ] Validate origami fr(theta) at three or more angles within 5% (Wire V-dipole fr is within 1% across 5 angles against NEC2, but Rin fails at 90° and 120°; origami surface patch tuning remains pending).
- [ ] Complete the full geometry dashboard and hand-computed per-pattern acceptance cases.
- [ ] Add a demo GIF after the solver workflow and validation narrative are stable.

Phase A is **not complete**. Phase B has metrics and geometry infrastructure but
has not met its physical exit criteria. Phase G has validation UI/CI infrastructure.
Optional far-field, optimization and fabrication expansions should wait for the
core antenna acceptance gates. Existing modules are not evidence those gates pass.

## Known limitations

1. **Conductor conversion**: Conductor vertices are sorted along a spatial axis to form an open wire polyline; physical trace topology is not preserved during folding.
2. **Branching and closed loops**: Antenna solver supports only single unbranched open polylines.
3. **Absence of RWG surface basis**: Antenna solver implements a thin-wire Galerkin rooftop basis, not an RWG surface basis.
4. **Substrate modeling**: Dielectric loading uses an approximate effective-permittivity scalar scaling, not a layered-medium Green's function.
5. **Far-field quantities**: Evaluated in `scripts/farfield_validation.py` and `scripts/efficiency_diagnostic.py` (wire V-dipole, free space, computed by `scripts/farfield_validation.py`). Directivity agrees with NEC2 within 0.006 dB (gate 0.5 dB) and peak direction within 0.00° (gate 5.0°, agreement limited by the angular grid) across all angles (0°, 30°, 60°, 90°, 120°). Radiation efficiency and gain are validated against NEC2 at 0 degrees only; at 30, 60, 90, 120 degrees the NEC2 reference is not reliable for efficiency, so they are unvalidated. Diagnostic investigation (`scripts/efficiency_diagnostic.py`) shows NEC2's sharp bend reference suffers an internal power-balance loss (96.6% at 60°, 92.8%–93.3% at 90°, 89.2%–91.9% at 120° on perfectly lossless PEC wire), which recovers to ~99.8% when smoothed ($K=9$). MoM maintains 100.0% power balance on lossless wire and 99.5%–99.8% on copper across all angles. Because NEC2's sharp junction violates energy conservation when bent, efficiency cannot be validated against NEC2 at bent angles. Furthermore, CLI and Web studio use an analytic aperture physical-optics stand-in (`MetasurfaceFarFieldEngine.calculate_bistatic_rcs`), not the MoM vector potential code; their outputs strictly retain the `Estimate - not validated` badge. Surface patch far field, HPBW, and axial ratio remain unvalidated estimates.
6. **Input resistance at steep bends**: Rin fails the 5% gate at 90° (5.08% at N=80) and 120° (6.72% at N=80) against NEC2. Status remains: f0 validated at all angles (<=1.02%), Rin validated at 0°, 30°, 60°, not validated at 90° and 120° (strict xfails preserved in test suite).
   - *Convergence analysis*: For $a = 0.5\text{ mm}$, $N=20 \to 40 \to 80$ shows Rin error converging toward NEC2 ($7.51\% \to 6.69\% \to 5.08\%$ at 90°; $8.70\% \to 8.00\% \to 6.72\%$ at 120°). The claim of thin-wire kernel breakdown at $N=160$ is restricted to $a = 0.5\text{ mm}$ ($\Delta = 0.359\text{ mm} < a = 0.5\text{ mm}$, $\Delta/a = 0.72$), where artificial delta-gap fringing capacitance inflates Rin error to $>20\%$. In contrast, at $a = 0.1\text{ mm}$ (where $\Delta/a \ge 3.59$ up to $N=160$), the 90°/120° error does not decrease with refinement and in fact grows at 120° ($8.06\%, 10.06\%, 11.24\%$ for $N = 40, 80, 160$), which indicates a systematic difference rather than a discretization error.
   - *Controlled numerics isolation*: Quadrature order (outer 8 to 64) is identical to 4 decimal places. Adjacent non-collinear rooftop 2D integrals match independent dense Gauss-Legendre quadrature to $<10^{-6}$ relative error (`test_adjacent_non_collinear_segment_interaction_matches_dense_quadrature`). The solver numerics, coordinate projections, and asinh static kernels are exact.
   - *Radius sweep experiment (`scripts/radius_sweep.py`)*: Controlled sweep across wire radii $a \in [0.5, 0.25, 0.1]\text{ mm}$ refuted the wire-cylinder overlap hypothesis. When $a$ is reduced to $0.1\text{ mm}$ (shrinking the overlap region by $5\times$), the $R_{\text{in}}$ error at $90^\circ$ and $120^\circ$ does not drop below 5%; for converged segment counts ($N=80, 160$), it persists at $5.7\%-7.0\%$ ($90^\circ$) and $10.1\%-11.2\%$ ($120^\circ$). In contrast, for straight dipoles ($0^\circ$), NEC2 and MoM agree within $0.18\%-0.24\%$ at $a=0.1\text{ mm}$ across $N \in [40, 80, 160]$.
   - *NEC2 feed and junction sensitivity (`scripts/nec2_sensitivity.py`)*: Standalone sensitivity evaluation tested NEC2 reference sensitivity across feed placement (segment 1 of wire 2 vs last segment of wire 1, 0.00% difference), center feed on a single bent wire (not possible in NEC-2 as wire cards must be straight cylinders; 0.00%–0.11% difference at 0°), and extended thin-wire kernel EK (-0.13% to -0.69% at 0°–90°, -0.62% to -1.22% at 120°). The spread of NEC2 $R_{\text{in}}$ across these modeling options is small (<2% at both 90° and 120°), confirming the reference is stable against feed placement and kernel choice, but drifts about 5% with segment count at 120 degrees. MoM $R_{\text{in}}$ falls strictly outside the NEC2 spread at 90° and 120°. The hypothesis that feed/junction conventions explain the 5%–11% MoM gap remains an untested hypothesis unsupported by NEC2 sensitivity data.
   - *NEC2 self-convergence at 120°*: NEC2's own $R_{\text{in}}$ at $120^\circ$ drifts from $28.63\,\Omega$ ($N=40$) to $27.79\,\Omega$ ($N=80$) and $27.23\,\Omega$ ($N=160$), a drift of about 5% (4.89%). Because the reference itself drifts by ~5% across segment counts at 120°, the 5% gate at that angle cannot cleanly separate solver error from reference uncertainty.
   - MoM and NEC2 Rin agree within 0.17%-1.45% on smoothed bends (scripts/nec2_smooth_bend.py). The power-balance diagnostic (scripts/efficiency_diagnostic.py) shows NEC2's sharp junction is internally inconsistent (radiated power below input power on a lossless wire, up to 10.8%) while MoM conserves power, so NEC2's sharp-junction Rin is the more suspect value. This is indicative, not proven: the smoothed geometries are not identical to the sharp one (f0 shifts), MoM energy conservation shows self-consistency and not correctness, and the Rin gates at 90 and 120 degrees still fail.
7. **No physical measurements**: All evidence is computational benchmark comparison against NEC2. Zero physical measurements exist.

## Future work

1. **Apex singularity & Rin convergence**: Refine apex charge accumulation modeling to bring Rin error below 5% at 90° and 120°.
2. **Topological path routing**: Formulate continuous trace routing preserving conductor topology through folding.
3. **Multi-wire junctions & loop basis**: Add junction basis functions for branched and closed origami structures.
4. **RWG surface MoM on dielectric substrates**: Implement triangular surface basis functions with layered-media Green's functions.
5. **Antenna far-field radiation integrals**: Near-to-far field transformation for 3D patterns, realized gain, and axial ratio.
6. **Physical hardware validation campaign**: Fabricate prototypes and perform VNA / anechoic chamber measurements.

## Reproducing diagnostics

```bash
python -m pip install -r requirements.txt
python -m pytest tests -v
python -m rf_origami.rf.solver.validation_report
python -m rf_origami.rf.solver.validation_report --strict
```

The default report command succeeds when it writes the report, even if physical
gates fail. `--strict` exits 1 until physical validation is complete. CI publishes
diagnostics as artifacts and does not confuse a report-generation pass with solver
acceptance. `GET /api/rf/validation` reads the saved report without running solves.

Use the [NEC2 model guidelines](https://www.nec2.org/part_3/cards/secii.html) for a
matched wire reference and the [openEMS patch tutorial](https://docs.openems.de/en/stable/octave/Tutorials/Simple_Patch_Antenna.html)
for a substrate-aware patch reference. No independent reference data or the
parameters PDF mentioned in the pasted plan were supplied with this repository.
