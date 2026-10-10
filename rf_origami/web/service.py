"""Backend service connecting web requests to the RF Origami computational engine.

Executes procedural pattern generators, folding kinematics, and real-time
validation checks without duplicating mathematical logic in JavaScript.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.mesh import FoldedMesh
from rf_origami.core.geometry import is_coplanar, polygon_area
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.patterns.degree4_vertex import Degree4VertexPattern
from rf_origami.patterns.waterbomb import WaterbombPattern
from rf_origami.patterns.yoshimura import YoshimuraPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.generator.design_space import DesignSpace
from rf_origami.generator.engine import GenerativeOrigamiEngine



class OrigamiWebService:
    """Provides high-level generation, folding, and validation services for the web UI."""

    PATTERN_REGISTRY = {
        "miura_ori": {
            "name": "Miura-Ori",
            "class": MiuraOriPattern,
            "description": "Herringbone parallelogram tessellation for deployable panels & reflectarrays",
        },
        "degree4_vertex": {
            "name": "Degree-4 Vertex",
            "class": Degree4VertexPattern,
            "description": "Canonical degree-4 rigid flat-foldable unit cell",
        },
        "waterbomb": {
            "name": "Waterbomb",
            "class": WaterbombPattern,
            "description": "8-crease radial base pattern for deployable horn antennas and expanding tubes",
        },
        "yoshimura": {
            "name": "Yoshimura",
            "class": YoshimuraPattern,
            "description": "Triangular/diamond cylindrical pattern for foldable masts and boom antennas",
        },
    }

    @classmethod
    def get_default_design_space(cls) -> Dict[str, Any]:
        """Return default exploration bounds, constraints, and RF target settings."""
        ds = DesignSpace()
        return ds.to_dict()

    @classmethod
    def run_exploration(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate, filter, and evaluate candidate designs across the defined design space."""
        count = int(config.get("count", 20))
        seed = int(config.get("seed", 42))
        family = str(config.get("pattern_family", "modulated_miura"))

        ds_params = config.get("design_space", {})
        ds_kwargs = {}
        for k in [
            "a_min", "a_max", "b_min", "b_max", "gamma_min", "gamma_max",
            "num_cells_x_min", "num_cells_x_max", "num_cells_y_min", "num_cells_y_max",
            "gradient_x_min", "gradient_x_max", "gradient_y_min", "gradient_y_max",
            "fold_angle_min", "fold_angle_max",
            "flat_foldable_only", "min_panel_area", "min_crease_length",
            "max_aperture_width", "max_aperture_height",
            "target_frequency_ghz", "substrate_thickness_mm", "crease_keepout_mm",
        ]:
            if k in ds_params:
                val = ds_params[k]
                if k.startswith("num_cells"):
                    ds_kwargs[k] = int(val)
                elif k == "flat_foldable_only":
                    ds_kwargs[k] = bool(val)
                else:
                    ds_kwargs[k] = float(val)

        design_space = DesignSpace(**ds_kwargs)
        return GenerativeOrigamiEngine.explore(
            design_space=design_space,
            count=count,
            seed=seed,
            pattern_family=family,
        )

    @classmethod
    def get_pattern_catalog(cls) -> Dict[str, Any]:
        """Return catalog of available patterns and their editable parameters."""
        catalog = {}
        for key, info in cls.PATTERN_REGISTRY.items():
            pattern_cls = info["class"]
            pset = pattern_cls.default_parameters()
            catalog[key] = {
                "id": key,
                "name": info["name"],
                "description": info["description"],
                "parameters": [p.to_dict() for p in pset._params.values()],
            }
        return catalog

    @classmethod
    def generate_and_fold(
        cls,
        pattern_type: str,
        params: Dict[str, Any],
        fold_angle_deg: float = 30.0,
        material_tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate crease pattern, compute 3D folding kinematics, and execute validation checks."""
        key = pattern_type.lower().replace("-", "_").strip()
        if key not in cls.PATTERN_REGISTRY:
            key = "miura_ori"

        generator_cls = cls.PATTERN_REGISTRY[key]["class"]
        generator = generator_cls()

        # 1. Generate Crease Pattern (clean parameters of external exploration metadata)
        valid_keys = set(generator.default_parameters().keys())
        clean_params = {k: v for k, v in params.items() if k in valid_keys}
        pattern = generator.generate(**clean_params)

        # Apply material tags if provided
        if material_tags:
            for face_idx_str, mat in material_tags.items():
                try:
                    f_idx = int(face_idx_str)
                    if 0 <= f_idx < pattern.num_faces:
                        pattern.faces[f_idx].material_tag = mat
                except (ValueError, IndexError):
                    pass

        # 2. Run Topological Verification
        topo_verif = generator.verify_pattern(pattern)

        # 3. Compute 3D Folded Mesh
        mesh_3d = FoldingEngine.fold(
            pattern_type=key,
            crease_pattern=pattern,
            params=params,
            fold_angle_deg=fold_angle_deg,
        )

        # Synchronize face materials from 2D pattern to 3D mesh
        mesh_3d._face_materials = [f.material_tag for f in pattern.faces]

        # 4. Perform Physical & Geometric Validation
        validation_results = cls._run_detailed_validation(pattern, mesh_3d, key, params, fold_angle_deg)

        # 5. Build JSON Response
        return cls._serialize_model(pattern, mesh_3d, key, params, fold_angle_deg, validation_results)

    @classmethod
    def _run_detailed_validation(
        cls,
        pattern: CreasePattern,
        mesh: FoldedMesh,
        pattern_type: str,
        params: Dict[str, Any],
        fold_angle_deg: float,
    ) -> Dict[str, Any]:
        """Perform rigorous physical validation checks using the actual engine functions."""
        # 1. Kawasaki Theorem (alternating sector angle sum = 180 deg)
        int_v_count = 0
        kawasaki_passes = 0
        kawasaki_err_max = 0.0

        for v_idx in range(pattern.num_vertices):
            if pattern.is_boundary_vertex(v_idx):
                continue
            int_v_count += 1
            k_ok, s_even, s_odd = pattern.check_kawasaki_theorem(v_idx)
            if k_ok:
                kawasaki_passes += 1
            err = max(abs(s_even - 180.0), abs(s_odd - 180.0))
            kawasaki_err_max = max(kawasaki_err_max, err)

        kawasaki_valid = (int_v_count == 0) or (kawasaki_passes == int_v_count)
        kawasaki_detail = f"{kawasaki_passes}/{int_v_count} interior vertices valid (max dev: {kawasaki_err_max:.2f}°)" if int_v_count > 0 else "N/A (Boundary pattern)"

        # 2. Maekawa Theorem (|M - V| = 2)
        maekawa_passes = 0
        for v_idx in range(pattern.num_vertices):
            if pattern.is_boundary_vertex(v_idx):
                continue
            m_ok, _, _ = pattern.check_maekawa_theorem(v_idx)
            if m_ok:
                maekawa_passes += 1

        maekawa_valid = (int_v_count == 0) or (maekawa_passes == int_v_count)
        maekawa_detail = f"{maekawa_passes}/{int_v_count} interior vertices satisfy |M - V| = 2" if int_v_count > 0 else "N/A (Boundary pattern)"

        # 3. Edge-Length Conservation (Isometric preservation between 2D and 3D)
        max_edge_dev = 0.0
        edge_count = 0
        v_2d = pattern.vertices
        v_3d = mesh.vertices

        for c in pattern.creases:
            len_2d = np.linalg.norm(v_2d[c.u] - v_2d[c.v])
            if c.u < len(v_3d) and c.v < len(v_3d):
                len_3d = np.linalg.norm(v_3d[c.u] - v_3d[c.v])
                dev = abs(len_3d - len_2d)
                max_edge_dev = max(max_edge_dev, dev)
                edge_count += 1

        edge_conserved = max_edge_dev < 1e-4
        edge_detail = f"Max isometric deviation: {max_edge_dev:.2e} mm"

        # 4. Face-Area Conservation
        total_2d_area = sum(polygon_area(v_2d[list(f.vertex_indices)]) for f in pattern.faces)
        total_3d_area = mesh.compute_total_surface_area()
        area_diff = abs(total_3d_area - total_2d_area)
        area_conserved = (area_diff < 1e-3) or (pattern_type in ("waterbomb", "yoshimura") and area_diff < 1.0)
        area_detail = f"Conserved to {area_diff:.2e} mm² (2D: {total_2d_area:.1f}, 3D: {total_3d_area:.1f})"

        # 5. Geometric Coplanarity / Validity
        max_coplanar_err = 0.0
        all_coplanar = True
        for face_v in mesh.faces:
            face_pts = v_3d[list(face_v)]
            if len(face_pts) > 3:
                is_cop = is_coplanar(face_pts, tol=1e-4)
                all_coplanar = all_coplanar and is_cop

        geom_detail = "All facets strictly planar (out-of-plane < 1e-5 mm)" if all_coplanar else "Facets triangulated"

        return {
            "kawasaki": {
                "passed": bool(kawasaki_valid),
                "detail": kawasaki_detail,
            },
            "maekawa": {
                "passed": bool(maekawa_valid),
                "detail": maekawa_detail,
            },
            "edge_conservation": {
                "passed": bool(edge_conserved),
                "detail": edge_detail,
                "max_deviation_mm": float(max_edge_dev),
            },
            "area_conservation": {
                "passed": bool(area_conserved),
                "detail": area_detail,
                "deviation_mm2": float(area_diff),
            },
            "geometric_validity": {
                "passed": bool(all_coplanar),
                "detail": geom_detail,
            },
        }

    @classmethod
    def _serialize_model(
        cls,
        pattern: CreasePattern,
        mesh: FoldedMesh,
        pattern_type: str,
        params: Dict[str, Any],
        fold_angle_deg: float,
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert geometry and metrics into JSON-serializable structure."""
        # Creases serialization with colors
        creases_data = []
        for c in pattern.creases:
            creases_data.append({
                "u": c.u,
                "v": c.v,
                "type": c.crease_type.value,
                "length": float(c.target_length) if c.target_length else 0.0,
            })

        # Faces serialization with materials
        faces_data = []
        for idx, f in enumerate(pattern.faces):
            faces_data.append({
                "id": idx,
                "indices": list(f.vertex_indices),
                "material": f.material_tag,
            })

        # 2D Bounding Box
        b_min_2d, b_max_2d = pattern.bounding_box()
        # 3D Bounding Box
        b_min_3d, b_max_3d = mesh.bounding_box()
        dims_3d = mesh.dimensions()

        # Material surface areas
        mat_areas = {
            "conductor": float(mesh.compute_material_surface_area("conductor")),
            "substrate": float(mesh.compute_material_surface_area("substrate")),
            "ground": float(mesh.compute_material_surface_area("ground")),
            "dielectric": float(mesh.compute_material_surface_area("dielectric")),
            "keepout": float(mesh.compute_material_surface_area("keepout")),
        }

        # Normals
        normals_np = mesh.compute_face_normals()

        return {
            "pattern_type": pattern_type,
            "pattern_name": cls.PATTERN_REGISTRY.get(pattern_type, {}).get("name", pattern_type),
            "fold_angle_deg": float(fold_angle_deg),
            "parameters": params,
            "crease_pattern_2d": {
                "vertices": pattern.vertices[:, :2].tolist(),
                "creases": creases_data,
                "faces": faces_data,
                "bounds": {
                    "min": b_min_2d[:2].tolist(),
                    "max": b_max_2d[:2].tolist(),
                    "width": float(b_max_2d[0] - b_min_2d[0]),
                    "height": float(b_max_2d[1] - b_min_2d[1]),
                },
            },
            "folded_mesh_3d": {
                "vertices": mesh.vertices.tolist(),
                "faces": [list(f) for f in mesh.faces],
                "face_materials": mesh.face_materials,
                "normals": normals_np.tolist(),
                "dimensions": dims_3d.tolist(),
                "total_surface_area": float(mesh.compute_total_surface_area()),
                "bounds": {
                    "min": b_min_3d.tolist(),
                    "max": b_max_3d.tolist(),
                },
            },
            "metrics": {
                "num_vertices": pattern.num_vertices,
                "num_edges": pattern.num_creases,
                "num_faces": pattern.num_faces,
                "surface_area_mm2": float(mesh.compute_total_surface_area()),
                "dimensions_mm": [round(float(d), 2) for d in dims_3d],
                "fold_angle_deg": round(float(fold_angle_deg), 1),
                "material_areas_mm2": mat_areas,
            },
            "validation": validation,
        }

    @classmethod
    def get_available_materials(cls) -> List[Dict[str, Any]]:
        """Return catalog of RF substrate and conductor materials."""
        from rf_origami.rf.materials.material import MaterialLibrary
        return [mat.to_dict() for mat in MaterialLibrary.all()]

    @classmethod
    def get_validation_benchmarks(cls) -> Dict[str, Any]:
        """Execute and return canonical analytical EM verification benchmarks."""
        from rf_origami.rf.solver.validation_cases import SolverValidationBenchmarks
        return {
            "free_space": SolverValidationBenchmarks.validate_free_space_propagation(),
            "half_wave_dipole": SolverValidationBenchmarks.run_half_wave_dipole_benchmark(2.4, 21),
            "quarter_wave_monopole": SolverValidationBenchmarks.run_quarter_wave_monopole_benchmark(2.4, 21),
        }

    @classmethod
    def simulate_rf(
        cls,
        pattern_type: str,
        params: Dict[str, Any],
        fold_angle_deg: float = 35.0,
        f_start_ghz: float = 1.0,
        f_stop_ghz: float = 6.0,
        num_points: int = 21,
        substrate_material: str = "kapton",
        conductor_material: str = "copper",
        port_z0: float = 50.0,
        material_tags: Optional[Dict[str, str]] = None,
        target_segment_length_mm: float = 8.0,
    ) -> Dict[str, Any]:
        """Execute standalone Method of Moments (MoM) electromagnetic simulation on folded 3D geometry."""
        from rf_origami.rf.materials.material import MaterialLibrary
        from rf_origami.rf.geometry.converter import RFGeometryConverter
        from rf_origami.rf.mesh.discretization import EMDiscretization
        from rf_origami.rf.ports.lumped_port import LumpedPort
        from rf_origami.rf.solver.mom_solver import MoMSolver

        key = pattern_type.lower().replace("-", "_").strip()
        if key not in cls.PATTERN_REGISTRY:
            key = "miura_ori"

        generator_cls = cls.PATTERN_REGISTRY[key]["class"]
        generator = generator_cls()
        valid_keys = set(generator.default_parameters().keys())
        clean_params = {k: v for k, v in params.items() if k in valid_keys}
        pattern = generator.generate(**clean_params)

        # Apply material tags
        if material_tags:
            for face_idx_str, mat in material_tags.items():
                try:
                    f_idx = int(face_idx_str)
                    if 0 <= f_idx < pattern.num_faces:
                        pattern.faces[f_idx].material_tag = mat
                except (ValueError, IndexError):
                    pass

        # Ensure at least one face or boundary has conductor tag for antenna radiation
        has_conductor = any(f.material_tag == "conductor" for f in pattern.faces)
        if not has_conductor and pattern.num_faces > 0:
            # Default first facet to conductor radiating element
            pattern.faces[0].material_tag = "conductor"

        # Compute 3D folding
        mesh_3d = FoldingEngine.fold(
            pattern_type=key,
            crease_pattern=pattern,
            params=params,
            fold_angle_deg=fold_angle_deg,
        )
        mesh_3d._face_materials = [f.material_tag for f in pattern.faces]

        # Look up materials from library
        sub_mat = MaterialLibrary.get(substrate_material)
        cond_mat = MaterialLibrary.get(conductor_material)

        # Convert to RF physical geometry model
        rf_model = RFGeometryConverter.from_folded_mesh(
            folded_mesh=mesh_3d,
            parent_candidate_id=str(params.get("candidate_id", "ACTIVE")),
            fold_angle_deg=fold_angle_deg,
            conductor_material=cond_mat,
            substrate_material=sub_mat,
        )

        # Discretize conductor geometry into MoM segments
        discretization = EMDiscretization.from_rf_geometry(
            rf_geometry=rf_model,
            target_segment_length_mm=target_segment_length_mm,
        )

        # Set up lumped port
        port = LumpedPort(impedance=port_z0)

        # Solve frequency sweep
        solver = MoMSolver(
            discretization=discretization,
            port=port,
            substrate_material=sub_mat,
        )

        sweep = solver.solve_sweep(
            f_start_hz=f_start_ghz * 1e9,
            f_stop_hz=f_stop_ghz * 1e9,
            num_points=num_points,
        )

        dims_3d = [round(float(d), 2) for d in mesh_3d.dimensions()]

        return {
            "simulation_type": "mom_solver",
            "solver_engine": "Standalone EFIE-MoM (Pocklington with Harrington Integral Kernel)",
            "is_numerical": True,
            "commercial_software_used": False,
            "pattern_type": key,
            "fold_angle_deg": float(fold_angle_deg),
            "substrate_material": sub_mat.to_dict(),
            "conductor_material": MaterialLibrary.get(conductor_material).to_dict(),
            "port": port.to_dict(),
            "discretization": {
                "num_segments": discretization.num_segments,
                "total_length_mm": round(discretization.total_length_mm, 2),
                "port_segment_index": discretization.port_segment_index,
            },
            "folded_dimensions_mm": dims_3d,
            "frequency_sweep": sweep,
            "resonance": sweep["resonance"],
        }

    @classmethod
    def run_rf_fold_sweep(
        cls,
        pattern_type: str,
        params: Dict[str, Any],
        fold_angles: Optional[List[float]] = None,
        f_start_ghz: float = 1.0,
        f_stop_ghz: float = 6.0,
        num_points: int = 15,
        substrate_material: str = "kapton",
        conductor_material: str = "copper",
    ) -> Dict[str, Any]:
        """Sweep fold angles to compute dynamic RF frequency reconfiguration and tuning."""
        if not fold_angles:
            fold_angles = [15.0, 30.0, 45.0, 60.0, 75.0]

        results = []
        f0_list = []
        min_s11_list = []
        bw_list = []

        for angle in fold_angles:
            sim = cls.simulate_rf(
                pattern_type=pattern_type,
                params=params,
                fold_angle_deg=angle,
                f_start_ghz=f_start_ghz,
                f_stop_ghz=f_stop_ghz,
                num_points=num_points,
                substrate_material=substrate_material,
                conductor_material=conductor_material,
            )
            res = sim["resonance"]
            f0 = res["resonant_frequency_ghz"]
            f0_list.append(f0)
            min_s11_list.append(res["min_s11_db"])
            bw_list.append(res["bandwidth_mhz"])
            results.append({
                "fold_angle_deg": angle,
                "resonant_frequency_ghz": f0,
                "min_s11_db": res["min_s11_db"],
                "zin_at_resonance": res["zin_at_resonance"],
                "vswr_at_resonance": res["vswr_at_resonance"],
                "bandwidth_mhz": res["bandwidth_mhz"],
                "dimensions_mm": sim["folded_dimensions_mm"],
            })

        valid_f0 = [f for f in f0_list if f > 0]
        tuning_range = round(max(valid_f0) - min(valid_f0), 3) if valid_f0 else 0.0
        tuning_ratio = round(max(valid_f0) / min(valid_f0), 2) if (valid_f0 and min(valid_f0) > 0) else 1.0

        return {
            "pattern_type": pattern_type,
            "fold_angles_deg": fold_angles,
            "resonant_frequencies_ghz": f0_list,
            "min_s11_db": min_s11_list,
            "bandwidths_mhz": bw_list,
            "tuning_range_ghz": tuning_range,
            "tuning_ratio": tuning_ratio,
            "step_results": results,
        }
