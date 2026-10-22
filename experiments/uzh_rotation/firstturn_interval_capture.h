/* Bounded first-revolution gyro/timestamp phase assignment for a 64-bin map.
 * The declared +/- uncertainty MUST be calibrated independently; this adapter
 * cannot authenticate gyro calibration, clock synchronization or scene identity.
 */
#ifndef MATHGRAPH_FIRSTTURN_INTERVAL_CAPTURE_H
#define MATHGRAPH_FIRSTTURN_INTERVAL_CAPTURE_H

#include "finite_partial_map.h"

enum { MG_FIRSTTURN_UNCERTAIN = 2, MG_FIRSTTURN_TICKS_PER_TURN = 1024 };

/* estimated_phase is in [0,1023], with 16 sub-bin ticks per reference bin.
 * max_phase_error is an external inclusive bound on absolute phase error,
 * not a measurement inferred from image matching. Map mutation occurs ONLY
 * if every possible physical phase belongs to one bin. On uncertainty return
 * MG_FIRSTTURN_UNCERTAIN, preserve the map, and request another observation.
 * Otherwise forward mg_map_capture's 0/1/-2 returns; -1 means invalid input,
 * frozen map, or missing pointer. Caller must freeze after its first revolution.
 */
int mg_firstturn_capture_interval(MGReferenceMap *map,
                                  uint16_t estimated_phase,
                                  uint16_t max_phase_error,
                                  uint16_t column);

#endif
