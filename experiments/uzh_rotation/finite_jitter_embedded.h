/* Bounded synthetic visual-compass witness core, C99, no dynamic allocation.
 *
 * The fixed prior has four candidate yaw bins: 0, 16, 32, and 48 in a
 * 64-bin first-revolution reference. A capture is a 16-bit column.
 * All source-fidelity, gyro timing, and binary error bounds are ASSUMPTIONS.
 * No aircraft correction is made by this library.
 */
#ifndef MATHGRAPH_FINITE_JITTER_EMBEDDED_H
#define MATHGRAPH_FINITE_JITTER_EMBEDDED_H

#include <stdint.h>

enum {
    MG_INVALID = 0,
    MG_SEPARATING_SET = 1,
    MG_ALREADY_UNIQUE = 2,
    MG_BOUNDED_OBSTRUCTION = 3,
    MG_NO_CANDIDATES = 4
};

typedef struct {
    uint32_t step_mask;       /* set bit s-1 for a planned capture at step s */
    uint16_t pair_checks;     /* attempted exact Hamming pair comparisons */
    uint8_t cost;             /* required captures */
    uint8_t first_step;       /* first required future capture, 0 if none */
    uint8_t status;
} MGPlan;

/* reference has exactly 64 uint16_t columns; candidate_mask has bits 0..3.
 * Step range is inclusive, 1..32. timing_jitter_bins is 0..3.
 * Returns 0 for a valid request (including an obstruction), -1 otherwise.
 * No ground-truth or future camera measurement is supplied to the planner.
 */
int mg_plan(const uint16_t reference[64], uint8_t candidate_mask,
            uint8_t first_step, uint8_t last_step,
            uint8_t noise_budget, uint8_t timing_jitter_bins, MGPlan *out);

/* A candidate survives if at least one allowed offset matches a measurement.
 * Returns surviving mask; zero also represents conflicting evidence.
 * Caller must use validated step/bounds (same preconditions as mg_plan).
 */
uint8_t mg_filter(const uint16_t reference[64], uint8_t candidate_mask,
                  uint8_t step, uint16_t actual_column,
                  uint8_t noise_budget, uint8_t timing_jitter_bins);

uint16_t mg_reference_bytes(void);

#endif
