# RF Origami Design Studio

**A First-Principles Computational Origami & Standalone Electromagnetic (RF) Engineering Platform**

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-147%20passed%2C%202%20xfail-success)](tests/)
[![Architecture](https://img.shields.io/badge/Architecture-100%25%20Standalone-brightgreen)](#core-architecture-philosophy)
[![Status](https://img.shields.io/badge/Status-Research%20prototype-yellow)](docs/STATUS.md)


---

## Table of Contents

1. [Validation Status & Benchmark Evidence](#validation-status--benchmark-evidence)
2. [Executive Summary & Core Philosophy](#executive-summary--core-philosophy)
3. [Current Progress & What Has Been Done Till Now](#current-progress--what-has-been-done-till-now)
   - [Phase 1: Computational Origami & Kinematic Engine](#phase-1-computational-origami--kinematic-engine)
   - [Phase 2: Generative Design & Exploration Pipeline](#phase-2-generative-design--exploration-pipeline)
   - [Phase 3: Standalone In-House RF & Electromagnetic Solver](#phase-3-standalone-in-house-rf--electromagnetic-solver)
   - [Phase 4: Design Studio Web Interface & Interactive Visualizer](#phase-4-design-studio-web-interface--interactive-visualizer)
4. [Project Directory Structure](#project-directory-structure)
5. [Quickstart & Usage Guide](#quickstart--usage-guide)
6. [In-Depth Technical Architecture](#in-depth-technical-architecture)
   - [Origami Geometry to RF Discretization Pipeline](#origami-geometry-to-rf-discretization-pipeline)
   - [Mathematical Validity Filtering](#mathematical-validity-filtering)
   - [Electromagnetic Formulation (Wire EFIE / MoM)](#electromagnetic-formulation-wire-efie--mom)
7. [Known Limitations](#known-limitations)
8. [Future Work & Forward Roadmap](#future-work--forward-roadmap)
9. [Verification & Test Suite](#verification--test-suite)

---

## Validation Status & Benchmark Evidence

**Research prototype — antenna RF metrics are not validated for origami surfaces or physical measurements.**

> **Scope: wire V-dipole vs NEC2 only; not an origami surface antenna, not a patch, not a measurement.**

The platform targets >95% agreement (error < 5%) for validated resonance, impedance, and S-parameter metrics. In our v0.1 benchmark against independent NEC2 reference data (`data/validation/nec2_reference.json`), **>95% agreement was met only for resonant frequency** ($f_r \le 1.02\%$ error across all tested bend angles). Input resistance $R_{\text{in}}$ meets the 5% gate for straight and moderate bends (0°, 30°, 60°), but fails at steeper bends (90° and 120°).

### Verified Evidence Summary

- **Antenna Solver Formulation**: Galerkin rooftop thin-wire Method of Moments (MoM) with reduced thin-wire kernel, exact static singularity integration ($\mathrm{asinh}$), Gauss-Legendre quadrature for the dynamic remainder, 1 V delta-gap node excitation, and open polyline geometry.
- **Reciprocity Gate**: PASS. Relative pre-symmetrization matrix asymmetry is $2.3 \times 10^{-5}$, well within the $\le 10^{-4}$ gate.
- **Mesh Convergence Gate**: PASS. Resonant frequency changes by only $0.068\%$ between 30 and 40 segments (gate $\le 1\%$).
- **Independent NEC2 Comparison**: Free-space copper wire ($L = 57.46\text{ mm}$, radius $a = 0.5\text{ mm}$, $\sigma = 5.8 \times 10^7\text{ S/m}$, 1.8–3.0 GHz, 61 points). Apex feed node ($N/2$).

#### NEC2 Comparison Results Table (Matched Geometry)

| Bend Angle | NEC2 $f_0$ (GHz) | MoM $f_0$ ($N=40$) | $f_0$ Err ($N=40$) | MoM $f_0$ ($N=80$) | $f_0$ Err ($N=80$) | NEC2 $R_{\text{in}}$ ($\Omega$) | MoM $R_{\text{in}}$ ($N=40$) | $R_{\text{in}}$ Err ($N=40$) | MoM $R_{\text{in}}$ ($N=80$) | $R_{\text{in}}$ Err ($N=80$) | $|X(f_0^{\text{NEC2}})|$ ($N=40$) | $|X(f_0^{\text{NEC2}})|$ ($N=80$) | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0° (Straight)** | 2.4124 | 2.4343 | 0.91% | 2.4369 | 1.01% | 73.61 | 73.54 | 0.10% | 75.17 | 2.12% | 5.34 $\Omega$ | 5.73 $\Omega$ | **PASS** |
| **30°** | 2.4213 | 2.4434 | 0.91% | 2.4455 | 1.00% | 70.66 | 69.96 | 0.99% | 71.48 | 1.16% | 5.41 $\Omega$ | 5.67 $\Omega$ | **PASS** |
| **60°** | 2.4520 | 2.4747 | 0.92% | 2.4751 | 0.94% | 61.82 | 59.66 | 3.49% | 60.85 | 1.57% | 5.51 $\Omega$ | 5.42 $\Omega$ | **PASS** |
| **90°** | 2.5169 | 2.5406 | 0.94% | 2.5386 | 0.86% | 47.14 | 43.98 | 6.69% | 44.74 | 5.08% | 5.56 $\Omega$ | 4.96 $\Omega$ | **FAIL** ($R_{\text{in}} > 5\%$) |
| **120°** | 2.6419 | 2.6672 | 0.96% | 2.6623 | 0.77% | 27.79 | 25.57 | 8.00% | 25.93 | 6.72% | 5.34 $\Omega$ | 4.22 $\Omega$ | **FAIL** ($R_{\text{in}} > 5\%$) |

*Gates: $f_r \text{ error} < 5\%$ at all angles (PASSED); $R_{\text{in}} \text{ error} < 5\%$ at each angle (FAILED at 90° and 120°).*

MoM N=40 and N=80 are both compared against the NEC2 reference at N=80.
*Matched-N note*: At N=40 against NEC2 N=40, $R_{\text{in}}$ error is 1.05% (0°), 2.68% (60°), 6.81% (90°), and 10.68% (120°).

### Unvalidated Quantities

The following quantities remain estimates and must **not** be considered physically validated:
- **Origami surface / patch antennas**: The benchmark above validates only a thin-wire V-dipole; folding conductive planar facets on flexible substrates is not validated.
- **Far-field radiation**: Far-field directivity and peak direction agree with NEC2 within 0.006 dB (gate 0.5 dB) and 0.00 deg (gate 5.0 deg, agreement limited by the angular grid) across all evaluated angles (0°, 30°, 60°, 90°, 120°) for the wire V-dipole in free space, computed by `scripts/farfield_validation.py`. Radiation efficiency and gain are validated against NEC2 at 0 degrees only; at 30, 60, 90, 120 degrees the NEC2 reference is not reliable for efficiency, so they are unvalidated. Diagnostic investigation (`scripts/efficiency_diagnostic.py`) shows NEC2's sharp-junction model suffers an internal power-balance loss (3.4% at 60°, 6.7%–7.2% at 90°, and 8.1%–10.8% at 120° even on a perfectly lossless PEC conductor), which recovers to ~99.8% when smoothed. MoM maintains exact energy conservation (100.0% on lossless wire) across all angles. Because the NEC2 reference itself violates power balance when bent, efficiency cannot be validated against NEC2 at bent angles. In the CLI and Web studio, antenna far-field directivity, gain, and efficiency are not implemented from solved currents; metasurface RCS uses an analytic aperture physical-optics stand-in (`rf_origami/rf/metasurface/farfield.py`) and carries the `Estimate - not validated` badge. All other far-field quantities (surface patch radiation, HPBW, axial ratio) remain unvalidated estimates.
- **Dielectric loading**: Effective-permittivity approximation is an exploratory estimate, not a full layered-media Green's function solve.
- **Metasurface / Absorber models**: The separate surface absorber solver provides analytical and unit consistency checks (conservation $R+T+A=1$), but is not physically validated against chamber measurements.
- **Physical measurements**: Zero physical fabrication or anechoic chamber measurements have been performed.

Read the detailed [metric status and repository audit](docs/STATUS.md) and the generated [validation report](docs/validation_report.md). Regenerate the report with:

```bash
python -m rf_origami.rf.solver.validation_report
# Strict mode exits with code 1 while physical acceptance gates fail:
python -m rf_origami.rf.solver.validation_report --strict
```

The studio's **Validation** dialog shows the saved report and live diagnostic failures. Antenna results carry Estimate / Not validated labels. Frequency sweeps use local parabolic S11 interpolation and contiguous, interpolated −10 dB crossings. Boundary minima, truncated bands, and frequency steps at or above 1% are flagged. Fold sweeps check panel isometry and non-degeneracy and return an S11 heat map, but physical fold-tuning validation remains pending.

## Executive Summary & Core Philosophy

Origami engineering enables physical surfaces to fold, deploy, and morph between compact 2D manufacturing layouts and functional 3D shapes. In radio frequency (RF) and microwave engineering, this morphing capability unlocks **frequency-reconfigurable antennas, deployable satellite reflectors, tunable frequency-selective surfaces (FSS), and beam-steering phased arrays** whose electromagnetic properties adapt continuously with mechanical folding.

### The Problem with Traditional Workflows
Typical origami RF engineering workflows rely on fragmented, proprietary software stacks:
- Folding kinematics are approximated in commercial CAD tools (e.g., Rhino/Grasshopper).
- Geometries are manually exported via intermediary files (`.step`, `.sat`, `.dxf`).
- Electromagnetic behavior is evaluated in heavy commercial solvers (Ansys HFSS, CST Studio Suite).
- Optimization loops across these disconnected tools are slow, fragile, expensive, and black-box.

### Our Core Philosophy: 100% Standalone & Native
**RF Origami Design Studio** is built from the ground up as a **completely self-contained computational platform**:
- **No Commercial CAD Dependencies**: Does not require Rhino, Grasshopper, SolidWorks, or AutoCAD.
- **No Commercial EM Solver Dependencies**: Does not require Ansys HFSS, CST Studio Suite, or FEKO.
- **Native Kinematic & EM Formulation**: Origami mathematics, rigid kinematics, surface mesh discretization, and Method of Moments (MoM) electromagnetic integral equation solvers are implemented natively in Python.
- **Unified Design Loop**: Geometry generation, physical validation, 3D kinematic folding, electromagnetic simulation, and multi-parameter exploration live within a single coherent environment.

```
+-----------------------------------------------------------------------------------+
|                           RF ORIGAMI DESIGN STUDIO                                |
|                                                                                   |
|  [Design Variables]  --->  [Procedural Generator]  --->  [Validity Filter]         |
|                                                                  |                |
|  [3D Kinematics]     <---  [Fold Angle Engine]     <---  [Candidate Gallery]      |
|         |                                                                         |
|         v                                                                         |
|  [RF Discretization] --->  [In-House MoM Solver]   --->  [S11, Zin, Fold Sweeps]  |
+-----------------------------------------------------------------------------------+
```

---

## Current Progress & What Has Been Done Till Now

The project provides a generative exploration suite and an interactive web studio, backed by 149 automated tests (147 passed, 2 xfailed on strict Rin gates). The sections below describe implemented prototype capabilities; physical antenna validation remains incomplete.

### Phase 1: Computational Origami & Kinematic Engine
- **Vector & Transformation Algebra (`core/geometry.py`)**:
  - Full $\mathbb{R}^3$ vector algebra (`Vector3D`, `Point3D`) with robust norm, dot, and cross products.
  - Rodrigues' rotation formula for arbitrary axis-angle rotations, Tait-Bryan Euler matrices, and $4 \times 4$ homogeneous affine transformations ($\mathrm{SE}(3)$).
  - Polygon normal estimation via Newell's method, projected cross-product area calculation, and coplanarity checks.
- **Crease Pattern Graph Representation (`core/crease_pattern.py`)**:
  - Topological graph complex $G = (V, E, F)$ representing flat 2D blueprints.
  - Strongly typed crease assignments: Mountain (`M`), Valley (`V`), Boundary (`B`), and Facet/Flat (`F`).
  - Mathematical flat-foldability verifications:
    - **Kawasaki's Theorem**: Evaluates whether the alternating sum of sector angles around interior vertices equals $180^\circ$ ($\sum (-1)^i \alpha_i = 0$).
    - **Maekawa's Theorem**: Enforces that the difference between Mountain and Valley creases at any flat-foldable degree-4 vertex is $|M - V| = \pm 2$.
  - FOLD (Fold Oriented Language for Designers) JSON schema serialization.
- **Folded 3D Mesh Infrastructure (`core/mesh.py`)**:
  - `FoldedMesh` container managing 3D vertices, polygonal facets, facet normals, surface area, and bounding boxes.
  - Fan triangulation routines for conformal triangular meshing.
- **Analytical Kinematics (`folding/kinematics.py`, `folding/engine.py`)**:
  - Closed-form isometric kinematics for standard origami families:
    - **Miura-Ori**: Tessellated unit cells parameterized by side lengths $a, b$, facet angle $\gamma$, and fold angle $\theta$.
    - **Yoshimura Pattern**: Triangular cylinder pattern with axial and circumferential fold kinematics.
    - **Waterbomb Pattern**: Radial multi-crease vertex deployment kinematics.
    - **Degree-4 Single Vertex**: General degree-4 rigid vertex fold propagation.

### Phase 2: Generative Design & Exploration Pipeline
Rather than limiting the user to predefined static patterns, the platform features a generative exploration engine:
- **Design Space Formulation (`generator/design_space.py`)**:
  - Multi-dimensional parametric spaces defining continuous and discrete ranges (cell counts, panel lengths, acute angles, fold bounds).
  - Multi-dimensional Latin Hypercube Sampling (LHS) and uniform random sampling to generate candidate design populations (10 to 250+ candidates).
- **Three-Tier Validity & Feasibility Filtering**:
  - **Topology Checks**: Vertex degree, connectivity, non-isolated vertices.
  - **Geometric Integrity**: Minimum/maximum edge lengths, non-degenerate face areas, aspect ratio bounds.
  - **Foldability Verification**: Kawasaki and Maekawa checks where applicable.
  - **Collision Prevention**: Bounding box self-intersection checks and face clearance constraints.
- **Candidate Exploration Engine (`generator/engine.py`)**:
  - Automated batch generation producing candidate objects with full metadata: geometric metrics, compactness ratios, deployment profiles, and SVG crease pattern thumbnails.

### Phase 3: Standalone In-House RF & Electromagnetic Solver
- **RF Material System (`rf/materials/material.py`)**:
  - Material models for conductors and dielectrics: Copper ($\sigma = 5.8 \times 10^7 \, \text{S/m}$), Aluminum, Polyimide, FR-4 ($\varepsilon_r = 4.4, \tan\delta = 0.02$), Rogers RO4350B ($\varepsilon_r = 3.66, \tan\delta = 0.0037$), and customizable substrates.
  - Surface resistance calculations: $R_s(f) = \sqrt{\pi f \mu / \sigma}$.
- **Electromagnetic Geometry Converter (`rf/geometry/converter.py`)**:
  - Converts 3D `FoldedMesh` into an electromagnetic computational mesh (`RFTriangleMesh`).
  - Tags conductive facets (radiators, ground planes, traces) and dielectric panels.
  - Automatic feed-port edge detection and coordinate mapping.
- **Port System (`rf/ports/lumped_port.py`)**:
  - Delta-gap and lumped ports ($Z_0 = 50\,\Omega$) positioned across conductive facet boundaries.
- **Method of Moments (MoM) EFIE Solver (`rf/solver/mom_solver.py`, `rf/solver/rooftop_wire.py`)**:
  - First-principles wire integral equation solver based on the Electric Field Integral Equation (EFIE).
  - Galerkin rooftop wire basis with a reduced kernel and exact static singularity integration; RWG surface basis functions are not implemented in the antenna solver.
  - Complex impedance matrix $[Z]$ assembly using reduced thin-wire Green's function with exact asinh static part and Gauss-Legendre quadrature for smooth dynamic remainder:
    $$G(\mathbf{r}, \mathbf{r}') = \frac{e^{-jk|\mathbf{r} - \mathbf{r}'|}}{4\pi |\mathbf{r} - \mathbf{r}'|}$$
  - Direct LU factorization and solution of $[Z][I] = [V]$ over discrete frequency sweeps.
  - Calculation of input impedance:
    $$Z_{\text{in}}(f) = R_{\text{in}}(f) + j X_{\text{in}}(f)$$
  - Return loss / S-parameter extraction:
    $$S_{11}(f) = \frac{Z_{\text{in}}(f) - Z_0}{Z_{\text{in}}(f) + Z_0}, \quad |S_{11}|_{\text{dB}} = 20 \log_{10} |S_{11}|$$
- **Fold-Angle EM Sweeps (`rf/solver/fold_sweep.py`)**:
  - Automatically sweeps folding angle $\theta \in [\theta_{\min}, \theta_{\max}]$, regenerates 3D mesh, executes EM solve, and traces resonant frequency shifts $f_0(\theta)$, bandwidth variations, and impedance trajectories.
- **Antenna Metrics (`rf/metrics/antenna_metrics.py`, `rf/metrics/result.py`)**:
  - Resonant frequency identification, $-10\,\text{dB}$ impedance bandwidth, VSWR, and quality factor $Q$.

### Phase 4: Design Studio Web Interface & Interactive Visualizer
- **Lightweight Built-In Web Server (`rf_origami/web/server.py`, `run_studio.py`)**:
  - Pure Python `http.server` backend with REST endpoints:
    - `POST /api/explore`: Generates and filters design candidates via LHS.
    - `POST /api/generate`: Generates specific 3D mesh and 2D crease pattern data.
    - `POST /api/fold`: Evaluates kinematics at arbitrary fold angles.
    - `POST /api/rf/simulate`: Runs MoM EM simulation over frequency range.
    - `POST /api/rf/fold-sweep`: Executes electromagnetic sweep across fold angles.
    - `GET /api/patterns`: Returns available reference pattern generators.
    - `GET /api/rf/materials`: Provides default material library.
    - `GET /api/rf/benchmarks`: Provides verification benchmark cases.
- **Clean White Engineering CAD UI (`web/static/styles.css`)**:
  - Professional, high-contrast, minimal white engineering aesthetic (slate/white/blue).
  - Fully responsive split-panel workspace with collapsible sidebars and inspector decks.
- **Interactive Visualizers (`web/static/app.js`)**:
  - **Three.js 3D Viewport**: OrbitControls, real-time wireframe and solid facet rendering, dynamic lighting, responsive to continuous fold slider.
  - **HTML5 Canvas 2D Crease Pattern**: Color-coded fold assignments (Red = Mountain, Blue dashed = Valley, Dark = Boundary).
  - **Interactive 2D Scatter Plot Canvas**: Interactive Pareto trade-off exploration (Aspect Ratio vs Packaging Ratio, Footprint vs Volume) with clickable candidate nodes.
  - **Candidate Gallery Grid**: Card-based gallery with status badges, metrics, and SVG thumbnails.
  - **RF Simulation Dashboard**: Embedded Canvas-based plots for $S_{11}$ return loss curves, $Z_{\text{in}}$ resistance/reactance curves, and fold-angle tuning tables.
  - **Self-Contained Offline Dependencies**: Bundled `three.min.js` and `OrbitControls.js` (operates with zero internet connectivity).

---

## Project Directory Structure

```text
RF Origami/
├── README.md                            # Comprehensive project documentation
├── run_studio.py                        # Studio launcher (starts web server at :8080)
├── test.py                              # Quick verification script
│
├── docs/                                # Technical design & architecture documents
│   ├── architecture.md                  # System architecture specification
│   └── rf_origami_architecture_proposal.md # In-depth mathematical & EM proposal
│
├── rf_origami/                          # Primary Python package
│   ├── __init__.py                      # Package exports and version
│   │
│   ├── core/                            # Core geometric & topological primitives
│   │   ├── __init__.py
│   │   ├── geometry.py                  # Vector3D, Point3D, SE(3) transforms, Newell normal
│   │   ├── crease_pattern.py            # CreasePattern, Crease, Face, Kawasaki/Maekawa
│   │   ├── mesh.py                      # FoldedMesh container, triangulation, bounds
│   │   └── parameters.py                # Parameter, ParameterSet, sampling routines
│   │
│   ├── patterns/                        # Parametric pattern generators
│   │   ├── __init__.py
│   │   ├── base.py                      # BasePattern abstract interface
│   │   ├── miura_ori.py                 # Miura-Ori tessellation generator
│   │   ├── yoshimura.py                 # Yoshimura triangular cylinder generator
│   │   ├── waterbomb.py                 # Waterbomb radial generator
│   │   └── degree4_vertex.py            # Single degree-4 parametric vertex
│   │
│   ├── folding/                         # Kinematic folding engines
│   │   ├── __init__.py
│   │   ├── kinematics.py                # Analytical kinematic relations
│   │   └── engine.py                    # FoldingEngine orchestrator
│   │
│   ├── generator/                       # Generative design exploration
│   │   ├── __init__.py
│   │   ├── design_space.py              # DesignSpace, LHS sampler, constraint filters
│   │   └── engine.py                    # GenerativeExplorerEngine batch generator
│   │
│   ├── rf/                              # Native electromagnetic simulation engine
│   │   ├── __init__.py
│   │   ├── materials/
│   │   │   ├── __init__.py
│   │   │   └── material.py              # RFMaterial library (copper, FR4, polyimide)
│   │   ├── geometry/
│   │   │   ├── __init__.py
│   │   │   ├── converter.py             # FoldedMesh to RFTriangleMesh converter
│   │   │   └── rf_object.py             # RF object & facet tag definitions
│   │   ├── ports/
│   │   │   ├── __init__.py
│   │   │   └── lumped_port.py           # LumpedPort, DeltaGapPort definitions
│   │   ├── mesh/
│   │   │   ├── __init__.py
│   │   │   └── discretization.py        # Surface discretization & edge pairs
│   │   ├── sparameters/
│   │   │   ├── __init__.py
│   │   │   └── network.py               # S-parameters, Zin, VSWR representations
│   │   ├── solver/
│   │   │   ├── __init__.py
│   │   │   ├── mom_solver.py            # In-house EFIE Method of Moments solver
│   │   │   ├── fold_sweep.py            # Dynamic folding angle EM sweep
│   │   │   └── validation_cases.py      # Standard benchmark verification cases
│   │   └── metrics/
│   │       ├── __init__.py
│   │       ├── antenna_metrics.py       # Resonant frequency, bandwidth, Q factor
│   │       └── result.py                # SimulationResult data container
│   │
│   ├── visualization/                   # Visualization utilities
│   │   ├── __init__.py
│   │   ├── plot_crease.py               # Matplotlib 2D crease plotter
│   │   ├── plot_folded.py               # Matplotlib 3D folded plotter
│   │   ├── svg_crease.py                # Procedural SVG crease pattern generator
│   │   └── svg_folded.py                # Procedural SVG 3D wireframe projector
│   │
│   └── web/                             # Web application & REST API
│       ├── __init__.py
│       ├── server.py                    # Pure Python HTTP REST server
│       ├── service.py                   # OrigamiWebService coordinator
│       └── static/                      # Web frontend assets
│           ├── index.html               # Single-page studio interface
│           ├── styles.css               # Clean white engineering CAD stylesheet
│           ├── app.js                   # Client-side controller (Three.js & Canvas)
│           ├── three.min.js             # Offline 3D engine (Three.js r128)
│           └── OrbitControls.js         # Offline camera controls
│
└── tests/                               # Comprehensive automated test suite
    ├── __init__.py
    ├── test_geometry.py                 # Vector math, transforms, polygon tests
    ├── test_crease_pattern.py           # Graph topology, Kawasaki, Maekawa tests
    ├── test_mesh.py                     # 3D mesh properties, triangulation tests
    ├── test_parameters.py               # Type safety, bounds, sampling tests
    ├── test_kinematics.py               # Folding kinematics tests
    ├── test_patterns.py                 # Miura-Ori, Yoshimura, Waterbomb tests
    ├── test_generator.py                # Design space & candidate generator tests
    ├── test_rf_materials.py             # Conductor & dielectric material tests
    ├── test_rf_geometry.py              # Mesh conversion & facet tagging tests
    ├── test_rf_ports.py                 # Port assignments & impedance tests
    ├── test_rf_metrics.py               # Resonant frequency & bandwidth tests
    ├── test_em_solver.py                # MoM solver matrix fill & solve tests
    ├── test_visualization.py            # SVG & plotting output tests
    └── test_web.py                      # REST endpoints & web service tests
```

---

## Quickstart & Usage Guide

### 1. Prerequisites
- **Python 3.10, 3.11, or 3.12**
- Python packages: `numpy`, `matplotlib`, `pytest`

Install dependencies:
```bash
python -m pip install -r requirements.txt
```

### 2. Run Automated Test Suite
Verify that all 136 automated tests pass across the entire mathematics, kinematics, and RF solver pipeline:
```bash
pytest tests -v
```

### 3. Launch RF Origami Design Studio
Start the local web application:
```bash
python run_studio.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8080
```

### 4. Typical Exploration Workflow
1. **Define Design Space**: Configure parametric ranges (cell counts, panel lengths $a, b$, facet angle $\gamma$, fold limits) in the left sidebar.
2. **Set Validation Constraints**: Toggle Kawasaki theorem, Maekawa theorem, non-degeneracy, and aspect ratio filters.
3. **Generate Candidates**: Click **Generate Candidates** to trigger Latin Hypercube Sampling (10 to 250 configurations).
4. **Explore & Filter**:
   - Inspect the **Candidate Gallery** for feasible vs. rejected patterns with SVG previews.
   - Use the **Scatter Plot** to visualize multi-objective trade-offs (e.g. Footprint Area vs. Compact Folded Volume).
5. **Select & Inspect**: Click any candidate to load its full 3D geometry and 2D crease layout into the Inspector.
6. **Continuous 3D Folding**: Drag the fold angle slider to watch the structure deploy dynamically in real time.
7. **Run Standalone RF Simulation**: Switch to the RF Analysis tab, configure material properties and frequency range, and execute the in-house Method of Moments solver to plot $S_{11}$ return loss and input impedance $Z_{\text{in}}$.

---

## In-Depth Technical Architecture

### Origami Geometry to RF Discretization Pipeline

```
+--------------------------+
|  Crease Pattern G(V,E,F) |  <-- 2D Reference Blueprint
+--------------------------+
             |
             | Kinematic Transformation T_f(theta)
             v
+--------------------------+
|     FoldedMesh (3D)      |  <-- Rigid panel isometric deformation
+--------------------------+
             |
             | Converter & Layer Stacking
             v
+--------------------------+
|      RFTriangleMesh      |  <-- Triangulated conductor & substrate facets
+--------------------------+
             |
             | Approximate wire-segment discretization
             v
+--------------------------+
|    MoM EFIE Matrix [Z]   |  <-- In-house Method of Moments formulation
+--------------------------+
             |
             | Direct Solve [Z][I] = [V]
             v
+--------------------------+
|   S11(f), Zin(f), f0     |  <-- Extracted RF performance observables
+--------------------------+
```

### Mathematical Validity Filtering
Before any candidate is simulated, it must satisfy rigorous physical and mathematical criteria:
1. **Topological Feasibility**: Graph connectivity, no degenerate vertices, valid face winding.
2. **Local Flat-Foldability (Kawasaki's Theorem)**:
   For an interior vertex of degree $2n$:
   $$\theta_1 - \theta_2 + \theta_3 - \dots - \theta_{2n} = 0 \iff \sum_{i=1}^n \theta_{2i-1} = \sum_{i=1}^n \theta_{2i} = \pi$$
3. **Crease Assignment (Maekawa's Theorem)**:
   At any flat-foldable interior vertex:
   $$|M - V| = \pm 2$$
4. **Facet Non-Degeneracy**: Minimum edge length $L_{\min} > 0.5\,\text{mm}$ and positive facet area $A_f > \epsilon$.
5. **Aspect Ratio & Packaging Bounds**: Bounding box ratios $L_x / L_y$ and packaging volume ratio $V_{\text{folded}} / V_{\text{flat}}$.

### Electromagnetic Formulation (Surface EFIE / MoM)
The internal RF solver implements a surface Electric Field Integral Equation (EFIE):
$$\hat{\mathbf{n}} \times \left[ \mathbf{E}^{\text{inc}}(\mathbf{r}) - j\omega\mu \int_S \mathbf{J}_s(\mathbf{r}') G(\mathbf{r}, \mathbf{r}') dS' - \frac{1}{j\omega\varepsilon} \nabla \int_S (\nabla' \cdot \mathbf{J}_s(\mathbf{r}')) G(\mathbf{r}, \mathbf{r}') dS' \right] = 0$$

- **Discretization**: The antenna solver discretizes open polylines into wire segments. The current panel-to-wire conversion sorts vertices along a spatial axis and is not a physical conductor-path model.
- **Basis Functions**: Galerkin rooftop basis functions defined on interior nodes between consecutive segments approximate wire currents $\mathbf{I}$, using a reduced thin-wire kernel with exact asinh static part and Gauss-Legendre quadrature.
- **Impedance Matrix**: Matrix elements $Z_{mn} = \langle \mathbf{f}_m, \mathcal{L}(\mathbf{f}_n) \rangle$ represent mutual electromagnetic coupling.
- **Port Excitation**: Delta-gap voltage feed $V$ applied across the designated interior node between segments $p-1$ and $p$.
- **Current Solution**: Direct linear solve $\mathbf{I} = \mathbf{Z}^{-1} \mathbf{V}$ yields complex currents at each frequency sample.

---

## Known Limitations

1. **Conductor Topology & Pathing**: The geometric converter sorts conductor vertices along a spatial axis to build an open wire polyline; it does not preserve a physical conductor path or routing topology through continuous origami folding.
2. **Branching & Closed Loops**: The antenna solver strictly requires a single unbranched open polyline. Branched wire junctions and closed conductive loops or rings are not supported.
3. **Absence of RWG Surface Basis**: The antenna solver implements a Galerkin rooftop thin-wire basis; it does not implement an RWG (Rao-Wilton-Glisson) surface triangular basis function formulation.
4. **Substrate & Dielectric Formulation**: Dielectric loading is modeled via an approximate effective-permittivity scalar scaling ($\varepsilon_{\text{eff}} \approx (\varepsilon_r + 1)/2$), not a full layered-media Green's function or dielectric volume/surface integral equation. Substrate-backed patch antennas are not supported in the antenna solver.
5. **Antenna Far-Field Radiation**:
   - *Directivity & Peak Direction*: Directivity $D$ (dBi) agrees with NEC2 within 0.006 dB (gate 0.5 dB) and peak direction within 0.00° (gate 5.0°, agreement limited by the angular grid) across all evaluated angles (0°, 30°, 60°, 90°, 120°) for $N=40$ and $N=80$, with the scope "wire V-dipole, free space, computed by `scripts/farfield_validation.py`".
   - *Radiation Efficiency & Gain Anomaly (`scripts/efficiency_diagnostic.py`)*: Radiation efficiency and gain are validated against NEC2 at 0 degrees only; at 30, 60, 90, 120 degrees the NEC2 reference is not reliable for efficiency, so they are unvalidated. Radiation efficiency against NEC2 appears to drop to 96.4% (60°), 92.5%–93.0% (90°), and 88.7%–91.5% (120°) in NEC2 for copper. However, diagnostic evaluation demonstrates this is an internal NEC2 sharp-junction power-balance error: on a perfectly lossless (PEC) conductor with zero resistance, NEC2 still loses 3.4% at 60°, 6.7%–7.2% at 90°, and 8.1%–10.8% at 120° ($P_{\text{rad}} < P_{\text{in}}$). Smoothing the bend ($K=9$ segments) restores NEC2 efficiency to 99.83% (lossless) and 99.54% (copper) at 90°, and 99.70% (lossless) and 99.24% (copper) at 120°. MoM preserves physical energy conservation (100.01%–100.03% on lossless wire, 99.5%–99.8% on copper) across all bend angles and smoothing levels. Because the sharp-junction NEC2 reference violates power conservation, efficiency and gain cannot be validated against it at bent angles.
   - *CLI and Web Studio*: Neither CLI nor Web app uses the MoM vector potential code in `scripts/farfield_validation.py`. The only far-field engine invoked is `MetasurfaceFarFieldEngine.calculate_bistatic_rcs` in `rf_origami/rf/metasurface/farfield.py`, an analytic aperture physical-optics stand-in for plane-wave metasurface RCS; its outputs strictly retain the `(Estimate - not validated)` badge.
   - *Unvalidated*: 3D radiation patterns for origami surface patches, half-power beamwidth (HPBW), and axial ratio remain unvalidated estimates.
6. **Input Resistance at Steep Bends**: While resonant frequency $f_r$ agrees with NEC2 within $1.02\%$ across all bend angles, input resistance $R_{\text{in}}$ at steep bend angles (90° and 120°) exceeds the 5% error threshold (5.08% and 6.72% at $N=80$). Status remains: $f_0$ validated at all angles, $R_{\text{in}}$ validated at 0°, 30°, 60°, not validated at 90° and 120° (strict xfails preserved).
   - *Convergence Analysis*: For $a = 0.5\text{ mm}$, $N=20 \to 40 \to 80$ shows $R_{\text{in}}$ error converging toward NEC2 ($7.51\% \to 6.69\% \to 5.08\%$ at 90°; $8.70\% \to 8.00\% \to 6.72\%$ at 120°). The claim of thin-wire kernel breakdown at $N=160$ is restricted to $a = 0.5\text{ mm}$ ($\Delta = 0.359\text{ mm} < a = 0.5\text{ mm}$, $\Delta/a = 0.72$), causing artificial delta-gap fringing capacitance that inflates $R_{\text{in}}$ error to $>20\%$. In contrast, at $a = 0.1\text{ mm}$ (where $\Delta/a \ge 3.59$ up to $N=160$), the 90°/120° error does not decrease with refinement and in fact grows at 120° ($8.06\%, 10.06\%, 11.24\%$ for $N = 40, 80, 160$), indicating a systematic solver difference rather than a discretization error.
   - *Controlled Numerical Isolation*: Quadrature order (outer 8 to 64) is identical to 4 decimal places. Adjacent non-collinear rooftop 2D coupling integrals match independent dense Gauss-Legendre quadrature to $<10^{-6}$ relative error (`test_adjacent_non_collinear_segment_interaction_matches_dense_quadrature`). Solver coordinate projections and $\mathrm{asinh}$ static singularity kernels are exact.
   - *Radius Sweep Experiment (`scripts/radius_sweep.py`)*: Controlled sweep across wire radii $a \in [0.5, 0.25, 0.1]\text{ mm}$ refuted the wire-cylinder overlap hypothesis. When $a$ is reduced to $0.1\text{ mm}$ (shrinking the overlap region by $5\times$), the $R_{\text{in}}$ error at $90^\circ$ and $120^\circ$ does not drop below 5%; for converged segment counts ($N=80, 160$), it persists at $5.7\%-7.0\%$ ($90^\circ$) and $10.1\%-11.2\%$ ($120^\circ$). In contrast, for straight dipoles ($0^\circ$), NEC2 and MoM agree within $0.18\%-0.24\%$ at $a=0.1\text{ mm}$ across $N \in [40, 80, 160]$.
   - *NEC2 Feed and Junction Sensitivity (`scripts/nec2_sensitivity.py`)*: Evaluated NEC2 modeling choices at $a = 0.5\text{ mm}$ ($N=40, 80$): feed on arm 1 vs arm 2 (0.00% difference), center feed on a single bent wire (not possible in NEC-2 as wire cards must be straight cylinders; 0.00%–0.11% difference at 0°), and extended thin-wire kernel EK (-0.13% to -0.69% at 0°–90°, -0.62% to -1.22% at 120°). The spread of NEC2 $R_{\text{in}}$ across these modeling options is small (<2% at both 90° and 120°), confirming the reference is stable against feed placement and kernel choice, but drifts about 5% with segment count at 120 degrees. MoM $R_{\text{in}}$ falls strictly outside the NEC2 spread at 90° and 120°. The hypothesis that feed/junction conventions explain the 5%–11% MoM gap remains an untested hypothesis unsupported by NEC2 sensitivity data.
   - *NEC2 Self-Convergence at 120°*: NEC2's own $R_{\text{in}}$ at $120^\circ$ drifts from $28.63\,\Omega$ ($N=40$) to $27.79\,\Omega$ ($N=80$) and $27.23\,\Omega$ ($N=160$), an internal drift of about 5% (4.89%). Consequently, the 5% validation gate at 120° cannot cleanly separate solver error from reference uncertainty.
   - MoM and NEC2 Rin agree within 0.17%-1.45% on smoothed bends (scripts/nec2_smooth_bend.py). The power-balance diagnostic (scripts/efficiency_diagnostic.py) shows NEC2's sharp junction is internally inconsistent (radiated power below input power on a lossless wire, up to 10.8%) while MoM conserves power, so NEC2's sharp-junction Rin is the more suspect value. This is indicative, not proven: the smoothed geometries are not identical to the sharp one (f0 shifts), MoM energy conservation shows self-consistency and not correctness, and the Rin gates at 90 and 120 degrees still fail.
7. **No Physical Measurements**: All results are computational. No physical prototypes have been fabricated or measured in an anechoic chamber.

---

## Future Work & Forward Roadmap

The future development roadmap addresses these known limitations to advance the platform from a research prototype toward experimental maturity:

1. **Input Resistance ($R_{\text{in}}$) Convergence**: Refine the apex singularity treatment and charge accumulation modeling at sharp bend angles ($90^\circ$ and $120^\circ$) to achieve $<5\%$ $R_{\text{in}}$ error across the entire folding range.
2. **Topological Conductor Path Preservation**: Implement graph-aware trace routing that preserves continuous physical conductor paths through arbitrary 3D folding sequences.
3. **Junction & Loop Formulations**: Develop multi-wire junction basis functions and closed loop formulations to enable folded loop antennas, spiral antennas, and multi-arm structures.
4. **Substrate-Aware Surface MoM**: Formulate RWG surface basis functions and layered-media Green's functions for origami patch antennas on flexible dielectric substrates (e.g., Kapton, PET).
5. **Antenna Far-Field Integral**: Implement near-to-far field transformations from solved rooftop and RWG current distributions to compute 3D radiation patterns, realized gain, and axial ratio.
6. **Physical Fabrication & Chamber Measurement Campaign**: Fabricate physical prototypes and validate simulated return loss and radiation patterns against vector network analyzer (VNA) and anechoic chamber measurements.

```
+-------------------------------------------------------------------------------+
|                             FORWARD ROADMAP                                   |
|                                                                               |
|  [Phase 5: Advanced EM Solver]  -->  [Phase 6: Multi-Physics Mechanics]       |
|                 |                                      |                      |
|                 v                                      v                      |
|  [Phase 7: Inverse Optimization] --> [Phase 8: Digital Fabrication & Hardware]|
+-------------------------------------------------------------------------------+
```

---

### Phase 5: Rigorous EM Solver Validation & Advanced Integral Equations

The current MoM solver is an in-house proof-of-concept labeled as *Experimental / Not validated*. Phase 5 focuses on transforming it into a high-precision, validated electromagnetic engine:

1. **Analytical Canonical Benchmarks**:
   - Implement automated regression benchmarks against classical closed-form antenna solutions:
     - Infinitesimal and center-fed half-wave dipoles ($R_{\text{in}} \approx 73.13\,\Omega$).
     - Thin wire loops and foldable resonant quadrifilar helices.
     - Rectangular microstrip patch antennas on finite substrates.
2. **Singularity Extraction & Numerical Quadrature**:
   - Enhance the Green's function integration with analytical singularity subtraction (e.g. Duffy transform or Wilton analytical formulas for $1/R$ and $\nabla(1/R)$ kernels on planar triangles) to eliminate near-field evaluation errors.
3. **Substrate & Dielectric Modeling**:
   - **Surface Impedance Boundary Condition (SIBC)**: Model conductor surface roughness and finite conductivity losses.
   - **Thin-Sheet Approximation**: Model thin dielectric substrates ($\varepsilon_r, \tan\delta$) as equivalent surface polarization currents without requiring full volumetric 3D discretization.
   - **Poggio-Miller-Chang-Harrington-Wu-Tsai (PMCHWT)** formulation for penetrable dielectric bodies.
4. **Far-Field Radiation & Directivity Engine**:
   - Integrate far-field radiation integrals to compute:
     - 3D Radiation Patterns $U(\theta, \phi)$ and 2D principal plane cuts ($E$-plane and $H$-plane).
     - Total radiated power: $P_{\text{rad}} = \iint U(\theta, \phi) \sin\theta d\theta d\phi$.
     - Directivity: $D(\theta, \phi) = \frac{4\pi U(\theta, \phi)}{P_{\text{rad}}}$.
     - Realized Gain: $G(\theta, \phi) = \eta_{\text{rad}} D(\theta, \phi)$.
     - Axial ratio (AR) for circularly polarized origami antennas.
5. **Computational Acceleration for Large Meshes**:
   - **Adaptive Cross Approximation (ACA)** or **Fast Multipole Method (FMM)** for $O(N \log N)$ impedance matrix evaluation, allowing meshes with $> 5000$ unknowns to solve in seconds.
   - Multi-threaded matrix fill via NumPy vectorization and OpenMP/multiprocessing.

---

### Phase 6: Multi-Physics Kinematics & Thick-Panel Mechanics

Real origami structures cannot always be modeled as zero-thickness rigid surfaces. Phase 6 introduces physical realism:

1. **Thick-Panel Origami Kinematics**:
   - **Axis-Shift & Chamfer Models**: Real substrates have thickness $h \in [0.1\,\text{mm}, 3.0\,\text{mm}]$. Implement axis-shift hinge offset kinematics to prevent facet collisions when folding thick RF substrates.
   - Kinematic volume preservation during folding.
2. **Compliant Hinge & Crease Mechanics**:
   - Torsional spring model for fold lines: $M_i = k_i (\theta_i - \theta_{0,i})$.
   - Strain energy evaluation: $E_{\text{strain}} = \frac{1}{2} \sum k_i (\Delta \theta_i)^2$.
   - Energy minimization to determine natural equilibrium folding trajectories and deployment forces.
3. **Rigorous Continuous Self-Penetration Detection**:
   - Bounding Volume Hierarchies (BVH / AABB trees) to detect panel-panel penetrations and facet contact collisions during dynamic folding animations.
   - Allowable folding limits $\theta_{\max}$ computed automatically per candidate.

---

### Phase 7: Autonomous Multi-Objective Inverse Optimization

Currently, the user generates candidates via forward sampling (LHS) and selects designs manually. Phase 7 implements automated inverse synthesis:

1. **Inverse RF Specification Engine**:
   - Allow the user to specify RF engineering targets:
     - Target resonant frequency: $f_0 = 2.45\,\text{GHz} \pm 10\,\text{MHz}$.
     - Target frequency tuning range: $\Delta f = 800\,\text{MHz}$ between flat and folded states.
     - Maximum return loss: $|S_{11}| < -15\,\text{dB}$ across operational band.
     - Maximum packaged volume: $V_{\text{folded}} \le 50 \times 50 \times 10\,\text{mm}^3$.
2. **Multi-Objective Evolutionary Algorithms (NSGA-II & Bayesian Optimization)**:
   - Formulate Pareto optimization across competing objectives:
     $$\min_{\mathbf{p}} \mathcal{J}(\mathbf{p}) = \begin{bmatrix} |S_{11}(f_0)| \\ -G_{\text{peak}} \\ -\text{Bandwidth} \\ V_{\text{folded}} \end{bmatrix}$$
   - Surrogate-assisted Gaussian Process modeling to predict RF performance with minimal solver invocations.
3. **Active Origami & Reconfigurable Surface Synthesis**:
   - Automatic placement of active RF components (PIN diodes, varactors, RF MEMS switches) across crease boundaries for hybrid mechanical/electronic tuning.

---

### Phase 8: Digital Fabrication & Hardware Prototyping Pipeline

Bridge computational design with physical laboratory hardware fabrication:

1. **Multi-Layer CAD & Manufacturing Blueprint Exports**:
   - **Gerber (RS-274X) & DXF Exports**: Separate layers for:
     - Top conductor traces (copper etching / screen-printing).
     - Substrate contour cutting.
     - Mountain fold crease score lines (half-depth kiss cuts).
     - Valley fold crease score lines (perforated / reverse cuts).
     - Ground plane metallization.
2. **Standardized 3D Model Formats**:
   - Robust export to `.stl`, `.obj`, and `.fold` (JSON schema) for 3D printing and digital archival.
3. **Fabrication Tolerancing & Crease Fatigue Analysis**:
   - Keep-out distance checks ($w_{\text{clearance}}$) between conductor boundaries and fold axes to prevent copper fatigue cracking over repeated folding cycles.
   - Design-for-manufacturability (DFM) verification reports.

---

## Verification & Test Suite

The codebase enforces automated testing across all modules.

Run the test suite:
```powershell
python -m pytest tests -v
```

### Current Test Coverage (149 Tests: 147 Passed, 2 xfailed)

The suite covers geometry, patterns, kinematics, RF calculations, absorber models, optimization, fabrication, web services, and validation integrity:

- **147 Passed**: Unit tests, numerical regression checks, and passing benchmarks (including 0°, 30°, and 60° V-dipole NEC2 comparisons and adjacent non-collinear 2D quadrature integrity).
- **2 xfailed**: Strict $R_{\text{in}}$ acceptance gates on the wire V-dipole at 90° and 120° bend angles (`test_nec2_v_dipole_fold_sweep_strict_gates[90]` and `[120]`), where $R_{\text{in}}$ error exceeds the 5% gate. Marked as strict expected failures to immediately flag regressions.
- **Physical Acceptance**: Passing unit tests do not establish physical antenna accuracy. Physical acceptance metrics remain visible in the generated [validation report](docs/validation_report.md).

### Reproducibility & Commands

Run the complete validation workflow locally:

```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Run the test suite (147 passed, 2 xfailed expected)
python -m pytest tests -v

# 3. Generate the Markdown and JSON validation report
python -m rf_origami.rf.solver.validation_report

# 4. Strict gate check (exits 1 while 90° and 120° Rin gates fail)
python -m rf_origami.rf.solver.validation_report --strict
```

> **Note on Reference Data**: The independent NEC2 reference dataset (`data/validation/nec2_reference.json`) is generated by `generate_nec2_reference.py` using `necpp` (`pip install necpp`, which requires a C compiler and may not install cleanly on Windows). The committed JSON file must never be edited by hand.

---

## Technical Citations & Foundational References

1. **Origami Mathematics & Kinematics**:
   - Miura, K. (1985). *Method of Packaging and Deployment of Large Membranes in Space*. Institute of Space and Astronautical Science Report.
   - Demaine, E. D., & O'Rourke, J. (2007). *Geometric Folding Algorithms: Linkages, Origami, Polyhedra*. Cambridge University Press.
   - Tachi, T. (2010). *Geometric Consideration for Designing Rigid-Foldable Structures*. Proceedings of the IASS Symposium.
2. **Electromagnetic Surface Integral Equations**:
   - Rao, S. M., Wilton, D. R., & Glisson, A. W. (1982). *Electromagnetic Scattering by Surfaces of Arbitrary Shape*. IEEE Transactions on Antennas and Propagation, 30(3), 409–418.
   - Harrington, R. F. (1993). *Field Computation by Moment Methods*. Wiley-IEEE Press.
   - Gibson, W. C. (2021). *The Method of Moments in Electromagnetics* (3rd ed.). CRC Press.
3. **Origami Antennas & Reconfigurable Electromagnetic Surfaces**:
   - Fuchi, K., Tang, J., Crowgey, B., et al. (2012). *Origami-inspired reconfigurable antennas*. IEEE Antennas and Wireless Propagation Letters.
   - Shah, S. I. H., & Lim, S. (2017). *A Review on Origami-Inspired Reconfigurable Antennas*. IEEE Transactions on Antennas and Propagation.
   - Liu, X., Yao, S., & Georgakopoulos, S. V. (2014). *Reconfigurable Foldable Origami Helical Antenna*. IEEE Antennas and Wireless Propagation Letters.

---

## License

This project is developed for computational origami and electromagnetic engineering research. See individual source files for license and copyright declarations.
