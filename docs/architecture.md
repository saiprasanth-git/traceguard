# Architecture

TraceGuard is a small, dependency-free pipeline. Understanding four stages is
enough to extend it.

```
                    traceguard.toml
                          |
                          v
  requirements/*.md ---> parse_requirements ---+
  src/**/*.c        ---> parse_code_annotations +--> TraceGraph --> resolve() --> reporters
  tests/**/*.c      ---> parse_verification_cases  (raw)          (rules run)     md/html/json
                                                                       |
                                                                       v
                                                              exit code (CI gate)
```

## Modules

| Module | Responsibility |
| --- | --- |
| `traceguard/model.py` | Data classes: `Requirement`, `CodeAnnotation`, `VerificationCase`, `Finding`, `TraceGraph`, plus the `ReqLevel` and `DalLevel` enumerations. No I/O, no rules. |
| `traceguard/parsers.py` | Text in, model objects out. Markdown requirement parsing, annotation extraction, symbol resolution, file discovery. No rules. |
| `traceguard/analyzer.py` | Links the graph (parents, code, tests) and runs every `TGnnn` rule. Pure function of the graph. |
| `traceguard/config.py` | Loads `traceguard.toml`, applies waivers. |
| `traceguard/reporters/` | Renders a resolved graph as Markdown, HTML or JSON. Read-only with respect to the graph. |
| `traceguard/cli.py` | Argument parsing, orchestration (`build_graph`), path relativisation, exit codes. |

The dependency direction is strictly one way: `cli -> reporters -> analyzer ->
parsers -> model`. Nothing lower ever imports something higher, which is what
keeps the rule set testable without touching the filesystem.

## The trace graph

`TraceGraph` is a dictionary of requirements keyed by id, plus flat lists of
annotations, verification cases and findings. Edges are stored as id strings
rather than object references so that a partially populated graph is still valid
and so that a dangling reference is data to be reported rather than a crash.

`resolve()` performs three linking passes and then two rule passes:

1. `_link_parents` - populates `Requirement.children` from `parents`, raising
   `TG002` for references that do not resolve.
2. `_link_code` - attaches `@implements` annotations to requirements, raising
   `TG007` for unknown ids.
3. `_link_tests` - attaches `@verifies` cases, raising `TG008` for unknown ids
   and `TG013` for unrecognised methods.
4. `_check_structure` - shape rules: orphans, derived rationale, level
   inversion, childless HLRs.
5. `_check_coverage` - completeness rules: unimplemented LLRs, unverified
   requirements, single-method verification on DAL A/B.

Every rule appends a `Finding` rather than raising, so one run reports every
problem in the repository instead of stopping at the first.

## Levels and what each one requires

| Level | Must trace up to | Must be implemented by code | Must have a verification case |
| --- | --- | --- | --- |
| `SYS-*` | nothing | no | no - verified transitively through its children |
| `HLR-*` | a `SYS-*` | no | yes |
| `LLR-*` | an `HLR-*` | yes | yes |

A requirement with no parent is an error unless it is explicitly marked
`derived: true` with a rationale. That mirrors DO-178C 5.1.2.h: derived
requirements are legitimate, but they must be identified and fed back to the
safety assessment process, so silence is not acceptable.

## Path handling

Parsers record absolute paths because they need to read files. `cli._relativize`
rewrites every `SourceRef` relative to the project root immediately before the
graph is returned. Reports are archived as certification evidence and must be
reproducible, so they must not contain the absolute paths of whichever build
agent happened to run.

## Adding a rule

1. Implement the check in `analyzer.py`, appending a `Finding` with the next free
   `TGnnn` identifier and a message that names the fix, not just the problem.
2. Register it in `cli.RULES` so `traceguard rules` documents it.
3. Add it to the tables in `README.md` and `docs/annotation-reference.md`.
4. Add a test in `tests/test_analyzer.py` that builds a project provoking exactly
   that finding, following the existing `test_tgNNN_*` pattern. Also add the
   negative case - the situation that looks similar but must **not** fire.

Rule identifiers are permanent. They appear in waiver files and review records,
so renaming or renumbering one is a breaking change.

## Adding a language

Language support lives entirely in `parsers.py`:

- Annotations are found with a plain regular expression, so any language whose
  comments can contain `@implements LLR-...` already works with no changes.
- Symbol resolution (the name shown in reports) is the only language-specific
  part: `_c_symbol` handles C-family declarations and `_PY_SYMBOL` handles
  Python `def`. Add a matcher to `_lookahead_symbol` for a new language and
  extend the `code`/`tests` globs in `traceguard.toml`.

Symbol resolution is intentionally best-effort. If no symbol is found the file
stem is used; the requirement link itself is never lost because of it.

## Test strategy

`tests/conftest.py` writes small throwaway projects to `tmp_path`, so the parsers
and rules are exercised end-to-end through real files rather than through mocks.
Each rule has a test that provokes it and, where a near-miss exists, a test that
proves it stays quiet. `tests/test_example_project.py` additionally compiles and
runs the C example with `gcc -Werror` and asserts the shipped example remains at
100% coverage with zero findings - if TraceGuard ever stops detecting gaps, that
suite fails.
