/* Alternative high-precision source-bound first-turn map capture.
 * The caller supplies an EXTERNALLY JUSTIFIED inclusive phase-error radius;
 * a publisher's nominal sensor time shift is NOT such a justification.
 * Captures no more authority than the finite interval declared by caller.
 */
#ifndef MATHGRAPH_FIRSTTURN_FINE_CAPTURE_H
#define MATHGRAPH_FIRSTTURN_FINE_CAPTURE_H

#include <stdint.h>
#include "firstturn_interval_capture.h"

/* estimated_phase: full uint16_t angular circle, 0 .. 65535.
 * max_phase_error: inclusive uint16_t ticks on BOTH sides.
 * Return MG_FIRSTTURN_UNCERTAIN=2 if interval crosses any one of 64
 * 1024-subtick bins or is too wide; map is never mutated in that case.
 * Otherwise delegate to the UNCHANGED mg_map_capture() implementation.
 */
int mg_firstturn_capture_fine_interval(MGReferenceMap *map,
                                       uint16_t estimated_phase,
                                       uint16_t max_phase_error,
                                       uint16_t column);
#endif
