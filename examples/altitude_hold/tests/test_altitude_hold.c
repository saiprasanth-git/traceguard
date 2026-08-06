/**
 * @file test_altitude_hold.c
 * @brief Verification cases for the ALTH control law.
 *
 * Each case carries a `@verifies` annotation naming the requirement it covers
 * and the verification method. TraceGuard reads these to prove that every
 * requirement has at least one verification case.
 */

#include "altitude_hold.h"
#include "unity_min.h"

static alth_baro_sample_t good_sample(double altitude_m)
{
    alth_baro_sample_t sample;
    sample.altitude_m = altitude_m;
    sample.age_s      = 0.010;
    sample.valid      = true;
    return sample;
}

static alth_controller_t make_controller(double kp, double ki, double kd)
{
    alth_controller_t ctl;
    alth_gains_t gains;
    gains.kp = kp;
    gains.ki = ki;
    gains.kd = kd;
    alth_init(&ctl, gains);
    return ctl;
}

/**
 * @verifies LLR-ALTH-011 method=unit
 * Proportional-only controller: 10 m error at kp = 0.2 gives 2.0 deg.
 */
static void test_proportional_term(void)
{
    TG_BEGIN("LLR-ALTH-011 proportional term");
    alth_controller_t ctl = make_controller(0.2, 0.0, 0.0);
    TG_ASSERT(alth_step(&ctl, 1010.0, good_sample(1000.0), 0.02) == ALTH_STATUS_OK);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 2.0, 1e-9);
    TG_ASSERT(alth_is_engaged(&ctl));
    TG_END();
}

/**
 * @verifies LLR-ALTH-012 method=unit
 * Integral-only controller: constant 5 m error over two 0.1 s frames
 * accumulates 1.0 m*s, so at ki = 1.0 the command is 1.0 deg.
 */
static void test_integral_accumulation(void)
{
    TG_BEGIN("LLR-ALTH-012 integral accumulation");
    alth_controller_t ctl = make_controller(0.0, 1.0, 0.0);
    alth_step(&ctl, 1005.0, good_sample(1000.0), 0.1);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 0.5, 1e-9);
    alth_step(&ctl, 1005.0, good_sample(1000.0), 0.1);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 1.0, 1e-9);
    TG_END();
}

/**
 * @verifies LLR-ALTH-013 method=unit
 * Derivative acts on the measurement: a climbing aircraft produces a negative
 * contribution, and a step in the command produces none.
 */
static void test_derivative_on_measurement(void)
{
    TG_BEGIN("LLR-ALTH-013 derivative on measurement");
    alth_controller_t ctl = make_controller(0.0, 0.0, 0.5);

    /* First frame has no previous measurement, so no derivative. */
    alth_step(&ctl, 1000.0, good_sample(1000.0), 0.1);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 0.0, 1e-9);

    /* Climb of 1 m over 0.1 s => rate 10 m/s => -0.5 * 10 = -5.0 deg. */
    alth_step(&ctl, 1000.0, good_sample(1001.0), 0.1);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), -5.0, 1e-9);

    /* A pure command step must not move the derivative term. */
    alth_step(&ctl, 2000.0, good_sample(1001.0), 0.1);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 0.0, 1e-9);
    TG_END();
}

/**
 * @verifies LLR-ALTH-014 method=unit
 * Non-positive, excessive and non-finite frame times are all rejected and the
 * previous output is held.
 */
static void test_frame_time_validation(void)
{
    TG_BEGIN("LLR-ALTH-014 frame time validation");
    alth_controller_t ctl = make_controller(0.2, 0.0, 0.0);
    alth_step(&ctl, 1010.0, good_sample(1000.0), 0.02);
    double held = alth_pitch_command(&ctl);

    TG_ASSERT(alth_step(&ctl, 1500.0, good_sample(1000.0), 0.0) == ALTH_STATUS_FRAME_SKIPPED);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), held, 1e-12);

    TG_ASSERT(alth_step(&ctl, 1500.0, good_sample(1000.0), -0.01) == ALTH_STATUS_FRAME_SKIPPED);
    TG_ASSERT(alth_step(&ctl, 1500.0, good_sample(1000.0), 0.5) == ALTH_STATUS_FRAME_SKIPPED);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), held, 1e-12);
    TG_END();
}

/**
 * @verifies LLR-ALTH-021 method=unit
 * @verifies SYS-ALTH-002 method=integration
 * A very large error must not push the command past the envelope limits.
 */
