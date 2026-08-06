/**
 * @file altitude_hold.c
 * @brief Altitude Hold (ALTH) control law implementation.
 *
 * Every function below carries an `@implements` annotation naming the low-level
 * requirement it satisfies. TraceGuard reads those annotations to build the
 * traceability matrix; removing one breaks the build.
 */

#include "altitude_hold.h"

#include <math.h>

/* ------------------------------------------------------------- internals --- */

static double clamp(double value, double low, double high)
{
    if (value < low) {
        return low;
    }
    if (value > high) {
        return high;
    }
    return value;
}

static void enter_safe_state(alth_controller_t *ctl, alth_status_t status)
{
    ctl->integral          = 0.0;
    ctl->pitch_cmd_deg     = 0.0;
    ctl->engaged           = false;
    ctl->has_last_altitude = false;
    ctl->status            = status;
}

/* -------------------------------------------------------------- lifecycle -- */

void alth_init(alth_controller_t *ctl, alth_gains_t gains)
{
    ctl->gains             = gains;
    ctl->integral          = 0.0;
    ctl->last_altitude_m   = 0.0;
    ctl->has_last_altitude = false;
    ctl->pitch_cmd_deg     = 0.0;
    ctl->engaged           = false;
    ctl->status            = ALTH_STATUS_OK;
}

void alth_reset(alth_controller_t *ctl)
{
    alth_gains_t gains = ctl->gains;
    alth_init(ctl, gains);
}

/* -------------------------------------------------------------- validation - */

/**
 * @implements LLR-ALTH-041
 * @implements LLR-ALTH-042
 */
bool alth_sample_is_valid(alth_baro_sample_t sample)
{
    if (!sample.valid) {
        return false;
    }
    /* LLR-ALTH-041: finiteness and measurement range. */
    if (!isfinite(sample.altitude_m)) {
        return false;
    }
    if (sample.altitude_m < ALTH_ALT_MIN_M || sample.altitude_m > ALTH_ALT_MAX_M) {
        return false;
    }
    /* LLR-ALTH-042: staleness. */
    if (!isfinite(sample.age_s) || sample.age_s > ALTH_MAX_SAMPLE_AGE_S) {
        return false;
    }
    return true;
}

/* ------------------------------------------------------------- control law - */

/**
 * @implements LLR-ALTH-011
 * @implements LLR-ALTH-012
 * @implements LLR-ALTH-013
 * @implements LLR-ALTH-014
 * @implements LLR-ALTH-021
 * @implements LLR-ALTH-031
 * @implements LLR-ALTH-051
 * @implements LLR-ALTH-052
 */
alth_status_t alth_step(alth_controller_t *ctl,
                        double commanded_alt_m,
                        alth_baro_sample_t sample,
                        double dt_s)
{
    /* LLR-ALTH-052: a latched input fault survives until alth_reset(). */
    if (ctl->status == ALTH_STATUS_FAULT_INPUT) {
        ctl->pitch_cmd_deg = 0.0;
        ctl->engaged       = false;
        return ALTH_STATUS_FAULT_INPUT;
    }

    /* LLR-ALTH-051: reject invalid input and enter the safe state. */
    if (!alth_sample_is_valid(sample)) {
        enter_safe_state(ctl, ALTH_STATUS_FAULT_INPUT);
        return ALTH_STATUS_FAULT_INPUT;
    }

    /* LLR-ALTH-014: reject a frame with an unusable frame time. */
    if (!isfinite(dt_s) || dt_s <= 0.0 || dt_s > ALTH_MAX_FRAME_TIME_S) {
        ctl->status = ALTH_STATUS_FRAME_SKIPPED;
        return ALTH_STATUS_FRAME_SKIPPED;
    }

    const double error_m = commanded_alt_m - sample.altitude_m;

    /* LLR-ALTH-011: proportional term. */
    const double proportional = ctl->gains.kp * error_m;

    /* LLR-ALTH-012: integral accumulation. */
    const double integral_delta = error_m * dt_s;
    ctl->integral += integral_delta;
    const double integral = ctl->gains.ki * ctl->integral;

    /* LLR-ALTH-013: derivative on measurement, negated. */
    double derivative = 0.0;
    if (ctl->has_last_altitude) {
        const double measurement_rate = (sample.altitude_m - ctl->last_altitude_m) / dt_s;
        derivative = ctl->gains.kd * (-measurement_rate);
    }
    ctl->last_altitude_m   = sample.altitude_m;
    ctl->has_last_altitude = true;

    const double unclamped = proportional + integral + derivative;

    /* LLR-ALTH-021: saturate the published command. */
    const double clamped = clamp(unclamped, ALTH_PITCH_MIN_DEG, ALTH_PITCH_MAX_DEG);

    /* LLR-ALTH-031: anti-windup - undo this frame's integration when saturated. */
    if (clamped != unclamped) {
        ctl->integral -= integral_delta;
    }

    ctl->pitch_cmd_deg = clamped;
    ctl->engaged       = true;
    ctl->status        = ALTH_STATUS_OK;
    return ALTH_STATUS_OK;
}

/* ---------------------------------------------------------------- getters -- */

double alth_pitch_command(const alth_controller_t *ctl)
{
    return ctl->pitch_cmd_deg;
}

bool alth_is_engaged(const alth_controller_t *ctl)
{
    return ctl->engaged;
}

alth_status_t alth_status(const alth_controller_t *ctl)
{
    return ctl->status;
}
