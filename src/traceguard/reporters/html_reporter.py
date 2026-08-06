"""Single-file HTML dashboard - no external assets, safe to archive."""

from __future__ import annotations

import html
from datetime import UTC, datetime

from ..analyzer import compute_metrics
from ..model import ReqLevel, TraceGraph

_CSS = """
:root {
  --bg: #0f1115; --panel: #171a21; --line: #262b36;
  --fg: #e6e8ee; --muted: #9aa3b2;
  --ok: #3fb950; --warn: #d29922; --err: #f85149; --accent: #58a6ff;
}
* { box-sizing: border-box; }
body { margin: 0; padding: 32px; background: var(--bg); color: var(--fg);
  font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 17px; margin: 36px 0 12px; color: var(--fg); }
.sub { color: var(--muted); font-size: 13px; margin-bottom: 28px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 14px 16px; }
.card .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
.card .v { font-size: 24px; font-weight: 600; margin-top: 6px; }
table { width: 100%; border-collapse: collapse; background: var(--panel);
  border: 1px solid var(--line); border-radius: 10px; overflow: hidden; font-size: 13.5px; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line);
  vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: .05em; background: #12151c; }
tr:last-child td { border-bottom: none; }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12.5px;
  color: var(--accent); }
.pill { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 11.5px;
  font-weight: 600; letter-spacing: .03em; }
.pass { background: rgba(63,185,80,.15); color: var(--ok); }
.gap  { background: rgba(248,81,73,.15); color: var(--err); }
.error { background: rgba(248,81,73,.15); color: var(--err); }
.warning { background: rgba(210,153,34,.15); color: var(--warn); }
.bar { height: 7px; background: #22262f; border-radius: 999px; overflow: hidden; margin-top: 9px; }
.bar > span { display: block; height: 100%; background: var(--ok); }
.empty { color: var(--muted); }
.nowrap { white-space: nowrap; }
td code { white-space: nowrap; }
th:nth-child(2) { min-width: 200px; }
td:nth-child(6), td:nth-child(7) { min-width: 180px; }
"""


def _e(value: object) -> str:
    return html.escape(str(value))


def render_html(graph: TraceGraph, title: str = "TraceGuard Traceability Report") -> str:
    metrics = compute_metrics(graph)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    cards = []
    for key in (
        "requirements_total",
        "implementation_coverage_pct",
        "verification_coverage_pct",
        "verification_cases",
        "errors",
        "warnings",
    ):
        value = metrics[key]
        label = key.replace("_pct", " %").replace("_", " ")
        bar = ""
        if key.endswith("_pct"):
            bar = f'<div class="bar"><span style="width:{float(value)}%"></span></div>'
        cards.append(
            f'<div class="card"><div class="k">{_e(label)}</div>'
            f'<div class="v">{_e(value)}</div>{bar}</div>'
        )

    rows = []
    for level in (ReqLevel.SYSTEM, ReqLevel.HIGH, ReqLevel.LOW):
        for req in graph.by_level(level):
            needs_code = req.is_verifiable_unit
            verified = bool(req.test_refs) or level is ReqLevel.SYSTEM
            ok = verified and (bool(req.code_refs) or not needs_code)
            status = "pass" if ok else "gap"
            code = (
                "<br>".join(f"<code>{_e(r)}</code>" for r in req.code_refs)
                or '<span class="empty">-</span>'
            )
            cases = (
                "<br>".join(f"{_e(c.case_id)} <span class='empty'>({_e(c.method)})</span>"
                            for c in req.test_refs)
                or '<span class="empty">-</span>'
            )
            parents = ", ".join(req.parents) or ("derived" if req.derived else "-")
            rows.append(
                "<tr>"
                f'<td class="nowrap"><code>{_e(req.id)}</code></td>'
                f"<td>{_e(req.title)}</td>"
                f'<td class="nowrap">{_e(req.level.value)}</td>'
                f'<td class="nowrap">{_e(req.dal.value)}</td>'
                f'<td class="nowrap">{_e(parents)}</td>'
                f"<td>{code}</td>"
                f"<td>{cases}</td>"
                f'<td><span class="pill {status}">{status.upper()}</span></td>'
                "</tr>"
            )

    if graph.findings:
        finding_rows = "".join(
            "<tr>"
            f'<td><span class="pill {_e(f.severity)}">{_e(f.severity)}</span></td>'
            f"<td><code>{_e(f.rule)}</code></td>"
            f"<td>{_e(f.requirement_id or '-')}</td>"
            f"<td>{_e(f.message)}</td>"
            f"<td><code>{_e(f.source or '-')}</code></td>"
            "</tr>"
            for f in sorted(graph.findings, key=lambda f: (f.severity != "error", f.rule))
        )
        findings_table = (
            "<table><thead><tr><th>Severity</th><th>Rule</th><th>Requirement</th>"
            f"<th>Message</th><th>Location</th></tr></thead><tbody>{finding_rows}</tbody></table>"
        )
    else:
        findings_table = (
            '<div class="card"><span class="pill pass">CLEAN</span> '
            "No traceability findings were raised.</div>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title><style>{_CSS}</style></head>
<body>
<h1>{_e(title)}</h1>
<div class="sub">Generated by TraceGuard &middot; {_e(stamp)}</div>
<div class="cards">{''.join(cards)}</div>
<h2>Traceability matrix</h2>
<table><thead><tr><th>Requirement</th><th>Title</th><th>Level</th><th>DAL</th>
<th class="nowrap">Traces to</th><th>Code</th><th>Verification</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Findings</h2>
{findings_table}
</body></html>
"""
