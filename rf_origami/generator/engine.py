"""Algorithmic generative origami engine and constraint filter cascade.

Constructs mathematically authentic origami candidate networks, executes multi-tier
feasibility filters, and computes geometric/kinematic exploration metrics.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rf_origami.core.crease_pattern import CreasePattern, CreaseType
from rf_origami.core.mesh import FoldedMesh
from rf_origami.core.geometry import polygon_area, segments_intersect_2d
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.patterns.waterbomb import WaterbombPattern
from rf_origami.patterns.yoshimura import YoshimuraPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.generator.design_space import DesignSpace, CandidateDesign
from rf_origami.visualization.svg_crease import export_crease_svg


class GenerativeOrigamiEngine:
    """Explorative generative origami engine with multi-tier physical filtering."""

    @classmethod
    def explore(
        cls,
        design_space: DesignSpace,
        count: int = 20,
        seed: int = 42,
        pattern_family: str = "modulated_miura",
    ) -> Dict[str, Any]:
        """Generate, filter, and evaluate `count` origami candidate designs.

        Args:
            design_space: Bounded parameter ranges and constraint thresholds.
            count: Number of candidate structures to generate (10, 50, 100, 500).
            seed: Deterministic integer seed for full reproducibility.
            pattern_family: 'modulated_miura', 'periodic_tess', 'waterbomb_array', 'yoshimura_lattice'.

        Returns:
            Dictionary containing candidate designs, design-space scatter points, and generation summary.
        """
        raw_samples = design_space.sample(count=count, seed=seed)
        candidates: List[CandidateDesign] = []
        scatter_points: List[Dict[str, Any]] = []

        valid_count = 0
        rejected_count = 0

        for idx, sample in enumerate(raw_samples):
            cand_id = f"CAND-{idx + 1:03d}"
            candidate = cls._build_and_filter_candidate(
                cand_id=cand_id,
                seed=seed,
                family=pattern_family,
                params=sample,
                design_space=design_space,
            )
            candidates.append(candidate)

            if candidate.is_valid:
                valid_count += 1
            else:
                rejected_count += 1

            # Extract 2D design space scatter coordinates:
            # X: Aspect Ratio (a / b), Y: Compactness Ratio
            x_val = candidate.parameters.get("a", 20.0) / max(0.1, candidate.parameters.get("b", 20.0))
            y_val = candidate.metrics.get("compactness_ratio", 0.5)

            scatter_points.append({
                "id": cand_id,
                "x": round(float(x_val), 3),
                "y": round(float(y_val), 3),
                "is_valid": candidate.is_valid,
                "gamma": candidate.parameters.get("gamma", 60.0),
                "surface_area": candidate.metrics.get("surface_area_mm2", 0.0),
                "fold_angle": candidate.parameters.get("fold_angle", 35.0),
            })

        return {
            "summary": {
                "total_generated": count,
                "valid_count": valid_count,
                "rejected_count": rejected_count,
                "seed": seed,
                "pattern_family": pattern_family,
            },
            "design_space_scatter": {
                "x_label": "Aspect Ratio (a / b)",
                "y_label": "Folded Compactness Ratio",
                "points": scatter_points,
            },
            "candidates": [c.to_dict() for c in candidates],
        }

    @classmethod
    def _build_and_filter_candidate(
        cls,
        cand_id: str,
        seed: int,
        family: str,
        params: Dict[str, Any],
        design_space: DesignSpace,
    ) -> CandidateDesign:
        """Construct the crease pattern and execute the three-tier constraint filter."""
        rejection_reasons = []
        fam = family.lower()

        # 1. Procedural Pattern Generation
        try:
            if "waterbomb" in fam:
                gen = WaterbombPattern()
                pattern = gen.generate(
                    cell_width=params.get("a", 30.0),
                    cell_height=params.get("b", 30.0),
                    num_cells_x=params.get("num_cells_x", 1),
                    num_cells_y=params.get("num_cells_y", 1),
                )
                fold_ptype = "waterbomb"
            elif "yoshimura" in fam:
                gen = YoshimuraPattern()
                pattern = gen.generate(
                    cell_width=params.get("a", 25.0),
                    cell_height=params.get("b", 20.0),
                    num_cells_x=max(2, params.get("num_cells_x", 3)),
                    num_cells_y=params.get("num_cells_y", 2),
                )
                fold_ptype = "yoshimura"
            else:
                # Modulated / Periodic Miura-ori
                gen = MiuraOriPattern()
                pattern = gen.generate(
                    a=params.get("a", 25.0),
                    b=params.get("b", 20.0),
                    gamma=params.get("gamma", 60.0),
                    num_cells_x=params.get("num_cells_x", 2),
                    num_cells_y=params.get("num_cells_y", 2),
                )
                fold_ptype = "miura_ori"

        except Exception as e:
            return CandidateDesign(
                id=cand_id,
                seed=seed,
                pattern_family=family,
                parameters=params,
                is_valid=False,
                rejection_reasons=[f"Construction failure: {str(e)}"],
            )

        # -------------------------------------------------------------
        # TIER 1: Topological & Structural Verification
        # -------------------------------------------------------------
        if pattern.num_vertices < 4 or pattern.num_faces < 1 or pattern.num_creases < 3:
            rejection_reasons.append("Topological failure: Degenerate cell complex.")

        # Check edge lengths
        v_2d = pattern.vertices
        min_len = float("inf")
        for c in pattern.creases:
            l = np.linalg.norm(v_2d[c.u] - v_2d[c.v])
            if l < min_len:
                min_len = l
            if l < 1e-3:
                rejection_reasons.append(f"Degenerate zero-length edge between nodes {c.u} and {c.v}.")
                break

        # Check non-adjacent crease self-intersections
        crease_list = pattern.creases
        n_creases = len(crease_list)
        has_self_intersection = False
        for i in range(n_creases):
            c1 = crease_list[i]
            p1 = v_2d[c1.u]
            p2 = v_2d[c1.v]
            for j in range(i + 1, n_creases):
                c2 = crease_list[j]
                if c1.u == c2.u or c1.u == c2.v or c1.v == c2.u or c1.v == c2.v:
                    continue
                p3 = v_2d[c2.u]
                p4 = v_2d[c2.v]
                if segments_intersect_2d(p1, p2, p3, p4):
                    rejection_reasons.append(f"Crease self-intersection detected between edges {c1.u}-{c1.v} and {c2.u}-{c2.v}.")
                    has_self_intersection = True
                    break
            if has_self_intersection:
                break

        # -------------------------------------------------------------
        # TIER 2: Origami Flat-Foldability Theorems (Kawasaki & Maekawa)
        # -------------------------------------------------------------
        kawasaki_passes = 0
        maekawa_passes = 0
        int_v_count = 0

        for v_idx in range(pattern.num_vertices):
            if pattern.is_boundary_vertex(v_idx):
                continue
            int_v_count += 1
            k_ok, _, _ = pattern.check_kawasaki_theorem(v_idx, tol_deg=2.0)
            if k_ok:
                kawasaki_passes += 1
            m_ok, _, _ = pattern.check_maekawa_theorem(v_idx)
            if m_ok:
                maekawa_passes += 1

        if design_space.flat_foldable_only and int_v_count > 0:
            if kawasaki_passes < int_v_count:
                rejection_reasons.append(f"Kawasaki theorem failed at {int_v_count - kawasaki_passes} interior nodes.")
            if maekawa_passes < int_v_count:
                rejection_reasons.append(f"Maekawa theorem failed at {int_v_count - maekawa_passes} interior nodes.")

        # -------------------------------------------------------------
        # TIER 3: Physical, Geometric, and Aperture Constraints
        # -------------------------------------------------------------
        # Face area checks
        min_area = float("inf")
        total_2d_area = 0.0
        for f in pattern.faces:
            area = polygon_area(v_2d[list(f.vertex_indices)])
            total_2d_area += area
            if area < min_area:
                min_area = area

        if min_area < design_space.min_panel_area:
            rejection_reasons.append(f"Minimum panel area {min_area:.1f} mm² < limit {design_space.min_panel_area:.1f} mm².")

        if min_len < design_space.min_crease_length:
            rejection_reasons.append(f"Minimum crease length {min_len:.1f} mm < limit {design_space.min_crease_length:.1f} mm.")

        # Aperture boundary envelope check
        b_min_2d, b_max_2d = pattern.bounding_box()
        width_2d = float(b_max_2d[0] - b_min_2d[0])
        height_2d = float(b_max_2d[1] - b_min_2d[1])

        if width_2d > design_space.max_aperture_width or height_2d > design_space.max_aperture_height:
            rejection_reasons.append(f"Aperture envelope ({width_2d:.1f}x{height_2d:.1f} mm) exceeds limit ({design_space.max_aperture_width:.1f}x{design_space.max_aperture_height:.1f} mm).")

        # 4. Kinematic 3D Folding & Foldability Verification
        fold_angle = float(params.get("fold_angle", 35.0))
        if fold_angle < 1.0 or fold_angle > 88.0:
            rejection_reasons.append(f"Fold angle {fold_angle:.1f}° outside kinematic foldability envelope [1°, 88°].")

        folded_mesh = FoldingEngine.fold(
            pattern_type=fold_ptype,
            crease_pattern=pattern,
            params=params,
            fold_angle_deg=fold_angle,
        )

        dims_3d = folded_mesh.dimensions()
        if dims_3d[0] < 1.0 or dims_3d[1] < 1.0:
            rejection_reasons.append(f"Folded structure collapsed: Dimensions ({dims_3d[0]:.1f}x{dims_3d[1]:.1f} mm) below physical threshold.")

        # Isometric conservation check
        total_3d_area = folded_mesh.compute_total_surface_area()
        area_diff = abs(total_3d_area - total_2d_area)
        if total_2d_area > 0 and (area_diff / total_2d_area) > 0.05:
            rejection_reasons.append(f"Kinematic isometry violation: Folded area dev {area_diff:.1f} mm² exceeds 5%.")

        # Determine overall validity
        is_valid = (len(rejection_reasons) == 0)

        folded_footprint_area = max(1e-4, dims_3d[0] * dims_3d[1])
        flat_footprint_area = max(1e-4, width_2d * height_2d)
        compactness = folded_footprint_area / flat_footprint_area

        # Total crease line length
        total_crease_len = sum(np.linalg.norm(v_2d[c.u] - v_2d[c.v]) for c in pattern.creases)
        crease_density = total_crease_len / max(1e-4, total_2d_area)

        # Preliminary RF frequency estimate based on facet diagonal
        max_diag = math.sqrt(params.get("a", 25.0)**2 + params.get("b", 20.0)**2)
        # Half-wave resonance: c / (2 * L * sqrt(eps_r)) with eps_r = 2.2
        est_res_ghz = 300.0 / (2.0 * max_diag * math.sqrt(2.2))

        metrics = {
            "num_vertices": pattern.num_vertices,
            "num_edges": pattern.num_creases,
            "num_faces": pattern.num_faces,
            "surface_area_mm2": float(round(total_2d_area, 1)),
            "flat_envelope_mm": [float(round(width_2d, 1)), float(round(height_2d, 1))],
            "folded_envelope_mm": [float(round(dims_3d[0], 1)), float(round(dims_3d[1], 1)), float(round(dims_3d[2], 1))],
            "compactness_ratio": float(round(compactness, 3)),
            "crease_density": float(round(crease_density, 3)),
            "est_half_wave_f0_ghz": float(round(est_res_ghz, 2)),
            "fold_angle_deg": float(round(fold_angle, 1)),
        }

        validation = {
            "kawasaki": {"passed": bool(kawasaki_passes == int_v_count or int_v_count == 0), "passes": int(kawasaki_passes), "total": int(int_v_count)},
            "maekawa": {"passed": bool(maekawa_passes == int_v_count or int_v_count == 0), "passes": int(maekawa_passes), "total": int(int_v_count)},
            "min_panel_area_mm2": float(round(min_area, 1)),
            "min_crease_len_mm": float(round(min_len, 1)),
        }

        # 5. Generate high-speed SVG thumbnail for grid view
        thumb_svg = export_crease_svg(
            pattern=pattern,
            width=220,
            height=160,
            margin=15,
            show_faces=True,
            show_vertices=False,
            show_labels=False,
            title="",
        )

        return CandidateDesign(
            id=cand_id,
            seed=seed,
            pattern_family=family,
            parameters=params,
            is_valid=is_valid,
            rejection_reasons=rejection_reasons,
            metrics=metrics,
            validation=validation,
            thumbnail_svg=thumb_svg,
        )
