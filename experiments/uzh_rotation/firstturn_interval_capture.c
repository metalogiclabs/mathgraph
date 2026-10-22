#include "firstturn_interval_capture.h"

int mg_firstturn_capture_interval(MGReferenceMap *map,
                                  uint16_t estimated_phase,
                                  uint16_t max_phase_error,
                                  uint16_t column)
{
    unsigned lower, upper;
    if (!map || map->frozen || estimated_phase >= MG_FIRSTTURN_TICKS_PER_TURN)
        return -1;
    /* A closed interval of >=17 phase ticks necessarily crosses a bin edge.
     * Reject without map writes even when its endpoints wrap to the same bin.
     */
    if (max_phase_error >= 8u) return MG_FIRSTTURN_UNCERTAIN;
    lower = ((unsigned)estimated_phase + MG_FIRSTTURN_TICKS_PER_TURN -
             (unsigned)max_phase_error) % MG_FIRSTTURN_TICKS_PER_TURN;
    upper = ((unsigned)estimated_phase + (unsigned)max_phase_error) %
            MG_FIRSTTURN_TICKS_PER_TURN;
    if (lower / 16u != upper / 16u) return MG_FIRSTTURN_UNCERTAIN;
    return mg_map_capture(map, (uint8_t)(lower / 16u), column);
}
