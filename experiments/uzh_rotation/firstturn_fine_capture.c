/* Fine 16-bit phase capture for the existing 64-bin MathGraph map.
 * NO new persistent map fields or visual authority assumptions.
 * 65536 phase ticks / 64 bins = 1024 ticks per bin.
 */
#include "firstturn_fine_capture.h"

int mg_firstturn_capture_fine_interval(MGReferenceMap *map,
                                       uint16_t estimated_phase,
                                       uint16_t max_phase_error,
                                       uint16_t column)
{
    unsigned lower, upper;
    if (!map || map->frozen)
        return -1;
    /* An inclusive interval of 2*radius+1 ticks cannot fit in 1024
     * discrete ticks when radius >= 512. Do not accept on wraparound.
     */
    if (max_phase_error >= 512u)
        return MG_FIRSTTURN_UNCERTAIN;
    lower = ((unsigned)estimated_phase + 65536u -
             (unsigned)max_phase_error) % 65536u;
    upper = ((unsigned)estimated_phase + (unsigned)max_phase_error) % 65536u;
    if (lower / 1024u != upper / 1024u)
        return MG_FIRSTTURN_UNCERTAIN;
    return mg_map_capture(map, (uint8_t)(lower / 1024u), column);
}
