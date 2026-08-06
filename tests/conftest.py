"""Shared fixtures: build throwaway projects on disk to exercise the parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

GOOD_REQUIREMENTS = """\
# Requirements

### SYS-DEM-001: System level goal

- dal: B

The system shall do the thing.

### HLR-DEM-010: Software computes the thing

- dal: B
- parents: SYS-DEM-001

The software shall compute the thing.

### LLR-DEM-011: Thing formula

- dal: B
- parents: HLR-DEM-010

result = a + b
"""

GOOD_CODE = """\
/**
 * @implements LLR-DEM-011
 */
int compute_thing(int a, int b)
{
    return a + b;
}
"""

GOOD_TEST = """\
/**
 * @verifies LLR-DEM-011 method=unit
 */
static void test_thing(void)
{
    assert(compute_thing(1, 2) == 3);
}

/**
 * @verifies LLR-DEM-011 method=review
 * @verifies HLR-DEM-010 method=integration
 */
static void test_thing_integration(void)
{
    assert(compute_thing(2, 2) == 4);
}

/**
 * @verifies HLR-DEM-010 method=review
 */
static void test_thing_reviewed(void)
{
    assert(compute_thing(0, 0) == 0);
}
"""


def write_project(root: Path, requirements: str, code: str, tests: str) -> Path:
    (root / "requirements").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "requirements" / "reqs.md").write_text(requirements, encoding="utf-8")
    (root / "src" / "thing.c").write_text(code, encoding="utf-8")
    (root / "tests" / "test_thing.c").write_text(tests, encoding="utf-8")
    return root


@pytest.fixture
def project_factory(tmp_path: Path):
    counter = {"n": 0}

    def factory(
        requirements: str = GOOD_REQUIREMENTS,
        code: str = GOOD_CODE,
        tests: str = GOOD_TEST,
    ) -> Path:
        counter["n"] += 1
        root = tmp_path / f"project{counter['n']}"
        return write_project(root, requirements, code, tests)

    return factory


@pytest.fixture
def clean_project(project_factory) -> Path:
    return project_factory()
