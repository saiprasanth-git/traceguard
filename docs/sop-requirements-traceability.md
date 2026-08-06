# SOP-SW-014: Requirements Traceability Management

| Field | Value |
| --- | --- |
| Document id | SOP-SW-014 |
| Revision | 1.0 |
| Status | Baselined |
| Applies to | All software projects using TraceGuard for trace data |
| Supersedes | Manual traceability matrix maintenance (spreadsheet-based) |
| Owner | Software Quality Assurance |
| Related | PSAC, SDP, Software Verification Plan, [do178c-mapping.md](do178c-mapping.md) |

## 1. Purpose

To define how requirements traceability is created, maintained, verified and
delivered on projects that use TraceGuard, such that trace data is a continuously
enforced property of the repository rather than an artefact reconstructed before
a review.

## 2. Scope

Applies to system requirements allocated to software, software high-level
requirements, low-level requirements, source code and verification cases held in
the project repository. Test procedures and test results trace data are outside
this SOP and are covered by the Software Verification Plan.

## 3. Roles and responsibilities

| Role | Responsibility |
| --- | --- |
| Requirements owner | Authors and maintains requirement specifications; assigns ids and DAL; declares and justifies derived requirements. |
| Software engineer | Adds and maintains `@implements` annotations; keeps them accurate when code is refactored. |
| Verification engineer | Adds and maintains `@verifies` annotations with the correct method; ensures the case genuinely exercises the requirement. |
| Peer reviewer | Confirms during review that annotations are truthful, not merely present. |
| Software QA | Audits waivers each release; confirms the CI gate is active and not bypassed. |
| Configuration management | Baselines requirement files, `traceguard.toml` and generated reports at each release. |

## 4. Process

### 4.1 Creating a requirement

1. Choose the level: `SYS`, `HLR` or `LLR`.
2. Allocate the next unused id in the form `<LEVEL>-<SUBSYSTEM>-<NUMBER>`. Ids are
   never reused, even after a requirement is retired.
3. Write the requirement in the appropriate file under `requirements/`, following
   [annotation-reference.md](annotation-reference.md).
4. Set `dal` and `parents`. If no parent exists, set `derived: true` **and** a
   `rationale` naming why - a derived requirement without a rationale is rejected
   by the gate and cannot be assessed by the safety process.
5. Commit the requirement in the same branch as the work that consumes it.

### 4.2 Implementing a requirement

1. Add an `@implements <ID>` annotation in a comment on the implementing function
   or module.
2. If the requirement is implemented across several functions, annotate each one.
   Partial implementation without annotation is a trace gap.
3. Run `traceguard check --root .` locally before pushing.

### 4.3 Verifying a requirement

1. Write the verification case.
2. Annotate it `@verifies <ID> method=<method>`.
3. For DAL A and DAL B requirements, plan for two independent methods. A single
   method raises `TG014`; either add the second method or raise a waiver per
   section 6.
4. Run `traceguard check --root .` and the project test suite.

### 4.4 Changing an existing requirement

1. Assess the change impact: run `traceguard show <ID>` to list every piece of
   code and every verification case attached to the requirement.
2. Update the requirement text, the implementation and the verification cases in
   the same change set.
3. Where the change alters behaviour, record the change in the requirement history
   and notify the safety assessment process if the requirement is derived or
   DAL A/B.

### 4.5 Retiring a requirement

1. Remove the requirement from the specification **and** remove every
   `@implements` and `@verifies` annotation naming it. Leaving an annotation
   behind raises `TG007`/`TG008`, which is the intended safety net.
2. Confirm the parent still has at least one child; an HLR left with no LLRs
   raises `TG009` and must either be decomposed again or retired too.
3. Record the retirement in the change record. The id is not reused.

## 5. Gate and enforcement

1. `traceguard check` runs on every pull request. A failing gate blocks merge.
2. The gate is configured with `fail_on = "error"` as a minimum. Projects at DAL A
   or B should use `fail_on = "warning"` and manage exceptions through waivers.
3. `traceguard report` runs on every push to the mainline. The Markdown, HTML and
   JSON artefacts are retained against the commit as review evidence.
4. Bypassing the gate (skipping CI, force-merging, disabling the job) requires
   written QA approval recorded in the change record.

## 6. Waivers

A waiver is acceptable only when all of the following hold:

1. The finding is understood, and the underlying objective is satisfied by another
   documented means.
2. The waiver is recorded in `traceguard.toml` with a comment naming the review
   record that approved it.
3. It is scoped as narrowly as possible - prefer `RULE:REQUIREMENT-ID` over a
   bare `RULE`.
4. It is reviewed at every release audit and removed as soon as it is unnecessary.

Waivers on error-severity rules (`TG001`-`TG009`, `TG011`, `TG012`) require QA
approval. Waivers on warning-severity rules require peer review approval. See
[waivers.md](waivers.md).

## 7. Records

| Record | Where | Retention |
| --- | --- | --- |
| Requirement specifications | `requirements/` in the repository, under version control | Life of programme |
| Trace annotations | Source and test files | Life of programme |
| Generated traceability matrix | CI artefacts, keyed by commit; baselined copy at each release | Per programme retention policy |
| Waiver register | `traceguard.toml` plus the referenced review records | Life of programme |
| Gate results | CI run history | Per programme retention policy |

## 8. Definition of done for any change set

- [ ] Every new or modified requirement has a parent or a justified `derived` flag
- [ ] Every LLR touched is implemented by annotated code
- [ ] Every requirement touched has at least one annotated verification case
- [ ] `traceguard check --root .` exits `0`
- [ ] The project test suite passes
- [ ] Reviewer has confirmed the annotations are truthful, not just present
- [ ] Any new waiver names its approving review record

## 9. Revision history

| Rev | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | Initial baseline | Software Quality Assurance | First issue, replacing spreadsheet-based traceability |
