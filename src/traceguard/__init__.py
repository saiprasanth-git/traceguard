"""TraceGuard - requirements traceability gate for safety-critical software.

TraceGuard reads plain-text requirement specifications, source-code
``@implements`` annotations and test ``@verifies`` annotations, resolves the
bidirectional traceability graph, and fails the build when the trace is broken.
"""

__version__ = "0.1.0"

from .analyzer import compute_metrics, resolve
from .config import Config
from .model import (
    CodeAnnotation,
    DalLevel,
    Finding,
    ReqLevel,
    Requirement,
    SourceRef,
    TraceGraph,
    VerificationCase,
)

__all__ = [
    "__version__",
    "Config",
    "CodeAnnotation",
    "DalLevel",
    "Finding",
    "ReqLevel",
    "Requirement",
    "SourceRef",
    "TraceGraph",
    "VerificationCase",
    "compute_metrics",
    "resolve",
]
