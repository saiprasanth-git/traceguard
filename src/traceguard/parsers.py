"""Parsers that turn project artefacts into TraceGuard model objects.

Three input formats are supported, all plain text so they diff cleanly in Git:

1. Requirement specifications  -- Markdown with a YAML-ish attribute block.
2. Source code annotations     -- ``@implements LLR-x`` inside C/C++/Python comments.
3. Verification annotations    -- ``@verifies LLR-x`` inside test files.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import (
    CodeAnnotation,
    DalLevel,
    Finding,
    ReqLevel,
    Requirement,
    SourceRef,
    VerificationCase,
)

# --------------------------------------------------------------------------- #
# Requirement specifications
# --------------------------------------------------------------------------- #

_REQ_HEADING = re.compile(r"^###\s+(?P<id>(?:SYS|HLR|LLR)-[A-Z0-9]+-\d+)\s*:\s*(?P<title>.+?)\s*$")
_ATTRIBUTE = re.compile(r"^-\s+(?P<key>[A-Za-z_]+)\s*:\s*(?P<value>.*?)\s*$")
_ANY_HEADING = re.compile(r"^#{1,6}\s+")

_LIST_KEYS = {"parents"}
_KNOWN_KEYS = {"dal", "parents", "derived", "rationale", "text"}


def parse_requirements(paths: list[Path]) -> tuple[list[Requirement], list[Finding]]:
    """Parse every requirement Markdown file into :class:`Requirement` objects."""
    requirements: list[Requirement] = []
    findings: list[Finding] = []

    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        current: Requirement | None = None
        body: list[str] = []

        def flush() -> None:
            nonlocal current, body
            if current is not None:
                if not current.text:
                    current.text = "\n".join(body).strip()
                requirements.append(current)
            current = None
            body = []

        for lineno, raw in enumerate(lines, start=1):
            heading = _REQ_HEADING.match(raw)
            if heading:
                flush()
                req_id = heading.group("id")
                current = Requirement(
                    id=req_id,
                    title=heading.group("title"),
                    level=ReqLevel.from_id(req_id),
                    dal=DalLevel.C,
                    source=SourceRef(str(path), lineno),
                )
                continue

            if current is None:
                continue

            if _ANY_HEADING.match(raw):
                # A non-requirement heading terminates the current block.
                flush()
                continue

            attribute = _ATTRIBUTE.match(raw)
            if attribute:
                key = attribute.group("key").lower()
                value = attribute.group("value").strip()
                if key not in _KNOWN_KEYS:
                    findings.append(
                        Finding(
                            rule="TG010-unknown-attribute",
                            severity="warning",
                            message=f"Unrecognised attribute {key!r} ignored",
                            requirement_id=current.id,
                            source=SourceRef(str(path), lineno),
                        )
                    )
                    continue
                _apply_attribute(current, key, value, findings, SourceRef(str(path), lineno))
                continue

            body.append(raw)

        flush()

    return requirements, findings


def _apply_attribute(
    requirement: Requirement,
    key: str,
    value: str,
    findings: list[Finding],
    source: SourceRef,
) -> None:
    if key == "dal":
        try:
            requirement.dal = DalLevel(value.strip().upper())
        except ValueError:
            findings.append(
                Finding(
                    rule="TG011-bad-dal",
                    severity="error",
                    message=f"Invalid DAL {value!r}; expected one of A-E",
                    requirement_id=requirement.id,
                    source=source,
                )
            )
    elif key in _LIST_KEYS:
        requirement.parents = [item.strip() for item in value.split(",") if item.strip()]
    elif key == "derived":
        requirement.derived = value.strip().lower() in {"true", "yes", "1"}
    elif key == "rationale":
        requirement.rationale = value
    elif key == "text":
        requirement.text = value


# --------------------------------------------------------------------------- #
# Code and verification annotations
# --------------------------------------------------------------------------- #

_IMPLEMENTS = re.compile(r"@implements\s+(?P<id>(?:SYS|HLR|LLR)-[A-Z0-9]+-\d+)")
_VERIFIES = re.compile(
    r"@verifies\s+(?P<id>(?:SYS|HLR|LLR)-[A-Z0-9]+-\d+)"
    r"(?:\s+method=(?P<method>[a-z]+))?"
)
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PY_SYMBOL = re.compile(r"^\s*def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")


def parse_code_annotations(paths: list[Path]) -> list[CodeAnnotation]:
    """Find every ``@implements`` marker and attach it to the nearest symbol."""
    annotations: list[CodeAnnotation] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, raw in enumerate(lines):
            match = _IMPLEMENTS.search(raw)
            if not match:
                continue
            annotations.append(
                CodeAnnotation(
                    requirement_id=match.group("id"),
                    symbol=_lookahead_symbol(lines, index) or path.stem,
                    source=SourceRef(str(path), index + 1),
                )
            )
    return annotations


def parse_verification_cases(paths: list[Path]) -> list[VerificationCase]:
    """Find every ``@verifies`` marker in the supplied test files."""
    cases: list[VerificationCase] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, raw in enumerate(lines):
            match = _VERIFIES.search(raw)
            if not match:
                continue
            symbol = _lookahead_symbol(lines, index) or f"{path.stem}:{index + 1}"
            cases.append(
                VerificationCase(
                    requirement_id=match.group("id"),
                    case_id=symbol,
                    method=match.group("method") or "unit",
                    source=SourceRef(str(path), index + 1),
                )
            )
    return cases


_C_KEYWORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "else", "do",
    "assert", "printf", "TEST", "static_assert",
}


def _lookahead_symbol(lines: list[str], start: int, window: int = 16) -> str | None:
    """Return the first function-like symbol declared after ``start``."""
    for raw in lines[start + 1 : start + 1 + window]:
        stripped = raw.strip()
        if not stripped or stripped.startswith(("*", "//", "#", "/*")):
            continue
        python_match = _PY_SYMBOL.match(raw)
        if python_match:
            return python_match.group("name")
        c_symbol = _c_symbol(stripped)
        if c_symbol:
            return c_symbol
    return None


def _c_symbol(line: str) -> str | None:
    """Return the declared function name on a C declaration line, if any.

    The name is the last identifier appearing immediately before the first
    ``(``. Control-flow keywords are rejected so that ``if (...)`` and friends
    are never mistaken for a declaration.
    """
    paren = line.find("(")
    if paren <= 0 or ";" in line[:paren]:
        return None
    identifiers = _IDENTIFIER.findall(line[:paren])
    if not identifiers:
        return None
    name = identifiers[-1]
    if name in _C_KEYWORDS or len(identifiers) < 2:
        return None
    return name


# --------------------------------------------------------------------------- #
# File discovery
# --------------------------------------------------------------------------- #

def discover(root: Path, patterns: list[str]) -> list[Path]:
    """Expand glob patterns relative to ``root``, skipping build noise."""
    ignored_parts = {".git", "build", "__pycache__", ".venv", "node_modules", ".pytest_cache"}
    found: list[Path] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            if ignored_parts & set(path.parts):
                continue
            if path not in found:
                found.append(path)
    return found
