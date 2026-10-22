/* Synthetic first-turn map acquisition and missing-reference-aware witnesses.
 * A gyro provides the first-turn angular bin. Its correctness is assumed.
 * No claims of calibrated timing or validated aircraft sensor acquisition.
 */
#ifndef MATHGRAPH_FINITE_PARTIAL_MAP_H
#define MATHGRAPH_FINITE_PARTIAL_MAP_H

#include "finite_jitter_embedded.h"

enum { MG_POTENTIAL_PROBE = 5 };

typedef struct {
    uint16_t columns[64];
    uint8_t seen[8];
    uint8_t quarantined[8];
    uint8_t count;
    uint8_t frozen;
} MGReferenceMap;

void mg_map_init(MGReferenceMap *map);

/* For the FIRST revolution only. 0=new bin, 1=confirming duplicate,
 * -2=inconsistent/quarantined duplicate, -1=invalid or already frozen.
 * Confirmations tolerate Hamming distance <=2 between two one-bit noisy
 * first-turn measurements. A large disagreement permanently quarantines bin.
 */
int mg_map_capture(MGReferenceMap *map, uint8_t angular_bin, uint16_t column);
int mg_map_freeze(MGReferenceMap *map);
uint8_t mg_map_has(const MGReferenceMap *map, uint8_t angular_bin);

/* Both require frozen map. Missing map cells are UNKNOWN, never filled with
 * zero or taken as negative evidence. Planner status MG_BOUNDED_OBSTRUCTION
 * means no guaranteed distinction IN THE AVAILABLE FROZEN MAP, not an
 * intrinsic impossibility in the physical environment.
 */
int mg_sparse_plan(const MGReferenceMap *map, uint8_t candidate_mask,
                   uint8_t first_step, uint8_t last_step,
                   uint8_t noise_budget, uint8_t timing_jitter_bins,
                   MGPlan *out);
/* If no guaranteed complete set exists, return an informative but explicitly
 * NON-GUARANTEED next capture. Only evidence from an actually acquired column
 * may shrink the support. Status 5 means potential discrimination, not warrant.
 * Maximize number of possible directed pair eliminations, then earliest step.
 */
int mg_sparse_next_probe(const MGReferenceMap *map, uint8_t candidate_mask,
                         uint8_t first_step, uint8_t last_step,
                         uint8_t noise_budget, uint8_t timing_jitter_bins,
                         MGPlan *out);
uint8_t mg_sparse_filter(const MGReferenceMap *map, uint8_t candidate_mask,
                         uint8_t step, uint16_t column,
                         uint8_t noise_budget, uint8_t timing_jitter_bins);

#endif
