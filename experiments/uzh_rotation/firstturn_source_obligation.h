/* MathGraph first-turn source-evidence acquisition obligation (C99, no heap).
 *
 * Observation ability, warrant and permission remain separate. This layer
 * DOES NOT authenticate any sensor on its own. All evidence flags below must
 * be set by a genuinely independent source verifier; code cannot determine
 * from a flag whether the verifier or its physical error bound was truthful.
 * EvSLAM publisher nominal camera-IMU timeshift MUST NOT set these flags.
 */
#ifndef MATHGRAPH_SOURCE_OBLIGATION_H
#define MATHGRAPH_SOURCE_OBLIGATION_H
#include <stdint.h>
#include "firstturn_fine_capture.h"

typedef struct {
    uint16_t reported_phase_65536;
    uint16_t externally_bounded_error_ticks;
    uint8_t clock_error_bound_authenticated_externally;
    uint8_t gyro_error_bound_authenticated_externally;
    uint8_t source_epoch_authenticated_externally;
    uint8_t within_first_revolution;
} MGSourcePhaseEvidence;

/* Each status is a distinct obligation, not proof or permission to navigate.
 * 0/1/-2 are reserved for the original map capture, -1 for invalid input.
 */
enum {
    MG_OBLIGATION_CLOCK_BOUND = 20,
    MG_OBLIGATION_GYRO_BOUND = 21,
    MG_OBLIGATION_SOURCE_EPOCH = 22,
    MG_OBLIGATION_FIRST_TURN = 23,
    MG_OBLIGATION_PHASE_UNCERTAIN = 24,
    MG_OBLIGATION_COLUMN_ALREADY_PRESENT = 25,
    MG_OBLIGATION_REFERENCE_QUARANTINED = 26,
    MG_OBLIGATION_ACQUIRE_COLUMN = 27
};

/* Returns a source-dependency/status code. out_bin is set to 255 on refusal.
 * A positive ACQUIRE_COLUMN result only requests a real observation, it
 * DOES NOT fabricate a camera column or mutate the map.
 * A missing/forged bound must be handled outside this function.
 */
int mg_source_firstturn_obligation(const MGReferenceMap *map,
                                   const MGSourcePhaseEvidence *evidence,
                                   uint8_t *out_bin);

/* Call ONLY after a physical sensor column has actually been acquired.
 * Returns unchanged original mg_firstturn_capture_fine_interval status
 * (0,1,-2,2) or one of the named evidence obligations. Existing bins are
 * skipped to reduce acquisitions, hence changed-scene duplicate checking
 * is not performed by this *active* path. Continuous tracking remains a
 * separately qualified baseline, and visual contradictions must withdraw
 * authority outside this module.
 */
int mg_source_capture_with_evidence(MGReferenceMap *map,
                                    const MGSourcePhaseEvidence *evidence,
                                    uint16_t observed_column);
#endif
