# System Requirements - Altitude Hold Function

Scope: the Altitude Hold (ALTH) function of a fixed-wing autopilot. These
requirements are allocated to software from the system-level safety assessment.

### SYS-ALTH-001: Maintain commanded barometric altitude

- dal: B
- rationale: Loss of altitude hold is a Major failure condition per the FHA.

The ALTH function shall command elevator deflection such that the aircraft
maintains the commanded barometric altitude within the accuracy defined by the
system requirements when engaged in steady, level flight.

### SYS-ALTH-002: Protect the aircraft from unsafe pitch commands

- dal: B

The ALTH function shall not command a pitch attitude outside the certified
envelope, regardless of altitude error magnitude or sensor behaviour.

### SYS-ALTH-003: Disengage on invalid sensor data

- dal: B

The ALTH function shall disengage and annunciate a failure when barometric
altitude data is invalid or stale.
