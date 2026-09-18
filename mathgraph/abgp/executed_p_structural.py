"""Source-distinct structural persistence candidate for preregistered arm P.

This is DEV-only implementation qualification. It uses a frozen old observable
(first/last equality) for the retained Bayesian control and a constructed,
serializable parity-of-differences capability for treatment. The future carrier
uses different surface symbols, longer structures and a different serialization.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product
from typing import Any

from .executed_p import run_worker
from .manifest import derive_dev_seed


SOURCE_SCHEMA = 'source-symbol-sequence+label-v1'
FUTURE_SCHEMA = 'future-symbol-sequence-v1'
FUTURE_LENGTHS = (6, 8, 10, 12)


def _parity(symbols: list[str] | tuple[str, ...]) -> int:
    return sum(value != symbols[0] for value in symbols) & 1


def _source_examples(episode_index: int) -> tuple[list[dict[str, Any]], set[str], str]:
    seed = derive_dev_seed('P', 'structural-source', episode_index, 'abgp-p-structural-v1')
    tokens = (f'src_{seed[:10]}_u', f'src_{seed[:10]}_v')
    examples = []
    for bits in product((0, 1), repeat=4):
        sequence = [tokens[bit] for bit in bits]
        examples.append({'sequence': sequence, 'label': _parity(sequence)})
    return examples, set(tokens), seed


def _future_task(episode_index: int, context: int) -> dict[str, Any]:
    length = FUTURE_LENGTHS[context]
    seed = derive_dev_seed(
        'P', f'structural-future-context-{context}', episode_index, 'abgp-p-structural-v1'
    )
    tokens = (f'fut_{seed[:10]}_alpha', f'fut_{seed[:10]}_omega')
    # Force alternating parity classes while choosing positions from a sealed seed.
    diff_count = (2, 3, 4, 5)[context]
    positions = list(range(1, length))
    positions.sort(key=lambda position: sha256(f'{seed}|position|{position}'.encode()).hexdigest())
    changed = set(positions[:diff_count])
    symbols = [tokens[0]] + [tokens[1] if i in changed else tokens[0] for i in range(1, length)]
    return {
        'context_class': context,
        'length': length,
        'truth': _parity(symbols),
        'seed_digest': seed,
        'surface_tokens': list(tokens),
        'payload': {
            'schema': FUTURE_SCHEMA,
            'instance_id': f'future-{seed[12:28]}',
            'symbols': symbols,
        },
    }


def _all_correct(actions: list[int], truths: list[int]) -> int:
    return int(len(actions) == len(truths) and all(a == y for a, y in zip(actions, truths)))


def run_structural_p_episode(episode_index: int) -> dict[str, Any]:
    if type(episode_index) is not int or episode_index < 0:
        raise ValueError('episode_index must be nonnegative')
    examples, source_tokens, source_seed = _source_examples(episode_index)
    future_tasks = [_future_task(episode_index, context) for context in range(4)]
    truths = [task['truth'] for task in future_tasks]
    payloads = [task['payload'] for task in future_tasks]

    acquisition = run_worker(
        {'operation': 'acquire_structural', 'examples': examples},
        worker_kind='structural_acquisition',
    )
    retained = acquisition['retained']
    if retained is None:
        raise RuntimeError('structural acquisition failed to identify retained capability')
    old_posterior = run_worker(
        {'operation': 'old_posterior_from_source', 'examples': examples},
        worker_kind='structural_acquisition',
    )
    if old_posterior['source_history_digest'] != acquisition['source_history_digest']:
        raise AssertionError('treatment and old posterior did not receive identical source history')

    def invoke_many(obj):
        return [
            run_worker(
                {'operation': 'invoke_structural', 'retained': obj, 'task': payload},
                worker_kind='structural_invocation',
            )
            for payload in payloads
        ]

    retained_runs = invoke_many(retained)
    cold_runs = invoke_many(None)
    equal_recheck_runs = invoke_many(None)
    sham_runs = invoke_many(acquisition['sham'])
    wrong_runs = invoke_many(acquisition['wrong_class'])
    verbal_runs = invoke_many(acquisition['verbal_rule'])

    old_posterior_runs = [
        run_worker(
            {'operation': 'invoke_old_posterior',
             'posterior_counts': old_posterior['posterior_counts'], 'task': payload},
            worker_kind='structural_posterior',
        )
        for payload in payloads
    ]
    target_only_counts = {'equal': [1, 1], 'different': [1, 1]}
    target_only_runs = [
        run_worker(
            {'operation': 'invoke_old_posterior',
             'posterior_counts': target_only_counts, 'task': payload},
            worker_kind='structural_posterior',
        )
        for payload in payloads
    ]

    deletion = run_worker(
        {'operation': 'delete_structural', 'retained': retained, 'lineage': retained['lineage']},
        worker_kind='structural_invocation',
    )
    deleted_runs = invoke_many(deletion['retained'])

    reacquire = run_worker(
        {'operation': 'acquire_structural', 'examples': examples},
        worker_kind='structural_acquisition',
    )
    reacquired_runs = invoke_many(reacquire['retained'])

    actions = {
        'retained': [row['action'] for row in retained_runs],
        'cold': [row['action'] for row in cold_runs],
        'equal_compute_recheck': [row['action'] for row in equal_recheck_runs],
        'size_matched_sham': [row['action'] for row in sham_runs],
        'wrong_class_object': [row['action'] for row in wrong_runs],
        'verbal_rule_negative': [row['action'] for row in verbal_runs],
        'target_only_bisimulation_bayes': [row['action'] for row in target_only_runs],
        'old_posterior': [row['action'] for row in old_posterior_runs],
        'deleted': [row['action'] for row in deleted_runs],
        'reacquired': [row['action'] for row in reacquired_runs],
    }
    probe_scores = {
        name: [int(action == truth) for action, truth in zip(values, truths)]
        for name, values in actions.items()
    }
    scores = {name: _all_correct(values, truths) for name, values in actions.items()}

    future_tokens = set(token for task in future_tasks for token in task['surface_tokens'])
    future_instance_ids = {task['payload']['instance_id'] for task in future_tasks}
    source_distinctness = {
        'source_future_surface_tokens_disjoint': source_tokens.isdisjoint(future_tokens),
        'source_future_serialization_distinct': SOURCE_SCHEMA != FUTURE_SCHEMA,
        'source_future_exact_structures_distinct': all(task['length'] != 4 for task in future_tasks),
        'future_instance_ids_disjoint': len(future_instance_ids) == 4,
        'future_payload_contains_target_labels': any('label' in task['payload'] for task in future_tasks),
        'label_free_applicability': all(
            not row['applicability_used_target_label'] for row in retained_runs
        ),
        'source_seed_digest': source_seed,
        'future_seed_digests': [task['seed_digest'] for task in future_tasks],
    }

    return {
        'schema': 'abgp.executed-p-structural-episode.v1',
        'mode': 'DEV_MECHANISM_ONLY',
        'episode_index': episode_index,
        'inferential_unit': 'acquisition_restart_future_episode',
        'future_task_count': 4,
        'future_tasks': future_tasks,
        'acquisition': acquisition,
        'runs': {
            'retained': retained_runs,
            'cold': cold_runs,
            'equal_compute_recheck': equal_recheck_runs,
            'size_matched_sham': sham_runs,
            'wrong_class_object': wrong_runs,
            'verbal_rule_negative': verbal_runs,
            'target_only_bisimulation_bayes': target_only_runs,
            'old_posterior': old_posterior,
            'old_posterior_invocations': old_posterior_runs,
            'deletion': deletion,
            'deleted': deleted_runs,
            'reacquire': reacquire,
            'reacquired': reacquired_runs,
        },
        'probe_scores': probe_scores,
        'scores': scores,
        'source_distinctness': source_distinctness,
        'future_verifier_calls': sum(
            row['trace']['verifier_calls']
            for group in (retained_runs, cold_runs, equal_recheck_runs, sham_runs, wrong_runs,
                          verbal_runs, old_posterior_runs, target_only_runs, deleted_runs, reacquired_runs)
            for row in group
        ),
        'future_reconstruction_search_count': sum(
            row['trace']['candidate_checks'] for row in retained_runs
        ),
        'confirmatory_namespace_used': False,
    }


def run_structural_p_batch(
    episode_count: int, *, namespace: str = 'ABGP-DEV-v1'
) -> dict[str, Any]:
    if namespace != 'ABGP-DEV-v1':
        raise ValueError('structural P executor accepts only ABGP-DEV-v1')
    if type(episode_count) is not int or episode_count <= 0:
        raise ValueError('episode_count must be positive')
    episodes = [run_structural_p_episode(index) for index in range(episode_count)]
    retained = [episode['scores']['retained'] for episode in episodes]
    baselines = {
        'cold': [episode['scores']['cold'] for episode in episodes],
        'equal_compute_recheck': [episode['scores']['equal_compute_recheck'] for episode in episodes],
        'verbal_rule_negative': [episode['scores']['verbal_rule_negative'] for episode in episodes],
        'size_matched_sham': [episode['scores']['size_matched_sham'] for episode in episodes],
        'wrong_class_object': [episode['scores']['wrong_class_object'] for episode in episodes],
        'target_only_bisimulation_bayes': [
            episode['scores']['target_only_bisimulation_bayes'] for episode in episodes
        ],
        'posterior_only_retained_bayes': [episode['scores']['old_posterior'] for episode in episodes],
        'targeted_deletion': [episode['scores']['deleted'] for episode in episodes],
    }
    source_distinct = all(
        all((
            episode['source_distinctness']['source_future_surface_tokens_disjoint'],
            episode['source_distinctness']['source_future_serialization_distinct'],
            episode['source_distinctness']['source_future_exact_structures_distinct'],
            episode['source_distinctness']['future_instance_ids_disjoint'],
            not episode['source_distinctness']['future_payload_contains_target_labels'],
            episode['source_distinctness']['label_free_applicability'],
        ))
        for episode in episodes
    )
    restart_clean = all(
        row['sandbox']['seccomp_mode'] == 2
        and row['sandbox']['no_new_privs'] == 1
        and not row['acquisition_code_loaded']
        for episode in episodes
        for row in episode['runs']['retained']
    )
    zero_search = all(episode['future_reconstruction_search_count'] == 0 for episode in episodes)
    zero_verifier = all(episode['future_verifier_calls'] == 0 for episode in episodes)
    label_free = all(episode['source_distinctness']['label_free_applicability'] for episode in episodes)
    lineage_targeted = all(episode['runs']['deletion']['removed'] for episode in episodes)
    reacquired = [episode['scores']['reacquired'] for episode in episodes]
    return {
        'schema': 'abgp.executed-p-structural-batch.v1',
        'mode': 'DEV_MECHANISM_ONLY',
        'episodes': episodes,
        'analysis_input': {
            'inferential_unit': 'acquisition_restart_future_episode',
            'future_tasks_per_episode': 4,
            'primary_episode_rule': 'all_four_source_distinct_future_probes_correct',
            'retained': retained,
            'baselines': baselines,
            'hard_gates': {
                'executed_generation': True,
                'zero_verifier': zero_verifier,
                'zero_search': zero_search,
                'label_free': label_free,
                'source_distinct': source_distinct,
                'restart_clean': restart_clean,
                'lineage_targeted': lineage_targeted,
                'targeted_deletion': lineage_targeted,
            },
            'cold_accuracy': sum(baselines['cold']) / len(episodes),
            'post_deletion_accuracy': sum(baselines['targeted_deletion']) / len(episodes),
            'reacquisition_search_count': sum(
                episode['runs']['reacquire']['candidate_checks'] for episode in episodes
            ),
            'reacquisition_restored': reacquired == retained and all(reacquired),
        },
        'hard_gates': {
            'zero_verifier': zero_verifier,
            'zero_search': zero_search,
            'source_distinct': source_distinct,
            'restart_clean': restart_clean,
            'label_free': label_free,
            'lineage_targeted': lineage_targeted,
        },
        'confirmatory_namespace_used': False,
    }
