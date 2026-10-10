# RF Origami Design Studio

**A First-Principles Computational Origami & Standalone Electromagnetic (RF) Engineering Platform**

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-63%20passed-success)](tests/)
[![Architecture](https://img.shields.io/badge/Architecture-100%25%20Standalone-brightgreen)](#core-architecture-philosophy)
[![Status](https://img.shields.io/badge/Status-Active%20Development-orange)](#what-we-have-built-so-far)

---

## Table of Contents

1. [Executive Summary & Core Philosophy](#executive-summary--core-philosophy)
2. [Current Progress & What Has Been Done Till Now](#current-progress--what-has-been-done-till-now)
   - [Phase 1: Computational Origami & Kinematic Engine](#phase-1-computational-origami--kinematic-engine)
   - [Phase 2: Generative Design & Exploration Pipeline](#phase-2-generative-design--exploration-pipeline)
   - [Phase 3: Standalone In-House RF & Electromagnetic Solver](#phase-3-standalone-in-house-rf--electromagnetic-solver)
   - [Phase 4: Design Studio Web Interface & Interactive Visualizer](#phase-4-design-studio-web-interface--interactive-visualizer)
3. [Project Directory Structure](#project-directory-structure)
4. [Quickstart & Usage Guide](#quickstart--usage-guide)
5. [In-Depth Technical Architecture](#in-depth-technical-architecture)
   - [Origami Geometry to RF Discretization Pipeline](#origami-geometry-to-rf-discretization-pipeline)
   - [Mathematical Validity Filtering](#mathematical-validity-filtering)
   - [Electromagnetic Formulation (Surface EFIE / MoM)](#electromagnetic-formulation-surface-efie--mom)
6. [Detailed Forward Roadmap (What We Are Going to Do Ahead)](#detailed-forward-roadmap-what-we-are-going-to-do-ahead)
   - [Phase 5: Rigorous EM Solver Validation & Advanced Integral Equations](#phase-5-rigorous-em-solver-validation--advanced-integral-equations)
   - [Phase 6: Multi-Physics Kinematics & Thick-Panel Mechanics](#phase-6-multi-physics-kinematics--thick-panel-mechanics)
   - [Phase 7: Autonomous Multi-Objective Inverse Optimization](#phase-7-autonomous-multi-objective-inverse-optimization)
   - [Phase 8: Digital Fabrication & Hardware Prototyping Pipeline](#phase-8-digital-fabrication--hardware-prototyping-pipeline)
7. [Verification & Test Suite](#verification--test-suite)

---

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

The project has advanced through four complete developmental stages, culminating in a fully functional generative exploration suite with 63 passing unit tests and an interactive web studio.

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
- **Method of Moments (MoM) EFIE Solver (`rf/solver/mom_solver.py`)**:
  - First-principles surface integral equation solver based on the Electric Field Integral Equation (EFIE).
  - Rao-Wilton-Glisson (RWG) inspired edge-element basis discretization.
  - Complex impedance matrix $[Z]$ assembly using free-space Green's function:
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
pip install numpy matplotlib pytest
```

### 2. Run Automated Test Suite
Verify that all 63 unit tests pass across the entire mathematics, kinematics, and RF solver pipeline:
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
             | Basis Function Discretization (RWG edge pairs)
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

- **Discretization**: Conductive surfaces are represented by triangular facet pairs sharing internal edges.
- **Basis Functions**: Rao-Wilton-Glisson (RWG) inspired vector basis functions represent surface currents $\mathbf{J}_s$.
- **Impedance Matrix**: Matrix elements $Z_{mn} = \langle \mathbf{f}_m, \mathcal{L}(\mathbf{f}_n) \rangle$ represent mutual electromagnetic coupling.
- **Port Excitation**: Delta-gap voltage feed $V_m$ applied across designated antenna port edges.
- **Current Solution**: Direct linear solve $\mathbf{I} = \mathbf{Z}^{-1} \mathbf{V}$ yields complex surface currents at each frequency sample.

---

## Detailed Forward Roadmap (What We Are Going to Do Ahead)

While the foundations, kinematics, generative explorer, and initial MoM solver are functional and tested, the next development phases will transform this project into a comprehensive, publication-grade, production-ready research platform.

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

The codebase enforces strict unit testing across all modules.

Run the test suite:
```powershell
pytest tests -v
```

### Current Test Coverage (63 Tests Passing)

| Test Module | Coverage & Verified Behaviors | Passing |
| :--- | :--- | :---: |
| `test_geometry.py` | Vector3D algebra, Rodrigues transforms, Euler angles, Newell normal, polygon area, coplanarity | 8 / 8 |
| `test_crease_pattern.py` | Graph creation, edge lookups, Kawasaki theorem, Maekawa theorem, FOLD JSON serialization | 5 / 5 |
| `test_mesh.py` | FoldedMesh creation, triangulation, bounding boxes, principal dimensions, surface areas | 2 / 2 |
| `test_parameters.py` | Parameter type checks, range validation, default assignments, grid sweeps, Monte Carlo sampling | 5 / 5 |
| `test_kinematics.py` | Miura-ori kinematics, fold angle propagation, 3D vertex positions, edge length conservation | 3 / 3 |
| `test_patterns.py` | Miura-Ori, Yoshimura, Waterbomb, Degree-4 Vertex pattern generators and parameter schemas | 5 / 5 |
| `test_generator.py` | DesignSpace definition, Latin Hypercube Sampling, constraint filtering, candidate batch generation | 5 / 5 |
| `test_rf_materials.py` | Conductor and dielectric properties, surface resistance, permittivity, loss tangent | 4 / 4 |
| `test_rf_geometry.py` | FoldedMesh to RFTriangleMesh conversion, facet material tagging, boundary extraction | 3 / 3 |
| `test_rf_ports.py` | LumpedPort creation, delta-gap port definition, impedance assignment, port coordinate lookups | 3 / 3 |
| `test_rf_metrics.py` | Resonant frequency detection, S11 minimum search, -10 dB bandwidth, VSWR, Q-factor | 4 / 4 |
| `test_em_solver.py` | MoM EFIE impedance matrix assembly, LU decomposition, current solve, Zin/S11 calculation | 4 / 4 |
| `test_visualization.py` | 2D crease pattern Matplotlib generation, 3D mesh Matplotlib plotting, procedural SVG exports | 3 / 3 |
| `test_web.py` | Web service endpoints (`/api/explore`, `/api/generate`, `/api/fold`, `/api/rf/simulate`, etc.) | 9 / 9 |
| **Total** | **Full verification across entire computational stack** | **63 / 63** |

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
