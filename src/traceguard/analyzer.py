"""Graph resolution and the TraceGuard rule set.

Rules are deliberately named ``TGnnn`` so they can be referenced from review
records, waivers and the CI log without ambiguity.

+--------+------------------------+------------------------------------------------+
| Rule   | Name                   | Meaning                                        |
+========+========================+================================================+
| TG001  | duplicate-req          | Requirement id declared twice                   |
| TG002  | missing-parent         | Parent id referenced but never declared         |
| TG003  | orphan-requirement     | Non-system requirement has no parent and is not |
|        |                        | flagged ``derived``                             |
| TG004  | derived-no-rationale   | Derived requirement lacks a rationale           |
| TG005  | unimplemented-llr      | LLR has no ``@implements`` annotation           |
| TG006  | unverified-requirement | Requirement has no ``@verifies`` annotation     |
| TG007  | dangling-code-trace    | Code traces to an unknown requirement           |
| TG008  | dangling-test-trace    | Test traces to an unknown requirement           |
| TG009  | childless-hlr          | HLR decomposes into no LLR                      |
| TG012  | level-inversion        | Parent is not one abstraction level higher      |
| TG013  | unknown-method         | ``method=`` value is not a recognised method    |
| TG014  | dal-a-single-method    | DAL A/B requirement verified by only one method |
+--------+------------------------+------------------------------------------------+
"""

from __future__ import annotations

from .model import DalLevel, Finding, ReqLevel, TraceGraph

_EXPECTED_PARENT: dict[ReqLevel, ReqLevel] = {
    ReqLevel.LOW: ReqLevel.HIGH,
    ReqLevel.HIGH: ReqLevel.SYSTEM,
}

_HIGH_INTEGRITY = {DalLevel.A, DalLevel.B}


def resolve(graph: TraceGraph) -> TraceGraph:
    """Link parents, code and tests into the graph, then run every rule."""
    _link_parents(graph)
    _link_code(graph)
    _link_tests(graph)
    _check_structure(graph)
    _check_coverage(graph)
    return graph


# --------------------------------------------------------------------------- #
# Linking
# --------------------------------------------------------------------------- #

def _link_parents(graph: TraceGraph) -> None:
    for requirement in graph.requirements.values():
        for parent_id in requirement.parents:
            parent = graph.requirements.get(parent_id)
            if parent is None:
                graph.findings.append(
                    Finding(
                        rule="TG002-missing-parent",
                        severity="error",
                        message=f"Parent {parent_id} is not declared in any specification",
                        requirement_id=requirement.id,
                        source=requirement.source,
                    )
                )
                continue
            if requirement.id not in parent.children:
                parent.children.append(requirement.id)


def _link_code(graph: TraceGraph) -> None:
    for annotation in graph.annotations:
        requirement = graph.requirements.get(annotation.requirement_id)
        if requirement is None:
            graph.findings.append(
                Finding(
                    rule="TG007-dangling-code-trace",
                    severity="error",
                    message=(
                        f"Code symbol {annotation.symbol!r} implements unknown requirement "
                        f"{annotation.requirement_id}"
                    ),
                    requirement_id=annotation.requirement_id,
                    source=annotation.source,
                )
            )
            continue
        requirement.code_refs.append(annotation.source)


def _link_tests(graph: TraceGraph) -> None:
    for case in graph.cases:
        requirement = graph.requirements.get(case.requirement_id)
        if requirement is None:
            graph.findings.append(
                Finding(
                    rule="TG008-dangling-test-trace",
                    severity="error",
                    message=(
                        f"Verification case {case.case_id!r} verifies unknown requirement "
                        f"{case.requirement_id}"
                    ),
                    requirement_id=case.requirement_id,
                    source=case.source,
                )
            )
            continue
        if case.method not in case.KNOWN_METHODS:
            graph.findings.append(
                Finding(
                    rule="TG013-unknown-method",
                    severity="warning",
                    message=(
                        f"Verification method {case.method!r} is not recognised; "
                        f"expected one of {', '.join(case.KNOWN_METHODS)}"
                    ),
                    requirement_id=case.requirement_id,
                    source=case.source,
                )
            )
        requirement.test_refs.append(case)


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #

