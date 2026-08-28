import hashlib
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


v23 = load('v23', 'run_v23_source_trained_method_transfer.py')
v19 = v23.v19
v13 = v23.v13
SOURCE = v23.SOURCE
TARGET = v23.TARGET
MAXQ = v23.MAXQ
SHAM_SEED = 20260828

# V27 deliberately adds no ARC observation feature, semantic role, task family,
# policy tree, or hand-written state category.  It asks whether developmental
# decision states themselves admit an exact source-distinct quotient.
#
# A decision state is represented only by anonymous verifier-local geometry:
#   * ordered history length,
#   * number of still-admissible separators for the returned collision,
#   * multiset of V23's already-frozen four generic candidate feature tuples.
# Candidate identities are erased.  Source verifier outcomes are used only to
# determine which anonymous feature tuple has the best one-step consequence.
# If two source states have the same observable signature but disagree about the
# best consequence tuple, that signature is NOT retained as a quotient class.

FEATURE_ORDER = v23.FEATURES


def admissible_profiles(states, keys, chosen, current, history):
    rows = []
    for k in keys:
        if k in chosen or not v19.separates(states, k, current):
            continue
        f = v23.feature_map(states, k, chosen, current, history)
        profile = tuple(int(f[x]) for x in FEATURE_ORDER)
        rows.append((k, profile, f))
    return rows


def state_signature(states, keys, chosen, current, history):
    rows = admissible_profiles(states, keys, chosen, current, history)
    # Multiset, not ordered candidate IDs.  Exact equality is preregistered: no
    # adaptive binning, normalization, nearest-neighbour rescue, or target tuning.
    counts = Counter(profile for _, profile, _ in rows)
    multiset = tuple(sorted((p, n) for p, n in counts.items()))
    return (len(history), len(rows), multiset), rows


def sig_jsonable(sig):
    h, n, ms = sig
    return {
        'history_size': h,
        'admissible_count': n,
        'profile_multiset': [
            {'profile': list(p), 'multiplicity': c} for p, c in ms
        ],
    }


def best_source_profile(states, keys, chosen, current, history, labels):
    sig, rows = state_signature(states, keys, chosen, current, history)
    if not rows:
        return sig, None, None
    scored = []
    for k, profile, f in rows:
        after = v19.unresolved(states, chosen + [k], labels)
        # Consequence first; anonymous feature profile next; hash is only a
        # deterministic within-profile tie-break and is never retained.
        scored.append((after, tuple(-x for x in profile), hashlib.sha256(k.encode()).hexdigest(), k, profile, f))
    scored.sort()
    best = scored[0]
    return sig, best[4], {'atom': best[3], 'profile': list(best[4]), 'one_step_unresolved': best[0], 'features': best[5]}


def collect_source_states(states, keys, labels, sham=False):
    chosen = []
    history = []
    rows = []
    rng = random.Random(SHAM_SEED + len(states))
    perm = list(range(len(states)))
    rng.shuffle(perm)
    sham_labels = [False] * len(labels)
    for i, x in enumerate(labels):
        sham_labels[perm[i]] = bool(x)
    drive_labels = sham_labels if sham else labels

    for qi in range(MAXQ):
        if v19.sufficient(states, chosen, drive_labels):
            break
        cur = v19.collision(states, chosen, drive_labels)
        if cur is None:
            break
        history.append(cur)
        sig, pref, meta = best_source_profile(states, keys, chosen, cur, history, drive_labels)
        if pref is None:
            break
        rows.append({'query': qi + 1, 'signature': sig_jsonable(sig), 'preferred_profile': list(pref), 'source_choice': meta})
        # Drive the source episode with the best verified one-step consequence.
        candidates = admissible_profiles(states, keys, chosen, cur, history)
        matching = [x for x in candidates if x[1] == pref]
        matching.sort(key=lambda x: hashlib.sha256(x[0].encode()).hexdigest())
        chosen.append(matching[0][0])
    return rows


