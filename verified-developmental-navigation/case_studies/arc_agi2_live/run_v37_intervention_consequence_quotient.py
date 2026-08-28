import hashlib, importlib.util, itertools, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

v36 = load('v36', 'run_v36_developmental_state_quotient_census.py')
v35, v34 = v36.v35, v36.v34
v32, v31, v28, v23, v19, v13 = v36.v32, v36.v31, v36.v28, v36.v23, v36.v19, v36.v13
MAXQ = v28.MAXQ

# V37 follows the V36 negative literally.  It does not add another scalar state feature.
# Instead it represents a remembered intervention by its relation to the *other available
# interventions* on the residual history already exposed by the verifier.
#
# Structural coordinates are generated mechanically from the candidate x history
# separation matrix at each reachable decision point:
#   history_pattern          ordered booleans: which residuals this candidate separates
#   peer_relation_counts     how many peers have subset/equal/superset/incomparable patterns
#   peer_hamming_histogram   multiset of Hamming distances to peer patterns
#   support_rank             ordinal rank of history-support among peers
#   current_split_rank       ordinal rank of current bucket balance among peers
#
# No ARC semantics, task IDs, future labels, absolute residual counts, thresholds, or new
# observation language enter these keys.  Counterfactual future preference is used only
# afterward to audit whether a quotient class has one stable future meaning.

STRUCT_FEATURES = (
    'history_pattern',
    'peer_relation_counts',
    'peer_hamming_histogram',
    'support_rank',
    'current_split_rank',
)


def relation(a, b):
    sa = {i for i, x in enumerate(a) if x}
    sb = {i for i, x in enumerate(b) if x}
    if sa == sb:
        return 'eq'
    if sa < sb:
        return 'sub'
    if sa > sb:
        return 'sup'
    return 'inc'


def ordinal_rank(vals, x):
    return (sum(v < x for v in vals), sum(v == x for v in vals), sum(v > x for v in vals))


def collect_rows(ev, tr, eligible, bounds):
    atoms = set(bounds)
    rows = []
    target_trunc = False
    for er in eligible:
        tid = er['task']
        states, keys, demo, held = v23.prepare(tr[tid])
        target_trunc |= any(s['truncated'] for s in states)
        for i, s in enumerate(states):
            s['_label'] = bool(demo[i])
        chosen, history = [], []
        for qi in range(MAXQ):
            if v19.unresolved(states, chosen, demo) == 0:
                break
            cur = v19.collision(states, chosen, demo)
            if cur is None:
                break
            history.append(cur)
            available, admitted = [], []
            for k in keys:
                if k in chosen or k not in atoms or not v19.separates(states, k, cur):
                    continue
                frac, counts = v32.balance_fraction(states, chosen, cur, k)
                lo, hi = bounds[k]
                pat = tuple(bool(v19.separates(states, k, p)) for p in history)
                available.append({'atom': k, 'frac': frac, 'counts': counts, 'lo': lo, 'hi': hi, 'pat': pat})
                if lo <= frac <= hi:
                    admitted.append((k, frac, lo, hi))
            fallback, _ = v19.history_atom(states, keys, chosen, cur, history)
            if available:
                support_vals = [sum(x['pat']) for x in available]
                split_vals = [min(x['counts'][0], x['counts'][1]) * 1.0 / max(1, x['counts'][2]) for x in available]
                for x in available:
                    pat = x['pat']
                    rel = {'sub': 0, 'eq': 0, 'sup': 0, 'inc': 0}
                    dists = []
                    for y in available:
                        rel[relation(pat, y['pat'])] += 1
                        dists.append(sum(a != b for a, b in zip(pat, y['pat'])))
                    maxd = len(history)
                    hist = tuple(sum(d == j for d in dists) for j in range(maxd + 1))
                    support = sum(pat)
                    split = min(x['counts'][0], x['counts'][1]) * 1.0 / max(1, x['counts'][2])
                    structural = {
                        'history_pattern': pat,
                        'peer_relation_counts': (rel['sub'], rel['eq'], rel['sup'], rel['inc']),
                        'peer_hamming_histogram': hist,
                        'support_rank': ordinal_rank(support_vals, support),
                        'current_split_rank': ordinal_rank(split_vals, split),
                    }
                    forced = v34.finish_v19(states, keys, demo, chosen + [x['atom']], history, MAXQ - (qi + 1))
                    if fallback is None:
                        fb = {'exact': False, 'queries': len(chosen), 'unresolved': v19.unresolved(states, chosen, demo)}
                    else:
                        fb = v34.finish_v19(states, keys, demo, chosen + [fallback], history, MAXQ - (qi + 1))
                    rows.append({
                        'task': tid,
                        'step': qi + 1,
                        'atom': x['atom'],
                        'v32_admitted': bool(x['lo'] <= x['frac'] <= x['hi']),
                        'structural': structural,
                        'prefer_source': v34.future_rank(forced) > v34.future_rank(fb),
                        'tie': v34.future_rank(forced) == v34.future_rank(fb),
                    })
            # Keep the reachable-state distribution frozen to V32 WARM_GATED.
            if admitted:
                admitted.sort(key=lambda z: hashlib.sha256(z[0].encode()).hexdigest())
                nxt = admitted[0][0]
            else:
                nxt = fallback
            if nxt is None:
                break
            chosen.append(nxt)
    return rows, target_trunc


