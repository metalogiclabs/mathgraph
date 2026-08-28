import hashlib, importlib.util, itertools, json, sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

v35 = load('v35', 'run_v35_leave_one_target_out_residual_gate.py')
v34 = v35.v34
v32, v31, v28, v23, v19, v13 = v35.v32, v35.v31, v35.v28, v35.v23, v35.v19, v35.v13
MAXQ = v28.MAXQ
FEATURES = v34.FEATURES

# V36 does not add another hand-written state coordinate.  It asks whether V34's
# absolute residual-relative measurements can be quotiented by their *ordinal relation*
# to the other currently available remembered moves.  For every numeric feature f and
# candidate remembered atom k we retain only:
#   (# peers lower than k, # peers equal to k, # peers greater than k).
# This erases absolute task-specific scales while preserving local intervention geometry.
# The verifier labels are used only after the representation is frozen, to audit whether
# quotient classes have a common future preference and whether they recur under LOO.


def as_scalar(x):
    if isinstance(x, list) and len(x) == 2:
        return Fraction(x[0], x[1])
    if isinstance(x, tuple) and len(x) == 2:
        return Fraction(x[0], x[1])
    return x


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
        chosen = []
        history = []
        for qi in range(MAXQ):
            if v19.unresolved(states, chosen, demo) == 0:
                break
            cur = v19.collision(states, chosen, demo)
            if cur is None:
                break
            history.append(cur)
            available = []
            admitted = []
            for k in keys:
                if k in chosen or k not in atoms or not v19.separates(states, k, cur):
                    continue
                frac, _ = v32.balance_fraction(states, chosen, cur, k)
                lo, hi = bounds[k]
                available.append((k, frac, lo, hi))
                if lo <= frac <= hi:
                    admitted.append((k, frac, lo, hi))
            fallback, _ = v19.history_atom(states, keys, chosen, cur, history)

            step_rows = []
            for k, frac, lo, hi in available:
                forced = v34.finish_v19(states, keys, demo, chosen + [k], history, MAXQ - (qi + 1))
                if fallback is None:
                    fb = {'exact': False, 'queries': len(chosen), 'unresolved': v19.unresolved(states, chosen, demo)}
                else:
                    fb = v34.finish_v19(states, keys, demo, chosen + [fallback], history, MAXQ - (qi + 1))
                feats = v34.profile_features(states, chosen, cur, history, k, len(available), len(admitted))
                feats['balance_fraction'] = list(feats['balance_fraction'])
                step_rows.append({
                    'task': tid,
                    'step': qi + 1,
                    'atom': k,
                    'v32_admitted': bool(lo <= frac <= hi),
                    'features': feats,
                    'prefer_source': v34.future_rank(forced) > v34.future_rank(fb),
                    'tie': v34.future_rank(forced) == v34.future_rank(fb),
                })

            # Build the task-scale-free local order geometry before verifier outcomes are audited.
            for r in step_rows:
                ordinal = {}
                for f in FEATURES:
                    x = as_scalar(r['features'][f])
                    vals = [as_scalar(q['features'][f]) for q in step_rows]
                    ordinal[f] = [sum(v < x for v in vals), sum(v == x for v in vals), sum(v > x for v in vals)]
                r['ordinal'] = ordinal
                rows.append(r)

            # Reachability remains exactly the frozen V32 WARM_GATED trajectory.
            if admitted:
                admitted.sort(key=lambda x: hashlib.sha256(x[0].encode()).hexdigest())
                nxt = admitted[0][0]
            else:
                nxt = fallback
            if nxt is None:
                break
            chosen.append(nxt)
    return rows, target_trunc


def exact_key(r):
    vals = []
    for f in FEATURES:
        x = r['features'][f]
        vals.append(tuple(x) if isinstance(x, list) else x)
    return (r['atom'], bool(r['v32_admitted'])) + tuple(vals)


def quotient_key(r, subset, include_atom):
    pre = (r['atom'], bool(r['v32_admitted'])) if include_atom else (bool(r['v32_admitted']),)
    return pre + tuple(tuple(r['ordinal'][f]) for f in subset)


def audit(rows, key_fn):
    groups = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r)
    mixed = 0
    pure = 0
    cross_target = 0
    positive_pure = 0
    for rs in groups.values():
        ys = {bool(r['prefer_source']) for r in rs}
        tasks = {r['task'] for r in rs}
        if len(ys) > 1:
            mixed += 1
        else:
            pure += 1
            if next(iter(ys)):
                positive_pure += 1
        if len(tasks) > 1:
            cross_target += 1

    supported = correct = positive_supported = positive_correct = 0
    seen_tasks = set()
    for r in rows:
        train = [q for q in groups[key_fn(r)] if q['task'] != r['task']]
        if not train:
            continue
        ys = {bool(q['prefer_source']) for q in train}
        if len(ys) != 1:
            continue
        pred = next(iter(ys))
        supported += 1
        seen_tasks.add(r['task'])
        correct += int(pred == bool(r['prefer_source']))
        if pred:
            positive_supported += 1
            positive_correct += int(bool(r['prefer_source']))

    return {
        'classes': len(groups),
        'pure_classes': pure,
        'mixed_classes': mixed,
        'cross_target_classes': cross_target,
        'positive_pure_classes': positive_pure,
        'loo_supported_rows': supported,
        'loo_correct_rows': correct,
        'loo_accuracy': (correct / supported) if supported else None,
        'loo_positive_supported_rows': positive_supported,
        'loo_positive_correct_rows': positive_correct,
        'loo_supported_targets': len(seen_tasks),
    }