def learn_quotient(ev, sham=False):
    evidence = defaultdict(list)
    source_rows = []
    source_atoms = []
    truncated = False
    for tid in SOURCE:
        states, keys, demo, _ = v23.prepare(ev[tid])
        truncated |= any(s['truncated'] for s in states)
        rows = collect_source_states(states, keys, demo, sham)
        for r in rows:
            # Stable JSON key preserves exact anonymous signature.
            key = json.dumps(r['signature'], sort_keys=True, separators=(',', ':'))
            evidence[key].append(tuple(r['preferred_profile']))
            source_atoms.append(r['source_choice']['atom'])
        source_rows.append({'task': tid, 'decision_states': len(rows), 'rows': rows})

    table = {}
    conflicts = {}
    for key, prefs in evidence.items():
        uniq = sorted(set(prefs))
        if len(uniq) == 1:
            table[key] = uniq[0]
        else:
            conflicts[key] = [list(x) for x in uniq]
    return {
        'table': table,
        'conflicts': conflicts,
        'source_rows': source_rows,
        'source_atoms': source_atoms,
        'truncated': truncated,
        'observed_signatures': len(evidence),
        'retained_classes': len(table),
        'conflicted_signatures': len(conflicts),
    }


def choose_from_quotient(states, keys, chosen, current, history, table):
    sig, rows = state_signature(states, keys, chosen, current, history)
    key = json.dumps(sig_jsonable(sig), sort_keys=True, separators=(',', ':'))
    preferred = table.get(key)
    if preferred is None:
        return None, {'quotient_hit': False, 'signature': sig_jsonable(sig)}
    matching = [x for x in rows if x[1] == tuple(preferred)]
    if not matching:
        # This should be impossible because the full profile multiset is part of
        # the signature, but keep the failure explicit rather than silently relax.
        return None, {'quotient_hit': True, 'profile_present': False, 'signature': sig_jsonable(sig), 'preferred_profile': list(preferred)}
    matching.sort(key=lambda x: hashlib.sha256(x[0].encode()).hexdigest())
    k, profile, f = matching[0]
    return k, {'quotient_hit': True, 'profile_present': True, 'signature': sig_jsonable(sig), 'preferred_profile': list(profile), 'features': f}


def run_warm(states, keys, labels, table):
    chosen = []
    history = []
    trace = []
    hits = 0
    for qi in range(MAXQ):
        before = v19.unresolved(states, chosen, labels)
        if before == 0:
            break
        cur = v19.collision(states, chosen, labels)
        if cur is None:
            break
        history.append(cur)
        k, meta = choose_from_quotient(states, keys, chosen, cur, history, table)
        if k is not None:
            hits += 1
            mode = 'QUOTIENT'
        else:
            # Frozen fallback is exactly V19's local history policy.  No relaxed
            # quotient matching is allowed after a miss.
            k, f = v19.history_atom(states, keys, chosen, cur, history)
            mode = 'V19_FALLBACK'
            meta['fallback_features'] = f
        if k is None:
            trace.append({'query': qi + 1, 'mode': mode, 'status': 'NO_SEPARATOR', **meta})
            break
        chosen.append(k)
        trace.append({'query': qi + 1, 'mode': mode, 'atom': k, 'unresolved_before': before,
                      'unresolved_after': v19.unresolved(states, chosen, labels), **meta})
    return chosen, trace, hits


def run_raw_budgeted(states, keys, labels, source_atoms):
    chosen = []
    history = []
    trace = []
    atomset = set(source_atoms)
    raw_hits = 0
    for qi in range(MAXQ):
        before = v19.unresolved(states, chosen, labels)
        if before == 0:
            break
        cur = v19.collision(states, chosen, labels)
        if cur is None:
            break
        history.append(cur)
        matches = [k for k in keys if k in atomset and k not in chosen and v19.separates(states, k, cur)]
        if matches:
            matches.sort(key=lambda k: hashlib.sha256(k.encode()).hexdigest())
            k = matches[0]
            mode = 'RAW_MATCH'
            raw_hits += 1
        else:
            k, _ = v19.history_atom(states, keys, chosen, cur, history)
            mode = 'V19_FALLBACK'
        if k is None:
            break
        chosen.append(k)
        trace.append({'query': qi + 1, 'mode': mode, 'atom': k, 'unresolved_before': before,
                      'unresolved_after': v19.unresolved(states, chosen, labels)})
    return chosen, trace, raw_hits


