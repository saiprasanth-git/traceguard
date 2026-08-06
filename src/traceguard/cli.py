"""Command line interface.

    traceguard check   -- run the rule set, exit non-zero on failure (CI gate)
    traceguard report  -- write markdown / html / json traceability artefacts
    traceguard show    -- print the trace tree for one requirement
    traceguard rules   -- list every rule TraceGuard enforces
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import compute_metrics, resolve
from .config import Config
from .model import SourceRef, TraceGraph
from .parsers import (
    discover,
    parse_code_annotations,
    parse_requirements,
    parse_verification_cases,
)
from .reporters import render_html, render_json, render_markdown

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

RULES = [
    ("TG001-duplicate-req", "error", "Requirement id declared more than once"),
    ("TG002-missing-parent", "error", "Parent requirement id does not exist"),
    ("TG003-orphan-requirement", "error", "HLR/LLR with no parent and not marked derived"),
    ("TG004-derived-no-rationale", "error", "Derived requirement without a rationale"),
    ("TG005-unimplemented-llr", "error", "LLR with no @implements annotation in code"),
    ("TG006-unverified-requirement", "error", "Requirement with no @verifies annotation"),
    ("TG007-dangling-code-trace", "error", "Code traces to an unknown requirement"),
    ("TG008-dangling-test-trace", "error", "Test traces to an unknown requirement"),
    ("TG009-childless-hlr", "error", "HLR not decomposed into any LLR"),
    ("TG010-unknown-attribute", "warning", "Unrecognised requirement attribute"),
    ("TG011-bad-dal", "error", "DAL outside A-E"),
    ("TG012-level-inversion", "error", "Parent is not one abstraction level higher"),
    ("TG013-unknown-method", "warning", "Unrecognised verification method"),
    ("TG014-dal-a-single-method", "warning", "DAL A/B verified by a single method"),
]


# --------------------------------------------------------------------------- #
# Graph construction
# --------------------------------------------------------------------------- #

def build_graph(config: Config) -> TraceGraph:
    """Discover artefacts, parse them, and resolve the traceability graph."""
    graph = TraceGraph()

    req_files = discover(config.root, config.requirements)
    code_files = discover(config.root, config.code)
    test_files = discover(config.root, config.tests)
    # A file cannot be both production code and a test.
    code_files = [p for p in code_files if p not in test_files]

    requirements, parse_findings = parse_requirements(req_files)
    for requirement in requirements:
        graph.add_requirement(requirement)
    graph.extend_findings(parse_findings)

    graph.annotations = parse_code_annotations(code_files)
    graph.cases = parse_verification_cases(test_files)

    resolve(graph)

    if config.waivers:
        graph.findings = [
            f for f in graph.findings if not config.is_waived(f.rule, f.requirement_id)
        ]
    _relativize(graph, config.root)
    return graph


def _relativize(graph: TraceGraph, root: Path) -> None:
    """Rewrite every file reference relative to the project root.

    Reports are archived as certification evidence, so they must not leak the
    absolute paths of whichever machine happened to run the build.
    """

    def rel(ref: SourceRef | None) -> SourceRef | None:
        if ref is None:
            return None
        try:
            return SourceRef(str(Path(ref.path).resolve().relative_to(root)), ref.line)
        except ValueError:
            return ref

    for requirement in graph.requirements.values():
        requirement.source = rel(requirement.source)
        requirement.code_refs = [r for r in (rel(ref) for ref in requirement.code_refs) if r]
        for case in requirement.test_refs:
            case.source = rel(case.source) or case.source
    for annotation in graph.annotations:
        annotation.source = rel(annotation.source) or annotation.source
    for case in graph.cases:
        case.source = rel(case.source) or case.source
    for finding in graph.findings:
        finding.source = rel(finding.source)


def _should_fail(graph: TraceGraph, fail_on: str) -> bool:
    if fail_on == "never":
        return False
    if fail_on == "warning":
        return bool(graph.findings)
    return bool(graph.errors)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_check(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    graph = build_graph(config)
    metrics = compute_metrics(graph)

    print(f"TraceGuard {__version__} - {config.root}")
    print(
        f"  requirements: {metrics['requirements_total']} "
        f"(SYS {metrics['system_requirements']} / "
        f"HLR {metrics['high_level_requirements']} / "
        f"LLR {metrics['low_level_requirements']})"
    )
    print(
        f"  implementation coverage: {metrics['implementation_coverage_pct']}%   "
        f"verification coverage: {metrics['verification_coverage_pct']}%"
    )
    print(f"  findings: {metrics['errors']} error(s), {metrics['warnings']} warning(s)")

    if graph.findings:
        print()
        for finding in sorted(graph.findings, key=lambda f: (f.severity != "error", f.rule)):
            print("  " + finding.format())

    if _should_fail(graph, config.fail_on):
        print(f"\nFAILED (fail_on={config.fail_on})")
        return EXIT_FINDINGS
    print("\nOK")
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    graph = build_graph(config)

    renderers = {"markdown": render_markdown, "html": render_html, "json": render_json}
    content = renderers[args.format](graph)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"Wrote {args.format} report to {out}")
    else:
        sys.stdout.write(content)
    return EXIT_OK


def cmd_show(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    graph = build_graph(config)
    requirement = graph.requirements.get(args.requirement_id)
    if requirement is None:
        print(f"Unknown requirement {args.requirement_id!r}", file=sys.stderr)
        return EXIT_USAGE

    print(f"{requirement.id}  [{requirement.level.value}, DAL {requirement.dal.value}]")
    print(f"  title      : {requirement.title}")
    if requirement.text:
        print(f"  text       : {requirement.text.splitlines()[0]}")
    print(f"  declared at: {requirement.source}")
    traces_to = ", ".join(requirement.parents)
    if not traces_to:
        traces_to = "derived" if requirement.derived else "nothing"
    print(f"  traces to  : {traces_to}")
    if requirement.derived and requirement.rationale:
        print(f"  rationale  : {requirement.rationale}")
    print(f"  children   : {', '.join(requirement.children) or 'none'}")
    print(f"  code       : {', '.join(str(r) for r in requirement.code_refs) or 'none'}")
    for case in requirement.test_refs:
        print(f"  verified by: {case.case_id} (method={case.method}) at {case.source}")
    if not requirement.test_refs:
        print("  verified by: nothing")

    related = [f for f in graph.findings if f.requirement_id == requirement.id]
    if related:
        print("  findings   :")
        for finding in related:
            print("    " + finding.format())
    return EXIT_OK


def cmd_rules(_: argparse.Namespace) -> int:
    width = max(len(rule) for rule, _, _ in RULES)
    print(f"{'RULE'.ljust(width)}  SEVERITY  DESCRIPTION")
    for rule, severity, description in RULES:
        print(f"{rule.ljust(width)}  {severity:8}  {description}")
    return EXIT_OK


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #

def _config_from_args(args: argparse.Namespace) -> Config:
    root = Path(args.root).resolve()
    config = Config.load(root, Path(args.config) if args.config else None)
    if getattr(args, "fail_on", None):
        config.fail_on = args.fail_on
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="traceguard",
        description="Requirements traceability gate for DO-178C style projects.",
    )
    parser.add_argument("--version", action="version", version=f"traceguard {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--root", default=".", help="project root (default: .)")
        sub.add_argument("--config", default=None, help="path to traceguard.toml")

    check = subparsers.add_parser("check", help="run the rule set and gate CI")
    add_common(check)
    check.add_argument(
        "--fail-on",
        dest="fail_on",
        choices=["error", "warning", "never"],
        default=None,
        help="override the configured failure threshold",
    )
    check.set_defaults(func=cmd_check)

    report = subparsers.add_parser("report", help="render a traceability report")
    add_common(report)
    report.add_argument(
        "--format", choices=["markdown", "html", "json"], default="markdown"
    )
    report.add_argument("--output", "-o", default=None, help="output file (default: stdout)")
    report.set_defaults(func=cmd_report)

    show = subparsers.add_parser("show", help="print the trace tree for one requirement")
    add_common(show)
    show.add_argument("requirement_id")
    show.set_defaults(func=cmd_show)

    rules = subparsers.add_parser("rules", help="list every enforced rule")
    rules.set_defaults(func=cmd_rules)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
