"""The shipped example must stay clean - it is the tool's own regression baseline."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from traceguard.analyzer import compute_metrics
from traceguard.cli import build_graph
from traceguard.config import Config

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "altitude_hold"


@pytest.fixture(scope="module")
def example_graph():
    return build_graph(Config.load(EXAMPLE))


def test_example_has_no_errors(example_graph):
    assert [f.format() for f in example_graph.errors] == []


def test_example_is_fully_covered(example_graph):
    metrics = compute_metrics(example_graph)
    assert metrics["implementation_coverage_pct"] == 100.0
    assert metrics["verification_coverage_pct"] == 100.0
    assert metrics["low_level_requirements"] == 10
    assert metrics["high_level_requirements"] == 5
    assert metrics["system_requirements"] == 3


def test_example_declares_its_derived_requirement(example_graph):
    derived = [r for r in example_graph.requirements.values() if r.derived]
    assert [r.id for r in derived] == ["LLR-ALTH-014"]
    assert derived[0].rationale


def test_every_llr_traces_to_an_hlr_and_a_sys(example_graph):
    for llr in example_graph.requirements.values():
        if llr.level.value != "LLR":
            continue
        if llr.derived and not llr.parents:
            continue
        parents = [example_graph.requirements[p] for p in llr.parents]
        assert parents, llr.id
        for hlr in parents:
            assert hlr.level.value == "HLR"
            assert hlr.parents, f"{hlr.id} does not trace to a system requirement"


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not available")
def test_c_verification_suite_passes(tmp_path: Path):
    binary = tmp_path / "test_altitude_hold"
    compile_result = subprocess.run(
        [
            "gcc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-O2",
            f"-I{EXAMPLE / 'include'}",
            f"-I{EXAMPLE / 'tests'}",
            str(EXAMPLE / "src" / "altitude_hold.c"),
            str(EXAMPLE / "tests" / "test_altitude_hold.c"),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr
    assert "0 failure(s)" in run_result.stdout
