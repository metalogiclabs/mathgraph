#include "finite_partial_map.h"

typedef struct {
    uint32_t chosen;
    uint8_t count;
    uint8_t last;
} SparseCover;

static unsigned popcount16(uint16_t word)
{
    unsigned count = 0;
    while (word) {
        word = (uint16_t)(word & (uint16_t)(word - 1u));
        ++count;
    }
    return count;
}

static int observed(const MGReferenceMap *map, unsigned bin)
{
    return (map->seen[bin / 8u] & (1u << (bin & 7u))) != 0u;
}

static unsigned bin_for(unsigned hypothesis, unsigned step, int delta)
{
    return (unsigned)((int)(hypothesis * 16u + step) + delta + 64) & 63u;
}

void mg_map_init(MGReferenceMap *map)
{
    unsigned bin;
    if (!map) return;
    for (bin = 0u; bin < 64u; ++bin) map->columns[bin] = 0u;
    for (bin = 0u; bin < 8u; ++bin) {
        map->seen[bin] = 0u;
        map->quarantined[bin] = 0u;
    }
    map->count = 0u;
    map->frozen = 0u;
}

uint8_t mg_map_has(const MGReferenceMap *map, uint8_t angular_bin)
{
    if (!map || angular_bin >= 64u) return 0u;
    return (uint8_t)observed(map, angular_bin);
}

int mg_map_capture(MGReferenceMap *map, uint8_t angular_bin, uint16_t column)
{
    uint8_t bit;
    unsigned byte;
    if (!map || map->frozen || angular_bin >= 64u) return -1;
    byte = angular_bin / 8u;
    bit = (uint8_t)(1u << (angular_bin & 7u));
    if (map->quarantined[byte] & bit) return -2;
    if (map->seen[byte] & bit) {
        if (popcount16((uint16_t)(map->columns[angular_bin] ^ column)) <= 2u)
            return 1;
        map->seen[byte] = (uint8_t)(map->seen[byte] & (uint8_t)~bit);
        map->quarantined[byte] = (uint8_t)(map->quarantined[byte] | bit);
        --map->count;
        return -2;
    }
    map->columns[angular_bin] = column;
    map->seen[byte] = (uint8_t)(map->seen[byte] | bit);
    ++map->count;
    return 0;
}

int mg_map_freeze(MGReferenceMap *map)
{
    if (!map) return -1;
    if (map->frozen) return 1;
    map->frozen = 1u;
    return 0;
}

static int lex_preferred(uint32_t proposal, uint32_t incumbent)
{
    unsigned bit;
    for (bit = 0u; bit < 32u; ++bit) {
        uint32_t flag = (uint32_t)1u << bit;
        if ((proposal & flag) != (incumbent & flag))
            return (proposal & flag) != 0u;
    }
    return 0;
}

static int better(SparseCover proposed, SparseCover incumbent)
{
    if (incumbent.count == 255u) return 1;
    if (proposed.count != incumbent.count)
        return proposed.count < incumbent.count;
    if (proposed.last != incumbent.last)
        return proposed.last < incumbent.last;
    return lex_preferred(proposed.chosen, incumbent.chosen);
}

static uint8_t first_bit(uint32_t flags)
{
    unsigned step;
    for (step = 0u; step < 32u; ++step)
        if (flags & ((uint32_t)1u << step)) return (uint8_t)(step + 1u);
    return 0u;
}

int mg_sparse_plan(const MGReferenceMap *map, uint8_t candidate_mask,
                   uint8_t first_step, uint8_t last_step,
                   uint8_t noise_budget, uint8_t timing_jitter_bins, MGPlan *out)
{
    SparseCover states[64];
    unsigned left[6], right[6], pair_count = 0u;
    unsigned i, j, step, k, mask;
    uint16_t checks = 0u;
    uint8_t target;
    if (out) {
        out->step_mask = 0u;
        out->pair_checks = 0u;
        out->cost = 0u;
        out->first_step = 0u;
        out->status = MG_INVALID;
    }
    if (!map || !map->frozen || !out || (candidate_mask & 0xf0u) ||
        first_step < 1u || last_step > 32u || first_step > last_step ||
        noise_budget > 16u || timing_jitter_bins > 3u) return -1;
    for (i = 0u; i < 4u; ++i) {
        if (!(candidate_mask & (1u << i))) continue;
        for (j = i + 1u; j < 4u; ++j) {
            if (!(candidate_mask & (1u << j))) continue;
            left[pair_count] = i;
            right[pair_count] = j;
            ++pair_count;
        }
    }
    if (!pair_count) {
        out->status = candidate_mask ? MG_ALREADY_UNIQUE : MG_NO_CANDIDATES;
        return 0;
    }
    target = (uint8_t)((1u << pair_count) - 1u);
    for (mask = 0u; mask < 64u; ++mask) {
        states[mask].chosen = 0u;
        states[mask].last = 0u;
        states[mask].count = 255u;
    }
    states[0].count = 0u;
    for (step = first_step; step <= last_step; ++step) {
        uint8_t separated = 0u;
        for (k = 0u; k < pair_count; ++k) {
            int da, db;
            int disjoint = 1;
            for (da = -(int)timing_jitter_bins; da <= (int)timing_jitter_bins; ++da) {
                unsigned a = bin_for(left[k], step, da);
                for (db = -(int)timing_jitter_bins;
                     db <= (int)timing_jitter_bins; ++db) {
                    unsigned b = bin_for(right[k], step, db);
                    if (!observed(map, a) || !observed(map, b)) {
                        disjoint = 0;
                    } else {
                        ++checks;
                        if (popcount16((uint16_t)(map->columns[a] ^ map->columns[b])) <=
                            2u * (unsigned)noise_budget) disjoint = 0;
                    }
                }
            }
            if (disjoint) separated = (uint8_t)(separated | (1u << k));
        }
        if (separated) {
            /* Adding bits strictly increases a cover mask. Reverse iteration
             * prevents selecting the same capture step more than once.
             */
            for (mask = 64u; mask-- > 0u;) {
                unsigned combined;
                SparseCover proposal;
                if (states[mask].count == 255u) continue;
                combined = mask | separated;
                proposal.chosen = states[mask].chosen | ((uint32_t)1u << (step - 1u));
                proposal.count = (uint8_t)(states[mask].count + 1u);
                proposal.last = (uint8_t)step;
                if (better(proposal, states[combined])) states[combined] = proposal;
            }
        }
    }
    out->pair_checks = checks;
    if (states[target].count == 255u) {
        out->status = MG_BOUNDED_OBSTRUCTION;
    } else {
        out->status = MG_SEPARATING_SET;
        out->step_mask = states[target].chosen;
        out->cost = states[target].count;
        out->first_step = first_bit(states[target].chosen);
    }
    return 0;
}

