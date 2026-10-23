/* Fail-closed first-turn observation/evidence permission boundary.
 * No persistent map memory, no heap, no raw sensor claims.
 */
#include "firstturn_source_obligation.h"

int mg_source_firstturn_obligation(const MGReferenceMap *map,
                                   const MGSourcePhaseEvidence *evidence,
                                   uint8_t *out_bin)
{
    unsigned low, high, bin, error;
    uint8_t mask;
    if (!out_bin) return -1;
    *out_bin = 255u;
    if (!map || map->frozen || !evidence) return -1;
    if (evidence->source_epoch_authenticated_externally != 1u)
        return MG_OBLIGATION_SOURCE_EPOCH;
    if (evidence->within_first_revolution != 1u)
        return MG_OBLIGATION_FIRST_TURN;
    if (evidence->clock_error_bound_authenticated_externally != 1u)
        return MG_OBLIGATION_CLOCK_BOUND;
    if (evidence->gyro_error_bound_authenticated_externally != 1u)
        return MG_OBLIGATION_GYRO_BOUND;

    error = evidence->externally_bounded_error_ticks;
    if (error >= 512u) return MG_OBLIGATION_PHASE_UNCERTAIN;
    low = ((unsigned)evidence->reported_phase_65536 + 65536u - error) % 65536u;
    high = ((unsigned)evidence->reported_phase_65536 + error) % 65536u;
    if (low / 1024u != high / 1024u) return MG_OBLIGATION_PHASE_UNCERTAIN;

    bin = low / 1024u;
    mask = (uint8_t)(1u << (bin & 7u));
    if ((map->quarantined[bin / 8u] & mask) != 0u)
        return MG_OBLIGATION_REFERENCE_QUARANTINED;
    if (mg_map_has(map,(uint8_t)bin))
        return MG_OBLIGATION_COLUMN_ALREADY_PRESENT;
    *out_bin = (uint8_t)bin;
    return MG_OBLIGATION_ACQUIRE_COLUMN;
}

int mg_source_capture_with_evidence(MGReferenceMap *map,
                                    const MGSourcePhaseEvidence *evidence,
                                    uint16_t observed_column)
{
    uint8_t bin;
    int obligation = mg_source_firstturn_obligation(map, evidence, &bin);
    if (obligation != MG_OBLIGATION_ACQUIRE_COLUMN) return obligation;
    /* Rechecks the entire inclusive phase interval with the unchanged fine
     * kernel before writing. Only then calls the existing map capture.
     */
    return mg_firstturn_capture_fine_interval(
        map, evidence->reported_phase_65536,
        evidence->externally_bounded_error_ticks, observed_column);
}
