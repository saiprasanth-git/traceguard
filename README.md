# TraceGuard

[![CI](https://github.com/saiprasanth-git/traceguard/actions/workflows/ci.yml/badge.svg)](https://github.com/saiprasanth-git/traceguard/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-2ea043)](pyproject.toml)
[![DO-178C / ISO 26262](https://img.shields.io/badge/safety--critical-DO--178C%20%7C%20ISO%2026262-d97706)](docs/do178c-mapping.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Requirements traceability gate for safety-critical software.

TraceGuard reads your requirement specifications, the `@implements` annotations
in your source code and the `@verifies` annotations in your tests, resolves the
bidirectional traceability graph, and **fails the build when the trace is
broken**. It turns "we will do the traceability matrix before the audit" into a
CI check that runs on every commit.

Everything lives in plain text next to the code, so requirements, code and
verification evidence are reviewed together in the same pull request and diff
cleanly in Git.

```
$ traceguard check --root examples/altitude_hold
TraceGuard 0.1.0 - /path/to/repo/examples/altitude_hold
  requirements: 18 (SYS 3 / HLR 5 / LLR 10)
  implementation coverage: 100.0%   verification coverage: 100.0%
  findings: 0 error(s), 0 warning(s)

OK
```

When something is missing, you get an actionable failure instead of a surprise
during the certification review:

```
$ traceguard check --root .
  ERROR   TG005-unimplemented-llr [LLR-ALTH-031] No source code carries an
          @implements annotation for this LLR (requirements/low_level.md:58)
  ERROR   TG006-unverified-requirement [LLR-ALTH-042] No verification case
          carries a @verifies annotation (requirements/low_level.md:71)
  WARNING TG014-dal-a-single-method [LLR-ALTH-021] DAL B requirement is
          verified by a single method (unit)

FAILED (fail_on=error)
```

---

## Why this exists

On DO-178C, IEC 62304, ISO 26262 and similar programmes, the traceability data
is a deliverable in its own right: every requirement must trace up to its
parent, down to code, and across to verification evidence. In practice that
matrix is usually rebuilt by hand from a spreadsheet late in the programme, by
which point the gaps are expensive.

TraceGuard makes the trace a **continuously enforced property of the
repository**:

| Without TraceGuard | With TraceGuard |
| --- | --- |
| Matrix maintained by hand in a spreadsheet | Matrix generated from the repository on every commit |
| Gaps found during the certification review | Gaps fail the pull request that introduced them |
| Requirements drift away from the code | Deleting an annotation breaks the build |
| Evidence assembled from memory | Markdown, HTML and JSON artefacts published by CI |

## Install

```bash
pip install -e ".[dev]"      # from a clone
traceguard --version
```

Python 3.11 or newer. No third-party runtime dependencies - the whole tool is
standard library only, which keeps it easy to qualify as a development tool.

## Quick start

1. **Write requirements** as Markdown headings with a small attribute block:

   ```markdown
   ### LLR-ALTH-021: Pitch command saturation

   - dal: B
   - parents: HLR-ALTH-020

   The published pitch command shall be clamped to the inclusive range
   `[ALTH_PITCH_MIN_DEG, ALTH_PITCH_MAX_DEG]`.
   ```

2. **Annotate the code** that implements it:

   ```c
   /**
    * @implements LLR-ALTH-021
    */
   alth_status_t alth_step(alth_controller_t *ctl, /* ... */)
   ```

3. **Annotate the verification case** that covers it:

   ```c
   /**
    * @verifies LLR-ALTH-021 method=unit
    */
   static void test_pitch_saturation(void)
   ```

4. **Gate CI** on the result:

   ```yaml
   - run: traceguard check --root .
   ```

Full syntax reference: [docs/annotation-reference.md](docs/annotation-reference.md).

## Commands

| Command | Purpose |
| --- | --- |
| `traceguard check` | Run the rule set. Exit `0` clean, `1` findings, `2` usage error. The CI gate. |
| `traceguard report --format markdown\|html\|json` | Render the traceability matrix as review evidence. |
| `traceguard show LLR-ALTH-021` | Print the full trace tree for one requirement while working. |
| `traceguard rules` | List every enforced rule and its severity. |

`traceguard show` is the day-to-day command:

```
$ traceguard show --root examples/altitude_hold LLR-ALTH-031
LLR-ALTH-031  [LLR, DAL B]
  title      : Integral anti-windup
  text       : When the unclamped pitch command lies outside the saturation limits, the
  declared at: requirements/low_level.md:49
  traces to  : HLR-ALTH-030
  children   : none
  code       : src/altitude_hold.c:88
  verified by: test_integral_anti_windup (method=unit) at tests/test_altitude_hold.c:127
```

## Enforced rules

| Rule | Severity | Meaning |
| --- | --- | --- |
| `TG001-duplicate-req` | error | Requirement id declared more than once |
| `TG002-missing-parent` | error | Parent requirement id does not exist |
| `TG003-orphan-requirement` | error | HLR/LLR with no parent and not marked `derived` |
| `TG004-derived-no-rationale` | error | Derived requirement without a rationale |
| `TG005-unimplemented-llr` | error | LLR with no `@implements` annotation in code |
| `TG006-unverified-requirement` | error | Requirement with no `@verifies` annotation |
| `TG007-dangling-code-trace` | error | Code traces to an unknown requirement |
| `TG008-dangling-test-trace` | error | Test traces to an unknown requirement |
| `TG009-childless-hlr` | error | HLR not decomposed into any LLR |
| `TG010-unknown-attribute` | warning | Unrecognised requirement attribute |
| `TG011-bad-dal` | error | DAL outside A-E |
| `TG012-level-inversion` | error | Parent is not one abstraction level higher |
| `TG013-unknown-method` | warning | Unrecognised verification method |
| `TG014-dal-a-single-method` | warning | DAL A/B requirement verified by a single method |

## Configuration

`traceguard.toml` at the project root:

```toml
[traceguard]
requirements = ["requirements/**/*.md"]
code         = ["src/**/*.c", "include/**/*.h"]
tests        = ["tests/**/*.c"]
fail_on      = "error"        # "error" | "warning" | "never"

# Documented, reviewed exceptions. "RULE" or "RULE:REQUIREMENT-ID".
waivers = ["TG014-dal-a-single-method:LLR-ALTH-021"]
```

Waivers are deliberately noisy: they live in a version-controlled file, they are
reviewed like code, and they are listed in the generated report. See
[docs/waivers.md](docs/waivers.md).

## The worked example

[`examples/altitude_hold`](examples/altitude_hold) is a complete, buildable
DAL B altitude-hold control law for a fixed-wing autopilot: 3 system
requirements, 5 high-level requirements, 10 low-level requirements (one of them
derived), ~150 lines of C99 compiled with `-Wall -Wextra -Werror -Wpedantic`,
and 14 verification cases covering the control law, the saturation limits, the
integral anti-windup behaviour, input validation and the latched fault state.

```bash
cd examples/altitude_hold
make test     # compile and run the verification suite
make trace    # requirements traceability gate
make report   # markdown + HTML + JSON evidence into build/
```

The example doubles as TraceGuard's own regression baseline: `pytest` asserts
that it stays at 100% implementation and verification coverage with zero
findings, so the tool cannot silently stop detecting gaps.
[docs/example-walkthrough.md](docs/example-walkthrough.md) walks through the
control law and the reasoning behind each requirement.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Module layout, the trace graph, how to add a rule |
| [docs/annotation-reference.md](docs/annotation-reference.md) | Requirement and annotation syntax, every rule in detail |
| [docs/do178c-mapping.md](docs/do178c-mapping.md) | Which DO-178C Table A objectives TraceGuard supports, and which it does not |
| [docs/sop-requirements-traceability.md](docs/sop-requirements-traceability.md) | Corporate SOP for running the process on a real programme |
| [docs/ci-integration.md](docs/ci-integration.md) | GitHub Actions, GitLab CI and pre-commit recipes |
| [docs/waivers.md](docs/waivers.md) | When a waiver is acceptable and how to record one |
| [docs/example-walkthrough.md](docs/example-walkthrough.md) | The altitude-hold example, requirement by requirement |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and definition of done |

## Scope and honest limitations

TraceGuard checks that the traceability graph is **complete and well formed**.
It does not, and is not intended to, do the following:

- **It does not judge requirement quality.** A vague requirement with an
  annotation passes. Peer review is still the control for that.
- **It does not measure structural coverage.** MC/DC and statement coverage come
  from your coverage tool; TraceGuard tells you a verification case exists, not
  that it exercises every branch.
- **It does not verify that a test actually tests what it claims.** An
  annotation is an assertion by the author, reviewed by a human.
- **It is not qualified tool-chain software.** Under DO-178C it is a development
  tool whose output is reviewed, not a verification tool credited with replacing
  a review activity. Tool qualification per DO-330 would be a separate effort.

Treat it as the mechanism that removes the clerical failure mode - a missing
link - so that review effort goes to the parts that need judgement.

## Licence

MIT. See [LICENSE](LICENSE).
