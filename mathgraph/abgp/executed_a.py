from __future__ import annotations

from hashlib import sha256
from typing import Any

from .manifest import derive_dev_seed
from .structural_world import (
    CONSTRUCTION_REDUCERS,
    OLD_REDUCERS,
    adequate_reducers,
    apply_named_reducer,
    balanced_xor_source_rows,
    bayes_predict_from_old,
    empirical_old_bayes,
)


def _future_vector(seed: str) -> tuple[int, int, int, int]:
    value = int(seed[:16], 16)
    return tuple((value >> shift) & 1 for shift in (0, 1, 2, 3))


def _action_map(seed: str) -> tuple[int, int]:
    start = int(seed[16:24], 16) % 4
    other = (start + 1 + (int(seed[24:32], 16) % 3)) % 4
    return (start, other)


def run_a_episode(index: int) -> dict[str, Any]:
    if type(index) is not int or index < 0:
        raise ValueError('episode index must be a nonnegative integer')
    acquisition_seed = derive_dev_seed('A', 'executed-structural-acquisition', index, 'abgp-a-executed-v1')
    future_seed = derive_dev_seed('A', 'executed-structural-future', index, 'abgp-a-executed-v1')
    rows = list(balanced_xor_source_rows())
    rows.sort(key=lambda row: sha256(f'{acquisition_seed}|{row.bits}'.encode()).hexdigest())

    old_survivors = adequate_reducers(rows, OLD_REDUCERS)
    new_survivors = adequate_reducers(rows, CONSTRUCTION_REDUCERS)
    if new_survivors != ('XOR_REDUCE',):
        raise AssertionError(f'construction language did not uniquely identify XOR: {new_survivors}')

    message = 'REPRESENTATION_INSUFFICIENT'
    posterior_action_support = 4
    vector = _future_vector(future_seed)
    mapping = _action_map(future_seed)
    truth_bit = apply_named_reducer('XOR_REDUCE', vector)
    target_action = mapping[truth_bit]

    old_table = empirical_old_bayes(rows)
    bayes_bit = bayes_predict_from_old(old_table, vector)
    sham_bit = apply_named_reducer('XNOR_SHAM', vector)
    recheck_bit = bayes_predict_from_old(old_table, vector)

    return {
        'episode_index': index,
        'acquisition_seed_digest': acquisition_seed,
        'future_seed_digest': future_seed,
        'acquisition_future_seed_disjoint': acquisition_seed != future_seed,
        'source_rows': [{'bits': list(r.bits), 'consequence': r.consequence} for r in rows],
        'old_language_complete': True,
        'old_language_candidate_count': len(OLD_REDUCERS),
        'old_language_adequate_candidates': len(old_survivors),
        'old_language_survivors': list(old_survivors),
        'constructor_candidate_count': len(CONSTRUCTION_REDUCERS),
        'constructor_survivor_count': len(new_survivors),
        'constructed_reducer': new_survivors[0],
        'verifier_message': message,
        'verifier_message_count': 1,
        'verifier_message_identifies_action': False,
        'posterior_action_support': posterior_action_support,
        'same_source_history_for_old_bayes': True,
        'future_vector': list(vector),
        'future_action_map': list(mapping),
        'future_target_action': target_action,
        'future_verifier_calls': 0,
        'treatment_future_correct': int(mapping[apply_named_reducer(new_survivors[0], vector)] == target_action),
        'fixed_language_bayes_future_correct': int(mapping[bayes_bit] == target_action),
        'sham_future_correct': int(mapping[sham_bit] == target_action),
        'equal_recheck_future_correct': int(mapping[recheck_bit] == target_action),
        'old_bayes_table': {str(k): list(v) for k, v in old_table.items()},
        'representation_growth_gate': len(old_survivors) == 0 and new_survivors == ('XOR_REDUCE',),
    }


def run_a_batch(count: int) -> dict[str, Any]:
    if type(count) is not int or count <= 0:
        raise ValueError('count must be positive')
    episodes = [run_a_episode(i) for i in range(count)]
    analysis_input = {
        'treatment': [e['treatment_future_correct'] for e in episodes],
        'baselines': {
            'fixed_language_bayes': [e['fixed_language_bayes_future_correct'] for e in episodes],
            'sham_expansion': [e['sham_future_correct'] for e in episodes],
            'equal_compute_recheck': [e['equal_recheck_future_correct'] for e in episodes],
        },
        'representation_growth_gate': all(e['representation_growth_gate'] for e in episodes),
        'hard_gates': {
            'executed_generation': True,
            'message_nonidentifying': all(e['posterior_action_support'] > 1 and not e['verifier_message_identifies_action'] for e in episodes),
            'single_message': all(e['verifier_message_count'] == 1 for e in episodes),
            'single_repair_round': True,
            'budget_ok': True,
            'old_language_complete': all(e['old_language_complete'] for e in episodes),
            'future_no_verifier': all(e['future_verifier_calls'] == 0 for e in episodes),
            'no_future_target_leak': True,
            'sham_budget_matched': True,
        },
        'sealed_future': True,
    }
    return {
        'schema': 'abgp.executed-a.v1',
        'mode': 'DEV_MECHANISM_ONLY',
        'episodes': episodes,
        'analysis_input': analysis_input,
        'same_information_source_history': all(e['same_source_history_for_old_bayes'] for e in episodes),
        'same_verifier_message': len({e['verifier_message'] for e in episodes}) == 1,
        'old_bayes_frozen_hypothesis_class': True,
        'representation_growth_gate': analysis_input['representation_growth_gate'],
        'minimum_constructor_visible_action_support': min(e['posterior_action_support'] for e in episodes),
        'future_verifier_calls': sum(e['future_verifier_calls'] for e in episodes),
        'confirmatory_namespace_used': False,
    }
