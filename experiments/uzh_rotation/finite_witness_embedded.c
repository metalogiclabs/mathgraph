#include "finite_witness_embedded.h"
#include <string.h>

#define MGW_DP_STATES 64u
#define MGW_UNREACHABLE 255u

static uint8_t bit_count16(uint16_t value) {
    uint8_t count = 0u;
    while (value != 0u) {
        value = (uint16_t)(value & (uint16_t)(value - 1u));
        ++count;
    }
    return count;
}

static int valid_hypotheses(const uint8_t *h, uint8_t n) {
    uint8_t i, j;
    if (n > MGW_MAX_HYPOTHESES) return 0;
    for (i = 0u; i < n; ++i) {
        if (h[i] >= MGW_MAP_BINS) return 0;
        for (j = 0u; j < i; ++j) {
            if (h[i] == h[j]) return 0;
        }
    }
    return 1;
}

static uint8_t last_step(uint32_t bits) {
    uint8_t i;
    for (i = MGW_MAX_HORIZON; i > 0u; --i) {
        if ((bits & ((uint32_t)1u << (i - 1u))) != 0u) return i;
    }
    return 0u;
}

/* Same-cardinality/last-step tie: earlier ordered step tuple wins. */
static int is_better(uint8_t candidate_cost, uint32_t candidate_bits,
                     uint8_t prior_cost, uint32_t prior_bits) {
    uint8_t i;
    if (candidate_cost < prior_cost) return 1;
    if (candidate_cost > prior_cost) return 0;
    if (last_step(candidate_bits) < last_step(prior_bits)) return 1;
    if (last_step(candidate_bits) > last_step(prior_bits)) return 0;
    for (i = 1u; i <= MGW_MAX_HORIZON; ++i) {
        uint32_t flag = (uint32_t)1u << (i - 1u);
        if ((candidate_bits & flag) != (prior_bits & flag))
            return (candidate_bits & flag) != 0u;
    }
    return 0;
}

static uint8_t pair_cover_for_step(
        const uint16_t *sig, const uint8_t *present, const uint8_t *h,
        uint8_t n, uint8_t s, uint8_t total_hamming_error) {
    uint8_t i, j, pair = 0u, covered = 0u;
    for (i = 0u; i < n; ++i) {
        for (j = (uint8_t)(i + 1u); j < n; ++j) {
            uint8_t ia = (uint8_t)((h[i] + s) % MGW_MAP_BINS);
            uint8_t ib = (uint8_t)((h[j] + s) % MGW_MAP_BINS);
            if (present[ia] != 0u && present[ib] != 0u &&
                bit_count16((uint16_t)(sig[ia] ^ sig[ib])) >
                    (uint8_t)(2u * total_hamming_error))
                covered = (uint8_t)(covered | ((uint8_t)1u << pair));
            ++pair;
        }
    }
    return covered;
}

int mgw_plan(const uint16_t signature[MGW_MAP_BINS],
             const uint8_t present[MGW_MAP_BINS],
             const uint8_t hypotheses[MGW_MAX_HYPOTHESES],
             uint8_t candidate_count, uint8_t first_future_step,
             uint8_t horizon, uint8_t total_hamming_error,
             mgw_plan_t *result) {
    uint8_t cost[MGW_DP_STATES], previous_cost[MGW_DP_STATES];
    uint32_t bits[MGW_DP_STATES], previous_bits[MGW_DP_STATES];
    uint8_t pairs, full, step, mask, count, p;
    if (signature == 0 || present == 0 || hypotheses == 0 || result == 0 ||
        !valid_hypotheses(hypotheses, candidate_count) ||
        horizon == 0u || horizon > MGW_MAX_HORIZON ||
        first_future_step == 0u || total_hamming_error > 2u)
        return -1;
    memset(result, 0, sizeof(*result));
    if (candidate_count == 0u) {
        result->status = MGW_NO_CANDIDATES;
        return 0;
    }
    if (candidate_count == 1u) {
        result->status = MGW_ALREADY_UNIQUE;
        return 0;
    }
    pairs = (uint8_t)(candidate_count * (candidate_count - 1u) / 2u);
    result->candidate_pairs = pairs;
    full = (uint8_t)(((uint8_t)1u << pairs) - 1u);
    for (mask = 0u; mask < MGW_DP_STATES; ++mask) {
        cost[mask] = MGW_UNREACHABLE;
        bits[mask] = 0u;
    }
    cost[0] = 0u;
    for (step = first_future_step; step <= horizon; ++step) {
        uint8_t coverage = pair_cover_for_step(signature, present, hypotheses,
                                                candidate_count, step,
                                                total_hamming_error);
        if (coverage == 0u) continue;
        memcpy(previous_cost, cost, sizeof(cost));
        memcpy(previous_bits, bits, sizeof(bits));
        for (mask = 0u; mask < MGW_DP_STATES; ++mask) {
            uint8_t next;
            uint32_t chosen;
            if (previous_cost[mask] == MGW_UNREACHABLE) continue;
            next = (uint8_t)(mask | coverage);
            chosen = previous_bits[mask] | ((uint32_t)1u << (step - 1u));
            count = (uint8_t)(previous_cost[mask] + 1u);
            if (is_better(count, chosen, cost[next], bits[next])) {
                cost[next] = count;
                bits[next] = chosen;
            }
        }
    }
    if (cost[full] == MGW_UNREACHABLE) {
        result->status = MGW_BOUNDED_OBSTRUCTION;
        return 0;
    }
    result->status = MGW_SEPARATING_SET;
    result->minimum_total_reads = cost[full];
    result->selected_steps_bits = bits[full];
    for (p = 1u; p <= horizon; ++p) {
        if ((bits[full] & ((uint32_t)1u << (p - 1u))) != 0u) {
            result->next_step = p;
            break;
        }
    }
    return 0;
}

int mgw_filter(const uint16_t signature[MGW_MAP_BINS],
               const uint8_t present[MGW_MAP_BINS],
               const uint8_t hypotheses[MGW_MAX_HYPOTHESES],
               uint8_t candidate_count, uint8_t observed_step,
               uint16_t observed_column, uint8_t total_hamming_error,
               uint8_t out[MGW_MAX_HYPOTHESES], uint8_t *out_count) {
    uint8_t i, n = 0u;
    if (signature == 0 || present == 0 || hypotheses == 0 ||
        out == 0 || out_count == 0 ||
        !valid_hypotheses(hypotheses, candidate_count) ||
        observed_step == 0u || observed_step > MGW_MAX_HORIZON ||
        total_hamming_error > 2u)
        return -1;
    for (i = 0u; i < candidate_count; ++i) {
        uint8_t index = (uint8_t)((hypotheses[i] + observed_step) % MGW_MAP_BINS);
        /* Missing bins cannot falsify a candidate; preserve UNKNOWN. */
        if (present[index] == 0u ||
            bit_count16((uint16_t)(signature[index] ^ observed_column))
                <= total_hamming_error)
            out[n++] = hypotheses[i];
    }
    *out_count = n;
    return 0;
}