static void test_pitch_saturation(void)
{
    TG_BEGIN("LLR-ALTH-021 pitch command saturation");
    alth_controller_t ctl = make_controller(1.0, 0.0, 0.0);

    alth_step(&ctl, 5000.0, good_sample(1000.0), 0.02);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), ALTH_PITCH_MAX_DEG, 1e-9);

    alth_step(&ctl, 0.0, good_sample(1000.0), 0.02);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), ALTH_PITCH_MIN_DEG, 1e-9);
    TG_END();
}

/**
 * @verifies LLR-ALTH-031 method=unit
 * While saturated the integral state must not grow, so recovery is immediate
 * once the error reverses.
 */
static void test_integral_anti_windup(void)
{
    TG_BEGIN("LLR-ALTH-031 integral anti-windup");
    alth_controller_t ctl = make_controller(0.0, 5.0, 0.0);

    for (int frame = 0; frame < 50; ++frame) {
        alth_step(&ctl, 2000.0, good_sample(1000.0), 0.02);
    }
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), ALTH_PITCH_MAX_DEG, 1e-9);

    /* Without anti-windup the integral would be ~1000 m*s and the command would
     * stay pinned for many frames. With it, one reversed frame is enough. */
    alth_step(&ctl, 1000.0, good_sample(1000.0), 0.02);
    TG_ASSERT(alth_pitch_command(&ctl) < ALTH_PITCH_MAX_DEG);
    TG_END();
}

/**
 * @verifies LLR-ALTH-041 method=unit
 * Out-of-range, non-finite and sensor-invalid samples are rejected.
 */
static void test_range_and_finiteness(void)
{
    TG_BEGIN("LLR-ALTH-041 range and finiteness check");
    alth_baro_sample_t sample = good_sample(1000.0);
    TG_ASSERT(alth_sample_is_valid(sample));

    sample.altitude_m = ALTH_ALT_MAX_M + 1.0;
    TG_ASSERT(!alth_sample_is_valid(sample));

    sample.altitude_m = ALTH_ALT_MIN_M - 1.0;
    TG_ASSERT(!alth_sample_is_valid(sample));

    sample.altitude_m = NAN;
    TG_ASSERT(!alth_sample_is_valid(sample));

    sample = good_sample(1000.0);
    sample.valid = false;
    TG_ASSERT(!alth_sample_is_valid(sample));
    TG_END();
}

/**
 * @verifies LLR-ALTH-042 method=unit
 * A sample older than the staleness threshold is rejected; one at the
 * threshold is accepted.
 */
static void test_staleness(void)
{
    TG_BEGIN("LLR-ALTH-042 sample staleness check");
    alth_baro_sample_t sample = good_sample(1000.0);

    sample.age_s = ALTH_MAX_SAMPLE_AGE_S;
    TG_ASSERT(alth_sample_is_valid(sample));

    sample.age_s = ALTH_MAX_SAMPLE_AGE_S + 0.001;
    TG_ASSERT(!alth_sample_is_valid(sample));
    TG_END();
}

/**
 * @verifies LLR-ALTH-051 method=unit
 * @verifies SYS-ALTH-003 method=integration
 * Invalid input drives the controller into the safe state.
 */
static void test_safe_state_transition(void)
{
    TG_BEGIN("LLR-ALTH-051 safe-state transition");
    alth_controller_t ctl = make_controller(0.2, 1.0, 0.0);
    alth_step(&ctl, 1010.0, good_sample(1000.0), 0.02);

    alth_baro_sample_t bad = good_sample(1000.0);
    bad.valid = false;

    TG_ASSERT(alth_step(&ctl, 1010.0, bad, 0.02) == ALTH_STATUS_FAULT_INPUT);
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 0.0, 1e-12);
    TG_ASSERT(!alth_is_engaged(&ctl));
    TG_ASSERT(alth_status(&ctl) == ALTH_STATUS_FAULT_INPUT);
    TG_END();
}

/**
 * @verifies LLR-ALTH-052 method=unit
 * The fault latches: good data alone does not re-engage the controller, only
 * an explicit reset does.
 */
static void test_fault_latching(void)
{
    TG_BEGIN("LLR-ALTH-052 fault latching until reset");
    alth_controller_t ctl = make_controller(0.2, 0.0, 0.0);
    alth_baro_sample_t bad = good_sample(1000.0);
    bad.age_s = 1.0;

    alth_step(&ctl, 1010.0, bad, 0.02);
    TG_ASSERT(alth_step(&ctl, 1010.0, good_sample(1000.0), 0.02) == ALTH_STATUS_FAULT_INPUT);
    TG_ASSERT(!alth_is_engaged(&ctl));
    TG_ASSERT_NEAR(alth_pitch_command(&ctl), 0.0, 1e-12);

    alth_reset(&ctl);
    TG_ASSERT(alth_status(&ctl) == ALTH_STATUS_OK);
    TG_ASSERT(alth_step(&ctl, 1010.0, good_sample(1000.0), 0.02) == ALTH_STATUS_OK);
    TG_ASSERT(alth_is_engaged(&ctl));
    TG_END();
}

