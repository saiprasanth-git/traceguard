# Software Low-Level Requirements - Altitude Hold

Each LLR traces upward to exactly one HLR and is implemented by annotated source
code in `src/` and verified by annotated cases in `tests/`.

### LLR-ALTH-011: Proportional term

- dal: B
- parents: HLR-ALTH-010

The proportional term shall equal `kp * error_m`, where `error_m` is the
commanded altitude minus the measured altitude in metres.

### LLR-ALTH-012: Integral term accumulation

- dal: B
- parents: HLR-ALTH-010

The integral state shall be updated as `integral += error_m * dt_s` on every
frame in which the control law executes.

### LLR-ALTH-013: Derivative term on measurement

- dal: B
- parents: HLR-ALTH-010

The derivative term shall be computed from the change in measured altitude
between consecutive frames, negated, and divided by `dt_s`, so that a step in
the commanded altitude does not produce a derivative spike.

### LLR-ALTH-014: Frame time validation

- dal: B
- parents: HLR-ALTH-010
- derived: true
- rationale: The frame time is supplied by the scheduler and is not constrained by any parent requirement; a non-positive or excessive dt would make the control law numerically invalid.

The control law shall reject a frame whose `dt_s` is not greater than zero or is
greater than `ALTH_MAX_FRAME_TIME_S`, and shall hold the previous output.

### LLR-ALTH-021: Pitch command saturation

- dal: B
- parents: HLR-ALTH-020

The published pitch command shall be clamped to the inclusive range
`[ALTH_PITCH_MIN_DEG, ALTH_PITCH_MAX_DEG]`.

### LLR-ALTH-031: Integral anti-windup

- dal: B
- parents: HLR-ALTH-030

When the unclamped pitch command lies outside the saturation limits, the
integral update of that frame shall be reverted so the integral state does not
accumulate while saturated.

### LLR-ALTH-041: Altitude range and finiteness check

- dal: B
- parents: HLR-ALTH-040

A barometric altitude sample shall be rejected when it is not finite or lies
outside `[ALTH_ALT_MIN_M, ALTH_ALT_MAX_M]`.

### LLR-ALTH-042: Sample staleness check

- dal: B
- parents: HLR-ALTH-040

A barometric altitude sample shall be rejected when its age exceeds
`ALTH_MAX_SAMPLE_AGE_S`.

### LLR-ALTH-051: Safe-state transition

- dal: B
- parents: HLR-ALTH-050

On rejection of a barometric altitude sample the controller shall set status to
`ALTH_STATUS_FAULT_INPUT`, set the pitch command to zero, clear the integral
state, and set `engaged` to false.

### LLR-ALTH-052: Fault latching until reset

- dal: B
- parents: HLR-ALTH-050

Once the fault status is set the controller shall remain disengaged and continue
to publish a zero pitch command until `alth_reset` is called.
