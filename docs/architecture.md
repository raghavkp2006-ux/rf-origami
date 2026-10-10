# RF Origami Design Generator: Architecture & Design Document

## 1. Executive Summary & Goals
The **RF Origami Design Generator** is a computational framework for exploring, modeling, and generating origami-inspired geometries tailored for radio-frequency (RF) and antenna engineering applications (such as reconfigurable frequency-selective surfaces (FSS), deployable reflector/horn antennas, tunable origami helices, and phased arrays).

The system provides:
1. Parametric 2D origami crease pattern definition and topological verification.
2. Kinematic mapping from 2D flat state to 3D folded geometry.
3. Visualization of both flat patterns and 3D folded states.
4. Parameter exploration, variation, and batch candidate generation.
5. Geometry export for CAD (Rhino/Grasshopper) and EM solvers (Ansys HFSS, CST Studio Suite).
6. Future hooks for RF simulation interfacing and goal-directed optimization.

---

## 2. Mathematical Representation

### 2.1 Geometric Primitives
- **Points & Vectors**: Defined in $\mathbb{R}^3$ (or embedded $\mathbb{R}^2$ where $z=0$). Vectorized operations are performed using NumPy $(N, 3)$ float arrays for high computational efficiency.
- **Transformations**: Rigid body transforms represented via $4 \times 4$ homogeneous transformation matrices $\mathbf{T} \in \mathrm{SE}(3)$ (rotations $\mathbf{R} \in \mathrm{SO}(3)$ and translations $\mathbf{t} \in \mathbb{R}^3$).
- **Facets / Faces**: Planar polygons represented as ordered sequences of coplanar vertex indices $(v_0, v_1, \dots, v_{k-1})$. Surface normal is calculated via Newell's method or the cross product of edge vectors:
  $$\hat{\mathbf{n}} = \frac{(\mathbf{p}_1 - \mathbf{p}_0) \times (\mathbf{p}_2 - \mathbf{p}_0)}{\|(\mathbf{p}_1 - \mathbf{p}_0) \times (\mathbf{p}_2 - \mathbf{p}_0)\|}$$

### 2.2 Origami Topology & Kinematics
- **Crease Pattern Graph $G = (V, E, F)$**:
  - $V = \{ \mathbf{p}_i \in \mathbb{R}^2 \}$: Set of flat vertex coordinates.
  - $E = \{ e_j = (u_j, v_j, \tau_j) \}$: Crease edges connecting vertices with assignment $\tau_j \in \{\text{Mountain (M)}, \text{Valley (V)}, \text{Boundary (B)}, \text{Facet/Flat (F)}\}$.
  - $F = \{ f_m = (v_{m,0}, \dots, v_{m,k-1}) \}$: Facets bounded by crease edges.
- **Dihedral Fold Angle**:
  Each internal crease $e_j$ between adjacent facets $f_A, f_B$ has a folding angle $\theta_j \in [-\pi, \pi]$:
  - $\theta_j = 0$: Flat (unfolded).
  - $\theta_j > 0$: Mountain fold (crease rises toward observer / outward normal).
  - $\theta_j < 0$: Valley fold (crease drops away from observer).
  - $|\theta_j| = \pi$: Completely folded (flat-folded state).
- **Rigid Origami Kinematics**:
  Facets are assumed to remain rigid polygons under folding, preserving edge lengths (isometry):
  $$\|\mathbf{p}_i^{(3D)} - \mathbf{p}_j^{(3D)}\| = \|\mathbf{p}_i^{(2D)} - \mathbf{p}_j^{(2D)}\| \quad \forall (i, j) \in E$$
  For standardized tessellations (e.g. Miura-ori, Yoshimura, Waterbomb), closed-form analytical kinematic relations map fold angles $\theta$ directly to 3D vertex coordinates. For arbitrary degree-4 and general meshes, constraint satisfaction or rotation-matrix propagation along dual spanning trees is used.

---

## 3. Data Structures

### 3.1 Core Data Structures (`rf_origami.core`)
1. `Point3D` / `Vector3D`: Immutable coordinate / direction vectors with helper vector arithmetic (`dot`, `cross`, `norm`, `normalize`).
2. `CreaseType`: Enumeration representing crease fold assignment:
   - `BOUNDARY` (`'B'`)
   - `MOUNTAIN` (`'M'`)
   - `VALLEY` (`'V'`)
   - `FACET` / `FLAT` (`'F'`)
3. `Crease`: Represents an edge between two vertex indices:
   - `u`, `v`: Vertex indices.
   - `crease_type`: `CreaseType`.
   - `fold_angle`: Target dihedral angle in radians or degrees.
   - `target_length`: Isometric rest length $L = \|\mathbf{p}_u - \mathbf{p}_v\|$.
4. `Face`: Represents an individual facet:
   - `vertex_indices`: Tuple of vertex indices in counter-clockwise winding.
   - `material_tag`: Tag indicating conductive surface (e.g. copper patch) vs. dielectric substrate.
