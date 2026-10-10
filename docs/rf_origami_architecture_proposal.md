# RF Origami Design Generator: Technical Architecture & System Proposal

**Project Name**: RF Origami  
**Purpose**: A self-contained computational design, kinematic simulation, and electromagnetic modeling environment for exploring and optimizing origami-based RF/antenna structures.  
**Guiding Constraint**: No runtime dependencies on commercial CAD/EM software (HFSS, CST, Rhino/Grasshopper) or external black-box origami engines. Computational solvers and kinematic engines are built natively from first principles.

---

## A. What Has Already Been Implemented?

Based on inspection of the codebase:
1. **`rf_origami/core/geometry.py`**:
   - `Vector3D`: Immutable 3D vector algebra (`+`, `-`, `*`, `/`, `dot`, `cross`, `norm`, `normalize`, `angle_to`).
   - `Point3D`: 3D position vector (`distance_to`, `vector_to`, `translate`).
   - Rigid Transformations: Rodrigues' rotation formula (`rotation_matrix_axis_angle`), Tait-Bryan Euler transforms (`rotation_matrix_euler`), $4 \times 4$ homogeneous SE(3) matrices (`create_affine_matrix`), and vectorized point transformations (`transform_points`).
   - Polygon Analysis: Newell's method for robust 3D normal evaluation (`polygon_normal`), projected cross-product surface area (`polygon_area`), geometric mean centroid (`polygon_centroid`), and plane coplanarity testing (`is_coplanar`).
2. **`rf_origami/core/crease_pattern.py`**:
   - `CreaseType`: Strongly typed enum (`BOUNDARY`, `MOUNTAIN`, `VALLEY`, `FACET`).
   - `Crease`: Canonical undirected edge representation `(u, v)` with fold angle $\theta$ and rest length.
   - `Face`: Polygonal facet indexing with material tag and RF properties dictionary.
   - `CreasePattern`: 2D/3D topological graph, vertex/crease/face insertion, edge adjacency, and bounding box.
   - Flat-Foldability Verification: Kawasaki's Theorem (alternating sector angle sums $= 180^\circ$) and Maekawa's Theorem ($|M - V| = \pm 2$).
   - FOLD-compatible dictionary serialization (`to_dict` / `from_dict`).
3. **`rf_origami/core/mesh.py`**:
   - `FoldedMesh`: 3D folded surface mesh container, facet normal calculation, bounding box, principal dimensions ($L_x, L_y, L_z$), total and per-material surface area.
   - Fan triangulation (`to_triangulated()`) for triangular CAD and simulation exports.
4. **`rf_origami/core/parameters.py`**:
   - `Parameter`: Strongly typed parameter (`FLOAT`, `INT`, `BOOL`, `STRING`) with bounds validation, units, step sizes, and uniform sampling.
   - `ParameterSet`: Parameter dictionary/attribute container with JSON serialization, Cartesian grid sweeps (`generate_grid_sweep`), and random Monte Carlo sampling (`generate_random_samples`).
5. **Test Suite (`tests/`)**:
   - 19 automated unit tests across all four core modules, executing with 100% pass rate under Python 3.12 (`pytest`).

---

## B. Which Existing Stage 1 Components Should Remain?

1. **`geometry.py`**: Kept intact. All vector algebra, Rodrigues' rotations, Newell's normal, affine transforms, and polygon area calculations form the mathematical bedrock for panel kinematics and RWG surface discretization.
2. **`CreaseType` and `CreasePattern` graph topology**: Kept intact. Acts as the 2D reference blueprint (rest state) and topological connectivity graph.
3. **`Parameter` and `ParameterSet`**: Kept intact. Directly utilized by pattern generators, kinematic solvers, and design-space exploration sweeps.
4. **`FoldedMesh`**: Kept as a foundational 3D geometric mesh representation, to be extended by conformal electromagnetic meshes.
5. **Automated Test Infrastructure (`tests/`)**: Kept and expanded as new modules are introduced.

---

## C. Which Existing Abstractions Need to Be Changed or Expanded?

1. **Decouple Blueprint CreasePattern from Dynamic Folding State**:
   - *Current limitation*: `Crease.fold_angle` is stored directly on the crease pattern, implying a single static folded state.
   - *Required change*: `CreasePattern` represents the reference 2D blueprint. Dynamic folding state is factored into a `KinematicState` (vector of fold angles $\boldsymbol{\theta}$ or a folding parameter $\rho \in [0, 1]$). The same crease pattern instance can thus generate any continuous deformation state without state mutation.
2. **Facet Representation Beyond a Single `material_tag`**:
   - *Current limitation*: `Face` has only a single string tag (e.g. `'substrate'`).
   - *Required change*: In RF origami, a facet consists of multiple physical layers:
     - Dielectric substrate backing (thickness $h$, permittivity $\varepsilon_r$, loss tangent $\tan\delta$).
     - Conductor metallization (patches, dipole arms, loop lines, ground planes) in local facet coordinates.
     - Hinge setbacks (keep-out clearance so conductors do not fatigue or short across creases unless explicitly bridged).
3. **Introduction of RF Ports and Boundary Excitations**:
   - *Current limitation*: No concept of electrical excitation or port definition exists.
   - *Required change*: Introduce an `RFPort` abstraction (delta-gap feed across triangle edges, microstrip feed, or lumped element RLC/diode bridges).
