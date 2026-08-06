# Example walkthrough: the altitude-hold function

`examples/altitude_hold` is a complete, buildable DAL B altitude-hold control law
for a fixed-wing autopilot. It exists to show what a fully traced component looks
like in practice, and it doubles as TraceGuard's own regression baseline.

```bash
cd examples/altitude_hold
make test     # compile with -Wall -Wextra -Werror -Wpedantic and run 14 cases
make trace    # requirements traceability gate
make report   # markdown + HTML + JSON evidence into build/
```

Expected result: 14 cases pass, 0 failures; the gate reports 18 requirements,
100% implementation coverage, 100% verification coverage, 0 errors, 0 warnings.

## The function

The ALTH function holds a commanded barometric altitude by commanding a pitch
attitude. It is a PID control law with three safety properties layered on top:

1. the pitch command never leaves the certified envelope,
2. the integral term cannot wind up while the output is saturated,
3. invalid or stale altitude data disengages the function into a safe state, and
   the fault latches until an explicit reset.

Those three properties are why the requirement tree looks the way it does: one
system requirement for the function, and two for the protections.

## The requirement tree

```
SYS-ALTH-001 Maintain commanded barometric altitude
└── HLR-ALTH-010 Compute pitch command from altitude error
    ├── LLR-ALTH-011 Proportional term
    ├── LLR-ALTH-012 Integral term accumulation
    ├── LLR-ALTH-013 Derivative term on measurement
    └── LLR-ALTH-014 Frame time validation            [derived]

SYS-ALTH-002 Protect the aircraft from unsafe pitch commands
├── HLR-ALTH-020 Limit the pitch command
│   └── LLR-ALTH-021 Pitch command saturation
└── HLR-ALTH-030 Bound the integral term
    └── LLR-ALTH-031 Integral anti-windup

SYS-ALTH-003 Disengage on invalid sensor data
├── HLR-ALTH-040 Validate barometric altitude input
│   ├── LLR-ALTH-041 Altitude range and finiteness check
│   └── LLR-ALTH-042 Sample staleness check
└── HLR-ALTH-050 Enter a safe state on invalid input
    ├── LLR-ALTH-051 Safe-state transition
    └── LLR-ALTH-052 Fault latching until reset
```

## Why each low-level requirement exists

| Requirement | Design decision it pins down |
| --- | --- |
| `LLR-ALTH-011` | Fixes the proportional term as `kp * error_m`, so the sign convention (command minus measurement) is unambiguous and testable to an exact number. |
| `LLR-ALTH-012` | Fixes integration as `integral += error * dt`, so behaviour is defined at any frame rate rather than assuming a fixed one. |
| `LLR-ALTH-013` | **Derivative on measurement, not on error.** A step change in the commanded altitude would otherwise produce a large derivative spike - a "derivative kick" - and command a violent pitch transient. Taking the derivative of the measurement and negating it gives the same damping with no kick. This is exactly the kind of decision that must be a requirement, not a comment: a well-meaning refactor to `d(error)/dt` would look equivalent and would be wrong. |
| `LLR-ALTH-014` | **Derived.** The frame time comes from the scheduler; no parent requirement constrains it. A zero or negative `dt` divides by zero in the derivative term, and an excessive `dt` makes the discrete approximation invalid. The safe response is to reject the frame and hold the previous output, so the requirement had to be written and flagged as derived for the safety assessment. |
| `LLR-ALTH-021` | Clamps the published command to `[-15, +15]` degrees, the certified envelope. This is the last line of defence: it holds regardless of gains, error magnitude or sensor behaviour. |
| `LLR-ALTH-031` | Anti-windup. Without it, a long saturated climb accumulates a huge integral state, and the aircraft overshoots badly because the controller stays pinned long after the error reverses. Implemented by reverting the current frame's integration whenever the output clamps. |
| `LLR-ALTH-041` | Range and finiteness. A NaN or an absurd altitude must never reach the control law. |
| `LLR-ALTH-042` | Staleness. Data that is 500 ms old is worse than no data, because it looks valid. |
| `LLR-ALTH-051` | Defines the safe state precisely: fault status set, pitch command zero, integral cleared, disengaged. "Do something sensible" is not verifiable. |
| `LLR-ALTH-052` | **Latching.** A sensor that fails intermittently would otherwise cause the function to flap between engaged and disengaged, which is worse than staying out. Recovery requires an explicit `alth_reset`, which is a crew or supervisory action. |

## How the trace is expressed in code

The implementation carries the annotations directly on the functions:

```c
/**
 * @implements LLR-ALTH-041
 * @implements LLR-ALTH-042
 */
bool alth_sample_is_valid(alth_baro_sample_t sample)
```

`alth_step` implements eight low-level requirements, and each is also marked
inline at the statement that satisfies it:

