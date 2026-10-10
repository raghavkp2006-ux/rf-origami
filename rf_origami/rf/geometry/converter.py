"""Conversion between FoldedMesh / CreasePattern and physical RFGeometryModel.

Partitions origami facets into physical conductor surfaces, ground planes,
and dielectric substrates with materials assigned.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np

from rf_origami.core.mesh import FoldedMesh
from rf_origami.rf.materials.material import Material, MaterialLibrary
from rf_origami.rf.geometry.rf_object import (
    RFGeometryModel,
    ConductorSurface,
    SubstrateSurface,
    GroundPlane,
    RFObject,
    RFObjectType,
)


class RFGeometryConverter:
    """Converts kinematic origami mesh representations into physical RF models."""

    @classmethod
    def from_folded_mesh(
        cls,
        folded_mesh: FoldedMesh,
        parent_candidate_id: str = "CAND-001",
        fold_angle_deg: float = 30.0,
        conductor_material: Optional[Material] = None,
        substrate_material: Optional[Material] = None,
        default_layout: str = "center_conductor",
    ) -> RFGeometryModel:
        """Convert a FoldedMesh with material tags into an RFGeometryModel.

        Args:
            folded_mesh: FoldedMesh geometry.
            parent_candidate_id: Identifier of source origami design.
            fold_angle_deg: Fold angle at which mesh was computed.
            conductor_material: Conductor Material (default: Copper).
            substrate_material: Substrate Material (default: Kapton/Polyimide).
            default_layout: Strategy for assigning materials if mesh has no tags:
                - 'center_conductor': Center facets become conductor, edges substrate.
                - 'all_conductor': Entire surface is metallic.
                - 'microstrip': Top facets conductor, bottom/rear ground.
        """
        c_mat = conductor_material or MaterialLibrary.get("copper")
        s_mat = substrate_material or MaterialLibrary.get("kapton")
        g_mat = MaterialLibrary.get("copper")

        v_3d = folded_mesh.vertices
        faces = folded_mesh.faces
        materials = folded_mesh.face_materials

        # If face_materials is empty, apply default layout
        if not materials or all(m == "substrate" for m in materials):
            materials = cls._generate_default_material_tags(faces, default_layout)

        conductor_faces = []
        substrate_faces = []
        ground_faces = []
        keepout_faces = []

        for idx, f in enumerate(faces):
            tag = materials[idx] if idx < len(materials) else "substrate"
            tag_lower = str(tag).lower()

            if "cond" in tag_lower:
                conductor_faces.append(list(f))
            elif "ground" in tag_lower:
                ground_faces.append(list(f))
            elif "keep" in tag_lower:
                keepout_faces.append(list(f))
            else:
                substrate_faces.append(list(f))

        # Build RF Objects
        conductors = []
        if conductor_faces:
            conductors.append(ConductorSurface(
                object_id=f"{parent_candidate_id}_cond_0",
                vertices=v_3d,
                faces=conductor_faces,
                material=c_mat,
                parent_candidate_id=parent_candidate_id,
                fold_angle_deg=fold_angle_deg,
            ))

        substrates = []
        if substrate_faces:
            substrates.append(SubstrateSurface(
                object_id=f"{parent_candidate_id}_sub_0",
                vertices=v_3d,
                faces=substrate_faces,
                material=s_mat,
                parent_candidate_id=parent_candidate_id,
                fold_angle_deg=fold_angle_deg,
            ))

        ground_planes = []
        if ground_faces:
            ground_planes.append(GroundPlane(
                object_id=f"{parent_candidate_id}_gnd_0",
                vertices=v_3d,
                faces=ground_faces,
                material=g_mat,
                parent_candidate_id=parent_candidate_id,
                fold_angle_deg=fold_angle_deg,
            ))

        keepouts = []
        if keepout_faces:
            keepouts.append(RFObject(
                object_id=f"{parent_candidate_id}_keep_0",
                object_type=RFObjectType.KEEPOUT,
                material=MaterialLibrary.get("air"),
                vertices=v_3d,
                faces=keepout_faces,
                parent_candidate_id=parent_candidate_id,
                fold_angle_deg=fold_angle_deg,
            ))

        return RFGeometryModel(
            parent_candidate_id=parent_candidate_id,
            fold_angle_deg=fold_angle_deg,
            conductors=conductors,
            substrates=substrates,
            ground_planes=ground_planes,
            keepouts=keepouts,
        )

    @classmethod
    def _generate_default_material_tags(cls, faces: List[Sequence[int]], layout: str) -> List[str]:
        """Synthesize physical RF layout for origami panels."""
        n_faces = len(faces)
        if layout == "all_conductor":
            return ["conductor"] * n_faces

        # Default center strip: middle 50% facets are metallized conductor radiating strip
        tags = []
        mid = n_faces / 2.0
        width = max(1.0, n_faces * 0.4)
        for i in range(n_faces):
            if abs(i - mid) <= width / 2.0:
                tags.append("conductor")
            else:
                tags.append("substrate")
        return tags