4. **Conformal Meshing for Electromagnetic Solvers**:
   - *Current limitation*: `FoldedMesh.to_triangulated()` performs naive fan triangulation from vertex 0, which can yield ill-conditioned sliver triangles unsuitable for integral equation solvers.
   - *Required change*: Introduce an `EMMesh` / `RWGMesh` generator that satisfies Delaunay edge length constraints ($h \le \lambda / 10$) and computes shared-edge connectivity for Rao-Wilton-Glisson basis functions.

---

## D. Mathematical Representation of an Origami Structure

An origami structure is modeled as an **isometric cell complex deformation**:
1. **Reference Complex (Flat State)**:
   $$\mathcal{C} = (\mathcal{V}, \mathcal{E}, \mathcal{F})$$
   where $\mathcal{V} \subset \mathbb{R}^2$ are flat coordinates, $\mathcal{E}$ are creases, and $\mathcal{F}$ are rigid planar facets.
2. **Configuration Space $\mathcal{Q}$**:
   The folded state is an isometric immersion:
   $$\phi: \mathcal{C} \to \mathbb{R}^3$$
   preserving geodesic distance (edge length) on each panel:
   $$\|\phi(\mathbf{v}_i) - \phi(\mathbf{v}_j)\| = \|\mathbf{v}_i - \mathbf{v}_j\| \quad \forall (i, j) \in \mathcal{E}$$
3. **Rigid Panel Kinematics**:
   For each panel $f \in \mathcal{F}$, the mapping is a rigid body transformation:
   $$\phi|_f(\mathbf{x}) = \mathbf{R}_f \mathbf{x} + \mathbf{t}_f, \quad \mathbf{R}_f \in \mathrm{SO}(3), \mathbf{t}_f \in \mathbb{R}^3$$
4. **Hinge Compatibility & Loop Closure**:
   Across any interior crease $e = f_a \cap f_b$, the dihedral angle $\theta_e$ satisfies:
   $$\mathbf{R}_b = \mathbf{R}_a \mathbf{R}_{\text{axis}}(\hat{\mathbf{u}}_e, \theta_e)$$
   For any closed loop of $k$ panels around an interior vertex, the cumulative rotation satisfies:
   $$\prod_{m=1}^k \mathbf{R}(e_m, \theta_m) = \mathbf{I}_{3 \times 3}$$

---

## E. Representation of Geometry & Kinematics

- **`CreasePattern`**: Stores 2D reference coordinates $\mathbf{U} \in \mathbb{R}^{N \times 2}$, edge list with fold types $\tau \in \{B, M, V, F\}$, and panel topology.
- **`Panel`**: Local 2D coordinate system $(u, v)$, boundary polygon vertices, internal conductive trace polygons, and dielectric layer properties.
- **`Hinge`**: Connects adjacent panels $(f_L, f_R)$ with fold angle bounds $[\theta_{\min}, \theta_{\max}]$, axis vector $\hat{\mathbf{u}}$, and keep-out clearance $w_k$.
- **`KinematicState`**: State vector $\boldsymbol{\theta} \in \mathbb{R}^{|\mathcal{E}|}$ or 1-DOF parameter $\rho \in [0, 1]$ mapping to the deformation trajectory.
- **`FoldedGeometry`**: Evaluated 3D assembly holding panel transformations $\mathbf{T}_f \in \mathrm{SE}(3)$, 3D vertex positions $\mathbf{X} \in \mathbb{R}^{N \times 3}$, and facet normal vectors $\hat{\mathbf{n}}_f$.

---

## F. Representation of RF-Specific Geometry

```text
+--------------------------------------------------------------+
|                        TOP CONDUCTOR                         |
|   (Copper patches, dipole traces, microstrip lines, ports)   |
+--------------------------------------------------------------+
|                     DIELECTRIC SUBSTRATE                     |
|           (Thickness h, Permittivity εr, Loss tanδ)          |
+--------------------------------------------------------------+
|                       BOTTOM CONDUCTOR                       |
|               (Ground plane, FSS, reflector)                 |
+--------------------------------------------------------------+
```

1. **`ConductorRegion`**: 2D polygons on panel surfaces.
   - Material: Electrical conductivity $\sigma$ (e.g. Copper: $5.8 \times 10^7 \, \mathrm{S/m}$) or PEC approximation.
   - Surface resistance: $R_s = \sqrt{\frac{\pi f \mu}{\sigma}}$.
2. **`DielectricSubstrate`**:
   - Substrate thickness $h$ ($0.05 \, \mathrm{mm} - 1.6 \, \mathrm{mm}$).
   - Relative permittivity $\varepsilon_r$, loss tangent $\tan\delta$, permeability $\mu_r = 1.0$.
3. **`SubstrateThicknessKinematics`**:
   - Zero-thickness approximation for thin origami films ($h < 0.05 \lambda$).
   - Kinematic axis-shift and chamfer models for thick origami panels.
4. **`HingeClearance` (Crease Keep-Out & Flexible Interconnects)**:
   - Conductor polygons automatically offset by clearance gap $g_{\text{hinge}}$ from fold lines to prevent physical cracking.
   - Explicit `FlexibleBridge` conductors for continuous electrical paths spanning across hinges.