def arm(states, chosen, trace, hits, demo, held):
    return {
        'queries': len(chosen),
        'demo_exact': v19.sufficient(states, chosen, demo),
        'heldout_exact': v19.sufficient(states, chosen, held),
        'unresolved': v19.unresolved(states, chosen, demo),
        'transfer_hits': hits,
        'trace': trace,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v27_developmental_state_quotient.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])

    warm_model = learn_quotient(ev, sham=False)
    sham_model = learn_quotient(ev, sham=True)
    states, keys, demo, held = v23.prepare(ev[TARGET])

    wc, wt, wh = run_warm(states, keys, demo, warm_model['table'])
    sc, st, sh = run_warm(states, keys, demo, sham_model['table'])
    cc, ct = v19.run_history(states, keys, demo, False)
    rc, rt, rh = run_raw_budgeted(states, keys, demo, warm_model['source_atoms'])

    arms = {
        'WARM_QUOTIENT': arm(states, wc, wt, wh, demo, held),
        'SHAM_QUOTIENT': arm(states, sc, st, sh, demo, held),
        'COLD': arm(states, cc, ct, 0, demo, held),
        'ABLATION': arm(states, cc, ct, 0, demo, held),
        'RAW_HISTORY': arm(states, rc, rt, rh, demo, held),
    }

    w = arms['WARM_QUOTIENT']
    controls = [arms[x] for x in ('SHAM_QUOTIENT', 'COLD', 'ABLATION', 'RAW_HISTORY')]
    strict = (
        w['transfer_hits'] > 0
        and w['demo_exact'] and w['heldout_exact']
        and all((not c['demo_exact']) or w['queries'] < c['queries'] for c in controls)
        and not warm_model['truncated']
        and not any(s['truncated'] for s in states)
    )

    if w['transfer_hits'] == 0:
        decision = 'NO_EXACT_DEVELOPMENTAL_STATE_QUOTIENT_SUPPORT'
    elif strict:
        decision = 'PASS_DEVELOPMENTAL_STATE_QUOTIENT_COMPOUNDING'
    else:
        decision = 'FAIL_DEVELOPMENTAL_STATE_QUOTIENT_COMPOUNDING'

    def model_summary(m):
        return {
            'observed_signatures': m['observed_signatures'],
            'retained_classes': m['retained_classes'],
            'conflicted_signatures': m['conflicted_signatures'],
            'source_rows': m['source_rows'],
        }

    result = {
        'schema': 'verified-developmental-navigation.arc-developmental-state-quotient.v27',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'source_tasks': SOURCE,
            'target_task': TARGET,
            'target_selection': 'frozen source-distinct V22 frontier task retained unchanged from V23/V24',
            'target_used_for_quotient_learning': False,
            'candidate_language': 'unchanged V17 observation language and V13 continuation language',
            'state_signature': 'exact anonymous multiset of frozen V23 candidate feature tuples + history size + admissible separator count',
            'quotient_rule': 'retain an exact signature only when all source occurrences agree on the one-step verifier-optimal anonymous feature tuple',
            'miss_rule': 'exact miss falls back to frozen V19 history policy; no normalization, nearest-neighbour, semantic labels, or target tuning',
            'sham': 'same learner after deterministic permutation of source verifier labels',
            'arms': ['WARM_QUOTIENT', 'SHAM_QUOTIENT', 'COLD', 'RAW_HISTORY', 'ABLATION'],
            'max_queries': MAXQ,
        },
        'warm_source_quotient': model_summary(warm_model),
        'sham_source_quotient': model_summary(sham_model),
        'target': {
            'task': TARGET,
            'states': len(states),
            'future_positive': sum(demo),
            'candidate_programs': len(keys),
            'any_truncation': any(s['truncated'] for s in states),
            'arms': arms,
        },
        'strict_gate': decision,
        'claim_boundary': 'Tests exact transfer of a source-learned quotient over developmental decision states. A support failure is evidence that this exact anonymous quotient is too fine, not evidence against state-conditioned developmental transfer in richer or differently induced quotient languages.',
    }

    out = HERE / 'results_v27_developmental_state_quotient'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
