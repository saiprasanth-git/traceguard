# Software High-Level Requirements - Altitude Hold

Each HLR traces upward to a system requirement and downward to one or more
low-level requirements in `low_level.md`.

### HLR-ALTH-010: Compute pitch command from altitude error

- dal: B
- parents: SYS-ALTH-001

The software shall compute a pitch attitude command from the difference between
commanded and measured barometric altitude using a proportional-integral-
derivative control law executed at the fixed frame rate.

### HLR-ALTH-020: Limit the pitch command

- dal: B
- parents: SYS-ALTH-002

The software shall saturate the computed pitch attitude command to the
configured minimum and maximum pitch limits before publishing it.

### HLR-ALTH-030: Bound the integral term

- dal: B
- parents: SYS-ALTH-002

The software shall prevent unbounded growth of the integral term when the pitch
command is saturated.

### HLR-ALTH-040: Validate barometric altitude input

- dal: B
- parents: SYS-ALTH-003

The software shall classify barometric altitude input as valid only when the
sample is finite, within the sensor measurement range, and no older than the
configured staleness threshold.

### HLR-ALTH-050: Enter a safe state on invalid input

- dal: B
- parents: SYS-ALTH-003

On detection of invalid barometric altitude input the software shall disengage
the control law, publish a zero pitch command, and set the fault status.
