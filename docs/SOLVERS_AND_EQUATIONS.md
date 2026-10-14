# RF ORIGAMI DESIGN STUDIO: MATHEMATICAL MODELS, EQUATIONS & SOLVER ARCHITECTURE
**Comprehensive Technical Guide for Reviewers, Examiners & Engineering Presentations**

---

## 1. Executive Overview

The **RF Origami Design Studio** bridges computational discrete differential geometry, classical kinematic origami mechanics, and computational electromagnetics (CEM). This document provides an exhaustive, equation-by-equation map of the underlying mathematical formulations and their exact implementation locations in this codebase.

```
                          ┌────────────────────────┐
                          │   DESIGN SPACE (LHS)   │
                          │   a, b, γ, Nx, Ny, θ   │
                          └───────────┬────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
      ┌─────────────────────────┐           ┌─────────────────────────┐
      │  GEOMETRIC KINEMATICS   │           │ COMPUTATIONAL EM (MoM)  │
      │  Kawasaki / Maekawa     │           │ Pocklington / EFIE-MoM  │
      │  Rigid Crease Buckling  │           │ S11, Zin, Absorber Metas│
      │  Facet & Crease Strain  │           │ Current Distributions   │
      └─────────────────────────┘           └─────────────────────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
                          ┌────────────────────────┐
                          │   FOLD 1.1 & CAD MESH  │
                          │   OrigamiSimulator.org │
                          │   WebGL / Three.js 3D  │
                          └────────────────────────┘
```

---

## 2. Geometric Origami Kinematics & Flat-Foldability

### 2.1 Kawasaki's Theorem (Local Flat-Foldability)
For any single degree-$2n$ vertex with alternating sector angles $\alpha_1, \alpha_2, \ldots, \alpha_{2n}$:
A crease pattern is flat-foldable if and only if the alternating sum of sector angles equals $180^\circ$ ($\pi$ radians):

$$\sum_{i=1}^{n} \alpha_{2i-1} = \sum_{i=1}^{n} \alpha_{2i} = 180^\circ$$

Equivalently expressed as:
$$\sum_{j=1}^{2n} (-1)^j \alpha_j = 0$$

