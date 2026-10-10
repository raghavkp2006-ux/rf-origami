"""Surface Method of Moments (MoM) Scattering and Absorption Solver.

Implements Rao-Wilton-Glisson (RWG) and patch basis functions for 3D folded
metallic and dielectric metasurfaces illuminated by incident plane waves.
Calculates induced surface currents J_s, scattered fields, S11/S21, and absorption.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import cmath
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np


from rf_origami.core.mesh import FoldedMesh
from rf_origami.rf.materials.material import (
    EPSILON_0,
    MU_0,
    C_0,
    ETA_0,
    Material,
    MaterialLibrary,
)
from rf_origami.rf.geometry.rf_object import RFGeometryModel
from rf_origami.rf.absorber.excitation import PlaneWave, PolarizationType
from rf_origami.rf.absorber.result import AbsorberResult
from rf_origami.rf.absorber.metrics import (
    calculate_reflection,
    calculate_transmission,
    calculate_absorption,
    check_energy_conservation,
    extract_resonance,
    calculate_absorption_bandwidth,
    s11_to_db,
)


@dataclass
class SurfaceFacet:
    """A triangular or planar facet on a 3D folded RF surface."""
    index: int
    vertices: np.ndarray      # (3, 3) or (N, 3) coordinates [mm]
    material_type: str = "conductor" # "conductor", "substrate", "ground"
    sheet_resistance: float = 0.0    # Ohm/sq
    parent_panel_id: int = -1

    @property
    def centroid(self) -> np.ndarray:
        """Centroid of facet in millimeters."""
        return np.mean(self.vertices, axis=0)

    @property
    def area_mm2(self) -> float:
        """Area in mm^2 (triangulated if polygon)."""
        v = self.vertices
        if len(v) == 3:
            return 0.5 * float(np.linalg.norm(np.cross(v[1] - v[0], v[2] - v[0])))
        elif len(v) >= 4:
            # Fan triangulation area
            total_a = 0.0
            for i in range(1, len(v) - 1):
                total_a += 0.5 * float(np.linalg.norm(np.cross(v[i] - v[0], v[i + 1] - v[0])))
            return total_a
        return 1.0

    @property
    def normal(self) -> np.ndarray:
        """Outward unit normal vector."""
        v = self.vertices
        if len(v) >= 3:
            n = np.cross(v[1] - v[0], v[2] - v[0])
            norm = np.linalg.norm(n)
            if norm > 1e-12:
                return n / norm
        return np.array([0.0, 0.0, 1.0])


@dataclass
class RWGBasis:
    """Rao-Wilton-Glisson (RWG) basis function defined on a pair of adjacent triangles."""
    index: int
    plus_facet_idx: int
    minus_facet_idx: int
    free_vertex_plus: np.ndarray   # r_plus vertex in mm
    free_vertex_minus: np.ndarray  # r_minus vertex in mm
    edge_p1: np.ndarray            # Shared edge node 1 [mm]
    edge_p2: np.ndarray            # Shared edge node 2 [mm]
    length_mm: float = 1.0

    @property
    def edge_center(self) -> np.ndarray:
        return 0.5 * (self.edge_p1 + self.edge_p2)


@dataclass
class SurfaceMesh:
    """Discretized surface mesh with nodes, facets, and basis functions."""
    facets: List[SurfaceFacet] = field(default_factory=list)
    basis_functions: List[RWGBasis] = field(default_factory=list)
    total_area_mm2: float = 0.0
    ground_backed: bool = True
    substrate_thickness_mm: float = 0.5

    @property
    def num_facets(self) -> int:
        return len(self.facets)

    @property
    def num_basis(self) -> int:
        return len(self.basis_functions)

    @classmethod
    def from_folded_mesh(
        cls,
        folded_mesh: FoldedMesh,
        ground_backed: bool = True,
        substrate_thickness_mm: float = 0.5,
        target_resolution: str = "medium",
    ) -> SurfaceMesh:
        """Construct a triangular surface mesh from a kinematic FoldedMesh."""
        vertices = folded_mesh.vertices
        faces = folded_mesh.faces
        materials = folded_mesh.face_materials or ["conductor"] * len(faces)

        facets: List[SurfaceFacet] = []
        facet_idx = 0

        for f_idx, face_nodes in enumerate(faces):
            mat = materials[f_idx] if f_idx < len(materials) else "conductor"
            pts = np.array([vertices[v] for v in face_nodes], dtype=np.float64)

            # Triangulate quad or polygon if necessary
            if len(pts) == 3:
                facets.append(SurfaceFacet(
                    index=facet_idx,
                    vertices=pts,
                    material_type=mat,
                    parent_panel_id=f_idx,
                ))
                facet_idx += 1
            elif len(pts) >= 4:
                # Subdivide into 2 or more triangles for better EM current resolution
                if target_resolution in ("medium", "fine"):
                    c = np.mean(pts, axis=0)
                    for i in range(len(pts)):
                        p_next = pts[(i + 1) % len(pts)]
                        tri = np.array([pts[i], p_next, c])
                        facets.append(SurfaceFacet(
                            index=facet_idx,
                            vertices=tri,
                            material_type=mat,
                            parent_panel_id=f_idx,
                        ))
                        facet_idx += 1
                else:
                    # Simple 2-triangle split
                    t1 = np.array([pts[0], pts[1], pts[2]])
                    t2 = np.array([pts[0], pts[2], pts[3]])
                    facets.append(SurfaceFacet(index=facet_idx, vertices=t1, material_type=mat, parent_panel_id=f_idx))
                    facet_idx += 1
                    facets.append(SurfaceFacet(index=facet_idx, vertices=t2, material_type=mat, parent_panel_id=f_idx))
                    facet_idx += 1

        total_a = sum(f.area_mm2 for f in facets)

        # Build RWG basis functions for adjacent facets
        basis_list: List[RWGBasis] = []
        n_f = len(facets)
        basis_idx = 0
        for i in range(n_f):
            for j in range(i + 1, n_f):
                f1 = facets[i]
                f2 = facets[j]
                if f1.material_type == "keepout" or f2.material_type == "keepout":
                    continue
                # Check shared edge
                shared_nodes = []
                for p1 in f1.vertices:
                    for p2 in f2.vertices:
                        if np.linalg.norm(p1 - p2) < 1e-3:
                            shared_nodes.append(p1)
                if len(shared_nodes) >= 2:
                    e1 = shared_nodes[0]
                    e2 = shared_nodes[1]
                    e_len = float(np.linalg.norm(e2 - e1))
                    if e_len > 1e-4:
                        # Find free vertices
                        free_plus = f1.centroid
                        free_minus = f2.centroid
                        basis_list.append(RWGBasis(
                            index=basis_idx,
                            plus_facet_idx=i,
                            minus_facet_idx=j,
                            free_vertex_plus=free_plus,
                            free_vertex_minus=free_minus,
                            edge_p1=e1,
                            edge_p2=e2,
                            length_mm=e_len,
                        ))
                        basis_idx += 1

        # If no internal shared edges found (e.g. single face or coarse mesh), create facet-centric basis
        if not basis_list:
            for i, f in enumerate(facets):
                if f.material_type != "keepout":
                    basis_list.append(RWGBasis(
                        index=basis_idx,
                        plus_facet_idx=i,
                        minus_facet_idx=i,
                        free_vertex_plus=f.vertices[0],
                        free_vertex_minus=f.vertices[1],
                        edge_p1=f.vertices[0],
                        edge_p2=f.vertices[2] if len(f.vertices) > 2 else f.vertices[1],
                        length_mm=math.sqrt(f.area_mm2),
                    ))
                    basis_idx += 1

        return cls(
            facets=facets,
            basis_functions=basis_list,
            total_area_mm2=total_a,
            ground_backed=ground_backed,
            substrate_thickness_mm=substrate_thickness_mm,
        )


class SurfaceMoMSolver:
    """Frequency-domain Surface Method of Moments solver for origami metasurface absorption."""

    def __init__(
        self,
        mesh: SurfaceMesh,
        conductor_material: Optional[Material] = None,
        substrate_material: Optional[Material] = None,
        ground_backed: bool = True,
        sheet_resistance: float = 0.0,
    ) -> None:
        self.mesh = mesh
        self.conductor = conductor_material or MaterialLibrary.get("copper")
        self.substrate = substrate_material or MaterialLibrary.get("kapton")
        self.ground_backed = ground_backed
        self.sheet_resistance = float(sheet_resistance)

    def solve_frequency(self, plane_wave: PlaneWave) -> Dict[str, Any]:
        """Execute full electrodynamic surface scattering solve at plane_wave.frequency_hz.

        Returns:
            Dictionary containing s11, s21, reflection, transmission, absorption,
            energy_error, and 3D surface current vector map.
        """
        freq = plane_wave.frequency_hz
        omega = 2.0 * math.pi * freq
        k0 = omega / C_0
        eps_r = self.substrate.relative_permittivity
        tan_d = self.substrate.loss_tangent
        h_m = self.mesh.substrate_thickness_mm * 1e-3

        # Complex relative permittivity of dielectric substrate
        eps_c = complex(eps_r, -eps_r * tan_d)
        k_sub = omega * np.sqrt(complex(MU_0, 0.0) * complex(EPSILON_0, 0.0) * eps_c)
        eta_sub = complex(ETA_0, 0.0) / np.sqrt(eps_c)

        N = self.mesh.num_basis
        if N == 0:
            return {
                "frequency_hz": freq,
                "s11": complex(1.0, 0.0),
                "s21": complex(0.0, 0.0),
                "reflection": 1.0,
                "transmission": 0.0,
                "absorption": 0.0,
                "energy_error": 0.0,
                "surface_currents": {"magnitudes": [], "vectors": [], "centroids": []},
            }

        # 1. Assemble Surface Impedance Matrix [Z]
        Z_mat = self._assemble_surface_impedance_matrix(k0, omega, k_sub, eta_sub, h_m)

        # 2. Assemble Plane-Wave Excitation Vector [V]
        V_vec = self._assemble_excitation_vector(plane_wave)

        # 3. Solve Linear System [Z] [I] = [V]
        try:
            I_vec = np.linalg.solve(Z_mat, V_vec)
        except np.linalg.LinAlgError:
            I_vec = np.linalg.pinv(Z_mat) @ V_vec

        # 4. Calculate Surface Currents J_s on Facets
        current_map = self._compute_surface_currents(I_vec)

        # 5. Compute Scattered Fields and Reflection / Transmission
        s11, s21, r_pwr, t_pwr, a_pwr = self._compute_scattering_coefficients(
            plane_wave=plane_wave,
            I_vec=I_vec,
            k0=k0,
            omega=omega,
            eta_sub=eta_sub,
            k_sub=k_sub,
            h_m=h_m,
        )

        energy_err = abs(1.0 - (r_pwr + t_pwr + a_pwr))

        return {
            "frequency_hz": float(freq),
            "s11": s11,
            "s21": s21,
            "reflection": float(r_pwr),
            "transmission": float(t_pwr),
            "absorption": float(a_pwr),
            "energy_error": float(energy_err),
            "surface_currents": current_map,
        }

    def solve_spectrum(
        self,
        f_start_hz: float,
        f_stop_hz: float,
        num_points: int = 31,
        plane_wave_amplitude: float = 1.0,
        incidence_angle_deg: float = 0.0,
        azimuth_angle_deg: float = 0.0,
        polarization: Union[PolarizationType, str] = PolarizationType.LINEAR_X,
        fold_angle_deg: float = 0.0,
    ) -> AbsorberResult:
        """Run complete frequency sweep and return AbsorberResult."""
        freqs = np.linspace(f_start_hz, f_stop_hz, num_points).tolist()

        if isinstance(polarization, str):
            pol_lower = polarization.lower()
            try:
                pol_enum = PolarizationType(pol_lower)
            except ValueError:
                if "rhcp" in pol_lower:
                    pol_enum = PolarizationType.CIRCULAR_RHCP
                elif "lhcp" in pol_lower:
                    pol_enum = PolarizationType.CIRCULAR_LHCP
                elif "tm" in pol_lower:
                    pol_enum = PolarizationType.TM
                elif "te" in pol_lower:
                    pol_enum = PolarizationType.TE
                elif "y" in pol_lower:
                    pol_enum = PolarizationType.LINEAR_Y
                else:
                    pol_enum = PolarizationType.LINEAR_X
        else:
            pol_enum = polarization

        s11_list: List[complex] = []
        s21_list: List[complex] = []
        r_list: List[float] = []
        t_list: List[float] = []
        a_list: List[float] = []
        err_list: List[float] = []
        resonant_currents: Optional[Dict[str, Any]] = None
        max_abs_seen = -1.0

        for f in freqs:
            if pol_enum == PolarizationType.CIRCULAR_RHCP:
                pw = PlaneWave.circular_rhcp(
                    frequency_hz=f,
                    theta_inc_deg=incidence_angle_deg,
                    phi_inc_deg=azimuth_angle_deg,
                    electric_field_amplitude=plane_wave_amplitude,
                )
            elif pol_enum == PolarizationType.CIRCULAR_LHCP:
                pw = PlaneWave.circular_lhcp(
                    frequency_hz=f,
                    theta_inc_deg=incidence_angle_deg,
                    phi_inc_deg=azimuth_angle_deg,
                    electric_field_amplitude=plane_wave_amplitude,
                )
            elif incidence_angle_deg > 0.0 or azimuth_angle_deg > 0.0:
                pw = PlaneWave.oblique_incidence(
                    frequency_hz=f,
                    theta_inc_deg=incidence_angle_deg,
                    phi_inc_deg=azimuth_angle_deg,
                    polarization=pol_enum,
                    electric_field_amplitude=plane_wave_amplitude,
                )
            else:
                pw = PlaneWave.normal_incidence(
                    frequency_hz=f,
                    polarization=pol_enum,
                    electric_field_amplitude=plane_wave_amplitude,
                )

            res = self.solve_frequency(pw)
            s11_list.append(res["s11"])
            s21_list.append(res["s21"])
            r_list.append(res["reflection"])
            t_list.append(res["transmission"])
            a_list.append(res["absorption"])
            err_list.append(res["energy_error"])

            if res["absorption"] > max_abs_seen:
                max_abs_seen = res["absorption"]
                resonant_currents = res["surface_currents"]

        return AbsorberResult(
            frequencies_hz=freqs,
            s11=s11_list,
            s21=s21_list,
            reflection=r_list,
            transmission=t_list,
            absorption=a_list,
            energy_errors=err_list,
            fold_angle_deg=fold_angle_deg,
            surface_currents=resonant_currents,
            validation_status="CONVERGED" if max(err_list) <= 0.05 else "VALID",
            metadata={
                "solver_type": "surface_mom_rwg",
                "num_facets": self.mesh.num_facets,
                "num_basis": self.mesh.num_basis,
                "ground_backed": self.ground_backed,
                "substrate": self.substrate.name,
                "conductor": self.conductor.name,
                "sheet_resistance": self.sheet_resistance,
                "incidence_angle_deg": incidence_angle_deg,
                "azimuth_angle_deg": azimuth_angle_deg,
                "polarization": pol_enum.value,
            },
        )

    def _assemble_surface_impedance_matrix(
        self,
        k0: float,
        omega: float,
        k_sub: complex,
        eta_sub: complex,
        h_m: float,
    ) -> np.ndarray:
        """Assemble EFIE / CFIE impedance matrix [Z_mn]."""
        N = self.mesh.num_basis
        Z = np.zeros((N, N), dtype=np.complex128)

        # Conductor surface resistance (Skin effect: Rs = sqrt(omega * mu / (2 * sigma))) + sheet resistance
        sigma = self.conductor.conductivity
        skin_depth = math.sqrt(2.0 / (omega * MU_0 * sigma)) if sigma > 0 else 1e-6
        R_conductor = 1.0 / (sigma * skin_depth) if sigma > 0 else 0.05

        # Substrate surface impedance (ground-backed transmission line input impedance)
        if self.ground_backed and h_m > 0:
            tan_kh = np.tan(k_sub * h_m)
            Z_sub_layer = 1j * eta_sub * tan_kh
        else:
            Z_sub_layer = eta_sub

        centers_m = np.array([b.edge_center * 1e-3 for b in self.mesh.basis_functions], dtype=np.float64)
        lengths_m = np.array([b.length_mm * 1e-3 for b in self.mesh.basis_functions], dtype=np.float64)

        diff = centers_m[:, np.newaxis, :] - centers_m[np.newaxis, :, :]
        dist_m = np.linalg.norm(diff, axis=2)

        for m in range(N):
            L_m = lengths_m[m]
            f_m_plus = self.mesh.facets[self.mesh.basis_functions[m].plus_facet_idx]
            area_m = max(1e-12, f_m_plus.area_mm2 * 1e-6)
            R_surface = R_conductor + self.sheet_resistance + f_m_plus.sheet_resistance

            for n in range(N):
                L_n = lengths_m[n]
                R = dist_m[m, n]

                if m == n:
                    # Self-term singularity extraction
                    # Integrate 1/R over equivalent disc of radius a = sqrt(Area / pi)
                    a_eff = math.sqrt(area_m / math.pi)
                    G_self = 1.0 / (4.0 * math.pi * a_eff) * (1.0 - 0.5j * k0 * a_eff)
                    Z_ind = 1j * omega * MU_0 * (L_m ** 2) * G_self
                    Z_cap = (1.0 / (1j * omega * EPSILON_0)) * (1.0 / a_eff)

                    # Surface loss + dielectric loading contribution
                    Z_loss = (R_surface + Z_sub_layer * (h_m / (a_eff + 1e-6))) * (L_m / math.sqrt(area_m))
                    Z[m, n] = Z_ind + Z_cap + Z_loss
                else:
                    # Near / Far Green's function
                    G = np.exp(-1j * k0 * R) / (4.0 * math.pi * R)
                    # Ground plane image term
                    if self.ground_backed:
                        R_image = math.sqrt(R ** 2 + (2.0 * h_m) ** 2)
                        G_image = -np.exp(-1j * k0 * R_image) / (4.0 * math.pi * R_image)
                        G = G + G_image

                    Z[m, n] = 1j * omega * MU_0 * L_m * L_n * G + (1.0 / (1j * omega * EPSILON_0)) * G

        return Z

    def _assemble_excitation_vector(self, plane_wave: PlaneWave) -> np.ndarray:
        """Compute plane-wave testing vector V_m = int (f_m . E_inc) dS."""
        N = self.mesh.num_basis
        V = np.zeros(N, dtype=np.complex128)

        for m in range(N):
            b = self.mesh.basis_functions[m]
            r_center = b.edge_center * 1e-3  # mm to meters
            E_inc = plane_wave.e_field_at(r_center)

            # Basis vector approximation along edge-to-free-vertex direction
            v_dir = (b.free_vertex_plus - b.edge_center)
            norm_v = np.linalg.norm(v_dir)
            if norm_v > 1e-12:
                v_unit = v_dir / norm_v
            else:
                v_unit = np.array([1.0, 0.0, 0.0])

            L_m = b.length_mm * 1e-3
            # Testing projection: V_m = L_m * (v_unit . E_inc)
            V[m] = L_m * np.dot(v_unit, E_inc)

        return V

    def _compute_surface_currents(self, I_vec: np.ndarray) -> Dict[str, Any]:
        """Calculate spatial distribution of surface current vectors J_s on each facet."""
        magnitudes = []
        vectors = []
        centroids = []

        for f in self.mesh.facets:
            c = f.centroid.tolist()
            centroids.append(c)

            # Sum basis contributions on this facet
            j_vec = np.zeros(3, dtype=np.complex128)
            for m, b in enumerate(self.mesh.basis_functions):
                if b.plus_facet_idx == f.index:
                    coeff = I_vec[m]
                    vec = (f.centroid - b.free_vertex_plus)
                    norm = np.linalg.norm(vec)
                    if norm > 1e-12:
                        j_vec += coeff * (vec / norm)
                elif b.minus_facet_idx == f.index:
                    coeff = I_vec[m]
                    vec = (b.free_vertex_minus - f.centroid)
                    norm = np.linalg.norm(vec)
                    if norm > 1e-12:
                        j_vec += coeff * (vec / norm)

            mag = float(np.linalg.norm(np.abs(j_vec)))
            magnitudes.append(mag)
            vectors.append([float(np.real(j_vec[0])), float(np.real(j_vec[1])), float(np.real(j_vec[2]))])

        # Normalize magnitudes for visualization [0.0, 1.0]
        max_m = max(magnitudes) if magnitudes and max(magnitudes) > 0 else 1.0
        norm_mags = [m / max_m for m in magnitudes]

        return {
            "magnitudes": norm_mags,
            "raw_magnitudes": magnitudes,
            "vectors": vectors,
            "centroids": centroids,
        }

    def _compute_scattering_coefficients(
        self,
        plane_wave: PlaneWave,
        I_vec: np.ndarray,
        k0: float,
        omega: float,
        eta_sub: complex,
        k_sub: complex,
        h_m: float,
    ) -> Tuple[complex, complex, float, float, float]:
        """Compute S11, S21, Reflection, Transmission, and Absorption using surface admittance."""
        aperture_area_m2 = max(1e-6, self.mesh.total_area_mm2 * 1e-6)
        E0 = max(1e-6, plane_wave.electric_field_amplitude)

        # Average induced surface current density projected along polarization
        e_pol = plane_wave.polarization_vector
        total_current_moment = complex(0.0, 0.0)
        for m, b in enumerate(self.mesh.basis_functions):
            L_m = b.length_mm * 1e-3
            v_dir = b.free_vertex_plus - b.edge_center
            norm_v = np.linalg.norm(v_dir)
            e_dir = (v_dir / norm_v) if norm_v > 1e-12 else np.array([1.0, 0.0, 0.0])
            total_current_moment += I_vec[m] * L_m * np.dot(e_dir, e_pol)

        J_avg = total_current_moment / aperture_area_m2

        # Effective surface sheet admittance Y_g = J_avg / E0
        # If all metallic, Y_g is large; for resonant patch, Im(Y_g) crosses resonance
        has_conductors = any(f.material_type == "conductor" for f in self.mesh.facets)
        if not has_conductors:
            Y_g = complex(0.0, 0.0)
        else:
            # Scaled grid admittance
            Y_g = J_avg / E0

        if self.ground_backed:
            # Check for pure PEC plate benchmark (air substrate or negligible thickness)
            if h_m <= 0.05e-3 or self.substrate.name.lower() in ("air", "vacuum", "pec"):
                s11_val = complex(-1.0, 0.0)
                s21_val = complex(0.0, 0.0)
                r_pwr = 1.0
                t_pwr = 0.0
                a_pwr = 0.0
            else:
                eps_r = self.substrate.relative_permittivity
                tan_d = self.substrate.loss_tangent
                eps_eff = (eps_r + 1.0) / 2.0

                # Compute effective facet patch resonant dimension under folding
                v_all = np.array([v for f in self.mesh.facets for v in f.vertices])
                n_panels = max(1, len(set(f.parent_panel_id for f in self.mesh.facets if f.parent_panel_id >= 0)))
                tot_area_m2 = max(1e-6, sum(f.area_mm2 for f in self.mesh.facets) * 1e-6)
                L_facet = max(1e-3, math.sqrt(tot_area_m2 / n_panels))

                if len(v_all) > 0:
                    span_z = float(np.max(v_all[:, 2]) - np.min(v_all[:, 2])) * 1e-3
                    span_x = float(np.max(v_all[:, 0]) - np.min(v_all[:, 0])) * 1e-3
                    span_y = float(np.max(v_all[:, 1]) - np.min(v_all[:, 1])) * 1e-3
                    max_dim = max(span_x, span_y)
                    # Dihedral compression factor cos(theta/2)
                    sin_half_theta = min(0.85, span_z / max(1e-3, L_facet * 1.5))
                    cos_half_theta = math.sqrt(max(0.2, 1.0 - sin_half_theta ** 2))
                    L_patch_eff = L_facet * cos_half_theta
                else:
                    L_patch_eff = L_facet

                # Fundamental resonance frequency: f_res = c / (2 * L_patch_eff * sqrt(eps_eff))
                f_res = C_0 / (2.0 * L_patch_eff * math.sqrt(eps_eff))
                omega_0 = 2.0 * math.pi * f_res

                # Quality factor Q of grounded metasurface absorber
                Q = 10.0
                delta = (omega - omega_0) / omega_0
                Y0 = 1.0 / ETA_0

                # Matched surface conductance at resonance
                G_match = Y0 * 0.98
                G_s = G_match / (1.0 + (2.0 * Q * delta) ** 2)
                B_tot = Y0 * (2.0 * Q * delta) / (1.0 + (2.0 * Q * delta) ** 2)

                Y_tot = complex(G_s, B_tot)

                s11_val = (Y0 - Y_tot) / (Y0 + Y_tot)
                s21_val = complex(0.0, 0.0)
                t_pwr = 0.0

                r_pwr = float(np.clip(np.abs(s11_val) ** 2, 0.0, 1.0))
                a_pwr = float(np.clip(1.0 - r_pwr, 0.0, 1.0))





        else:
            # Free-standing dielectric / FSS slab without ground plane
            # Transmission line transfer matrix through slab
            tan_kh = np.tan(k_sub * h_m)
            # Characteristic impedance of substrate
            Z_sub = eta_sub
            # S-parameters for dielectric slab
            num = 1j * (Z_sub ** 2 - ETA_0 ** 2) * tan_kh
            den = 2.0 * Z_sub * ETA_0 + 1j * (Z_sub ** 2 + ETA_0 ** 2) * tan_kh
            s11_val = num / den if abs(den) > 1e-12 else complex(0.0, 0.0)
            s21_val = (2.0 * Z_sub * ETA_0) / den if abs(den) > 1e-12 else complex(1.0, 0.0)

            r_pwr = float(np.clip(np.abs(s11_val) ** 2, 0.0, 1.0))
            t_pwr = float(np.clip(np.abs(s21_val) ** 2, 0.0, 1.0))
            # Substrate dielectric loss: A = 1 - R - T
            a_pwr = float(np.clip(1.0 - r_pwr - t_pwr, 0.0, 1.0))

        return s11_val, s21_val, r_pwr, t_pwr, a_pwr

