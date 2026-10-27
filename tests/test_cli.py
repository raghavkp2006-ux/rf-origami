"""Unit tests for the RF Origami Forge CLI."""

import json
import pytest
from rf_origami.cli import main


def test_cli_help():
    assert main([]) == 0


def test_cli_benchmark():
    assert main(["benchmark"]) == 0


def test_cli_simulate(tmp_path):
    out_file = str(tmp_path / "sim.json")
    ret = main([
        "simulate",
        "--pattern", "miura_ori",
        "--fold", "30",
        "--fstart", "2.0",
        "--fstop", "4.0",
        "--points", "5",
        "--out", out_file,
    ])
    assert ret == 0
    with open(out_file, "r") as f:
        data = json.load(f)
    assert "resonant_frequency_hz" in data


def test_cli_sweep(tmp_path):
    out_file = str(tmp_path / "sweep.json")
    ret = main([
        "sweep",
        "--pattern", "miura_ori",
        "--angles", "0", "30", "60",
        "--fstart", "2.0",
        "--fstop", "5.0",
        "--points", "5",
        "--out", out_file,
    ])
    assert ret == 0


def test_cli_phase():
    ret = main([
        "phase",
        "--pattern", "miura_ori",
        "--fstart", "3.0",
        "--fstop", "5.0",
    ])
    assert ret == 0


def test_cli_polarization():
    ret = main([
        "polarization",
        "--pattern", "miura_ori",
        "--fold", "30",
        "--fstart", "3.0",
        "--fstop", "5.0",
    ])
    assert ret == 0


def test_cli_rcs():
    ret = main([
        "rcs",
        "--pattern", "miura_ori",
        "--fold", "30",
        "--freq", "3.0",
    ])
    assert ret == 0


def test_cli_ecm():
    ret = main([
        "ecm",
        "--length", "25.0",
        "--fold", "30.0",
    ])
    assert ret == 0


def test_cli_optimize(capsys):
    ret = main([
        "optimize",
        "--pop", "2",
        "--gens", "1",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Estimate - not validated" in captured.out

