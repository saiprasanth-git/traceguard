# DO-178C mapping

This document states precisely which DO-178C traceability expectations TraceGuard
helps satisfy, and - just as importantly - which it does not. Read it before
citing the tool in a plan.

> TraceGuard is a development aid. Nothing here should be read as a claim of tool
> qualification. See [Tool qualification](#tool-qualification) below.

## What DO-178C asks for

DO-178C section 5.5 was extensively revised from DO-178B to make traceability
explicitly **bidirectional**, and it introduced trace data as a distinct life
cycle data item, described in section 11.21 ([FAA DO-178B/C Differences
Tool](https://www.faa.gov/sites/faa.gov/files/aircraft/air_cert/design_approvals/air_software/differences_tool.pdf)).
Trace data must show bidirectional associations between six pairs of artefacts
([DO-178C peer review checklist,
airworthinesscert.com](https://airworthinesscert.com/wp-content/uploads/2023/02/P10.STM-Sample.pdf)):

| # | Association | DO-178C ref | Annex A |
| --- | --- | --- | --- |
| 1 | System requirements allocated to software ↔ high-level requirements | 11.21.a | Table A-2.1 |
| 2 | High-level requirements ↔ low-level requirements | 11.21.b | Table A-2.4 |
| 3 | Low-level requirements ↔ source code | 11.21.c | Table A-2.6 |
| 4 | Software requirements ↔ test cases | 11.21.d | Table A-6 |
| 5 | Test cases ↔ test procedures | 11.21.e | Table A-6 |
| 6 | Test procedures ↔ test results | 11.21.f | Table A-6 |

Downstream traceability shows that all intended functionality is implemented;
upstream traceability shows that nothing exists in the implementation which is
not required - which is how orphan and dead code are kept out ([Rapita Systems,
DO-178C
Verification](https://www.rapitasystems.com/files/MC-WP-011%20DO-178C%20Verification_5.pdf)).
Traceability is a cornerstone of the SOI#2 and SOI#3 reviews, so the matrix is
one of the first artefacts a DER examines ([RTMify DO-178C
guide](https://rtmify.io/standards/do-178c)).

## What TraceGuard covers

| Association | TraceGuard support | Rules involved |
| --- | --- | --- |
| 1. SYS ↔ HLR | **Full, both directions.** Every HLR must declare a `SYS-*` parent; the parent must exist and be one level higher. A SYS requirement with no HLR child is visible in the forward-trace table of the report. | `TG002`, `TG003`, `TG012` |
| 2. HLR ↔ LLR | **Full, both directions.** Every LLR must declare an `HLR-*` parent, and every HLR must decompose into at least one LLR. | `TG002`, `TG003`, `TG009`, `TG012` |
| 3. LLR ↔ source code | **Full in the requirement→code direction**, at function granularity, via `@implements`. The reverse direction (all code traces to a requirement) is **not** enforced - see the gap table below. | `TG005`, `TG007` |
| 4. Requirements ↔ test cases | **Full, both directions.** Every HLR and LLR needs a `@verifies` case; every `@verifies` must name a requirement that exists. | `TG006`, `TG008` |
| 5. Test cases ↔ test procedures | **Not covered.** The annotation identifies a case, not a procedure document. | - |
| 6. Test procedures ↔ test results | **Not covered.** Results come from your test runner and CI logs. | - |

Additional DO-178C expectations TraceGuard helps with:

| Expectation | DO-178C ref | How |
| --- | --- | --- |
| Derived requirements are identified and provided to the safety assessment process | 5.1.2.h, 5.2.2.d | `derived: true` is mandatory for any parentless requirement, and `TG004` requires a rationale. The report has a dedicated derived-requirements section listing each rationale. |
| Verification independence at the higher levels | Table A-6/A-7 independence columns; DAL A requires 30 objectives with independence, DAL B 18 ([Jama Software](https://www.jamasoftware.com/requirements-management-guide/aerospace-and-defense/do-178c/)) | `TG014` warns when a DAL A or B requirement is covered by only one verification method. |
| Trace data as a configuration-managed life cycle data item | 11.21, Table A-8 | Requirements, annotations and `traceguard.toml` are files in the repository, so they are under the same configuration management and baselining as the code. Generated reports are CI artefacts tied to a commit. |

## Gaps you must close by other means

| Objective area | Why TraceGuard does not cover it | What to use |
| --- | --- | --- |
| **Source code → requirement (upstream) completeness** | TraceGuard reads annotations, so unannotated code is invisible to it. It cannot prove the absence of untraced code. | Code review against the design, plus structural coverage analysis to expose code no test reaches. |
| **Structural coverage** - MC/DC for DAL A, decision coverage for DAL B, statement coverage for DAL C ([Jama Software](https://www.jamasoftware.com/requirements-management-guide/aerospace-and-defense/do-178c/)) | Out of scope. An annotated test proves a case exists, not that it exercises every branch. | `gcov`/`lcov`, VectorCAST, LDRA, Rapita. |
| **Requirement quality** - unambiguous, verifiable, consistent | Not machine-checkable. A vague requirement with an annotation passes. | Peer review against your requirements standard. |
| **Test correctness** - the case really verifies what it claims | The annotation is an author assertion. | Review of test cases and procedures. |
| **Additional code not traceable to source code** (Table A-7 objective 9, DAL A) | Concerns compiler/linker output, below TraceGuard's view. | Object code verification. |
| **Test procedures and test results trace data** (11.21.e, 11.21.f) | Not modelled. | Your test management and CI evidence retention. |

## Applicability beyond DO-178C

The SYS → HLR → LLR → code → test structure is not unique to aviation. The same
rule set maps onto:

| Standard | Domain | Notes |
| --- | --- | --- |
| ISO 26262 | Automotive | Technical safety requirements → software requirements → units. ASIL A-D maps onto the `dal` attribute. |
| IEC 62304 | Medical devices | Software system requirements → unit requirements, with Class A/B/C in place of DAL. |
| EN 50128 | Rail | SIL 0-4 in place of DAL. |
| DO-278A | Ground-based CNS/ATM | AL1-AL6 in place of DAL. |

Only the `dal` vocabulary is aviation-flavoured; the graph rules are identical.

## Tool qualification

Under DO-178C, tools are qualified per DO-330 when a process eliminates,
reduces or automates an activity and the output is not otherwise verified.

TraceGuard, as delivered here, is intended to be used **without** qualification
credit:

- It is a development aid that makes gaps visible early. The traceability review
  activity still happens, performed by people.
- Its output - the generated matrix - is reviewed, not accepted blindly.
- No verification activity is removed on the strength of a passing
  `traceguard check`.

If you did want to claim credit (for example, using the generated matrix as the
trace data deliverable without independent review), that is a TQL-5 discussion at
minimum, and would require a tool operational requirements document, tool
qualification plan, and verification of the tool itself against those
requirements. The existing test suite and the shipped example baseline are a
reasonable starting point for that evidence, but they are not that evidence.

Record the intended usage in your PSAC and SDP, stating explicitly that
TraceGuard output is reviewed and no credit is claimed.
