import importlib.util
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

v28 = load('v28', 'run_v28_reusable_observation_transfer.py')
v27 = v28.v27
v23 = v28.v23
v19 = v28.v19
v13 = v28.v13
SOURCE = v28.SOURCE
TARGET = v28.TARGET
MAXQ = v28.MAXQ

# V29 keeps the V28 learner, target, language, policy and budget frozen.
# It asks which true-source retained executable observations are causally
# necessary for the 4-query transfer, and finds the smallest subset preserving
# V28's exact target outcome. No target-derived new observation is introduced.

def arm(states, keys, demo, held, atoms):
    return v28.make_arm(states, keys, demo, held, atoms)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v29_minimal_causal_memory.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    true_model = v27.learn_quotient(ev, sham=False)
    atoms = sorted(set(true_model['source_atoms']))
    states, keys, demo, held = v23.prepare(ev[TARGET])

    full = arm(states, keys, demo, held, atoms)
    if not (full['demo_exact'] and full['heldout_exact']):
        raise RuntimeError('V28 true-source baseline no longer exact')
    baseline_q = full['queries']

    leave_one_out = []
    necessary = []
    for a in atoms:
        kept = [x for x in atoms if x != a]
        r = arm(states, keys, demo, held, kept)
        worsens = (not r['demo_exact']) or (not r['heldout_exact']) or r['queries'] > baseline_q
        if worsens:
            necessary.append(a)
        leave_one_out.append({
            'removed': a,
            'queries': r['queries'],
            'demo_exact': r['demo_exact'],
            'heldout_exact': r['heldout_exact'],
            'transfer_hits': r['transfer_hits'],
            'worsens_baseline': worsens,
        })

    # Exhaustive subset search over 15 unique atoms is only 32768 subsets.
    # Search by cardinality and stop at first cardinality with exact 4-query
    # solutions; enumerate all minima at that cardinality for robustness.
    minima = []
    min_k = None
    evaluated = 0
    for k in range(len(atoms) + 1):
        hits = []
        for comb in itertools.combinations(atoms, k):
            evaluated += 1
            r = arm(states, keys, demo, held, list(comb))
            if r['demo_exact'] and r['heldout_exact'] and r['queries'] <= baseline_q:
                hits.append({
                    'atoms': list(comb),
                    'queries': r['queries'],
                    'transfer_hits': r['transfer_hits'],
                    'trace': r['trace'],
                })
        if hits:
            min_k = k
            minima = hits
            break

    intersection = sorted(set.intersection(*(set(x['atoms']) for x in minima))) if minima else []
    union = sorted(set.union(*(set(x['atoms']) for x in minima))) if minima else []

    result = {
        'schema': 'verified-developmental-navigation.arc-minimal-causal-memory.v29',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'source_tasks': SOURCE,
            'target_task': TARGET,
            'candidate_language': 'unchanged V17 observation language and V13 continuation language',
            'retained_source_object': 'unique literal executable observations selected by the unchanged V28 true-source learner',
            'target_rule': 'unchanged V28 reusable-observation rule with V19 fallback',
            'max_queries': MAXQ,
            'minimality_criterion': 'smallest retained subset preserving demo+heldout exactness in no more queries than the full V28 true-source baseline',
            'search': 'exhaustive subsets by increasing cardinality; no semantic pruning or target-derived feature creation',
        },
        'baseline': {
            'unique_source_atoms': len(atoms),
            'atoms': atoms,
            'queries': baseline_q,
            'demo_exact': full['demo_exact'],
            'heldout_exact': full['heldout_exact'],
            'transfer_hits': full['transfer_hits'],
            'trace': full['trace'],
        },
        'leave_one_out': leave_one_out,
        'individually_necessary_for_full_set': necessary,
        'minimal_basis': {
            'cardinality': min_k,
            'number_of_minima': len(minima),
            'intersection_all_minima': intersection,
            'union_all_minima': union,
            'minima': minima,
            'subsets_evaluated_until_minimal_cardinality_closed': evaluated,
        },
        'strict_gate': 'PASS_MINIMAL_CAUSAL_MEMORY_BASIS' if minima and min_k < len(atoms) and baseline_q == 4 else 'FAIL_MINIMAL_CAUSAL_MEMORY_BASIS',
        'claim_boundary': 'Identifies a smallest retained executable-observation subset sufficient to preserve the already-established V28 4-query exact transfer on the frozen source-distinct target. Minimality is target-relative and does not imply a globally minimal ARC memory basis.',
    }
    out = HERE / 'results_v29_minimal_causal_memory'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
