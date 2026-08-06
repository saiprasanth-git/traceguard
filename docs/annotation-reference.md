# Annotation and syntax reference

Everything TraceGuard reads is plain text in the repository. There are exactly
three input formats.

## 1. Requirement specifications

A requirement is a level-3 Markdown heading followed by an optional attribute
list and free-form body text.

```markdown
### LLR-ALTH-021: Pitch command saturation

- dal: B
- parents: HLR-ALTH-020

The published pitch command shall be clamped to the inclusive range
`[ALTH_PITCH_MIN_DEG, ALTH_PITCH_MAX_DEG]`.
```

### Identifier format

```
<LEVEL>-<SUBSYSTEM>-<NUMBER>
```

| Part | Rule |
| --- | --- |
| `LEVEL` | `SYS`, `HLR` or `LLR`. The level is inferred from this prefix - there is no separate attribute for it. |
| `SUBSYSTEM` | Uppercase letters and digits, e.g. `ALTH`, `FCS`, `NAV2`. |
| `NUMBER` | One or more digits. |

Examples: `SYS-ALTH-001`, `HLR-ALTH-020`, `LLR-ALTH-021`.

Ids are permanent. They appear in code, tests, waivers and review records, so
renumbering is a breaking change. Retire a requirement by marking it in the text
rather than reusing its id.

### Attributes

| Attribute | Type | Default | Meaning |
| --- | --- | --- | --- |
| `dal` | `A`-`E` | `C` | Design Assurance Level. Drives the stricter DAL A/B checks. |
| `parents` | comma-separated ids | none | The requirement(s) this one decomposes. Exactly one level higher. |
| `derived` | `true`/`false` | `false` | The requirement has no parent by design. Requires `rationale`. |
| `rationale` | free text | none | Why the requirement exists with no parent. Mandatory when `derived`. |
| `text` | free text | body | Overrides the body as the requirement statement. Rarely needed. |

Unrecognised attributes raise `TG010-unknown-attribute` (warning) and are
ignored, so a typo is visible rather than silently dropped.

### Body text

Everything between the attribute list and the next heading is the requirement
statement. Any Markdown heading terminates the block, so prose sections between
requirements are safe.

### Derived requirements

A requirement with no parent must be declared explicitly:

```markdown
### LLR-ALTH-014: Frame time validation

- dal: B
- parents: HLR-ALTH-010
- derived: true
- rationale: The frame time is supplied by the scheduler and is not constrained
  by any parent requirement; a non-positive or excessive dt would make the
  control law numerically invalid.
```

Under DO-178C 5.1.2.h derived requirements must be identified and provided to
the safety assessment process. `TG004` enforces that the rationale exists so the
safety engineer has something to assess.

## 2. Code annotations - `@implements`

Placed in any comment, anywhere in a file matched by the `code` globs:

```c
/**
 * @implements LLR-ALTH-041
 * @implements LLR-ALTH-042
 */
bool alth_sample_is_valid(alth_baro_sample_t sample)
```

- One requirement id per `@implements`. Repeat the tag for several ids.
- Many requirements may map to one function, and one requirement may be
  implemented across several functions or files. Both directions are many.
- TraceGuard reports the nearest function-like symbol declared within 16 lines
  after the annotation, purely to make the report readable. If it finds none, it
  falls back to the file stem; the trace link itself is never affected.
- Only `LLR-*` ids are *required* to appear in code (`TG005`). Annotating an HLR
  or SYS id is allowed and shown in the report.

Because the annotation is a comment, it costs nothing at runtime and works in
any language.

## 3. Verification annotations - `@verifies`

```c
/**
 * @verifies LLR-ALTH-021 method=unit
 * @verifies SYS-ALTH-002 method=integration
 */
static void test_pitch_saturation(void)
```

`method=` is optional and defaults to `unit`. Recognised values:

| Method | Use for |
| --- | --- |
| `unit` | Isolated test of one function or module |
| `integration` | Test across module or subsystem boundaries |
| `hardware` | Test executed on target hardware or a HIL rig |
| `review` | Verification by peer review or inspection |
| `analysis` | Verification by analysis, proof or modelling |

Anything else raises `TG013-unknown-method` (warning). For DAL A and DAL B
requirements, `TG014` warns when only a single method covers a requirement,
because those levels expect independence between verification activities.

## 4. Complete rule reference

| Rule | Severity | Fires when | Fix |
| --- | --- | --- | --- |
| `TG001-duplicate-req` | error | The same id appears in two headings | Give the second requirement a new id |
| `TG002-missing-parent` | error | A `parents` id is not declared anywhere | Fix the typo or add the parent requirement |
| `TG003-orphan-requirement` | error | An HLR or LLR has no `parents` and no `derived: true` | Add the parent, or mark it derived with a rationale |
| `TG004-derived-no-rationale` | error | `derived: true` with no `rationale` | State why no parent exists |
| `TG005-unimplemented-llr` | error | An LLR has no `@implements` in code | Annotate the implementing code, or delete the requirement |
| `TG006-unverified-requirement` | error | An HLR or LLR has no `@verifies` | Write the verification case and annotate it |
| `TG007-dangling-code-trace` | error | Code implements an id that does not exist | Fix the annotation, or add the requirement |
| `TG008-dangling-test-trace` | error | A test verifies an id that does not exist | Fix the annotation, or add the requirement |
| `TG009-childless-hlr` | error | An HLR has no LLR children | Decompose it, or fix the children's `parents` |
| `TG010-unknown-attribute` | warning | An unrecognised `- key: value` line | Correct the attribute name |
| `TG011-bad-dal` | error | `dal` is outside `A`-`E` | Use a valid DAL |
| `TG012-level-inversion` | error | An LLR's parent is not an HLR, or an HLR's parent is not a SYS | Point at the correct level |
| `TG013-unknown-method` | warning | `method=` is not a recognised method | Use one of the five methods |
| `TG014-dal-a-single-method` | warning | A DAL A/B requirement has only one verification method | Add an independent method, or record a waiver |

System requirements are exempt from `TG006`: they are verified transitively
through their high-level children, which is how the objective is normally
satisfied.

## Configuration file

```toml
[traceguard]
requirements = ["requirements/**/*.md"]
code         = ["src/**/*.c", "include/**/*.h"]
tests        = ["tests/**/*.c"]
fail_on      = "error"                              # "error" | "warning" | "never"
waivers      = ["TG014-dal-a-single-method:LLR-ALTH-021"]
```

- Globs are relative to `--root`. `.git`, `build`, `__pycache__`, `.venv`,
  `node_modules` and `.pytest_cache` are always skipped.
- A file matched by both `code` and `tests` is treated as a test, so test helpers
  never satisfy `TG005` by accident.
- `fail_on` sets the CI gate threshold and can be overridden per invocation with
  `--fail-on`.
- Waiver format is `RULE` or `RULE:REQUIREMENT-ID`. See
  [waivers.md](waivers.md).

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No findings at or above the `fail_on` threshold |
| `1` | Findings present - the gate failed |
| `2` | Usage error, for example an unknown requirement passed to `show` |