uint8_t mg_sparse_filter(const MGReferenceMap *map, uint8_t candidate_mask,
                         uint8_t step, uint16_t column,
                         uint8_t noise_budget, uint8_t timing_jitter_bins)
{
    uint8_t retained = 0u;
    unsigned candidate;
    if (!map || !map->frozen || (candidate_mask & 0xf0u) ||
        step < 1u || step > 32u || noise_budget > 16u ||
        timing_jitter_bins > 3u) return 0u;
    for (candidate = 0u; candidate < 4u; ++candidate) {
        int delta;
        if (!(candidate_mask & (1u << candidate))) continue;
        for (delta = -(int)timing_jitter_bins;
             delta <= (int)timing_jitter_bins; ++delta) {
            unsigned angular_bin = bin_for(candidate, step, delta);
            if (!observed(map, angular_bin) ||
                popcount16((uint16_t)(column ^ map->columns[angular_bin])) <=
                noise_budget) {
                retained = (uint8_t)(retained | (1u << candidate));
                break;
            }
        }
    }
    return retained;
}

/* Is there an admissible column under source hypothesis a that would
 * EXCLUDE hypothesis b? This is existential, not a worst-case guarantee.
 * Even a single missing target-map offset prevents such exclusion.
 */
static int possible_direction(const MGReferenceMap *map, unsigned a, unsigned b,
                              unsigned step, unsigned noise, unsigned jitter,
                              uint16_t *checks)
{
    int da, db;
    for (da = -(int)jitter; da <= (int)jitter; ++da) {
        unsigned ia = bin_for(a, step, da);
        int disjoint = 1;
        if (!observed(map, ia)) continue;
        for (db = -(int)jitter; db <= (int)jitter; ++db) {
            unsigned ib = bin_for(b, step, db);
            if (!observed(map, ib)) {
                disjoint = 0;
            } else {
                ++*checks;
                if (popcount16((uint16_t)(map->columns[ia] ^ map->columns[ib])) <=
                    2u * noise) disjoint = 0;
            }
        }
        if (disjoint) return 1;
    }
    return 0;
}

int mg_sparse_next_probe(const MGReferenceMap *map, uint8_t candidate_mask,
                         uint8_t first_step, uint8_t last_step,
                         uint8_t noise_budget, uint8_t timing_jitter_bins,
                         MGPlan *out)
{
    uint16_t extra_checks = 0u;
    unsigned step, a, b;
    unsigned max_score = 0u, best_step = 0u;
    int status = mg_sparse_plan(map, candidate_mask, first_step, last_step,
                                noise_budget, timing_jitter_bins, out);
    if (status != 0 || out->status != MG_BOUNDED_OBSTRUCTION) return status;
    for (step = first_step; step <= last_step; ++step) {
        unsigned score = 0u;
        for (a = 0u; a < 4u; ++a) {
            if (!(candidate_mask & (1u << a))) continue;
            for (b = a + 1u; b < 4u; ++b) {
                if (!(candidate_mask & (1u << b))) continue;
                score += (unsigned)possible_direction(map,a,b,step,noise_budget,
                                                       timing_jitter_bins,&extra_checks);
                score += (unsigned)possible_direction(map,b,a,step,noise_budget,
                                                       timing_jitter_bins,&extra_checks);
            }
        }
        if (score > max_score) {
            max_score = score;
            best_step = step;
        }
    }
    out->pair_checks = (uint16_t)(out->pair_checks + extra_checks);
    if (max_score) {
        out->status = MG_POTENTIAL_PROBE;
        out->cost = 1u;
        out->step_mask = (uint32_t)1u << (best_step - 1u);
        out->first_step = (uint8_t)best_step;
    }
    return 0;
}
