"""Unit tests for fabrication export and DFM verification."""

import zipfile
import io
import pytest

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.engine import FoldingEngine
from rf_origami.fabrication.gerber import GerberExporter
from rf_origami.fabrication.dxf import DXFExporter
from rf_origami.fabrication.stl import STLExporter
from rf_origami.fabrication.dfm import DFMVerifier, DFMStatus
from rf_origami.fabrication.package import FabricationPackageBuilder


def test_gerber_export():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    top_gbr = GerberExporter.export_top_copper(pattern)
    assert "G04 RF Origami Forge" in top_gbr
    assert "%MOMM*%" in top_gbr
    assert "M02*" in top_gbr

    gnd_gbr = GerberExporter.export_ground_plane(pattern)
    assert "Bottom Ground Layer" in gnd_gbr
    assert "G36*" in gnd_gbr


def test_dxf_export():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    dxf_text = DXFExporter.export_crease_pattern(pattern)
    assert "MOUNTAIN_CREASE" in dxf_text
    assert "VALLEY_CREASE" in dxf_text
    assert "SUBSTRATE_CUT" in dxf_text
    assert "EOF" in dxf_text


def test_stl_export():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=30.0)
    stl_text = STLExporter.export_folded_mesh_ascii(folded, thickness_mm=0.5)
    assert "solid rf_origami_folded" in stl_text
    assert "facet normal" in stl_text
    assert "endsolid rf_origami_folded" in stl_text


def test_dfm_verification():
    pattern = MiuraOriPattern.generate(a=25.0, b=25.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    res = DFMVerifier.verify(pattern, substrate_thickness_mm=0.5)
    assert "overall_status" in res
    assert "rules" in res
    assert len(res["rules"]) >= 4
    assert res["passed"] is True


def test_zip_package_builder():
    pattern = MiuraOriPattern.generate(a=20.0, b=20.0, gamma_deg=65.0, num_cells_x=2, num_cells_y=2)
    folded = FoldingEngine.fold_analytical(pattern, fold_angle_deg=25.0)

    zip_bytes = FabricationPackageBuilder.build_zip_package(
        pattern=pattern,
        folded_mesh=folded,
        design_id="TEST-PACKAGE",
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        assert "TEST-PACKAGE/copper_top.gbr" in names
        assert "TEST-PACKAGE/ground.gbr" in names
        assert "TEST-PACKAGE/creases.dxf" in names
        assert "TEST-PACKAGE/model.stl" in names
        assert "TEST-PACKAGE/design.fold" in names
        assert "TEST-PACKAGE/bom.csv" in names
        assert "TEST-PACKAGE/engineering_report.md" in names
