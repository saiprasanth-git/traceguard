# Altitude Hold (ALTH) - fully traced DAL B example

A complete, buildable altitude-hold control law for a fixed-wing autopilot, used
to demonstrate TraceGuard end to end and as the tool's own regression baseline.

```bash
make test     # compile with -Wall -Wextra -Werror -Wpedantic and run 14 cases
make trace    # requirements traceability gate
make report   # markdown + HTML + JSON evidence into build/
make          # test + trace
```

Requires a C99 compiler and `traceguard` on `PATH` (`pip install -e ../..` from
this directory).

## Contents

| Path | Contents |
| --- | --- |
| `requirements/system.md` | 3 system requirements allocated to software |
| `requirements/high_level.md` | 5 software high-level requirements |
| `requirements/low_level.md` | 10 low-level requirements, one of them derived |
| `include/altitude_hold.h` | Public interface, limits and types |
| `src/altitude_hold.c` | Implementation, ~150 lines of C99, `@implements` annotated |
| `tests/test_altitude_hold.c` | 14 verification cases, `@verifies` annotated |
| `tests/unity_min.h` | Minimal dependency-free xUnit harness |
| `traceguard.toml` | Discovery globs, gate threshold, one documented waiver |
| `Makefile` | `test`, `trace`, `report`, `clean` |

## Expected result

```
requirements: 18 (SYS 3 / HLR 5 / LLR 10)
implementation coverage: 100.0%   verification coverage: 100.0%
findings: 0 error(s), 0 warning(s)
```

## Design properties under trace

1. **Altitude hold** - PID control law, derivative taken on the measurement rather
   than the error so a command step produces no derivative kick.
2. **Envelope protection** - the published pitch command is clamped to
   ±15 degrees regardless of gains, error magnitude or sensor behaviour.
3. **Anti-windup** - integration is reverted on any frame where the output
   saturates, so the controller leaves saturation as soon as the error reverses.
4. **Input validation and latched fault** - non-finite, out-of-range or stale
   barometric samples disengage the function into a defined safe state, and the
   fault latches until `alth_reset` is called.

Requirement-by-requirement reasoning, the verification matrix and a "try breaking
it" exercise are in
[../../docs/example-walkthrough.md](../../docs/example-walkthrough.md). The review
record for this component is [../../docs/reviews/SRR-001.md](../../docs/reviews/SRR-001.md).
