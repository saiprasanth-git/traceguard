"""CLI behaviour, exit codes and report rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from traceguard.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main


def test_check_passes_on_clean_project(clean_project: Path, capsys):
    assert main(["check", "--root", str(clean_project)]) == EXIT_OK
    assert "OK" in capsys.readouterr().out


def test_check_fails_on_gap(project_factory, capsys):
    root = project_factory(code="/* nothing */\n")
    assert main(["check", "--root", str(root)]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "TG005-unimplemented-llr" in out
    assert "FAILED" in out


def test_fail_on_never_always_passes(project_factory):
    root = project_factory(code="/* nothing */\n")
    assert main(["check", "--root", str(root), "--fail-on", "never"]) == EXIT_OK


def test_fail_on_warning_gates_warnings(project_factory):
    tests = """\
/**
 * @verifies LLR-DEM-011 method=vibes
 */
static void test_thing(void) {}
"""
    root = project_factory(tests=tests)
    assert main(["check", "--root", str(root), "--fail-on", "warning"]) == EXIT_FINDINGS


def test_report_markdown_to_stdout(clean_project: Path, capsys):
    assert main(["report", "--root", str(clean_project)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Requirements Traceability Matrix" in out
    assert "LLR-DEM-011" in out
    assert "PASS" in out


def test_report_json_is_valid_and_structured(clean_project: Path, capsys):
    assert main(["report", "--root", str(clean_project), "--format", "json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "traceguard/v1"
    assert payload["metrics"]["errors"] == 0
    ids = [r["id"] for r in payload["requirements"]]
    assert ids == sorted(ids)


def test_report_html_written_to_file(clean_project: Path, tmp_path: Path):
    out = tmp_path / "nested" / "report.html"
    assert main(
        ["report", "--root", str(clean_project), "--format", "html", "-o", str(out)]
    ) == EXIT_OK
    content = out.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert "Traceability matrix" in content
    assert "LLR-DEM-011" in content


def test_html_escapes_requirement_titles(project_factory, tmp_path: Path):
    spec = """\
### LLR-X-001: Handle <script> input

- derived: true
- rationale: Standalone check.
"""
    root = project_factory(requirements=spec)
    out = tmp_path / "r.html"
    main(["report", "--root", str(root), "--format", "html", "-o", str(out)])
    assert "<script>" not in out.read_text(encoding="utf-8")


def test_show_prints_trace_tree(clean_project: Path, capsys):
    assert main(["show", "--root", str(clean_project), "LLR-DEM-011"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "traces to  : HLR-DEM-010" in out
    assert "thing.c" in out
    assert "verified by" in out


def test_show_unknown_requirement_is_usage_error(clean_project: Path):
    assert main(["show", "--root", str(clean_project), "LLR-NOPE-000"]) == EXIT_USAGE


def test_rules_lists_every_rule(capsys):
    assert main(["rules"]) == EXIT_OK
    out = capsys.readouterr().out
    for rule in ("TG001", "TG005", "TG009", "TG014"):
        assert rule in out


def test_no_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_config_file_is_honoured(project_factory, tmp_path: Path):
    root = project_factory(code="/* nothing */\n")
    config = tmp_path / "tg.toml"
    config.write_text(
        '[traceguard]\nfail_on = "never"\nrequirements = ["requirements/**/*.md"]\n',
        encoding="utf-8",
    )
    assert main(["check", "--root", str(root), "--config", str(config)]) == EXIT_OK


def test_report_paths_are_relative_to_the_project_root(clean_project: Path, capsys):
    main(["report", "--root", str(clean_project), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    llr = next(r for r in payload["requirements"] if r["id"] == "LLR-DEM-011")
    assert llr["source"].startswith("requirements/")
    assert llr["code"] == ["src/thing.c:2"]
    assert all(t["source"].startswith("tests/") for t in llr["tests"])
    assert str(clean_project) not in json.dumps(payload)
