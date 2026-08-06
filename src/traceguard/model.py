"""Core data model for TraceGuard.

The model mirrors the DO-178C life-cycle data relationships:

    System Requirement (SYS)
        -> High-Level Requirement (HLR)
            -> Low-Level Requirement (LLR)
                -> Source Code
                -> Verification Case (TEST)

Every object is intentionally simple and hashable-by-id so that the graph can be
built incrementally from independent parsers without a database.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class ReqLevel(StrEnum):
    """Requirement abstraction levels recognised by TraceGuard."""

    SYSTEM = "SYS"
    HIGH = "HLR"
    LOW = "LLR"

    @classmethod
    def from_id(cls, requirement_id: str) -> ReqLevel:
        prefix = requirement_id.split("-", 1)[0].upper()
        for level in cls:
            if level.value == prefix:
                return level
        raise ValueError(
            f"Cannot infer requirement level from id {requirement_id!r}. "
            "Ids must start with SYS-, HLR- or LLR-."
        )


class DalLevel(StrEnum):
    """DO-178C Design Assurance Levels, ordered from most to least critical."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


@dataclass(frozen=True)
class SourceRef:
    """A file/line pointer used in every finding so results are actionable."""

    path: str
    line: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.path}:{self.line}"


@dataclass
class Requirement:
    """A single requirement parsed from a Markdown requirement specification."""

    id: str
    title: str
    level: ReqLevel
    dal: DalLevel
    text: str = ""
    parents: list[str] = field(default_factory=list)
    derived: bool = False
    rationale: str = ""
    source: SourceRef | None = None

    # Populated during graph resolution.
    children: list[str] = field(default_factory=list)
    code_refs: list[SourceRef] = field(default_factory=list)
    test_refs: list[VerificationCase] = field(default_factory=list)

    @property
    def is_verifiable_unit(self) -> bool:
        """LLRs are the level at which code and unit tests must exist."""
        return self.level is ReqLevel.LOW


@dataclass
class CodeAnnotation:
    """An `@implements` marker found in source code."""

    requirement_id: str
    symbol: str
    source: SourceRef


@dataclass
class VerificationCase:
    """A `@verifies` marker found in a test file."""

    requirement_id: str
    case_id: str
    method: str
    source: SourceRef

    KNOWN_METHODS = ("unit", "integration", "hardware", "review", "analysis")


@dataclass
class Finding:
    """A single traceability defect."""

    rule: str
    severity: str  # "error" | "warning"
    message: str
    requirement_id: str | None = None
    source: SourceRef | None = None

    def format(self) -> str:
        location = f" ({self.source})" if self.source else ""
        subject = f"[{self.requirement_id}] " if self.requirement_id else ""
        return f"{self.severity.upper():7} {self.rule:22} {subject}{self.message}{location}"


@dataclass
class TraceGraph:
    """The resolved traceability graph plus every finding raised against it."""

    requirements: dict[str, Requirement] = field(default_factory=dict)
    annotations: list[CodeAnnotation] = field(default_factory=list)
    cases: list[VerificationCase] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    # ---------------------------------------------------------------- helpers
    def add_requirement(self, requirement: Requirement) -> None:
        if requirement.id in self.requirements:
            self.findings.append(
                Finding(
                    rule="TG001-duplicate-req",
                    severity="error",
                    message="Requirement id declared more than once",
                    requirement_id=requirement.id,
                    source=requirement.source,
                )
            )
            return
        self.requirements[requirement.id] = requirement

    def by_level(self, level: ReqLevel) -> list[Requirement]:
        return sorted(
            (r for r in self.requirements.values() if r.level is level),
            key=lambda r: r.id,
        )

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def extend_findings(self, findings: Iterable[Finding]) -> None:
        self.findings.extend(findings)