- **Physical Meaning**: Ensures that when folded flat ($180^\circ$ dihedral fold), the faces can pack into the plane without self-intersection or angular deficit.
- **Code Location**: 
  - File: [`rf_origami/core/crease_pattern.py`](file:///c:/antigravity_projects/rfori/rf_origami/core/crease_pattern.py)
  - Method: `CreasePattern.validate_kawasaki(tolerance_deg=1e-3)`

---

### 2.2 Maekawa-Justin Theorem (Mountain-Valley Parity)
At any interior flat-foldable flat degree-$2n$ vertex, the difference between the number of Mountain creases ($M$) and Valley creases ($V$) is always $\pm 2$:

$$M - V = \pm 2$$

- **Physical Meaning**: A topological invariant of 2D embedded flat folds; one parity of folds must dominate by two to enclose the vertex.
- **Code Location**:
  - File: [`rf_origami/core/crease_pattern.py`](file:///c:/antigravity_projects/rfori/rf_origami/core/crease_pattern.py)
  - Method: `CreasePattern.validate_maekawa()`

---

### 2.3 Rigid Origami Kinematics (Miura-Ori Parameterization)
The Miura-ori cell consists of parallelograms with side lengths $a$ and $b$ and acute crease angle $\gamma$. When folded with dihedral fold angle $\theta \in (0, 90^\circ)$, the spatial unit cell dimensions $(L_x, L_y, H_z)$ satisfy the non-linear kinematic system:

$$L_x(\theta) = 2 a \frac{\cos\theta \sin\gamma}{\sqrt{1 - \sin^2\theta \sin^2\gamma}}$$

$$L_y(\theta) = 2 b \frac{\cos\gamma}{\sqrt{1 - \sin^2\theta \sin^2\gamma}}$$

$$H_z(\theta) = a \sin\theta \sin\gamma$$

The effective spatial contraction / compactness ratio $\xi(\theta)$ is defined as:
$$\xi(\theta) = \frac{L_x(\theta) \cdot L_y(\theta)}{L_{x, flat} \cdot L_{y, flat}} = \frac{\cos\theta}{1 - \sin^2\theta \sin^2\gamma}$$

- **Physical Meaning**: Predicts the exact rigid 3D coordinates of all vertices during continuous deployment without stretching individual panels.
- **Code Location**:
  - File: [`rf_origami/folding/engine.py`](file:///c:/antigravity_projects/rfori/rf_origami/folding/engine.py)
  - Method: `FoldingEngine.fold_miura_ori(fold_angle_deg, a, b, gamma)`

---

### 2.4 Degree-4 Vertex Rigid Folding Kinematics
For a general single degree-4 vertex with sector angles $\alpha_1, \alpha_2, \alpha_3, \alpha_4$, the dihedral angles $\rho_1, \rho_2, \rho_3, \rho_4$ across the creases satisfy spherical trigonometry spherical law of cosines:

$$\cos \rho_3 = \cos \rho_1 + \frac{\sin\rho_1 (\cos\alpha_1 \cos\alpha_2 - \cos\alpha_3 \cos\alpha_4)}{\sin\alpha_1 \sin\alpha_2}$$

- **Code Location**:
  - File: [`rf_origami/folding/engine.py`](file:///c:/antigravity_projects/rfori/rf_origami/folding/engine.py)
  - Method: `FoldingEngine.fold_degree4_vertex(fold_angle_deg, ...)`

---

## 3. Mechanical Strain Analysis (Origami Simulator Model)

In non-ideal origami or thick foldable substrates (e.g. Copper on Kapton polyimide or FR-4), folding induces two strain components:

### 3.1 In-Plane Facet Strain (Panel Elongation)
For any facet edge $e = (u, v)$ with uncreased 2D length $L_{2D} = \|\mathbf{x}_u^{2D} - \mathbf{x}_v^{2D}\|$ and folded 3D length $L_{3D} = \|\mathbf{x}_u^{3D} - \mathbf{x}_v^{3D}\|$:

$$\epsilon_{axial}(e) = \frac{|L_{3D}(e) - L_{2D}(e)|}{L_{2D}(e)}$$

Facet-averaged strain for facet $F$:
$$\bar{\epsilon}_{facet}(F) = \frac{1}{|E_F|} \sum_{e \in E_F} \epsilon_{axial}(e)$$

- **Ideal Rigid Origami**: $\epsilon_{axial} \equiv 0$ (Pure isometry, edge lengths strictly preserved).
- **Physical Realization**: Edge elongation appears due to geometric misalignment, vertex compliance, or imperfect folding trajectories.

---

### 3.2 Crease Hinge Bending Strain
At each crease line with substrate thickness $t_{sub}$, hinge crease gap $w_{crease}$, and dihedral fold angle $\theta_{dihedral}$ (in radians):
The localized radius of curvature is $R = \frac{w_{crease}}{\theta_{dihedral}}$.
The maximum outer fiber tensile bending strain is:

$$\epsilon_{bend} = \frac{t_{sub}}{2 R} = \frac{t_{sub} \cdot |\theta_{dihedral}|}{2 w_{crease}}$$

Total Equivalent Von Mises Strain:
$$\epsilon_{eq} = \sqrt{\epsilon_{axial}^2 + \epsilon_{bend}^2}$$

Total Strain Energy stored in the folded origami:
$$U_{strain} = \sum_{edges} \frac{1}{2} k_{axial} (L_{3D} - L_{2D})^2 + \sum_{creases} \frac{1}{2} k_{rot} (\theta - \theta_0)^2$$

- **Code Location**:
  - Frontend: [`rf_origami/web/static/app.js`](file:///c:/antigravity_projects/rfori/rf_origami/web/static/app.js) (`OrigamiStrainEngine`)
  - Colormap: 5-stop Turbo/Jet gradient:
    - $\le 0.5\%$: Deep Blue (`#2563eb`)
    - $1.5\%$: Cyan (`#06b6d4`)
    - $3.0\%$: Green (`#22c55e`)
    - $5.0\%$: Amber (`#eab308`)
    - $\ge 8.0\%$: Crimson (`#ef4444` — plastic yield warning)

---

## 4. Electromagnetic Numerical Solvers (Method of Moments & EFIE)

### 4.1 Electric Field Integral Equation (EFIE)
The origami metallic creases and conductive patches are modeled by enforcing the tangential boundary condition on conducting surfaces $S$:

$$\hat{n} \times \left[ \mathbf{E}^{inc}(\mathbf{r}) + \mathbf{E}^{scat}(\mathbf{r}) \right] = 0, \quad \mathbf{r} \in S$$

Where the scattered electric field $\mathbf{E}^{scat}$ is related to the surface current density $\mathbf{J}(\mathbf{r}')$ and magnetic vector potential $\mathbf{A}$ and electric scalar potential $\Phi$:

$$\mathbf{E}^{scat}(\mathbf{r}) = -j\omega \mathbf{A}(\mathbf{r}) - \nabla \Phi(\mathbf{r})$$

$$\mathbf{A}(\mathbf{r}) = \mu \iint_S \mathbf{J}(\mathbf{r}') G(\mathbf{r}, \mathbf{r}') \, dS'$$

$$\Phi(\mathbf{r}) = \frac{1}{\epsilon} \iint_S \rho_s(\mathbf{r}') G(\mathbf{r}, \mathbf{r}') \, dS'$$

With the free-space Green's function:
$$G(\mathbf{r}, \mathbf{r}') = \frac{e^{-jk |\mathbf{r} - \mathbf{r}'|}}{4\pi |\mathbf{r} - \mathbf{r}'|}, \quad k = \omega \sqrt{\mu_0 \epsilon_0 \epsilon_{r, eff}}$$

---

### 4.2 Pocklington's Integral Equation Discretization (Thin-Wire / Segment Basis)
For 3D folded origami crease wireframes and strip antennas:

$$\hat{s} \cdot \mathbf{E}^{inc}(s) = \frac{j\eta}{4\pi k} \int_0^L I(s') \left[ \frac{\partial^2}{\partial s^2} + k^2 \right] \frac{e^{-jk R(s, s')}}{R(s, s')} \, ds'$$

Discretizing into $N$ segments using pulse / piecewise linear basis functions yields the linear matrix equation:

$$\mathbf{[Z]} \mathbf{[I]} = \mathbf{[V]}$$

Where:
- $\mathbf{[Z]} \in \mathbb{C}^{N \times N}$ is the Mutual Impedance Matrix.
- $\mathbf{[I]} \in \mathbb{C}^N$ is the unknown Current Distribution vector.
- $\mathbf{[V]} \in \mathbb{C}^N$ is the Excitation Voltage vector (delta-gap generator $V_i = 1.0\text{ V}$ at port segment).

- **Impedance Matrix Elements**:
  $$Z_{mn} = \frac{j\eta}{4\pi k} \int_{\Delta s_m} \int_{\Delta s_n} \left[ k^2 \hat{s}_m \cdot \hat{s}_n - \frac{\partial}{\partial s_m} \frac{\partial}{\partial s_n} \right] \frac{e^{-jk R_{mn}}}{R_{mn}} \, ds' \, ds$$

- **Code Location**:
  - File: [`rf_origami/em/mom_solver.py`](file:///c:/antigravity_projects/rfori/rf_origami/em/mom_solver.py)
  - Class: `MoMSolver`, `WireSegment`, `solve_currents()`

---

### 4.3 Input Impedance & S-Parameters ($S_{11}$)
At the feed port terminal $k_{port}$, the driving-point input impedance $Z_{in}(f)$ is:

$$Z_{in}(f) = \frac{V_{port}}{I(k_{port})} = R_{in}(f) + j X_{in}(f)$$

The reflection coefficient / Return Loss $S_{11}$ referenced to system impedance $Z_0 = 50\,\Omega$ is:

$$\Gamma(f) = \frac{Z_{in}(f) - Z_0}{Z_{in}(f) + Z_0}$$

$$S_{11}(f) \, [\text{dB}] = 20 \log_{10} |\Gamma(f)|$$

Voltage Standing Wave Ratio (VSWR):
$$\text{VSWR}(f) = \frac{1 + |\Gamma(f)|}{1 - |\Gamma(f)|}$$

Resonant Frequency $f_0$:
$$f_0 = \arg\min_f |S_{11}(f)| \quad \text{or} \quad X_{in}(f_0) = 0$$

$-10\text{ dB}$ Impedance Fractional Bandwidth:
$$\text{FBW} = \frac{f_{high} - f_{low}}{f_0} \times 100\% \quad \text{for } S_{11} \le -10\text{ dB}$$

- **Code Location**:
  - File: [`rf_origami/em/mom_solver.py`](file:///c:/antigravity_projects/rfori/rf_origami/em/mom_solver.py)
  - Method: `MoMSolver.sweep_frequency(f_start, f_stop, num_pts)`

---

## 5. Metasurface Absorber Physics

### 5.1 Plane Wave Reflection & Power Absorption
For an incident plane wave with incidence angles $(\theta_{inc}, \phi_{inc})$ illuminating a lossy ground-backed origami metasurface:

$$A(\omega) = 1 - |R(\omega)|^2 - |T(\omega)|^2$$

For a perfect ground-plane backing, transmission $T(\omega) \equiv 0$, simplifying to:
$$A(\omega) = 1 - |R(\omega)|^2$$

Where $R(\omega)$ is the complex reflection coefficient:
$$R(\omega) = \frac{Z_{in}^{meta}(\omega) - \eta_0}{Z_{in}^{meta}(\omega) + \eta_0}, \quad \eta_0 = \sqrt{\frac{\mu_0}{\epsilon_0}} \approx 376.73\,\Omega$$

### 5.2 Salisbury & Dallenbach Equivalent Transmission Line Matching
The origami tessellation modulates the effective surface impedance $Z_s = R_s + j X_s(\theta)$.
Near resonance, perfect impedance matching is achieved when:
$$\text{Re}\{Z_{in}^{meta}\} \approx \eta_0 \approx 377\,\Omega \quad \text{and} \quad \text{Im}\{Z_{in}^{meta}\} \approx 0$$
Yielding near unity absorption:
$$A(\omega) \ge 90\% \quad (S_{11} \le -10\text{ dB})$$

- **Code Location**:
  - File: [`rf_origami/em/metasurface_solver.py`](file:///c:/antigravity_projects/rfori/rf_origami/em/metasurface_solver.py)
  - Method: `MetasurfaceSolver.simulate_frequency_sweep(...)`

---

## 6. FOLD 1.1 Specification (Origami Simulator Interoperability)

To guarantee flawless import into [Origami Simulator](https://origamisimulator.org/) and [TreeMaker/FoldFormat](https://github.com/edemaine/fold), all exports adhere to the **FOLD 1.1 Specification**:

| Key | Type | Description |
|---|---|---|
| `file_spec` | `float` | `1.1` |
| `vertices_coords` | `[[x, y, z], ...]` | 3D Cartesian coordinates of all crease vertices (mm) |
| `edges_vertices` | `[[u, v], ...]` | 0-indexed endpoint vertex pairs |
| `edges_assignment` | `["M", "V", "B", ...]` | Fold assignments: `M` (Mountain), `V` (Valley), `B` (Border) |
| `edges_foldAngle` | `[-180.0, 180.0, 0.0]` | Dihedral fold angle in degrees ($M=-180^\circ$, $V=+180^\circ$) |
| `faces_vertices` | `[[v0, v1, v2, ...], ...]` | CCW vertex index loops defining closed planar facets |
| `faces_materials` | `["conductor", ...]` | RF material assignment per facet |

- **Code Location**:
  - File: [`rf_origami/core/crease_pattern.py`](file:///c:/antigravity_projects/rfori/rf_origami/core/crease_pattern.py)
  - Method: `CreasePattern.to_fold(as_3d=False)`
  - Web Endpoint: `/api/fold/export` in [`rf_origami/web/service.py`](file:///c:/antigravity_projects/rfori/rf_origami/web/service.py)

---

## 7. Codebase File & Function Directory

| Module | Purpose | Key Classes & Functions |
|---|---|---|
| [`rf_origami/core/crease_pattern.py`](file:///c:/antigravity_projects/rfori/rf_origami/core/crease_pattern.py) | Crease pattern 2D topology & FOLD 1.1 export | `CreasePattern`, `to_fold()`, `to_dict()`, `validate_kawasaki()`, `validate_maekawa()` |
| [`rf_origami/folding/engine.py`](file:///c:/antigravity_projects/rfori/rf_origami/folding/engine.py) | Rigid origami spatial kinematics | `FoldingEngine`, `fold_miura_ori()`, `fold_waterbomb()`, `fold_yoshimura()` |
| [`rf_origami/em/mom_solver.py`](file:///c:/antigravity_projects/rfori/rf_origami/em/mom_solver.py) | Numerical Method of Moments EFIE solver | `MoMSolver`, `sweep_frequency()`, `build_impedance_matrix()` |
| [`rf_origami/em/metasurface_solver.py`](file:///c:/antigravity_projects/rfori/rf_origami/em/metasurface_solver.py) | Metasurface reflection & absorption solver | `MetasurfaceSolver`, `simulate_frequency_sweep()` |
| [`rf_origami/web/service.py`](file:///c:/antigravity_projects/rfori/rf_origami/web/service.py) | REST API endpoints for studio frontend | `/api/explore`, `/api/generate`, `/api/fold/export`, `/api/rf/simulate` |
| [`rf_origami/web/static/app.js`](file:///c:/antigravity_projects/rfori/rf_origami/web/static/app.js) | Frontend UI, strain engine, cross-sync & 3D Three.js | `OrigamiStrainEngine`, `syncDesignToAllSections()`, `renderReference3D()` |

---
*Created for RF Origami Design Studio Presentation & Technical Defense.*
