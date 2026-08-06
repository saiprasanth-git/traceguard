# Waivers

A waiver suppresses a specific TraceGuard finding. Waivers exist because the
alternative - people disabling the gate entirely when one rule is inconvenient -
is far worse. They are deliberately visible, version-controlled and reviewable.

## Format

In `traceguard.toml`:

```toml
waivers = [
  "TG014-dal-a-single-method:LLR-ALTH-021",   # one rule, one requirement
  "TG014-dal-a-single-method",                # one rule, project wide
]
```

- `RULE:REQUIREMENT-ID` - narrow. Suppresses that rule for that requirement only.
- `RULE` - broad. Suppresses that rule everywhere. Use only when the rule genuinely
  does not apply to the project.
- Matching is by prefix, so `TG014` also works as shorthand for the full rule name.

Waived findings are removed from the report and from the exit-code decision. They
are not silently dropped from the record: the waiver list itself is a
configuration-managed file, reviewed like code, and the comment above each entry
carries the justification.

## When a waiver is acceptable

All four conditions must hold:

1. **The finding is understood.** Somebody has read it and can explain it.
2. **The underlying objective is satisfied another way**, and that way is
   documented. "We ran out of time" is not another way.
3. **The waiver is scoped as narrowly as possible.** Prefer
   `RULE:REQUIREMENT-ID`.
4. **The waiver names its approving review record** in a comment.

## Approval

| Rule severity | Rules | Approval required |
| --- | --- | --- |
| error | `TG001`-`TG009`, `TG011`, `TG012` | Software QA, recorded in the change record |
| warning | `TG010`, `TG013`, `TG014` | Peer reviewer |

Error-severity waivers should be rare and short-lived. An error means the trace
graph is broken - usually the honest fix is to write the missing annotation or
delete the requirement.

## Good and bad examples

**Acceptable** - the objective is met by another documented method:

```toml
# TG014 asks for two independent verification methods on DAL A/B requirements.
# The LLRs below are covered by unit test plus the closed-loop integration cases
# that exercise them through their parent HLR; recorded here rather than
# duplicating cases. Review record: docs/reviews/SRR-001.
waivers = ["TG014-dal-a-single-method"]
```

**Acceptable** - the rule does not apply to a repository that deliberately holds
system requirements elsewhere:

```toml
# System requirements live in the systems-engineering tool; HLRs in this
# repository trace to them by id, so the parents cannot be resolved locally.
# Approved in PSAC section 4.3.
waivers = ["TG002-missing-parent"]
```

**Not acceptable** - hiding real gaps:

```toml
# TODO: annotate the code later
waivers = ["TG005-unimplemented-llr", "TG006-unverified-requirement"]
```

This waives exactly the two rules that make the tool worth running. If the trace
genuinely cannot be completed yet, use `--fail-on never` during the adoption
period instead, so the findings stay visible in the report while not blocking.

## Reviewing waivers

Software QA reviews the full waiver list at each release audit and confirms:

- every entry still names a valid rule and, where scoped, an existing requirement
- every entry still has a live justification and a review record
- no entry has outlived its reason

Remove a waiver as soon as it is unnecessary. A waiver list that only ever grows
is a sign the gate has stopped doing its job.