```c
    /* LLR-ALTH-021: saturate the published command. */
    const double clamped = clamp(unclamped, ALTH_PITCH_MIN_DEG, ALTH_PITCH_MAX_DEG);

    /* LLR-ALTH-031: anti-windup - undo this frame's integration when saturated. */
    if (clamped != unclamped) {
        ctl->integral -= integral_delta;
    }
```

Only the `@implements` tags in the header comment are read by TraceGuard; the
inline comments are for the reviewer, who has to answer a question the tool
cannot: does this code actually do what the requirement says?

## How verification is expressed

Verification cases name the requirement and the method:

```c
/**
 * @verifies LLR-ALTH-021 method=unit
 * @verifies SYS-ALTH-002 method=integration
 */
static void test_pitch_saturation(void)
```

The suite mixes methods deliberately:

| Case | Requirement(s) | Method | What it does |
| --- | --- | --- | --- |
| `test_proportional_term` | `LLR-ALTH-011` | unit | 10 m error at `kp = 0.2` must give exactly 2.0 deg |
| `test_integral_accumulation` | `LLR-ALTH-012` | unit | Constant 5 m error over two 0.1 s frames must give exactly 1.0 deg at `ki = 1.0` |
| `test_derivative_on_measurement` | `LLR-ALTH-013` | unit | A climb produces a negative contribution; a pure command step produces none |
| `test_frame_time_validation` | `LLR-ALTH-014` | unit | Zero, negative and excessive `dt` are rejected and the output is held |
| `test_pitch_saturation` | `LLR-ALTH-021`, `SYS-ALTH-002` | unit, integration | Extreme errors clamp to exactly the envelope limits |
| `test_integral_anti_windup` | `LLR-ALTH-031` | unit | After 50 saturated frames, one reversed frame is enough to leave saturation |
| `test_range_and_finiteness` | `LLR-ALTH-041` | unit | Over-range, under-range, NaN and sensor-invalid samples all rejected |
| `test_staleness` | `LLR-ALTH-042` | unit | A sample at the threshold is accepted; one past it is rejected |
| `test_safe_state_transition` | `LLR-ALTH-051`, `SYS-ALTH-003` | unit, integration | Invalid input zeroes the command and disengages |
| `test_fault_latching` | `LLR-ALTH-052` | unit | Good data alone does not re-engage; only `alth_reset` does |
| `test_closed_loop_convergence` | `HLR-ALTH-010`, `SYS-ALTH-001` | integration | 4000 frames against a first-order plant model settle within 5 m of the command |
| `test_envelope_never_exceeded` | `HLR-ALTH-020` | integration | A 401-point error sweep never leaves the envelope |
| `test_integral_bounded` | `HLR-ALTH-030` | analysis | 5000 saturated frames keep the integral state bounded |
| `test_validation_gates_engagement` | `HLR-ALTH-040`, `HLR-ALTH-050` | unit, integration | Stale input prevents engagement end to end |

The exact-value assertions matter. `TG_ASSERT_NEAR(..., 2.0, 1e-9)` verifies the
requirement as written; a test that merely asserts "the output is positive" would
satisfy the tool and prove almost nothing. TraceGuard checks that a case exists -
the reviewer checks that it is a real one.

## What the waiver is for

The example carries one waiver:

```toml
waivers = ["TG014-dal-a-single-method"]
```

`TG014` warns when a DAL A or B requirement is covered by a single verification
method. Most LLRs here have exactly one unit test, so the rule fires. Each is
also exercised through the closed-loop and envelope-sweep integration cases
attached to its parent HLR, so the objective is met; adding a second annotation to
every LLR would inflate the trace without adding verification value. The reasoning
is recorded in [reviews/SRR-001.md](reviews/SRR-001.md), and the waiver comment
points at it. That is the pattern to copy: a waiver is a decision with a paper
trail, not a way to quieten the tool.

## Try breaking it

The fastest way to understand the gate is to watch it fail.

```bash
# Delete an @implements annotation
sed -i 's|@implements LLR-ALTH-031||' src/altitude_hold.c
traceguard check --root .
# ERROR   TG005-unimplemented-llr [LLR-ALTH-031] No source code carries an
#         @implements annotation for this LLR (requirements/low_level.md:49)

# Point a requirement at a parent that does not exist
sed -i 's|parents: HLR-ALTH-030|parents: HLR-ALTH-999|' requirements/low_level.md
traceguard check --root .
# ERROR   TG002-missing-parent [LLR-ALTH-031] Parent HLR-ALTH-999 is not
#         declared in any specification (requirements/low_level.md:49)
# ERROR   TG009-childless-hlr [HLR-ALTH-030] HLR is not decomposed into any
#         low-level requirement (requirements/high_level.md:23)

git checkout .
```

The second case is the interesting one: a single typo produces two findings, from
both directions of the trace. That is what bidirectional means in practice.
