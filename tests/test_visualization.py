import os
import pytest

from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.folding.kinematics import MiuraKinematics
from rf_origami.visualization.svg_crease import export_crease_svg
from rf_origami.visualization.svg_folded import export_folded_svg
from rf_origami.visualization.plot_crease import plot_crease_pattern
from rf_origami.visualization.plot_folded import plot_folded_mesh


def test_svg_crease_export(tmp_path):
    generator = MiuraOriPattern()
    pattern = generator.generate(num_cells_x=2, num_cells_y=2)

    svg_file = str(tmp_path / "test_pattern.svg")
    svg_content = export_crease_svg(pattern, filepath=svg_file)

    assert os.path.exists(svg_file)
    assert os.path.getsize(svg_file) > 500
    assert "<svg" in svg_content
    assert "Mountain" in svg_content
    assert "Valley" in svg_content
    assert "Boundary" in svg_content


def test_svg_folded_export(tmp_path):
    solver = MiuraKinematics(a=25.0, b=18.0, gamma_deg=65.0)
    mesh = solver.fold(nx=2, ny=2, rho=0.4)

    svg_file = str(tmp_path / "test_folded.svg")
    svg_content = export_folded_svg(mesh, filepath=svg_file)

    assert os.path.exists(svg_file)
    assert os.path.getsize(svg_file) > 500
    assert "<svg" in svg_content
    assert "polygon points=" in svg_content
    assert "Dimensions:" in svg_content


def test_plot_fallbacks(tmp_path):
    generator = MiuraOriPattern()
    pattern = generator.generate(num_cells_x=1, num_cells_y=1)
    solver = MiuraKinematics(a=20.0, b=20.0, gamma_deg=60.0)
    mesh = solver.fold(nx=1, ny=1, rho=0.3)

    crease_out = str(tmp_path / "crease.png")
    res1 = plot_crease_pattern(pattern, save_path=crease_out)
    assert res1 is not None

    folded_out = str(tmp_path / "folded.png")
    res2 = plot_folded_mesh(mesh, save_path=folded_out)
    assert res2 is not None
