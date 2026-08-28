import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

v27 = load('v27', 'run_v27_developmental_state_quotient.py')
v23 = v27.v23
v19 = v27.v19
v13 = v27.v13
SOURCE = v27.SOURCE
TARGET = v27.TARGET
MAXQ = v27.MAXQ

# V28 isolates the unexpected V27 RAW_HISTORY effect.  It adds no new
# observation, policy feature, task family, or target-derived rule.  Genuine and
# sham source experience each produce a retained multiset of executable
# observation atoms using exactly V27's source learner.  On the frozen target,
# both arms use exactly the same budgeted transfer rule: while a retained atom
# exists that separates the verifier-returned residual, choose the deterministic
# SHA-order match; otherwise fall back to frozen V19.  Only the source history
# that selected the retained atom set differs.

def summarize_atoms(xs):
    c = Counter(xs)
    return {
        'total_occurrences': len(xs),
        'unique_atoms': len(c),
        'atoms': [{'atom': k, 'count': c[k]} for k in sorted(c)],
    }


def make_arm(states, keys, demo, held, source_atoms):
    ch, tr, hits = v27.run_raw_budgeted(states, keys, demo, source_atoms)
    return v27.arm(states, ch, tr, hits, demo, held)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v28_reusable_observation_transfer.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])

    true_model = v27.learn_quotient(ev, sham=False)
    sham_model = v27.learn_quotient(ev, sham=True)
    true_atoms = list(true_model['source_atoms'])
    sham_atoms = list(sham_model['source_atoms'])

    states, keys, demo, held = v23.prepare(ev[TARGET])
    warm = make_arm(states, keys, demo, held, true_atoms)
    sham = make_arm(states, keys, demo, held, sham_atoms)
    cc, ct = v19.run_history(states, keys, demo, False)
    cold = v27.arm(states, cc, ct, 0, demo, held)

    # Set-ablation preserves the target algorithm and budget but removes all
    # retained source atoms, reducing exactly to frozen V19 COLD.
    arms = {
        'WARM_TRUE_SOURCE_ATOMS': warm,
        'SHAM_SOURCE_ATOMS': sham,
        'COLD': cold,
        'ABLATION': dict(cold),
    }

    true_set = set(true_atoms)
    sham_set = set(sham_atoms)
    target_key_set = set(keys)
    overlap = {
        'true_vs_sham_unique_intersection': len(true_set & sham_set),
        'true_target_literal_support': len(true_set & target_key_set),
        'sham_target_literal_support': len(sham_set & target_key_set),
        'true_only_target_support': sorted((true_set - sham_set) & target_key_set),
        'sham_only_target_support': sorted((sham_set - true_set) & target_key_set),
    }

    controls = [arms['SHAM_SOURCE_ATOMS'], arms['COLD'], arms['ABLATION']]
    strict = (
        warm['transfer_hits'] > 0
        and warm['demo_exact'] and warm['heldout_exact']
        and all((not c['demo_exact']) or warm['queries'] < c['queries'] for c in controls)
        and not true_model['truncated']
        and not sham_model['truncated']
        and not any(s['truncated'] for s in states)
    )

    if warm['transfer_hits'] == 0:
        decision = 'NO_TRUE_SOURCE_ATOM_SUPPORT'
    elif strict:
        decision = 'PASS_CAUSAL_REUSABLE_OBSERVATION_TRANSFER'
    elif warm['queries'] < cold['queries'] and warm['queries'] == sham['queries']:
        decision = 'TRANSFER_GAIN_NOT_SOURCE_CAUSAL'
    elif warm['queries'] < cold['queries'] and warm['queries'] > sham['queries']:
        decision = 'SHAM_OUTPERFORMS_TRUE_SOURCE'
    else:
        decision = 'FAIL_CAUSAL_REUSABLE_OBSERVATION_TRANSFER'

    result = {
        'schema': 'verified-developmental-navigation.arc-reusable-observation-transfer.v28',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'source_tasks': SOURCE,
            'target_task': TARGET,
            'target_selection': 'frozen V22 frontier target, unchanged since V23',
            'target_used_for_source_atom_selection': False,
            'candidate_language': 'unchanged V17 observation language and V13 continuation language',
            'retained_object': 'multiset of literal executable observation atoms selected by source developmental episodes',
            'source_learner': 'exactly V27 collect_source_states / one-step verifier-optimal source episodes',
            'sham': 'same learner after deterministic permutation of source verifier labels',
            'target_rule': 'if any retained literal atom exists on target and separates current verifier residual, choose deterministic SHA-order match; otherwise frozen V19 fallback',
            'max_queries': MAXQ,
            'arms': ['WARM_TRUE_SOURCE_ATOMS', 'SHAM_SOURCE_ATOMS', 'COLD', 'ABLATION'],
        },
        'retained': {
            'true_source': summarize_atoms(true_atoms),
            'sham_source': summarize_atoms(sham_atoms),
            'support_overlap': overlap,
        },
        'target': {
            'task': TARGET,
            'states': len(states),
            'future_positive': sum(demo),
            'candidate_programs': len(keys),
            'any_truncation': any(s['truncated'] for s in states),
            'arms': arms,
        },
        'strict_gate': decision,
        'claim_boundary': 'Tests whether genuine source developmental experience causally selects a reusable set of executable observations that improves source-distinct target navigation beyond an identically trained sham-history set under the same target rule and query budget. It does not establish broad ARC transfer from one target.',
    }
    out = HERE / 'results_v28_reusable_observation_transfer'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
