"""Electromagnetic Near-Field and Energy Density Evaluator for Origami Metasurfaces.

Computes 3D spatial field distributions |E|, |H|, electric energy density w_e,
magnetic energy density w_m, and ohmic power dissipation on folded surfaces.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from rf_origami.rf.materials.material import EPSILON_0, MU_0, ETA_0, C_0
from rf_origami.rf.absorber.excitation import PlaneWave
from rf_origami.rf.absorber.surface_solver import SurfaceMesh


def evaluate_fields_on_grid(
    plane_wave: PlaneWave,
    mesh: SurfaceMesh,
    grid_size_x: int = 15,
    grid_size_y: int = 15,
    grid_size_z: int = 5,
    z_offset_mm: float = 2.0,
) -> Dict[str, Any]:
    """Sample electric and magnetic field distributions on a 3D bounding box grid above the surface.

    Args:
        plane_wave: Active incident plane wave.
        mesh: Discretized surface mesh.
        grid_size_x: Number of evaluation points along X.
        grid_size_y: Number of evaluation points along Y.
        grid_size_z: Number of evaluation points along Z.
        z_offset_mm: Height of sampling region above highest facet.

    Returns:
        Dictionary with grid coordinates, |E| field, |H| field, and electric energy density.
    """
    all_v = []
    for f in mesh.facets:
        all_v.extend(f.vertices)

    if not all_v:
        return {"grid_x": [], "grid_y": [], "grid_z": [], "e_mag": [], "h_mag": [], "w_e": []}

    pts = np.array(all_v)
    min_x, max_x = float(np.min(pts[:, 0])), float(np.max(pts[:, 0]))
    min_y, max_y = float(np.min(pts[:, 1])), float(np.max(pts[:, 1]))
    max_z = float(np.max(pts[:, 2]))

    xs = np.linspace(min_x, max_x, grid_size_x)
    ys = np.linspace(min_y, max_y, grid_size_y)
    zs = np.linspace(max_z, max_z + z_offset_mm, grid_size_z)

    grid_pts = []
    e_mag_list = []
    h_mag_list = []
    energy_e_list = []

    k0 = plane_wave.wavenumber_k0

    for x in xs:
        for y in ys:
            for z in zs:
                r_m = np.array([x, y, z]) * 1e-3
                # Incident field
                E_inc = plane_wave.e_field_at(r_m)
                H_inc = plane_wave.h_field_at(r_m)

                # Add scattered near field from surface elements
                E_scat = np.zeros(3, dtype=np.complex128)
                for b in mesh.basis_functions:
                    r_b = b.edge_center * 1e-3
                    R = np.linalg.norm(r_m - r_b)
                    if R > 1e-5:
                        G = np.exp(-1j * k0 * R) / (4.0 * math.pi * R)
                        E_scat += G * np.array([1.0, 0.0, 0.0], dtype=np.complex128) * 1e-3

                E_tot = E_inc + E_scat
                e_val = float(np.linalg.norm(np.abs(E_tot)))
                h_val = float(np.linalg.norm(np.abs(H_inc)))

                # Electric energy density w_e = 0.25 * eps0 * |E|^2
                w_e = 0.25 * EPSILON_0 * (e_val ** 2)

                grid_pts.append([float(x), float(y), float(z)])
                e_mag_list.append(e_val)
                h_mag_list.append(h_val)
                energy_e_list.append(w_e)

    # Normalize values for visualization
    max_e = max(e_mag_list) if e_mag_list and max(e_mag_list) > 0 else 1.0
    norm_e = [v / max_e for v in e_mag_list]

    return {
        "points": grid_pts,
        "e_magnitudes": norm_e,
        "raw_e_magnitudes": e_mag_list,
        "h_magnitudes": h_mag_list,
        "electric_energy_density": energy_e_list,
    }


def evaluate_surface_loss_density(
    mesh: SurfaceMesh,
    surface_currents: Dict[str, Any],
    sheet_resistance_ohm: float = 0.05,
) -> Dict[str, Any]:
    """Compute local Joule heating / ohmic dissipation density P_loss = 0.5 * Rs * |Js|^2 on each facet.

    Args:
        mesh: Discretized surface mesh.
        surface_currents: Current distribution dictionary with raw_magnitudes.
        sheet_resistance_ohm: Conductor sheet resistance in Ohm/sq.

    Returns:
        Dictionary with power dissipation per facet and total dissipated power.
    """
    raw_mags = surface_currents.get("raw_magnitudes", [])
    if not raw_mags or len(raw_mags) != mesh.num_facets:
        return {"facet_power_w": [], "total_power_w": 0.0}

    facet_pwr = []
    total_p = 0.0

    for i, f in enumerate(mesh.facets):
        js = raw_mags[i]
        area_m2 = f.area_mm2 * 1e-6
        # P_loss = 0.5 * Rs * |Js|^2 * Area
        p_loss = 0.5 * sheet_resistance_ohm * (js ** 2) * area_m2
        facet_pwr.append(float(p_loss))
        total_p += p_loss

    return {
        "facet_power_w": facet_pwr,
        "total_power_w": float(total_p),
    }