def key_for(r, subset, include_atom, include_admitted):
    key = []
    if include_atom:
        key.append(r['atom'])
    if include_admitted:
        key.append(bool(r['v32_admitted']))
    key.extend(tuple(r['structural'][f]) for f in subset)
    return tuple(key)


def audit(rows, key_fn):
    groups = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r)
    mixed = pure = cross = pos_pure = 0
    for rs in groups.values():
        ys = {bool(r['prefer_source']) for r in rs}
        ts = {r['task'] for r in rs}
        mixed += int(len(ys) > 1)
        pure += int(len(ys) == 1)
        pos_pure += int(len(ys) == 1 and next(iter(ys)))
        cross += int(len(ts) > 1)
    supported = correct = pos_supported = pos_correct = 0
    support_targets = set()
    for r in rows:
        peers = [q for q in groups[key_fn(r)] if q['task'] != r['task']]
        if not peers:
            continue
        ys = {bool(q['prefer_source']) for q in peers}
        if len(ys) != 1:
            continue
        pred = next(iter(ys))
        supported += 1
        support_targets.add(r['task'])
        correct += int(pred == bool(r['prefer_source']))
        if pred:
            pos_supported += 1
            pos_correct += int(bool(r['prefer_source']))
    return {
        'classes': len(groups), 'pure_classes': pure, 'mixed_classes': mixed,
        'cross_target_classes': cross, 'positive_pure_classes': pos_pure,
        'loo_supported_rows': supported, 'loo_correct_rows': correct,
        'loo_accuracy': (correct / supported) if supported else None,
        'loo_positive_supported_rows': pos_supported,
        'loo_positive_correct_rows': pos_correct,
        'loo_supported_targets': len(support_targets),
    }


def quality(rec):
    a = rec['audit']
    return (
        a['mixed_classes'] == 0,
        a['loo_positive_correct_rows'],
        a['loo_positive_supported_rows'],
        a['loo_supported_rows'],
        a['loo_correct_rows'],
        -a['classes'],
        -len(rec['features']),
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: run_v37_intervention_consequence_quotient.py EVAL TRAIN')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    tr = v13.v2.v1.load_tasks(sys.argv[2])
    _, _, eligible = v31.select_target(tr)
    bounds, _, source_trunc = v32.source_profiles(ev, False)
    rows, target_trunc = collect_rows(ev, tr, eligible, bounds)

    families = {}
    strict_winners = []
    configs = (
        ('ATOM_ADMITTED', True, True),
        ('ATOM_ONLY', True, False),
        ('ANON_ADMITTED', False, True),
        ('FULLY_ANONYMOUS', False, False),
    )
    for name, include_atom, include_admitted in configs:
        recs, strict = [], []
        for n in range(len(STRUCT_FEATURES) + 1):
            for subset in itertools.combinations(STRUCT_FEATURES, n):
                au = audit(rows, lambda r, s=subset, ia=include_atom, iad=include_admitted: key_for(r, s, ia, iad))
                rec = {'features': list(subset), 'audit': au}
                recs.append(rec)
                if au['classes'] < len(rows) and au['mixed_classes'] == 0 and au['loo_supported_rows'] > 0:
                    strict.append(rec)
        best = max(recs, key=quality)
        if strict:
            min_n = min(len(r['features']) for r in strict)
            minima = [r for r in strict if len(r['features']) == min_n]
            strict_winners.append(name)
        else:
            minima = []
        families[name] = {
            'searched_subsets': len(recs),
            'best': best,
            'strict_quotient_count': len(strict),
            'minimum_strict_quotients': minima,
        }

    strict_gate = bool(strict_winners) and not source_trunc and not target_trunc
    result = {
        'schema': 'verified-developmental-navigation.arc-intervention-consequence-quotient.v37',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'panel': 'same 29 frozen V31-eligible training targets',
            'reachable_states': 'exact frozen V32 WARM_GATED trajectories',
            'memory': 'TRUE V32 source profiles',
            'representation': 'candidate x residual-history separation structure and relations to peer remembered interventions; no task IDs, ARC semantics, future labels, absolute unresolved counts, thresholds, or new observation features in quotient key',
            'structural_features': list(STRUCT_FEATURES),
            'families': [x[0] for x in configs],
            'search': 'exhaustive all subsets of generated intervention-structural features',
            'future_audit': 'same V34 counterfactual preference: force candidate once vs frozen V19 fallback, then finish remaining budget with frozen V19',
            'strict_gate': 'compression below one class per decision row, zero mixed future-preference classes, and positive leave-one-target-out support',
            'target_labels_used_for_representation': False,
            'target_labels_used_for_posthoc_future_audit': True,
            'max_queries': MAXQ,
        },
        'measurements': {
            'eligible_targets': len(eligible), 'decision_rows': len(rows),
            'successful_families': strict_winners,
            'source_truncated': source_trunc, 'target_truncated': target_trunc,
        },
        'families': families,
        'strict_gate': 'PASS_RECURRENT_FUTURE_SUFFICIENT_INTERVENTION_QUOTIENT' if strict_gate else 'FAIL_RECURRENT_FUTURE_SUFFICIENT_INTERVENTION_QUOTIENT',
        'claim_boundary': 'Post-V36 mechanism census on the already-audited panel. Representation is generated label-free from intervention/history incidence; future sufficiency is scored post hoc. A PASS identifies a recurrent behavioral intervention quotient candidate, not yet a prospective deployed transfer law.'
    }
    out = HERE / 'results_v37_intervention_consequence_quotient'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
