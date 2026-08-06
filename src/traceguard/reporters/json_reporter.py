"""Machine-readable report, suitable for dashboards and downstream tooling."""

from __future__ import annotations

import json

from ..analyzer import compute_metrics
from ..model import TraceGraph


def to_dict(graph: TraceGraph) -> dict:
    return {
        "schema": "traceguard/v1",
        "metrics": compute_metrics(graph),
        "requirements": [
            {
                "id": r.id,
                "title": r.title,
                "level": r.level.value,
                "dal": r.dal.value,
                "derived": r.derived,
                "rationale": r.rationale,
                "parents": r.parents,
                "children": r.children,
                "source": str(r.source) if r.source else None,
                "code": [str(ref) for ref in r.code_refs],
                "tests": [
                    {"case": c.case_id, "method": c.method, "source": str(c.source)}
                    for c in r.test_refs
                ],
            }
            for r in sorted(graph.requirements.values(), key=lambda r: r.id)
        ],
        "findings": [
            {
                "rule": f.rule,
                "severity": f.severity,
                "message": f.message,
                "requirement": f.requirement_id,
                "source": str(f.source) if f.source else None,
            }
            for f in graph.findings
        ],
    }


def render_json(graph: TraceGraph) -> str:
    return json.dumps(to_dict(graph), indent=2) + "\n"
