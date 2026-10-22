/* Exact four-hypothesis minimum witness planner for a synthetic spinning
 * single-column compass. Portable C99 with no libc, heap, or floating point.
 * The deliberately tiny grammar is not a general heading estimator.
 */
#include "finite_jitter_embedded.h"

typedef struct {
    uint32_t chosen;
    uint8_t count;
    uint8_t last;
} Cover;

static unsigned hamming16(uint16_t word)
{
    unsigned count = 0;
    while (word) {
        word = (uint16_t)(word & (uint16_t)(word - 1u));
        ++count;
    }
    return count;
}

static unsigned column_at(unsigned hypothesis, unsigned step, int offset)
{
    /* Add 64 to make negative signed offsets safe before applying modulo. */
    return (unsigned)((int)(hypothesis * 16u + step) + offset + 64) & 63u;
}

/* Compare ascending capture tuples of equal length and equal final step. */
static int lex_earlier(uint32_t proposed, uint32_t incumbent)
{
    unsigned step;
    for (step = 0; step < 32u; ++step) {
        uint32_t bit = (uint32_t)1u << step;
        if ((proposed & bit) != (incumbent & bit))
            return (proposed & bit) != 0u;
    }
    return 0;
}

static int preferable(Cover proposed, Cover incumbent)
{
    if (incumbent.count == 255u) return 1;
    if (proposed.count != incumbent.count)
        return proposed.count < incumbent.count;
    if (proposed.last != incumbent.last)
        return proposed.last < incumbent.last;
    return lex_earlier(proposed.chosen, incumbent.chosen);
}

static uint8_t first_selected(uint32_t chosen)
{
    unsigned step;
    for (step = 0; step < 32u; ++step)
        if (chosen & ((uint32_t)1u << step)) return (uint8_t)(step + 1u);
    return 0;
}

int mg_plan(const uint16_t reference[64], uint8_t candidate_mask,
            uint8_t first_step, uint8_t last_step,
            uint8_t noise_budget, uint8_t timing_jitter_bins, MGPlan *out)
{
    Cover current[64];
    unsigned pairs_a[6], pairs_b[6], npairs = 0;
    unsigned step, mask, a, b, j;
    uint8_t target;
    uint16_t comparisons = 0;

    if (out) {
        out->step_mask = 0;
        out->pair_checks = 0;
        out->cost = 0;
        out->first_step = 0;
        out->status = MG_INVALID;
    }
    if (!reference || !out || (candidate_mask & 0xf0u) ||
        first_step < 1u || last_step > 32u || first_step > last_step ||
        noise_budget > 16u || timing_jitter_bins > 3u) return -1;

    for (a = 0; a < 4u; ++a) {
        if (!(candidate_mask & (1u << a))) continue;
        for (b = a + 1u; b < 4u; ++b) {
            if (!(candidate_mask & (1u << b))) continue;
            pairs_a[npairs] = a;
            pairs_b[npairs] = b;
            ++npairs;
        }
    }
    if (npairs == 0u) {
        out->status = candidate_mask ? MG_ALREADY_UNIQUE : MG_NO_CANDIDATES;
        return 0;
    }

    target = (uint8_t)((1u << npairs) - 1u);
    for (mask = 0; mask < 64u; ++mask) {
        current[mask].chosen = 0u;
        current[mask].count = 255u;
        current[mask].last = 0u;
    }
    current[0].count = 0u;

    for (step = first_step; step <= last_step; ++step) {
        uint8_t separated = 0u;
        for (j = 0u; j < npairs; ++j) {
            int offset_a, offset_b;
            int disjoint = 1;
            for (offset_a = -(int)timing_jitter_bins;
                 offset_a <= (int)timing_jitter_bins; ++offset_a) {
                uint16_t left = reference[column_at(pairs_a[j], step, offset_a)];
                for (offset_b = -(int)timing_jitter_bins;
                     offset_b <= (int)timing_jitter_bins; ++offset_b) {
                    uint16_t right = reference[column_at(pairs_b[j], step, offset_b)];
                    ++comparisons;
                    if (hamming16((uint16_t)(left ^ right)) <=
                        2u * (unsigned)noise_budget) disjoint = 0;
                }
            }
            if (disjoint) separated = (uint8_t)(separated | (1u << j));
        }
        if (separated) {
            /* OR only adds mask bits. Descending in-place traversal therefore
             * never consumes an entry created at this step, avoiding a second
             * 64-entry DP table and keeping stack usage bounded.
             */
            for (mask = 64u; mask-- > 0u;) {
                unsigned combined;
                Cover proposed;
                if (current[mask].count == 255u) continue;
                combined = mask | separated;
                proposed.chosen = current[mask].chosen | ((uint32_t)1u << (step - 1u));
                proposed.count = (uint8_t)(current[mask].count + 1u);
                proposed.last = (uint8_t)step;
                if (preferable(proposed, current[combined])) current[combined] = proposed;
            }
        }
    }

    out->pair_checks = comparisons;
    if (current[target].count == 255u) {
        out->status = MG_BOUNDED_OBSTRUCTION;
    } else {
        out->step_mask = current[target].chosen;
        out->cost = current[target].count;
        out->first_step = first_selected(out->step_mask);
        out->status = MG_SEPARATING_SET;
    }
    return 0;
}

uint8_t mg_filter(const uint16_t reference[64], uint8_t candidate_mask,
                  uint8_t step, uint16_t actual_column,
                  uint8_t noise_budget, uint8_t timing_jitter_bins)
{
    unsigned hypothesis;
    uint8_t survivors = 0u;
    if (!reference || (candidate_mask & 0xf0u) || step < 1u || step > 32u ||
        noise_budget > 16u || timing_jitter_bins > 3u) return 0u;
    for (hypothesis = 0u; hypothesis < 4u; ++hypothesis) {
        int offset;
        if (!(candidate_mask & (1u << hypothesis))) continue;
        for (offset = -(int)timing_jitter_bins;
             offset <= (int)timing_jitter_bins; ++offset) {
            unsigned index = column_at(hypothesis, step, offset);
            if (hamming16((uint16_t)(actual_column ^ reference[index])) <=
                noise_budget) {
                survivors = (uint8_t)(survivors | (1u << hypothesis));
                break;
            }
        }
    }
    return survivors;
}

uint16_t mg_reference_bytes(void)
{
    return (uint16_t)(64u * sizeof(uint16_t));
}