5. **`RFPort`**:
   - `DeltaGapPort`: Infinitesimal voltage gap across two conductive vertices/edges with characteristic impedance $Z_0$ (typically $50 \, \Omega$).
   - `CoaxialProbePort`: Feed pin traversing substrate from ground to radiator.
   - `LumpedElement`: Discrete $R, L, C$, or diode switch mounted across panel gaps.

---

## G. Conversion from Folded Geometry to Electromagnetic Computational Model

The conversion pipeline operates without CAD dependencies:
1. **Panel Surface Discretization**:
   Conductor polygons on each panel are triangulated into a quality planar mesh in local panel coordinates using constrained Delaunay triangulation.
2. **Kinematic Rigid Transform**:
   Local mesh vertices $\mathbf{u}_i$ are transformed into global 3D space:
   $$\mathbf{x}_i = \mathbf{R}_f \begin{bmatrix} \mathbf{u}_i \\ 0 \end{bmatrix} + \mathbf{t}_f$$
3. **RWG Basis Function Construction**:
   - Identify all interior shared edges between pairs of conductive triangles $(T_m^+, T_m^-)$.
   - Each interior edge defines a **Rao-Wilton-Glisson (RWG)** basis function:
     $$\mathbf{f}_m(\mathbf{r}) = \begin{cases} \frac{\ell_m}{2 A_m^+} (\mathbf{r} - \mathbf{v}_m^+), & \mathbf{r} \in T_m^+ \\ \frac{\ell_m}{2 A_m^-} (\mathbf{v}_m^- - \mathbf{r}), & \mathbf{r} \in T_m^- \\ 0, & \text{otherwise} \end{cases}$$
   - Divergence of RWG basis function yields the surface charge density: $\nabla \cdot \mathbf{f}_m = \pm \frac{\ell_m}{A_m^\pm}$.
4. **Port Node Identification**:
   Locate the specific edge corresponding to the `RFPort` and assign its excitation index $p$ in the excitation vector $\mathbf{V}$.

---

## H. Electromagnetic Solver Approach Comparison & Selection

### Comprehensive Solver Comparison

| Solver Method | Formulation & Equations | Strengths for Origami RF | Limitations / Drawbacks | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Method of Moments (MoM) — Surface EFIE** | Surface Integral Equation discretizing electric current $\mathbf{J}_s$ with RWG basis functions. Discretizes only conductor boundaries. Green's function in free space: $G(\mathbf{r}, \mathbf{r}') = \frac{e^{-jkR}}{4\pi R}$. | **Best fit for open radiating structures**. Only discretizes the 2D surface of conductors, NOT the surrounding 3D air box. No absorbing boundaries (PML) needed. No grid staircasing during continuous folding. Direct input impedance $Z_{\text{in}} = V/I$. | Dense impedance matrix $\mathbf{Z} \in \mathbb{C}^{N_b \times N_b}$. Matrix fill is $O(N_b^2)$ with singular kernel integration. (For $N_b < 2000$, direct LU solve in NumPy/SciPy is fast and accurate). | **SELECTED: Primary Surface Solver (Stage 5B)** |
| **Thin-Wire MoM (Pocklington / Hallén)** | 1D integral equation for thin wire segments using triangle basis functions. | **Extremely fast** ($< 0.1 \, \mathrm{s}$ per frequency). Ideal for foldable wire antennas, origami dipole/loop arrays, and conductive traces along creases. Low implementation complexity. | Limited to thin wire/trace structures ($a \ll \lambda$). Cannot model broad continuous patch surfaces directly without wire grids. | **SELECTED: Initial Fast Engine (Stage 5A)** |
| **Finite-Difference Time-Domain (FDTD)** | Explicit time-stepping of Maxwell's curl equations on 3D Yee grid. | Broadband response from a single Gaussian pulse; easily handles arbitrary inhomogeneous substrates. | Requires discretizing entire 3D air volume. Slanted/folded panels suffer severe **Cartesian staircasing errors**. Requires writing complex CPML absorbing boundaries from scratch. | *Deferred to future advanced stage* |
| **Finite Element Method (FEM)** | Vector Helmholtz wave equation on volumetric tetrahedral mesh. | Handles arbitrary 3D inhomogeneous dielectrics and cavities. | Highest implementation complexity: requires 3D Delaunay volumetric meshing of empty air box, Nédélec vector elements, and radiation boundary conditions. | *Deferred to future advanced stage* |
| **Transmission-Line / Cavity Models** | Analytical equivalent circuits. | Instantaneous ($< 1 \, \mathrm{ms}$). | Valid only for standard planar rectangular patches. Inapplicable to complex 3D folded deformation geometry. | *Benchmark comparison only* |