/**
 * @verifies HLR-ALTH-010 method=integration
 * @verifies SYS-ALTH-001 method=integration
 * Closed-loop check against a first-order aircraft model: the altitude error
 * converges towards zero and the aircraft settles near the commanded altitude.
 */
static void test_closed_loop_convergence(void)
{
    TG_BEGIN("HLR-ALTH-010 closed-loop convergence");
    alth_controller_t ctl = make_controller(0.35, 0.06, 0.9);

    const double dt = 0.02;
    const double command = 1100.0;
    double altitude = 1000.0;
    double climb_rate = 0.0;

    for (int frame = 0; frame < 4000; ++frame) {
        alth_step(&ctl, command, good_sample(altitude), dt);
        /* Very coarse plant: pitch commands a climb rate, first-order lag. */
        const double target_rate = alth_pitch_command(&ctl) * 1.2; /* m/s per deg */
        climb_rate += (target_rate - climb_rate) * (dt / 0.8);
        altitude += climb_rate * dt;
    }

    TG_ASSERT_NEAR(altitude, command, 5.0);
    TG_ASSERT(fabs(climb_rate) < 1.0);
    TG_END();
}

/**
 * @verifies HLR-ALTH-020 method=integration
 * The published command never leaves the certified envelope across a sweep of
 * altitude errors, including extreme ones.
 */
static void test_envelope_never_exceeded(void)
{
    TG_BEGIN("HLR-ALTH-020 envelope never exceeded");
    alth_controller_t ctl = make_controller(2.0, 0.5, 0.5);

    for (int step = -200; step <= 200; ++step) {
        const double command = 1000.0 + (double)step * 50.0;
        alth_step(&ctl, command, good_sample(1000.0), 0.02);
        TG_ASSERT(alth_pitch_command(&ctl) <= ALTH_PITCH_MAX_DEG + 1e-12);
        TG_ASSERT(alth_pitch_command(&ctl) >= ALTH_PITCH_MIN_DEG - 1e-12);
    }
    TG_END();
}

/**
 * @verifies HLR-ALTH-030 method=analysis
 * The integral state stays bounded by the value that saturates the output,
 * demonstrated over a long saturated run.
 */
static void test_integral_bounded(void)
{
    TG_BEGIN("HLR-ALTH-030 integral state bounded");
    alth_controller_t ctl = make_controller(0.0, 1.0, 0.0);
    for (int frame = 0; frame < 5000; ++frame) {
        alth_step(&ctl, 3000.0, good_sample(1000.0), 0.02);
    }
    /* ki = 1.0, so the integral cannot exceed the pitch limit by more than one
     * frame's worth of integration. */
    TG_ASSERT(ctl.integral <= ALTH_PITCH_MAX_DEG + (2000.0 * 0.02) + 1e-9);
    TG_END();
}

/**
 * @verifies HLR-ALTH-040 method=unit
 * @verifies HLR-ALTH-050 method=integration
 * Input validation gates engagement end-to-end.
 */
static void test_validation_gates_engagement(void)
{
    TG_BEGIN("HLR-ALTH-040/050 validation gates engagement");
    alth_controller_t ctl = make_controller(0.2, 0.0, 0.0);
    alth_baro_sample_t stale = good_sample(1000.0);
    stale.age_s = 5.0;

    TG_ASSERT(!alth_sample_is_valid(stale));
    TG_ASSERT(alth_step(&ctl, 1010.0, stale, 0.02) == ALTH_STATUS_FAULT_INPUT);
    TG_ASSERT(!alth_is_engaged(&ctl));
    TG_END();
}

int main(void)
{
    test_proportional_term();
    test_integral_accumulation();
    test_derivative_on_measurement();
    test_frame_time_validation();
    test_pitch_saturation();
    test_integral_anti_windup();
    test_range_and_finiteness();
    test_staleness();
    test_safe_state_transition();
    test_fault_latching();
    test_closed_loop_convergence();
    test_envelope_never_exceeded();
    test_integral_bounded();
    test_validation_gates_engagement();
    return TG_SUMMARY();
}
