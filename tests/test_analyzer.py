"""Rule-set tests: each rule gets a project that provokes exactly that finding."""

from __future__ import annotations

from pathlib import Path

from traceguard.analyzer import compute_metrics
from traceguard.cli import build_graph
from traceguard.config import Config

from .conftest import GOOD_CODE, GOOD_REQUIREMENTS, GOOD_TEST


def rules_for(root: Path) -> set[str]:
    graph = build_graph(Config.load(root))
    return {f.rule for f in graph.findings}


def test_clean_project_has_no_findings(clean_project: Path):
    graph = build_graph(Config.load(clean_project))
    assert graph.findings == []
    assert graph.errors == []


def test_clean_project_metrics(clean_project: Path):
    graph = build_graph(Config.load(clean_project))
    metrics = compute_metrics(graph)
    assert metrics["requirements_total"] == 3
    assert metrics["low_level_requirements"] == 1
    assert metrics["implementation_coverage_pct"] == 100.0
    assert metrics["verification_coverage_pct"] == 100.0
    assert metrics["errors"] == 0


def test_tg001_duplicate_requirement(project_factory):
    duplicate = "\n### LLR-DEM-011: Again\n\n- parents: HLR-DEM-010\n"
    root = project_factory(requirements=GOOD_REQUIREMENTS + duplicate)
    assert "TG001-duplicate-req" in rules_for(root)


def test_tg002_missing_parent(project_factory):
    spec = GOOD_REQUIREMENTS.replace("- parents: HLR-DEM-010", "- parents: HLR-NOPE-999")
    assert "TG002-missing-parent" in rules_for(project_factory(requirements=spec))


def test_tg003_orphan_requirement(project_factory):
    spec = GOOD_REQUIREMENTS.replace("- parents: SYS-DEM-001\n", "")
    assert "TG003-orphan-requirement" in rules_for(project_factory(requirements=spec))


def test_tg004_derived_without_rationale(project_factory):
    spec = GOOD_REQUIREMENTS.replace(
        "- parents: SYS-DEM-001\n", "- derived: true\n"
    )
    assert "TG004-derived-no-rationale" in rules_for(project_factory(requirements=spec))


def test_derived_with_rationale_is_accepted(project_factory):
    spec = GOOD_REQUIREMENTS.replace(
        "- parents: SYS-DEM-001\n",
        "- derived: true\n- rationale: Imposed by the scheduler, no parent exists.\n",
    )
    rules = rules_for(project_factory(requirements=spec))
    assert "TG004-derived-no-rationale" not in rules
    assert "TG003-orphan-requirement" not in rules


def test_tg005_unimplemented_llr(project_factory):
    assert "TG005-unimplemented-llr" in rules_for(project_factory(code="/* no annotations */\n"))


def test_tg006_unverified_requirement(project_factory):
    assert "TG006-unverified-requirement" in rules_for(project_factory(tests="/* nothing */\n"))


def test_system_requirements_need_no_direct_test(clean_project: Path):
    graph = build_graph(Config.load(clean_project))
    unverified = [f for f in graph.findings if f.rule == "TG006-unverified-requirement"]
    assert unverified == []


def test_tg007_dangling_code_trace(project_factory):
    code = GOOD_CODE.replace("LLR-DEM-011", "LLR-GHOST-999")
    assert "TG007-dangling-code-trace" in rules_for(project_factory(code=code))


def test_tg008_dangling_test_trace(project_factory):
    tests = GOOD_TEST.replace("LLR-DEM-011 method=unit", "LLR-GHOST-999 method=unit")
    assert "TG008-dangling-test-trace" in rules_for(project_factory(tests=tests))


def test_tg009_childless_hlr(project_factory):
    spec = GOOD_REQUIREMENTS.replace("- parents: HLR-DEM-010", "- parents: SYS-DEM-001")
    rules = rules_for(project_factory(requirements=spec))
    assert "TG009-childless-hlr" in rules
    assert "TG012-level-inversion" in rules


def test_tg013_unknown_method(project_factory):
    tests = GOOD_TEST.replace("method=unit", "method=vibes")
    assert "TG013-unknown-method" in rules_for(project_factory(tests=tests))


def test_tg014_single_method_on_dal_b(project_factory):
    tests = GOOD_TEST.replace("method=review", "method=unit")
    rules = rules_for(project_factory(tests=tests))
    assert "TG014-dal-a-single-method" in rules


def test_dal_c_single_method_is_fine(project_factory):
    spec = GOOD_REQUIREMENTS.replace("- dal: B", "- dal: C")
    tests = GOOD_TEST.replace("method=review", "method=unit")
    assert "TG014-dal-a-single-method" not in rules_for(
        project_factory(requirements=spec, tests=tests)
    )


def test_waiver_suppresses_finding(project_factory):
    root = project_factory(code="/* no annotations */\n")
    config = Config.load(root)
    config.waivers = ["TG005-unimplemented-llr:LLR-DEM-011"]
    graph = build_graph(config)
    assert "TG005-unimplemented-llr" not in {f.rule for f in graph.findings}


def test_waiver_is_scoped_to_the_requirement(project_factory):
    root = project_factory(code="/* no annotations */\n")
    config = Config.load(root)
    config.waivers = ["TG005-unimplemented-llr:LLR-OTHER-001"]
    graph = build_graph(config)
    assert "TG005-unimplemented-llr" in {f.rule for f in graph.findings}


def test_parents_link_children_both_ways(clean_project: Path):
    graph = build_graph(Config.load(clean_project))
    assert graph.requirements["SYS-DEM-001"].children == ["HLR-DEM-010"]
    assert graph.requirements["HLR-DEM-010"].children == ["LLR-DEM-011"]
