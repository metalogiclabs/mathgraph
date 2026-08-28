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
v27, v23, v19, v13 = v28.v27, v28.v23, v28.v19, v28.v13
SOURCE, TARGET, MAXQ = v28.SOURCE, v28.TARGET, v28.MAXQ


def arm(states, keys, demo, held, atoms):
    return v28.make_arm(states, keys, demo, held, list(atoms))


def compact(a):
    return {k: a[k] for k in ('queries','demo_exact','heldout_exact','unresolved','transfer_hits')}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v29_minimal_causal_observation_basis.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    model = v27.learn_quotient(ev, sham=False)
    states, keys, demo, held = v23.prepare(ev[TARGET])
    true_unique = sorted(set(model['source_atoms']))
    target_supported = sorted(set(true_unique) & set(keys))

    full = arm(states, keys, demo, held, true_unique)
    cc, ct = v19.run_history(states, keys, demo, False)
    cold = v27.arm(states, cc, ct, 0, demo, held)

    leave_one_out = []
    for atom in true_unique:
        a = arm(states, keys, demo, held, [x for x in true_unique if x != atom])
        leave_one_out.append({'removed': atom, **compact(a), 'causal_for_4q': a['queries'] > full['queries'] or not a['demo_exact'] or not a['heldout_exact']})

    # Unsupported source atoms can never be chosen by the frozen target rule, so
    # exact subset minimization needs only the source-acquired atoms that exist in
    # the target candidate language.  There are eight in V28 => 256 subsets.
    subset_rows = []
    best_q = MAXQ + 1
    best_size = None
    minimal = []
    for r in range(len(target_supported)+1):
        for comb in itertools.combinations(target_supported, r):
            a = arm(states, keys, demo, held, comb)
            row = {'atoms': list(comb), **compact(a)}
            subset_rows.append(row)
            if a['demo_exact'] and a['heldout_exact']:
                if a['queries'] < best_q:
                    best_q, best_size, minimal = a['queries'], r, [row]
                elif a['queries'] == best_q:
                    if best_size is None or r < best_size:
                        best_size, minimal = r, [row]
                    elif r == best_size:
                        minimal.append(row)

    four_query = [r for r in subset_rows if r['demo_exact'] and r['heldout_exact'] and r['queries'] <= full['queries']]
    min4_size = min((len(r['atoms']) for r in four_query), default=None)
    min4 = [r for r in four_query if len(r['atoms']) == min4_size] if min4_size is not None else []

    individually_necessary = sorted(x['removed'] for x in leave_one_out if x['causal_for_4q'])
    decision = (
        'PASS_MINIMAL_CAUSAL_RETAINED_BASIS'
        if full['queries'] < cold['queries'] and min4_size is not None and min4_size < len(target_supported)
        else 'NO_STRICT_MINIMAL_CAUSAL_BASIS'
    )

    result = {
        'schema': 'verified-developmental-navigation.arc-minimal-causal-observation-basis.v29',
        'source': {'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'source_tasks': SOURCE, 'target_task': TARGET,
            'candidate_language':'unchanged V17/V13', 'target_rule':'unchanged V28 retained-atom-first then V19 fallback',
            'search':'leave-one-out over all unique true-source atoms; exhaustive powerset over true-source atoms literally supported on target',
            'target_used_to_learn_atoms': False, 'max_queries': MAXQ,
        },
        'source_retained': {'unique_atoms': len(true_unique), 'target_supported_atoms': target_supported, 'target_supported_count': len(target_supported)},
        'baseline': {'full_warm': compact(full), 'cold': compact(cold)},
        'leave_one_out': leave_one_out,
        'individually_necessary_for_full_4q_trajectory': individually_necessary,
        'exact_subset_census': {
            'subsets_tested': len(subset_rows), 'best_query_count': best_q if best_q <= MAXQ else None,
            'minimum_cardinality_at_best_query_count': best_size,
            'best_minimum_subsets': minimal,
            'minimum_cardinality_preserving_full_warm_query_count_or_better': min4_size,
            'minimum_4q_or_better_subsets': min4,
        },
        'strict_gate': decision,
        'claim_boundary':'Identifies a target-relative minimal causal basis inside observations genuinely selected on source tasks. It does not show that this same basis is minimal across ARC or that target support was unknown when this post-V28 mechanism audit was designed.'
    }
    out = HERE / 'results_v29_minimal_causal_observation_basis'
    out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
