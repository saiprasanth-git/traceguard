/**
 * @file altitude_hold.h
 * @brief Altitude Hold (ALTH) control law - public interface.
 *
 * Design assurance level: B. No dynamic memory, no recursion, no unbounded
 * loops. All state is owned by the caller through alth_controller_t.
 */

#ifndef ALTITUDE_HOLD_H
#define ALTITUDE_HOLD_H

#include <stdbool.h>

/* ---------------------------------------------------------------- limits --- */

#define ALTH_PITCH_MIN_DEG      (-15.0)
#define ALTH_PITCH_MAX_DEG      (15.0)
#define ALTH_ALT_MIN_M          (-500.0)
#define ALTH_ALT_MAX_M          (15000.0)
#define ALTH_MAX_SAMPLE_AGE_S   (0.100)
#define ALTH_MAX_FRAME_TIME_S   (0.100)

/* ---------------------------------------------------------------- types ---- */

typedef enum {
    ALTH_STATUS_OK = 0,          /**< Control law executed normally.        */
    ALTH_STATUS_FAULT_INPUT = 1, /**< Latched fault: invalid/stale input.   */
    ALTH_STATUS_FRAME_SKIPPED = 2 /**< Frame rejected, previous output held. */
} alth_status_t;

/** Gains for the PID control law. */
typedef struct {
    double kp;
    double ki;
    double kd;
} alth_gains_t;

/** One barometric altitude sample as delivered by the sensor interface. */
typedef struct {
    double altitude_m; /**< Measured barometric altitude, metres.       */
    double age_s;      /**< Age of the sample at frame start, seconds.  */
    bool   valid;      /**< Sensor-reported validity flag.              */
} alth_baro_sample_t;

/** Controller state. Treat as opaque; use the functions below. */
typedef struct {
    alth_gains_t  gains;
    double        integral;
    double        last_altitude_m;
    bool          has_last_altitude;
    double        pitch_cmd_deg;
    bool          engaged;
    alth_status_t status;
} alth_controller_t;

/* ------------------------------------------------------------ interface ---- */

/**
 * @brief Initialise a controller to the disengaged, fault-free state.
 * @param ctl   Controller to initialise. Must not be NULL.
 * @param gains PID gains to apply.
 */
void alth_init(alth_controller_t *ctl, alth_gains_t gains);

/**
 * @brief Clear a latched fault and reset all control state.
 */
void alth_reset(alth_controller_t *ctl);

/**
 * @brief Execute one control frame.
 *
 * @param ctl              Controller state.
 * @param commanded_alt_m  Commanded barometric altitude, metres.
 * @param sample           Latest barometric altitude sample.
 * @param dt_s             Frame time, seconds.
 * @return The status of this frame. The pitch command is readable through
 *         alth_pitch_command().
 */
alth_status_t alth_step(alth_controller_t *ctl,
                        double commanded_alt_m,
                        alth_baro_sample_t sample,
                        double dt_s);

/** @brief Last published pitch attitude command, degrees. */
double alth_pitch_command(const alth_controller_t *ctl);

/** @brief True when the control law is engaged and fault-free. */
bool alth_is_engaged(const alth_controller_t *ctl);

/** @brief Current controller status. */
alth_status_t alth_status(const alth_controller_t *ctl);

/**
 * @brief Validate a barometric sample against range, finiteness and staleness.
 * @return true when the sample may be used by the control law.
 */
bool alth_sample_is_valid(alth_baro_sample_t sample);

#endif /* ALTITUDE_HOLD_H */