def candidate_better(a, b):
    # Prefer a true quotient that remains future-pure and recurs.  Among such candidates,
    # maximize held-out support, then positive support, then compression, then fewer features.
    ka = (
        a['audit']['mixed_classes'] == 0,
        a['audit']['loo_supported_rows'] > 0,
        a['audit']['loo_supported_rows'],
        a['audit']['loo_positive_supported_rows'],
        -a['audit']['classes'],
        -len(a['features']),
    )
    kb = (
        b['audit']['mixed_classes'] == 0,
        b['audit']['loo_supported_rows'] > 0,
        b['audit']['loo_supported_rows'],
        b['audit']['loo_positive_supported_rows'],
        -b['audit']['classes'],
        -len(b['features']),
    )
    return ka > kb


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: run_v36_developmental_state_quotient_census.py EVAL TRAIN')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    tr = v13.v2.v1.load_tasks(sys.argv[2])
    _, _, eligible = v31.select_target(tr)
    bounds, source_rows, source_trunc = v32.source_profiles(ev, False)
    rows, target_trunc = collect_rows(ev, tr, eligible, bounds)

    exact = audit(rows, exact_key)
    families = {}
    winners = []
    for include_atom, family in ((True, 'ATOM_RELATIVE'), (False, 'ANONYMOUS')):
        records = []
        best = None
        successful = []
        for n in range(len(FEATURES) + 1):
            for subset in itertools.combinations(FEATURES, n):
                au = audit(rows, lambda r, s=subset, ia=include_atom: quotient_key(r, s, ia))
                rec = {'features': list(subset), 'audit': au}
                records.append(rec)
                strict = (
                    au['classes'] < exact['classes'] and
                    au['mixed_classes'] == 0 and
                    au['loo_supported_rows'] > 0
                )
                if strict:
                    successful.append(rec)
                if best is None or candidate_better(rec, best):
                    best = rec
        if successful:
            min_n = min(len(x['features']) for x in successful)
            minima = [x for x in successful if len(x['features']) == min_n]
        else:
            minima = []
        families[family] = {
            'searched_subsets': len(records),
            'best': best,
            'minimum_strict_quotients': minima,
            'strict_quotient_count': len(successful),
        }
        if successful:
            winners.append(family)

    strict = bool(winners) and not source_trunc and not target_trunc
    result = {
        'schema': 'verified-developmental-navigation.arc-developmental-state-quotient-census.v36',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'panel': 'same 29 frozen V31-eligible training targets',
            'reachable_states': 'exact frozen V32 WARM_GATED trajectories',
            'memory': 'TRUE V32 source profiles',
            'representation': 'for each frozen V34 feature retain only counts of available remembered moves with lower/equal/greater value; no absolute feature values, ratios, thresholds, ARC semantics, task IDs, or target-derived labels enter the quotient key',
            'families': ['ATOM_RELATIVE keeps remembered atom identity + V32 admitted bit', 'ANONYMOUS erases remembered atom identity and keeps only V32 admitted bit'],
            'search': 'exhaustive all subsets of the ten already-frozen V34 features in each family; no new feature is introduced',
            'future_audit': 'counterfactual future preference from V34: force remembered move once versus frozen V19 fallback, then finish remaining budget with frozen V19',
            'loo_support': 'a held-out row counts as supported only if its quotient class occurs on another target and all non-held-out occurrences agree on future preference',
            'strict_gate': 'fewer classes than exact V34 state, zero mixed future-preference classes, and positive LOO support',
            'target_labels_used_for_representation': False,
            'target_labels_used_for_posthoc_future_audit': True,
            'max_queries': MAXQ,
        },
        'measurements': {
            'eligible_targets': len(eligible),
            'decision_rows': len(rows),
            'exact_v34_state': exact,
            'features': list(FEATURES),
            'successful_families': winners,
            'source_truncated': source_trunc,
            'target_truncated': target_trunc,
        },
        'families': families,
        'strict_gate': 'PASS_RECURRENT_FUTURE_SUFFICIENT_DEVELOPMENTAL_QUOTIENT' if strict else 'FAIL_RECURRENT_FUTURE_SUFFICIENT_DEVELOPMENTAL_QUOTIENT',
        'claim_boundary': 'Post-V34/V35 quotient-discovery census on the already-audited 29-target panel. The ordinal representation is label-free and scale-free, but future purity is scored post hoc on this panel. A PASS identifies a recurrent future-sufficient developmental-state quotient candidate; it is not yet a deployed prospective transfer policy.',
    }
    out = HERE / 'results_v36_developmental_state_quotient_census'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