### Final Solver Architecture Decision:
1. **Stage 5A: Thin-Wire / Strip Method of Moments (Pocklington's Equation)**:
   - Implemented first as a rapid, mathematically rigorous proof-of-concept for wire/trace origami antennas (foldable dipoles, Yagi-Uda arrays, helical origami, loop antennas).
   - Establishes the full solver pipeline, matrix fill, LU solve, input impedance $Z_{\text{in}}(f)$, and far-field radiation integration in concise, verifiable Python code.
2. **Stage 5B: Surface Method of Moments (Electric Field Integral Equation with RWG Basis Functions)**:
   - Full 3D surface MoM for arbitrary conductive panels, patch antennas, and ground planes.
   - Thin dielectric substrates modeled via Surface Impedance Boundary Conditions (SIBC) or thin-sheet approximations.

---

## I. Representation of Different Folding States

- **Continuous Kinematic Trajectory**:
  $$\rho \in [0, 1] \mapsto \boldsymbol{\theta}(\rho) = (\theta_1(\rho), \theta_2(\rho), \dots, \theta_M(\rho))$$
  - $\rho = 0.0$: Flat state (as manufactured).
  - $0 < \rho < 1.0$: Partially folded / intermediate deployment states.
  - $\rho = 1.0$: Fully folded / deployed operating state.
- **State-Agnostic Model Design**:
  The `OrigamiStructure` (crease topology + RF layer layout) is completely decoupled from `KinematicState`.
  An `RFAssembly` accepts `(structure, state)` and evaluates:
  $$\text{FoldedGeometry}(\rho) \implies \text{EMMesh}(\rho) \implies \mathbf{Z}(f, \rho) \implies S_{11}(f, \rho)$$
  This enables sweeping $\rho$ across $[0, 1]$ to compute dynamic frequency tuning curves, reconfigurable impedance matching, and radiation pattern steering during folding.

---

## J. Connecting RF Performance to Origami Parameters

The system couples parameters to RF observables via an explicit mathematical mapping:

```text
PARAMETRIC INPUT VECTOR p
  ├── Crease angles / folding factor ρ
  ├── Panel dimensions (a, b, γ)
  ├── Tessellation cell count (Nx, Ny)
  ├── Substrate properties (h, εr, tanδ)
  └── Conductor layout (L_patch, w_trace, feed_pos)
                          ↓
             KINEMATICS & 3D MESHING
  ├── Folded coordinates X_3D(p)
  ├── Surface RWG mesh M_EM(p)
  └── Port boundary definition
                          ↓
              ELECTROMAGNETIC SOLVER
  ├── Impedance matrix: Z_mn(f) = <f_m, L(f_n)>
  ├── Excitation vector: V_m
  └── Current distribution: I(f) = Z(f)^(-1) V
                          ↓
             EXTRACTED RF OBSERVABLES
  ├── Input Impedance:       Z_in(f) = V_port / I_port(f) = R_in + j X_in
  ├── Return Loss / S11:     S11(f) = (Z_in - Z0) / (Z_in + Z0)
  ├── Resonant Frequency:    f0 = arg min_f |S11(f)|
  ├── -10 dB Bandwidth:      BW = (f_high - f_low) / f0 * 100%
  ├── Radiated E-field:      E_far(θ, φ) via Green's function integration
  ├── Radiation Pattern:     Directivity D(θ, φ) = 4π U(θ, φ) / P_rad
  ├── Radiation Efficiency:  η_rad = P_rad / P_in
  └── Realized Gain:         G(θ, φ) = η_rad * D(θ, φ)
```

---

## K. Design-Space Exploration & Validity Filtering

To generate thousands of candidate structures without physical violations, a **Three-Tier Cascade Filter** is implemented:

```text
             Candidate Parameter Vector p
                          ↓
+----------------------------------------------------+
|  LEVEL 1: Algebraic & Kinematic Feasibility Filter  |
|  - Kawasaki & Maekawa flat-foldability conditions  |
|  - Degree-4 loop closure validity                  |
|  - Parameter bounds check [min_val, max_val]       |
+----------------------------------------------------+
         PASS ↓                   FAIL ✗ -> Discard
+----------------------------------------------------+
|  LEVEL 2: Geometric & Collision Avoidance Filter   |
|  - Panel self-intersection / penetration check     |
|  - Minimum facet clearance > 0                     |
|  - Hinge clearance violation check                 |
+----------------------------------------------------+
         PASS ↓                   FAIL ✗ -> Discard
+----------------------------------------------------+
|  LEVEL 3: RF Physical Integrity Filter             |
|  - Port terminals lie on distinct conductors       |
|  - Conductor path continuity to port               |
|  - Minimum fabrication feature width > w_min       |
+----------------------------------------------------+
         PASS ↓                   FAIL ✗ -> Discard
                 VALID CANDIDATE
           (Sent to EM Solver Pipeline)
```

---

## L. Optimization Architecture

The optimization framework operates on the verified parameter space:
1. **Objective Function Formulation**:
   Scalar or multi-objective Pareto optimization:
   $$\min_{\mathbf{p} \in \Omega} \mathcal{J}(\mathbf{p}) = \left[ |S_{11}(f_0)|, \quad -G(f_0), \quad -\text{BW}, \quad |f_0(\rho_{\max}) - f_0(\rho_{\min}) - \Delta f_{\text{target}}| \right]^T$$
2. **Algorithms**:
   - **Population-based Genetic Algorithms**: NSGA-II for multi-objective Pareto front generation (trading off folded compactness vs. antenna gain and bandwidth).
   - **Bayesian Optimization (BO-GP)**: Gaussian Process regression with Expected Improvement (EI) acquisition function for sample-efficient optimization when EM evaluations require higher compute.
   - **Local Gradient-Free Polish**: Nelder-Mead / Powell refinement on the most promising Pareto candidates.

---

## M. Reproducible Data Storage & Provenance

Every simulation run is stored immutably to guarantee 100% computational reproducibility:
1. **Design Manifest (JSON)**:
   - Canonical SHA-256 hash of design parameters and solver configuration.
   - Exact git commit hash, timestamp, random seed, and software version.
   - Scalar RF performance metrics ($f_0, S_{11,\min}, \text{BW}, G_{\max}, \eta_{\text{rad}}$).
2. **Numerical Data Archive (`.npz` / HDF5)**:
   - Folded 3D vertex coordinates $\mathbf{X}(\rho)$.
   - Conformal EM mesh (triangles, RWG basis functions).
   - Frequency sweep vector $\mathbf{f}$.
   - Complex surface current distribution $\mathbf{I}(f)$.
   - Complex input impedance $\mathbf{Z}_{\text{in}}(f)$ and $\mathbf{S}_{11}(f)$.
   - 3D far-field radiation spheres $(E_\theta(\theta, \phi), E_\phi(\theta, \phi))$.
3. **Deterministic Re-Execution**:
   A stored manifest can be re-run at any time using `rf_origami run --manifest <hash>.json`, guaranteeing identical results.

---

## N. Complete Module Architecture

```text
rf_origami/
│
├── core/                        # Foundation (Stage 1 - Complete)
│   ├── __init__.py
│   ├── geometry.py              # 3D vectors, affine transforms, Newell's normal, area
│   ├── crease_pattern.py        # CreasePattern graph, CreaseType, origami theorems
│   ├── mesh.py                  # FoldedMesh container, bounding box, triangulation
│   └── parameters.py            # Parameter, ParameterSet, validation, sweeps
│
├── patterns/                    # Origami Pattern Generators (Stage 2)
│   ├── __init__.py
│   ├── base.py                  # BasePattern abstract interface
│   ├── miura_ori.py             # Standard and generalized Miura-ori tessellations
│   ├── yoshimura.py             # Yoshimura cylindrical and triangular patterns
│   ├── waterbomb.py             # Waterbomb base and tube patterns
│   └── degree4_vertex.py        # Generic single degree-4 vertex generator
│
├── folding/                     # Kinematics & Collision Engine (Stage 3)
│   ├── __init__.py
│   ├── kinematics.py            # Analytical 1-DOF kinematic paths for standard patterns
│   ├── rigid_solver.py          # Nonlinear constraint-based kinematic solver for arbitrary meshes
│   ├── trajectory.py            # Folding trajectory manager (folding parameter ρ ∈ [0, 1])
│   └── collision.py             # Panel-panel self-intersection & clearance detector
│
├── rf/                          # RF-Specific Geometry & Physical Modeling (Stage 4)
│   ├── __init__.py
│   ├── materials.py             # Dielectric & conductor material database (Copper, Rogers, Kapton)
│   ├── layers.py                # Multilayer stackup (dielectric core, top/bottom conductors)
│   ├── layout.py                # Conductor 2D polygon layouts on panel facets
│   ├── keepout.py               # Hinge clearance and setback generator
│   ├── ports.py                 # RFPort definitions (Delta-gap feed, coaxial probe, lumped RLC)
│   └── assembly.py              # Full 3D RF assembly combining folded geometry and RF stackup
│
├── em/                          # Electromagnetic Solver Engine (Stage 5)
│   ├── __init__.py
│   ├── mesh/
│   │   ├── __init__.py
│   │   ├── discretizer.py       # Quality 2D/3D Delaunay surface mesher
│   │   ├── rwg.py               # Rao-Wilton-Glisson (RWG) basis function generator
│   │   └── wire_mesh.py         # 1D wire/trace segment mesher
│   ├── solvers/
│   │   ├── __init__.py
│   │   ├── base_solver.py       # Abstract BaseEMSolver interface
│   │   ├── wire_mom.py          # Stage 5A: Thin-wire Pocklington/Hallén MoM solver
│   │   └── surface_mom.py       # Stage 5B: Surface EFIE RWG Method of Moments solver
│   ├── postprocess/
│   │   ├── __init__.py
│   │   ├── impedance.py         # Input impedance Zin(f) and S11 calculations
│   │   ├── radiation.py         # Far-field integration, directivity, and 3D gain
│   │   └── currents.py          # Surface current density vector field evaluation
│
├── coupling/                    # RF / Origami Kinematic Coupling (Stage 6)
│   ├── __init__.py
│   ├── coupled_evaluator.py     # Evaluates RF response across folding trajectory ρ
│   └── reconfigurability.py     # Quantifies frequency tuning range, pattern steering, BW change
│
├── exploration/                 # Automated Design-Space Exploration (Stage 7)
│   ├── __init__.py
│   ├── sampler.py               # Latin hypercube, Sobol, and uniform grid samplers
│   ├── filters.py               # Three-tier feasibility and collision filters
│   └── runner.py                # Multiprocessing batch simulation runner
│
├── optimization/                # Design Optimization (Stage 8)
│   ├── __init__.py
│   ├── objectives.py            # RF objective functions (S11, gain, tuning range, compactness)
│   ├── genetic.py               # NSGA-II multi-objective genetic algorithm
│   └── bayesian.py              # Bayesian optimization with Gaussian Processes
│
├── visualization/               # Visualization & Research UI (Stage 9)
│   ├── __init__.py
│   ├── plot_crease.py           # 2D crease pattern viewer (M=red, V=blue, B=black)
│   ├── plot_folded.py           # 3D interactive folded state viewer
│   ├── plot_rf.py               # S11 curves, Smith charts, and far-field 2D/3D radiation cuts
│   ├── plot_currents.py         # 3D surface current vector overlay
│   └── interactive_app.py       # Real-time Matplotlib interactive slider GUI
│
├── storage/                     # Data Storage & Provenance (Cross-cutting)
│   ├── __init__.py
│   ├── database.py              # SQLite/JSON design index and metadata tracker
│   └── serializer.py            # HDF5 / NPZ numerical array archiver
│
└── validation/                  # Independent Benchmark & Validation Suite (Stage 10)
    ├── __init__.py
    ├── analytical_antennas.py   # Closed-form half-wave dipole and loop antenna benchmarks
    └── literature_cases.py      # Published origami antenna benchmarks from RF literature
```

---

## O. Staged Development Roadmap

```text
STAGE 1: Mathematical & Core Foundation           [COMPLETE]
   ↓
STAGE 2: Origami Pattern Generation               [NEXT]
   ↓
STAGE 3: Folding & Kinematics Engine
   ↓
STAGE 4: RF Geometry Representation
   ↓
STAGE 5: Electromagnetic Solver (Wire & Surface MoM)
   ↓
STAGE 6: RF / Origami Kinematic Coupling
   ↓
STAGE 7: Automated Design-Space Exploration
   ↓
STAGE 8: Multi-Objective Optimization
   ↓
STAGE 9: Visualization & Research Workflow
   ↓
STAGE 10: Validation Against Analytical & External Benchmarks
```

---

### Stage 1: Mathematical & Core Foundation
- **Status**: Complete & Verified (19/19 tests passing).
- **Objective**: Establish foundational 3D geometry, crease pattern graph topology, 3D mesh container, and parameter validation.
- **Mathematical Methods**: Rodrigues' rotation formula, Newell's polygon normal, SE(3) homogeneous transforms, Kawasaki's and Maekawa's theorems.
- **Modules/Files**: `rf_origami/core/geometry.py`, `crease_pattern.py`, `mesh.py`, `parameters.py`.
- **Inputs**: Coordinate tuples, crease assignments, parameter definitions.
- **Outputs**: Verified vector/mesh classes, validated parameter dictionaries.
- **Tests**: `tests/test_geometry.py`, `test_crease_pattern.py`, `test_mesh.py`, `test_parameters.py`.
- **Validation Strategy**: Exact geometric invariants (vector dot/cross products, rotation matrices, square areas).
- **Dependencies**: Python standard library, `numpy`, `pytest`.

---

### Stage 2: Origami Pattern Generation
- **Objective**: Procedurally generate standard and generalized parametric origami crease patterns.
- **Mathematical Methods**:
  - Trigonometric unit-cell tessellation equations for Miura-ori: cell dimensions $a, b$, sector angle $\gamma$, repetition counts $N_x, N_y$.
  - Yoshimura cylinder/triangle lattice equations.
  - Waterbomb base cell tessellations.
- **Modules/Files**:
  - `rf_origami/patterns/base.py`
  - `rf_origami/patterns/miura_ori.py`
  - `rf_origami/patterns/yoshimura.py`
  - `rf_origami/patterns/waterbomb.py`
  - `rf_origami/patterns/degree4_vertex.py`
- **Inputs**: `ParameterSet` containing unit-cell geometric parameters ($a, b, \gamma, N_x, N_y$).
- **Outputs**: Fully populated `CreasePattern` instances with verified topology and Mountain/Valley assignments.
- **Tests**: `tests/test_patterns.py` (verify vertex counts, edge assignments, symmetry, and boundary identification).
- **Validation Strategy**: Verify Kawasaki and Maekawa conditions on all generated interior vertices.
- **Dependencies**: `numpy`.

---

### Stage 3: Folding & Kinematics Engine
- **Objective**: Compute continuous 3D folded coordinates preserving facet isometry, and detect panel self-intersections.
- **Mathematical Methods**:
  - Analytical closed-form kinematics for standard degree-4 tessellations:
    $$S_x = 2 a \sin(\theta/2) \sqrt{1 - \frac{\cos^2\gamma}{\sin^2(\theta/2)}}, \quad S_y = 2 b \cos\gamma \dots$$
  - General rigid origami kinematics: Nonlinear constraint satisfaction using constrained least-squares / dual-quaternion propagation:
    $$\min_{\mathbf{X}} \sum_{(i,j)} (\|\mathbf{x}_i - \mathbf{x}_j\| - L_{ij})^2$$
  - Collision detection: Gilbert-Johnson-Keerthi (GJK) or bounding-box-filtered triangle-triangle intersection testing.
- **Modules/Files**:
  - `rf_origami/folding/kinematics.py`
  - `rf_origami/folding/rigid_solver.py`
  - `rf_origami/folding/trajectory.py`
  - `rf_origami/folding/collision.py`
- **Inputs**: `CreasePattern`, folding parameter $\rho \in [0, 1]$ or target dihedral angles $\boldsymbol{\theta}$.
- **Outputs**: `FoldedGeometry` containing 3D vertex coordinates $\mathbf{X}(\rho)$, panel transformation frames $\mathbf{T}_f(\rho)$, and collision status (`is_colliding: bool`).
- **Tests**: `tests/test_kinematics.py`, `tests/test_collision.py` (verify edge length conservation to $10^{-6}$ relative tolerance, verify collision detection on deliberately interpenetrating panels).
- **Validation Strategy**: Compare numerical solver positions with closed-form Miura-ori coordinates.
- **Dependencies**: `numpy`, `scipy.optimize`.

---

### Stage 4: RF Geometry Representation
- **Objective**: Model multilayer substrates, conductive traces/patches, hinge keep-out clearances, and RF ports on folded panels.
- **Mathematical Methods**:
  - 2D polygon clipping and offsetting (Minkowski sum / buffer operations) for hinge setback clearance:
    $$P_{\text{conductor}} = P_{\text{facet}} \ominus g_{\text{hinge}}$$
  - Local-to-global affine coordinate mapping: $\mathbf{x} = \mathbf{R}_f \mathbf{u} + \mathbf{t}_f$.
- **Modules/Files**:
  - `rf_origami/rf/materials.py`
  - `rf_origami/rf/layers.py`
  - `rf_origami/rf/layout.py`
  - `rf_origami/rf/keepout.py`
  - `rf_origami/rf/ports.py`
  - `rf_origami/rf/assembly.py`
- **Inputs**: `FoldedGeometry`, material properties ($\varepsilon_r, \tan\delta, \sigma$), trace geometry, setback distance $g$, port locations.
- **Outputs**: `RFAssembly` holding complete 3D conductive boundaries, dielectric volumes, and excitation ports.
- **Tests**: `tests/test_rf_geometry.py` (verify clearance margins around creases, verify port terminal connectivity).
- **Validation Strategy**: Verify that conductive areas match CAD planar layout projections and do not overlap across fold lines.
- **Dependencies**: `numpy`.

---

### Stage 5: Electromagnetic Solver Engine
- **Objective**: Implement self-contained Method of Moments solvers for wire/trace and surface RF structures without external simulation software.
- **Mathematical Methods**:
  - **Stage 5A (Thin-Wire MoM)**: Pocklington's Electric Field Integral Equation with pulse/triangle basis functions:
    $$\int_{-L/2}^{L/2} I(z') \left( \frac{\partial^2}{\partial z^2} + k^2 \right) G(z, z') dz' = -j \omega \varepsilon E_z^{\text{inc}}$$
  - **Stage 5B (Surface MoM)**: Rao-Wilton-Glisson (RWG) Electric Field Integral Equation (EFIE):
    $$Z_{mn} = j \omega \mu_0 \int_{T_m} \int_{T_n} \mathbf{f}_m(\mathbf{r}) \cdot \mathbf{f}_n(\mathbf{r}') G(\mathbf{r}, \mathbf{r}') dS' dS - \frac{j}{\omega \varepsilon_0} \int_{T_m} \int_{T_n} (\nabla \cdot \mathbf{f}_m)(\nabla' \cdot \mathbf{f}_n) G(\mathbf{r}, \mathbf{r}') dS' dS$$
  - Numerical singularity cancellation (Duffy transform / analytical potential evaluation for self-terms).
  - Dense matrix linear solve: $\mathbf{I} = \mathbf{Z}^{-1} \mathbf{V}$ via SciPy/NumPy LU decomposition.
  - Far-field Poynting vector integration for gain and radiation efficiency.
- **Modules/Files**:
  - `rf_origami/em/mesh/discretizer.py`
  - `rf_origami/em/mesh/rwg.py`
  - `rf_origami/em/mesh/wire_mesh.py`
  - `rf_origami/em/solvers/wire_mom.py`
  - `rf_origami/em/solvers/surface_mom.py`
  - `rf_origami/em/postprocess/impedance.py`
  - `rf_origami/em/postprocess/radiation.py`
  - `rf_origami/em/postprocess/currents.py`
- **Inputs**: `RFAssembly`, frequency range vector $\mathbf{f} \in [f_{\min}, f_{\max}]$.
- **Outputs**: Input impedance $\mathbf{Z}_{\text{in}}(f)$, return loss $S_{11}(f)$, resonant frequency $f_0$, 3D radiation pattern $D(\theta, \phi)$, realized gain $G$, efficiency $\eta$.
- **Tests**: `tests/test_em_solvers.py` (half-wave dipole benchmark, loop antenna benchmark, RWG divergence continuity test).
- **Validation Strategy**: Compare input impedance of straight half-wave dipole with classical analytical solution ($Z_{\text{in}} \approx 73 + j42.5 \, \Omega$).
- **Dependencies**: `numpy`, `scipy` (`scipy.linalg`, `scipy.spatial`).

---

### Stage 6: RF / Origami Kinematic Coupling
- **Objective**: Couple origami folding mechanics with electromagnetic response across continuous deformation trajectories.
- **Mathematical Methods**:
  - Trajectory sampling: Evaluate $\mathbf{Z}_{\text{in}}(f, \rho)$ over dynamic parameter grid $(\rho_k, f_m)$.
  - Reconfigurability metric evaluation: Frequency tuning ratio $\mathrm{TR} = f_0(\rho_{\max}) / f_0(\rho_{\min})$, beam steering angle $\Delta \theta_{\text{peak}}(\rho)$.
- **Modules/Files**:
  - `rf_origami/coupling/coupled_evaluator.py`
  - `rf_origami/coupling/reconfigurability.py`
- **Inputs**: `OrigamiStructure`, folding range $[\rho_{\min}, \rho_{\max}]$, frequency band.
- **Outputs**: Tuning curves $f_0(\rho)$, $S_{11}(\rho, f)$ 2D contour maps, dynamic radiation pattern evolution.
- **Tests**: `tests/test_coupling.py` (verify smooth frequency shift as folded dipole arms rotate).
- **Validation Strategy**: Verify monotonic inductance/capacitance trends during folding.
- **Dependencies**: `numpy`, `scipy`.

---

### Stage 7: Automated Design-Space Exploration
- **Objective**: Automatically sample, filter, and evaluate thousands of candidate origami antenna designs.
- **Mathematical Methods**:
  - Quasi-random Latin Hypercube Sampling (LHS) and Sobol sequence distribution across parameter bounds.
  - Three-tier rejection filter (Kinematic feasibility $\to$ Collision avoidance $\to$ RF port integrity).
  - Parallel batch worker distribution across CPU cores.
- **Modules/Files**:
  - `rf_origami/exploration/sampler.py`
  - `rf_origami/exploration/filters.py`
  - `rf_origami/exploration/runner.py`
- **Inputs**: `ParameterSet` bounds, sample count $N_{\text{samples}}$, target objectives.
- **Outputs**: Database of valid candidate designs with computed RF figures of merit; filtered rejection statistics log.
- **Tests**: `tests/test_exploration.py` (verify 100% rejection of self-penetrating test geometries, verify reproducibility across random seeds).
- **Validation Strategy**: Verify uniform parameter coverage via histogram and pairwise scatter checks.
- **Dependencies**: `numpy`, `multiprocessing` (Python standard library).

---

### Stage 8: Multi-Objective Optimization
- **Objective**: Discover optimal origami geometries matching user-defined RF targets (e.g. maximum bandwidth, target resonance, minimum footprint).
- **Mathematical Methods**:
  - NSGA-II (Non-dominated Sorting Genetic Algorithm II) for Pareto optimal front calculation.
  - Bayesian Optimization with Gaussian Process surrogates (Matérn 5/2 kernel) for expensive EM evaluations.
- **Modules/Files**:
  - `rf_origami/optimization/objectives.py`
  - `rf_origami/optimization/genetic.py`
  - `rf_origami/optimization/bayesian.py`
- **Inputs**: Target objective vector (e.g. $f_0 = 2.4 \, \mathrm{GHz}$, $S_{11} \le -15 \, \mathrm{dB}$, $\mathrm{Gain} \ge 5 \, \mathrm{dBi}$), parameter bounds.
- **Outputs**: Pareto-optimal design set, convergence history, sensitivity rankings.
- **Tests**: `tests/test_optimization.py` (test optimization on synthetic RF objective functions and known test landscapes).
- **Validation Strategy**: Convergence to known optimum within specified evaluation budget.
- **Dependencies**: `numpy`, `scipy`.

---

### Stage 9: Interactive Visualization & Research Workflow
- **Objective**: Provide comprehensive visual analysis of flat patterns, 3D folded geometry, surface currents, and radiation patterns with real-time parameter exploration.
- **Mathematical Methods**:
  - 3D spherical coordinate mapping for radiation pattern rendering: $(r, \theta, \phi) \mapsto (x, y, z)$.
  - Color-mapped surface current density streamlines $\mathbf{J}_s$.
  - Interactive slider binding with Matplotlib UI events.
- **Modules/Files**:
  - `rf_origami/visualization/plot_crease.py`
  - `rf_origami/visualization/plot_folded.py`
  - `rf_origami/visualization/plot_rf.py`
  - `rf_origami/visualization/plot_currents.py`
  - `rf_origami/visualization/interactive_app.py`
- **Inputs**: `CreasePattern`, `FoldedGeometry`, EM solver simulation results.
- **Outputs**: Interactive 2D/3D visualization windows, high-resolution publication figures (PNG, PDF, SVG).
- **Tests**: `tests/test_visualization.py` (non-interactive render tests to headless image buffers).
- **Validation Strategy**: Visual verification of mountain (red), valley (blue), boundary (black) crease conventions and 3D lobe orientations.
- **Dependencies**: `matplotlib`.

---

### Stage 10: Validation Against Independent External Benchmarks
- **Objective**: Rigorously validate our custom solvers and kinematics against classical electromagnetic theory, published academic literature, and external CAD/EM exports.
- **Mathematical Methods**:
  - Classical analytical solutions:
    - Infinitesimal dipole, finite half-wave dipole ($Z_{\text{in}} = 73.1 + j42.5 \, \Omega$, directivity $= 1.64$ / $2.15 \, \mathrm{dBi}$).
    - Small circular/square loop antennas ($R_{\text{rad}} = 31200 (A/\lambda^2)^2$).
    - Rectangular microstrip patch cavity model.
  - Published peer-reviewed origami antenna benchmarks (e.g. reconfigurable Miura-ori dipole arrays, folded helical antennas).
- **Modules/Files**:
  - `rf_origami/validation/analytical_antennas.py`
  - `rf_origami/validation/literature_cases.py`
  - `rf_origami/export/cad_export.py` (clean OBJ, STL, DXF, and FOLD schema exports for independent cross-tool inspection).
- **Inputs**: Standard benchmark geometry specifications.
- **Outputs**: Automated validation report comparing custom solver results against analytical/literature values (percentage error, correlation coefficient).
- **Tests**: `tests/test_validation.py`.
- **Validation Strategy**: Error $< 3\%$ on input resistance and resonant frequency against canonical analytical antenna solutions.
- **Dependencies**: `numpy`, `scipy`.
