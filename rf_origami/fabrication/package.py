"""Fabrication Release Package Builder for Reconfigurable Origami Metasurfaces.

Bundles Gerber lithography layers, DXF laser-cut vector paths, STL 3D models,
FOLD interchange format, Bill of Materials (BOM), and engineering report into a single ZIP.
"""

from __future__ import annotations
import datetime
import io
import json
from typing import Any, Dict, Optional
import zipfile

from rf_origami.core.crease_pattern import CreasePattern
from rf_origami.core.mesh import FoldedMesh
from rf_origami.fabrication.gerber import GerberExporter
from rf_origami.fabrication.dxf import DXFExporter
from rf_origami.fabrication.stl import STLExporter
from rf_origami.fabrication.dfm import DFMVerifier


class FabricationPackageBuilder:
    """Creates complete, production-ready manufacturing release archives."""

    @classmethod
    def build_zip_package(
        cls,
        pattern: CreasePattern,
        folded_mesh: Optional[FoldedMesh] = None,
        design_id: str = "ORIGAMI-ABS-001",
        substrate_material: str = "Kapton Polyimide",
        conductor_material: str = "Rolled Annealed Copper (35 um)",
        substrate_thickness_mm: float = 0.5,
    ) -> bytes:
        """Create in-memory ZIP package containing all manufacturing deliverables."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Top Copper Gerber
            top_gbr = GerberExporter.export_top_copper(pattern)
            zf.writestr(f"{design_id}/copper_top.gbr", top_gbr)

            # 2. Bottom Ground Gerber
            bot_gbr = GerberExporter.export_ground_plane(pattern)
            zf.writestr(f"{design_id}/ground.gbr", bot_gbr)

            # 3. Laser Cut / Crease DXF
            dxf_text = DXFExporter.export_crease_pattern(pattern)
            zf.writestr(f"{design_id}/creases.dxf", dxf_text)

            # 4. FOLD standard interchange file
            fold_data = pattern.to_dict()
            zf.writestr(f"{design_id}/design.fold", json.dumps(fold_data, indent=2))

            # 5. 3D STL Model
            if folded_mesh is not None:
                stl_text = STLExporter.export_folded_mesh_ascii(folded_mesh, thickness_mm=substrate_thickness_mm)
                zf.writestr(f"{design_id}/model.stl", stl_text)

            # 6. Bill of Materials (BOM) CSV
            bom_rows = [
                "Item,Designator,Description,Material,Quantity,Unit",
                f"1,SUB-01,Flexible Dielectric Substrate,{substrate_material},1,Sheet",
                f"2,COND-01,Top Metallization Pattern,{conductor_material},1,Layer",
                f"3,GND-01,Bottom Shielding Ground Plane,{conductor_material},1,Layer",
                "4,COV-01,Solder Mask / Coverlay,Flexible Polyimide,1,Layer",
            ]
            bom_csv = "\n".join(bom_rows) + "\n"
            zf.writestr(f"{design_id}/bom.csv", bom_csv)

            # 7. DFM Report & Engineering Documentation
            dfm_res = DFMVerifier.verify(pattern, substrate_thickness_mm=substrate_thickness_mm)
            report_md = cls._generate_engineering_report(
                design_id=design_id,
                pattern=pattern,
                substrate_material=substrate_material,
                conductor_material=conductor_material,
                substrate_thickness_mm=substrate_thickness_mm,
                dfm_res=dfm_res,
            )
            zf.writestr(f"{design_id}/engineering_report.md", report_md)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @classmethod
    def _generate_engineering_report(
        cls,
        design_id: str,
        pattern: CreasePattern,
        substrate_material: str,
        conductor_material: str,
        substrate_thickness_mm: float,
        dfm_res: Dict[str, Any],
    ) -> str:
        """Compile Markdown engineering report for manufacturing technicians."""
        min_xyz, max_xyz = pattern.bounding_box()
        w = float(max_xyz[0] - min_xyz[0])
        h = float(max_xyz[1] - min_xyz[1])

        dfm_table_rows = []
        for r in dfm_res["rules"]:
            dfm_table_rows.append(f"| {r['rule']} | {r['status']} | {r['measured']:.2f} {r['unit']} | {r['limit']:.2f} {r['unit']} | {r['message']} |")
        dfm_table = "\n".join(dfm_table_rows)

        return f"""# RF Origami Forge — Manufacturing Release Report
**Design Identifier:** `{design_id}`  
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Status:** **{dfm_res['overall_status']}**

---

## 1. Physical Specifications
- **Unfolded Dimensions:** {w:.2f} mm x {h:.2f} mm
- **Panel Count:** {len(pattern.faces)} facets
- **Crease Count:** {len(pattern.creases)} fold lines
- **Substrate Material:** {substrate_material}
- **Substrate Thickness:** {substrate_thickness_mm:.2f} mm
- **Conductor Layer:** {conductor_material}


---

## 2. Design for Manufacturing (DFM) Audit
| Rule | Status | Measured | Limit | Details |
|---|---|---|---|---|
{dfm_table}

---

## 3. Package File Manifest
- `copper_top.gbr` — Top circuit metallization (RS-274X)
- `ground.gbr` — Solid continuous ground plane (RS-274X)
- `creases.dxf` — Vector crease score and perimeter cut lines (AutoCAD DXF)
- `model.stl` — Watertight 3D folded panel model (STL)
- `design.fold` — Standard computational origami topology (FOLD)
- `bom.csv` — Bill of materials for component procurement

---
*Generated by RF Origami Forge Computational Engineering Platform.*
"""