5. `CreasePattern`:
   - `vertices_2d`: Array of shape $(N, 2)$ or $(N, 3)$ representing flat state.
   - `creases`: List of `Crease` instances.
   - `faces`: List of `Face` instances.
   - Helper methods: edge lookups, adjacency matrices, validity checks (Kawasaki's and Maekawa's theorems for flat-foldable vertices).
6. `FoldedMesh`:
   - `vertices_3d`: Array of shape $(N, 3)$ representing 3D folded coordinates.
   - `faces`: Polygon / triangle index lists.
   - `normals`: Computed per-face and per-vertex unit normals.
   - `bounds`: Axis-aligned bounding box (min/max/dimensions).
7. `Parameter` & `ParameterSet`:
   - Strongly-typed parameter definition (`float`, `int`, `str`, `bool`) with default value, valid range `[min_val, max_val]`, engineering units (`mm`, `deg`, `rad`), and descriptive metadata.
   - Serialization to/from dictionaries and JSON.
   - Sampling support (uniform grid sampling, random Latin hypercube / Monte Carlo sampling) for exploratory candidate generation.

---

## 4. Module Architecture

```text
rf_origami/
│
├── core/                        # Foundational data structures & mathematics
│   ├── __init__.py
│   ├── geometry.py              # 3D vectors, transforms, planes, distance, normals
│   ├── crease_pattern.py        # CreaseType, Crease, Face, CreasePattern class
│   ├── mesh.py                  # 3D folded geometry mesh container & properties
│   └── parameters.py            # Parameter, ParameterSet, validation, sampling
│
├── patterns/                    # Origami pattern generators (Stage 2)
│   ├── __init__.py
│   ├── base.py                  # Abstract BasePattern interface
│   ├── miura_ori.py             # Miura-ori parametric tessellation
│   ├── yoshimura.py             # Yoshimura cylindrical/triangular pattern
│   └── waterbomb.py             # Waterbomb base / tube pattern
│
├── folding/                     # Kinematics and 3D folding solvers (Stage 2)
│   ├── __init__.py
│   ├── kinematics.py            # Closed-form kinematic equations for standard patterns
│   └── rigid_solver.py          # General constraint-based folding projection
│
├── visualization/               # 2D & 3D visualization (Stage 2 & Stage 3)
│   ├── __init__.py
│   ├── flat_plotter.py          # 2D crease pattern plotting (M=red, V=blue, B=black)
│   ├── folded_plotter.py        # 3D interactive folded state plotting (Matplotlib 3D)
│   └── interactive_app.py       # Interactive parameter sliders & real-time update
│
├── generator/                   # Candidate design exploration (Stage 3)
│   ├── __init__.py
│   └── candidate_generator.py   # Parameter sweep, batch generation, metrics logging
│
└── export/                      # CAD and EM Simulation Export (Stage 4)
    ├── __init__.py
    ├── obj_exporter.py          # Wavefront .OBJ export (Rhino, CST)
    ├── stl_exporter.py          # Stereolithography .STL export
    ├── dxf_exporter.py          # 2D/3D DXF crease lines (Laser cutting, AutoCAD, HFSS)
    └── json_exporter.py         # Standard FOLD / JSON format
```

---

## 5. Dependencies
- **Core (Strictly minimal)**:
  - `numpy`: Fast vectorized linear algebra, matrix transforms, and coordinate operations.
  - `matplotlib`: 2D crease pattern plotting, 3D surface visualization, and built-in interactive slider controls (`matplotlib.widgets.Slider`).
- **Standard Library**:
  - `dataclasses`: Clean, memory-efficient data structures.
  - `typing`: Full type hints (`Optional`, `List`, `Tuple`, `Dict`, `Union`).
  - `enum`: Strongly typed crease and boundary classifications.
  - `json`: Parameter serialization and FOLD schema interchange.
  - `math`: Geometric trigonometric routines.
- **Testing**:
  - `pytest`: Automated test suite for regression and verification.

*No unnecessary heavy external CAD dependencies are required for core operations.*

---

## 6. Development Stages

### Stage 1: Foundation (Current Target)
- Modular package structure setup (`rf_origami/core/`).
- Mathematical geometry representation (`geometry.py`).
- Crease pattern representation (`crease_pattern.py`).
- Type-safe parameter system with range validation and sampling (`parameters.py`).
- Full unit test suite with high coverage.

### Stage 2: Pattern Generation & 3D Folding
- Analytical kinematic generators for standard RF origami (starting with Miura-ori: unit cell dimensions $a, b$, facet angle $\gamma$, fold angle $\theta$).
- 2D crease pattern visualization (red/blue mountain-valley conventions).
- 3D folded coordinate calculation preserving facet isometry.

### Stage 3: Interactive Visualization & Candidate Generation
- Interactive Matplotlib visualizer with responsive parameter sliders.
- Design space sampling and candidate generation (DOE / grid / random sweeps).
- Candidate metrics extraction (volume, folded footprint, surface area, aspect ratio).

### Stage 4: Geometry Export
- Clean export pipelines to `.obj`, `.stl`, `.dxf`, and `.fold` (JSON).
- Verification of CAD compatibility for Rhino/Grasshopper and EM simulation workflows (HFSS/CST).
