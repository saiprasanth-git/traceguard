/**
 * @file unity_min.h
 * @brief Minimal xUnit-style harness for the ALTH verification suite.
 *
 * Deliberately tiny and dependency-free so the example builds anywhere with a
 * C99 compiler. A real DO-178C project would substitute its qualified test
 * framework here without changing any test body.
 */

#ifndef UNITY_MIN_H
#define UNITY_MIN_H

#include <math.h>
#include <stdio.h>
#include <string.h>

static int tg_tests_run = 0;
static int tg_tests_failed = 0;
static int tg_current_failed = 0;
static const char *tg_current_name = "";

#define TG_BEGIN(name)                     \
    do {                                   \
        tg_current_name = (name);          \
        tg_current_failed = 0;             \
        tg_tests_run++;                    \
    } while (0)

#define TG_END()                                               \
    do {                                                       \
        if (tg_current_failed) {                               \
            tg_tests_failed++;                                 \
            printf("FAIL  %s\n", tg_current_name);             \
        } else {                                               \
            printf("ok    %s\n", tg_current_name);             \
        }                                                      \
    } while (0)

#define TG_ASSERT(cond)                                                        \
    do {                                                                       \
        if (!(cond)) {                                                         \
            tg_current_failed = 1;                                             \
            printf("      assert failed: %s (%s:%d)\n", #cond, __FILE__, __LINE__); \
        }                                                                      \
    } while (0)

#define TG_ASSERT_NEAR(actual, expected, tol)                                  \
    do {                                                                       \
        double tg_a = (double)(actual);                                        \
        double tg_e = (double)(expected);                                      \
        if (!(fabs(tg_a - tg_e) <= (tol))) {                                   \
            tg_current_failed = 1;                                             \
            printf("      expected %g, got %g (%s:%d)\n",                      \
                   tg_e, tg_a, __FILE__, __LINE__);                            \
        }                                                                      \
    } while (0)

#define TG_SUMMARY()                                                           \
    (printf("\n%d test(s), %d failure(s)\n", tg_tests_run, tg_tests_failed),    \
     tg_tests_failed == 0 ? 0 : 1)

#endif /* UNITY_MIN_H */