def _check_structure(graph: TraceGraph) -> None:
    for requirement in graph.requirements.values():
        expected_parent_level = _EXPECTED_PARENT.get(requirement.level)

        if expected_parent_level and not requirement.parents:
            if requirement.derived:
                if not requirement.rationale:
                    graph.findings.append(
                        Finding(
                            rule="TG004-derived-no-rationale",
                            severity="error",
                            message=(
                                "Derived requirement must carry a rationale for the safety "
                                "assessment process (DO-178C 5.1.2.h)"
                            ),
                            requirement_id=requirement.id,
                            source=requirement.source,
                        )
                    )
            else:
                graph.findings.append(
                    Finding(
                        rule="TG003-orphan-requirement",
                        severity="error",
                        message=(
                            f"{requirement.level.value} has no parent and is not marked derived"
                        ),
                        requirement_id=requirement.id,
                        source=requirement.source,
                    )
                )

        for parent_id in requirement.parents:
            parent = graph.requirements.get(parent_id)
            if parent is None or expected_parent_level is None:
                continue
            if parent.level is not expected_parent_level:
                graph.findings.append(
                    Finding(
                        rule="TG012-level-inversion",
                        severity="error",
                        message=(
                            f"{requirement.level.value} traces to {parent.level.value} "
                            f"{parent_id}; expected a {expected_parent_level.value} parent"
                        ),
                        requirement_id=requirement.id,
                        source=requirement.source,
                    )
                )

        if requirement.level is ReqLevel.HIGH and not requirement.children:
            graph.findings.append(
                Finding(
                    rule="TG009-childless-hlr",
                    severity="error",
                    message="HLR is not decomposed into any low-level requirement",
                    requirement_id=requirement.id,
                    source=requirement.source,
                )
            )


def _check_coverage(graph: TraceGraph) -> None:
    for requirement in graph.requirements.values():
        if requirement.is_verifiable_unit and not requirement.code_refs:
            graph.findings.append(
                Finding(
                    rule="TG005-unimplemented-llr",
                    severity="error",
                    message="No source code carries an @implements annotation for this LLR",
                    requirement_id=requirement.id,
                    source=requirement.source,
                )
            )

        if requirement.level is ReqLevel.SYSTEM:
            # System requirements are verified transitively through their children.
            continue

        if not requirement.test_refs:
            graph.findings.append(
                Finding(
                    rule="TG006-unverified-requirement",
                    severity="error",
                    message="No verification case carries a @verifies annotation",
                    requirement_id=requirement.id,
                    source=requirement.source,
                )
            )
            continue

        if requirement.dal in _HIGH_INTEGRITY:
            methods = {case.method for case in requirement.test_refs}
            if len(methods) < 2:
                graph.findings.append(
                    Finding(
                        rule="TG014-dal-a-single-method",
                        severity="warning",
                        message=(
                            f"DAL {requirement.dal.value} requirement is verified by a single "
                            f"method ({', '.join(sorted(methods))}); independent verification "
                            "is expected"
                        ),
                        requirement_id=requirement.id,
                        source=requirement.source,
                    )
                )


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def compute_metrics(graph: TraceGraph) -> dict[str, object]:
    """Summarise the graph into the numbers a certification review asks for."""
    llrs = graph.by_level(ReqLevel.LOW)
    hlrs = graph.by_level(ReqLevel.HIGH)
    tracked = llrs + hlrs

    implemented = [r for r in llrs if r.code_refs]
    verified = [r for r in tracked if r.test_refs]

    def pct(part: int, whole: int) -> float:
        return round(100.0 * part / whole, 1) if whole else 0.0

    return {
        "requirements_total": len(graph.requirements),
        "system_requirements": len(graph.by_level(ReqLevel.SYSTEM)),
        "high_level_requirements": len(hlrs),
        "low_level_requirements": len(llrs),
        "derived_requirements": sum(1 for r in graph.requirements.values() if r.derived),
        "code_annotations": len(graph.annotations),
        "verification_cases": len(graph.cases),
        "implementation_coverage_pct": pct(len(implemented), len(llrs)),
        "verification_coverage_pct": pct(len(verified), len(tracked)),
        "errors": len(graph.errors),
        "warnings": len(graph.warnings),
    }
