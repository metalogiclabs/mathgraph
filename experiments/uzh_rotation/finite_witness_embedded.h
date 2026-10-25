#ifndef MATHGRAPH_FINITE_WITNESS_C99_H
#define MATHGRAPH_FINITE_WITNESS_C99_H

/* Standalone deterministic finite scene discriminator; no hardware access.
 * This is NOT an ArduPilot or moteus flight-controller integration.
 * Caller supplies a FROZEN first-turn 64-bin map and noise-budget premises.
 * No encoder, optical ground truth, clock, heap or camera driver dependencies.
 */
#include <stdint.h>

#define MGW_MAP_BINS 64u
#define MGW_MAX_HYPOTHESES 4u
#define MGW_MAX_HORIZON 32u

enum {
    MGW_INVALID = 0,
    MGW_SEPARATING_SET = 1,
    MGW_BOUNDED_OBSTRUCTION = 2,
    MGW_ALREADY_UNIQUE = 3,
    MGW_NO_CANDIDATES = 4
};

typedef struct {
    uint8_t status;
    uint8_t next_step;              /* 1..horizon; zero if no request */
    uint8_t minimum_total_reads;    /* exact nonadaptive pair-cover basis */
    uint8_t candidate_pairs;
    uint32_t selected_steps_bits;   /* bit (step-1) = scheduled future read */
} mgw_plan_t;

/* Returns 0 on valid input, -1 on invalid input.
 * For a bounded obstruction, no new visual correction is permitted.
 * Map holes (present[index] == 0) are NEVER used as separating evidence.
 */
int mgw_plan(const uint16_t signature[MGW_MAP_BINS],
             const uint8_t present[MGW_MAP_BINS],
             const uint8_t hypotheses[MGW_MAX_HYPOTHESES],
             uint8_t candidate_count, uint8_t first_future_step,
             uint8_t horizon, uint8_t total_hamming_error,
             mgw_plan_t *result);

/* Filter candidate offsets with ONE actually acquired 16-bit column.
 * Never call based on an unavailable/occluded camera observation.
 * Returns 0 on valid input, -1 on invalid input. Output may be empty
 * (CONFLICT) and must not be interpreted as a justified correction.
 */
int mgw_filter(const uint16_t signature[MGW_MAP_BINS],
               const uint8_t present[MGW_MAP_BINS],
               const uint8_t hypotheses[MGW_MAX_HYPOTHESES],
               uint8_t candidate_count, uint8_t observed_step,
               uint16_t observed_column, uint8_t total_hamming_error,
               uint8_t out[MGW_MAX_HYPOTHESES], uint8_t *out_count);

#endif
