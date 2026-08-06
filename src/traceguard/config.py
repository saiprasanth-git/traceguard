"""Project configuration loaded from ``traceguard.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REQUIREMENTS = ["requirements/**/*.md"]
DEFAULT_CODE = ["src/**/*.c", "src/**/*.h", "src/**/*.py"]
DEFAULT_TESTS = ["tests/**/*.c", "tests/**/*.py"]


@dataclass
class Config:
    root: Path
    requirements: list[str] = field(default_factory=lambda: list(DEFAULT_REQUIREMENTS))
    code: list[str] = field(default_factory=lambda: list(DEFAULT_CODE))
    tests: list[str] = field(default_factory=lambda: list(DEFAULT_TESTS))
    fail_on: str = "error"  # "error" | "warning" | "never"
    waivers: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path, path: Path | None = None) -> Config:
        candidate = path or (root / "traceguard.toml")
        if not candidate.exists():
            return cls(root=root)
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        section = data.get("traceguard", data)
        return cls(
            root=root,
            requirements=section.get("requirements", list(DEFAULT_REQUIREMENTS)),
            code=section.get("code", list(DEFAULT_CODE)),
            tests=section.get("tests", list(DEFAULT_TESTS)),
            fail_on=section.get("fail_on", "error"),
            waivers=section.get("waivers", []),
        )

    def is_waived(self, rule: str, requirement_id: str | None) -> bool:
        """Waivers are ``RULE`` or ``RULE:REQ-ID`` strings."""
        for waiver in self.waivers:
            if ":" in waiver:
                waived_rule, waived_req = waiver.split(":", 1)
                if rule.startswith(waived_rule.strip()) and requirement_id == waived_req.strip():
                    return True
            elif rule.startswith(waiver.strip()):
                return True
        return False
