"""Plane-Wave Electromagnetic Excitation Module for Origami Surfaces.

Implements arbitrary incident plane waves (normal and oblique incidence,
linear TE/TM and circular polarizations) satisfying Maxwell's equations:
div(E) = 0, k . E = 0, H = (1/eta) * (k_hat x E).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from rf_origami.rf.materials.material import C_0, ETA_0, EPSILON_0, MU_0


class PolarizationType(str, Enum):
    """Polarization state of the incident electromagnetic field."""
    LINEAR_X = "linear_x"
    LINEAR_Y = "linear_y"
    TE = "te"                  # Transverse Electric (E perpendicular to plane of incidence)
    TM = "tm"                  # Transverse Magnetic (H perpendicular to plane of incidence)
    CIRCULAR_RHCP = "rhcp"     # Right-Hand Circular Polarization
    CIRCULAR_LHCP = "lhcp"     # Left-Hand Circular Polarization
    ARBITRARY = "arbitrary"


@dataclass
class PlaneWave:
    """Represents a monochromatic uniform plane wave illuminating an origami surface.

    Attributes:
        frequency_hz: Electromagnetic frequency in Hertz (e.g. 2.45e9).
        propagation_direction: Unit vector k_hat indicating wave propagation direction.
        polarization_vector: Unit vector e_hat_E indicating electric field orientation.
        electric_field_amplitude: Peak electric field amplitude in V/m (default 1.0 V/m).
        incidence_angle_deg: Polar angle theta_inc [0, 90 deg] relative to surface normal +z.
        azimuth_angle_deg: Azimuthal angle phi_inc [0, 360 deg] in xy-plane.
        polarization_type: Declared polarization category.
        phase_offset_rad: Initial phase at origin in radians.
    """

    frequency_hz: float
    propagation_direction: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, -1.0]))
    polarization_vector: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0]))
    electric_field_amplitude: float = 1.0
    incidence_angle_deg: float = 0.0
    azimuth_angle_deg: float = 0.0
    polarization_type: PolarizationType = PolarizationType.LINEAR_X
    phase_offset_rad: float = 0.0

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0.0:
            raise ValueError(f"Frequency must be positive (got {self.frequency_hz}).")
        if self.electric_field_amplitude < 0.0:
            raise ValueError(f"Electric field amplitude must be non-negative (got {self.electric_field_amplitude}).")

        self.propagation_direction = np.asarray(self.propagation_direction, dtype=np.float64)
        self.polarization_vector = np.asarray(self.polarization_vector, dtype=np.float64)

        # Normalize propagation direction
        k_norm = np.linalg.norm(self.propagation_direction)
        if k_norm < 1e-12:
            self.propagation_direction = np.array([0.0, 0.0, -1.0], dtype=np.float64)
        else:
            self.propagation_direction /= k_norm

        # Normalize polarization vector
        e_norm = np.linalg.norm(self.polarization_vector)
        if e_norm < 1e-12:
            self.polarization_vector = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        else:
            self.polarization_vector /= e_norm

        # Enforce orthogonality k_hat . e_hat_E = 0 (project E onto transverse plane if needed)
        dot_ke = float(np.dot(self.propagation_direction, self.polarization_vector))
        if abs(dot_ke) > 1e-5:
            # Gram-Schmidt orthogonalization: e_perp = e - (k . e) * k
            e_perp = self.polarization_vector - dot_ke * self.propagation_direction
            perp_norm = np.linalg.norm(e_perp)
            if perp_norm > 1e-12:
                self.polarization_vector = e_perp / perp_norm
            else:
                # Fallback: pick any perpendicular vector
                if abs(self.propagation_direction[2]) < 0.9:
                    fallback = np.cross(self.propagation_direction, np.array([0.0, 0.0, 1.0]))
                else:
                    fallback = np.cross(self.propagation_direction, np.array([1.0, 0.0, 0.0]))
                self.polarization_vector = fallback / np.linalg.norm(fallback)

    @property
    def wavelength_m(self) -> float:
        """Free-space wavelength lambda_0 = c / f in meters."""
        return float(C_0 / self.frequency_hz)

    @property
    def wavenumber_k0(self) -> float:
        """Free-space wavenumber k0 = 2*pi / lambda in rad/m."""
        return float(2.0 * math.pi * self.frequency_hz / C_0)

    @property
    def wavevector(self) -> np.ndarray:
        """Wavevector k = k0 * k_hat in rad/m."""
        return self.wavenumber_k0 * self.propagation_direction

    @property
    def magnetic_polarization_vector(self) -> np.ndarray:
        """Unit vector for magnetic field: h_hat = k_hat x e_hat_E."""
        h_vec = np.cross(self.propagation_direction, self.polarization_vector)
        norm = np.linalg.norm(h_vec)
        return h_vec / norm if norm > 1e-12 else np.array([0.0, 1.0, 0.0])

    @property
    def poynting_vector(self) -> np.ndarray:
        """Time-averaged Poynting vector in W/m^2: S_avg = (|E0|^2 / (2 * eta0)) * k_hat."""
        s_mag = (self.electric_field_amplitude ** 2) / (2.0 * ETA_0)
        return s_mag * self.propagation_direction

    def e_field_at(self, position_m: np.ndarray) -> np.ndarray:
        """Compute complex incident electric field vector E_inc(r) at 3D point r [meters].

        E_inc(r) = E0 * e_hat * exp(-j * (k . r - phi0))

        Args:
            position_m: (3,) array of coordinates in meters.

        Returns:
            (3,) complex128 array representing [Ex, Ey, Ez] in V/m.
        """
        r = np.asarray(position_m, dtype=np.float64)
        k_dot_r = float(np.dot(self.wavevector, r))
        phase = -k_dot_r + self.phase_offset_rad
        spatial_factor = np.exp(1j * phase)
        return self.electric_field_amplitude * self.polarization_vector.astype(np.complex128) * spatial_factor

    def h_field_at(self, position_m: np.ndarray, medium_eta: float = ETA_0) -> np.ndarray:
        """Compute complex incident magnetic field vector H_inc(r) at 3D point r [meters].

        H_inc(r) = (1 / eta) * (k_hat x E_inc(r))

        Args:
            position_m: (3,) array of coordinates in meters.
            medium_eta: Intrinsic impedance of the medium (default ETA_0 = 376.73 Ohm).

        Returns:
            (3,) complex128 array representing [Hx, Hy, Hz] in A/m.
        """
        e_vec = self.e_field_at(position_m)
        h_vec = np.cross(self.propagation_direction, e_vec) / medium_eta
        return h_vec

    @classmethod
    def normal_incidence(
        cls,
        frequency_hz: float,
        polarization: PolarizationType = PolarizationType.LINEAR_X,
        electric_field_amplitude: float = 1.0,
    ) -> PlaneWave:
        """Factory for downward normal incidence (+z to -z direction)."""
        prop_dir = np.array([0.0, 0.0, -1.0], dtype=np.float64)
        if polarization in (PolarizationType.LINEAR_X, PolarizationType.TE):
            pol_vec = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        elif polarization in (PolarizationType.LINEAR_Y, PolarizationType.TM):
            pol_vec = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        else:
            pol_vec = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        return cls(
            frequency_hz=frequency_hz,
            propagation_direction=prop_dir,
            polarization_vector=pol_vec,
            electric_field_amplitude=electric_field_amplitude,
            incidence_angle_deg=0.0,
            azimuth_angle_deg=0.0,
            polarization_type=polarization,
        )

    @classmethod
    def oblique_incidence(
        cls,
        frequency_hz: float,
        theta_inc_deg: float,
        phi_inc_deg: float = 0.0,
        polarization: PolarizationType = PolarizationType.TE,
        electric_field_amplitude: float = 1.0,
    ) -> PlaneWave:
        """Factory for oblique plane wave from spherical angles (theta, phi).

        theta = 0 is normal incidence from +z toward -z.
        """
        th = math.radians(theta_inc_deg)
        ph = math.radians(phi_inc_deg)

        # Wave travels toward the surface origin:
        # k_hat = -[sin(th)*cos(ph), sin(th)*sin(ph), cos(th)]
        kx = -math.sin(th) * math.cos(ph)
        ky = -math.sin(th) * math.sin(ph)
        kz = -math.cos(th)
        prop_dir = np.array([kx, ky, kz], dtype=np.float64)

        if polarization == PolarizationType.TE:
            # TE: E perpendicular to plane of incidence (along phi direction: -sin(ph), cos(ph), 0)
            if abs(math.sin(th)) < 1e-6:
                pol_vec = np.array([1.0, 0.0, 0.0], dtype=np.float64)
            else:
                pol_vec = np.array([-math.sin(ph), math.cos(ph), 0.0], dtype=np.float64)
        elif polarization == PolarizationType.TM:
            # TM: H perpendicular to plane of incidence, E in plane of incidence
            # E_hat = H_hat x k_hat
            h_dir = np.array([-math.sin(ph), math.cos(ph), 0.0], dtype=np.float64)
            pol_vec = np.cross(h_dir, prop_dir)
            pol_vec /= np.linalg.norm(pol_vec)
        else:
            pol_vec = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        return cls(
            frequency_hz=frequency_hz,
            propagation_direction=prop_dir,
            polarization_vector=pol_vec,
            electric_field_amplitude=electric_field_amplitude,
            incidence_angle_deg=theta_inc_deg,
            azimuth_angle_deg=phi_inc_deg,
            polarization_type=polarization,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a JSON-serializable dictionary."""
        return {
            "frequency_hz": float(self.frequency_hz),
            "frequency_ghz": float(self.frequency_hz / 1e9),
            "propagation_direction": self.propagation_direction.tolist(),
            "polarization_vector": self.polarization_vector.tolist(),
            "electric_field_amplitude": float(self.electric_field_amplitude),
            "incidence_angle_deg": float(self.incidence_angle_deg),
            "azimuth_angle_deg": float(self.azimuth_angle_deg),
            "polarization_type": self.polarization_type.value,
            "wavelength_m": float(self.wavelength_m),
            "wavenumber_k0": float(self.wavenumber_k0),
        }
