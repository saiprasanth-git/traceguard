# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Rule identifiers (`TGnnn`) are part of the public interface: they appear in user
waiver files and review records. Renaming or renumbering a rule is a breaking
change and requires a major version bump.

## [0.1.0] - Initial release

### Added

- **Trace graph model** - `Requirement`, `CodeAnnotation`, `VerificationCase`,
  `Finding` and `TraceGraph`, with `SYS`/`HLR`/`LLR` levels and DAL A-E.
- **Markdown requirement parser** - level-3 headings with a `dal` / `parents` /
  `derived` / `rationale` attribute block, level inferred from the id prefix.
- **Annotation parsers** - `@implements` in source code and
  `@verifies ... method=` in tests, with best-effort symbol resolution for
  C-family and Python declarations.
- **14 rules** (`TG001`-`TG014`) covering duplicate ids, missing and inverted
  parents, orphan requirements, derived requirements without rationale,
  unimplemented LLRs, unverified requirements, dangling code and test traces,
  childless HLRs, invalid DALs, unknown attributes and methods, and
  single-method verification of DAL A/B requirements.
- **CLI** - `check` (CI gate, exit `0`/`1`/`2`), `report`, `show`, `rules`.
- **Three report formats** - Markdown matrix for review records, self-contained
  HTML dashboard with coverage bars and no external assets, and JSON under the
  stable `traceguard/v1` schema.
- **Configuration** - `traceguard.toml` with glob-based discovery, a `fail_on`
  threshold, and scoped waivers (`RULE` or `RULE:REQUIREMENT-ID`).
- **Root-relative paths** in all reports, so evidence is reproducible across
  build agents.
- **Worked example** - `examples/altitude_hold`, a DAL B altitude-hold control law
  in C99: 18 requirements (one derived), 14 verification cases, a Makefile driving
  build, verification and the trace gate, and a review record.
- **Test suite** - 50 tests covering the parsers, every rule, the CLI, waiver
  scoping and path relativisation, plus compilation and execution of the C example
  under `-Wall -Wextra -Werror -Wpedantic`.
- **CI** - GitHub Actions across Python 3.11/3.12/3.13, publishing the
  traceability matrix to the run summary and retaining the artefacts against the
  commit.
- **Documentation** - architecture, annotation reference, DO-178C objective
  mapping with stated gaps, corporate SOP, CI integration recipes, waiver policy
  and an example walkthrough.
