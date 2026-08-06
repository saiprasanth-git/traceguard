"""Parser unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from traceguard.model import DalLevel, ReqLevel
from traceguard.parsers import (
    discover,
    parse_code_annotations,
    parse_requirements,
    parse_verification_cases,
)


def test_parses_id_title_level_and_dal(clean_project: Path):
    requirements, findings = parse_requirements([clean_project / "requirements" / "reqs.md"])
    by_id = {r.id: r for r in requirements}

    assert set(by_id) == {"SYS-DEM-001", "HLR-DEM-010", "LLR-DEM-011"}
    assert by_id["LLR-DEM-011"].level is ReqLevel.LOW
    assert by_id["LLR-DEM-011"].dal is DalLevel.B
    assert by_id["HLR-DEM-010"].title == "Software computes the thing"
    assert by_id["HLR-DEM-010"].parents == ["SYS-DEM-001"]
    assert not findings


def test_body_text_is_captured(clean_project: Path):
    requirements, _ = parse_requirements([clean_project / "requirements" / "reqs.md"])
    hlr = next(r for r in requirements if r.id == "HLR-DEM-010")
    assert "compute the thing" in hlr.text


def test_multiple_parents_are_split(tmp_path: Path):
    spec = tmp_path / "r.md"
    spec.write_text(
        "### LLR-X-001: Multi parent\n\n- parents: HLR-X-010, HLR-X-020\n",
        encoding="utf-8",
    )
    requirements, _ = parse_requirements([spec])
    assert requirements[0].parents == ["HLR-X-010", "HLR-X-020"]


def test_invalid_dal_raises_finding(tmp_path: Path):
    spec = tmp_path / "r.md"
    spec.write_text("### LLR-X-001: Bad dal\n\n- dal: Z\n", encoding="utf-8")
    _, findings = parse_requirements([spec])
    assert [f.rule for f in findings] == ["TG011-bad-dal"]


def test_unknown_attribute_warns(tmp_path: Path):
    spec = tmp_path / "r.md"
    spec.write_text("### LLR-X-001: Odd\n\n- priority: high\n", encoding="utf-8")
    _, findings = parse_requirements([spec])
    assert findings[0].rule == "TG010-unknown-attribute"
    assert findings[0].severity == "warning"


def test_level_inference_rejects_unknown_prefix():
    with pytest.raises(ValueError):
        ReqLevel.from_id("REQ-X-001")


def test_code_annotation_resolves_symbol(clean_project: Path):
    annotations = parse_code_annotations([clean_project / "src" / "thing.c"])
    assert len(annotations) == 1
    assert annotations[0].requirement_id == "LLR-DEM-011"
    assert annotations[0].symbol == "compute_thing"
    assert annotations[0].source.line == 2


def test_verification_cases_capture_method(clean_project: Path):
    cases = parse_verification_cases([clean_project / "tests" / "test_thing.c"])
    methods = sorted(c.method for c in cases)
    assert methods == ["integration", "review", "review", "unit"]
    assert {c.requirement_id for c in cases} == {"LLR-DEM-011", "HLR-DEM-010"}


def test_method_defaults_to_unit(tmp_path: Path):
    test_file = tmp_path / "t.c"
    test_file.write_text("/* @verifies LLR-X-001 */\nvoid t(void) {}\n", encoding="utf-8")
    cases = parse_verification_cases([test_file])
    assert cases[0].method == "unit"


def test_python_symbol_lookahead(tmp_path: Path):
    module = tmp_path / "m.py"
    module.write_text("# @implements LLR-X-001\ndef do_work():\n    pass\n", encoding="utf-8")
    annotations = parse_code_annotations([module])
    assert annotations[0].symbol == "do_work"


def test_control_keywords_are_not_symbols(tmp_path: Path):
    source = tmp_path / "m.c"
    source.write_text(
        "/* @implements LLR-X-001 */\nif (x) {\n}\nvoid real_symbol(void) {}\n",
        encoding="utf-8",
    )
    annotations = parse_code_annotations([source])
    assert annotations[0].symbol == "real_symbol"


def test_discover_skips_build_directories(clean_project: Path):
    (clean_project / "build").mkdir()
    generated = clean_project / "build" / "generated.c"
    generated.write_text("/* @implements LLR-X */", encoding="utf-8")
    found = discover(clean_project, ["**/*.c"])
    assert all("build" not in p.parts for p in found)
