import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


v23 = load('v23', 'run_v23_observation_generator_transfer.py')
v19 = v23.v19
v17 = v23.v17
v13 = v23.v13
MAX_SCAN = 100


def greedy_all_schemas(p):
    chosen = []
    remaining = list(p['schemas'])
    cur = v23.unresolved(p, chosen)
    trace = []
    while cur > 0 and remaining:
        best = None
        for g in remaining:
            nxt = v23.unresolved(p, chosen + [g])
            cand = (cur - nxt, -nxt, g)
            if best is None or cand > best[0]:
                best = (cand, g, nxt)
        if best is None or best[0][0] <= 0:
            break
        _, g, nxt = best
        chosen.append(g)
        remaining.remove(g)
        trace.append({'schema': g, 'before': cur, 'after': nxt})
        cur = nxt
    return chosen, trace


def representative_collision(p):
    # Full-language collision, if any, as program audits only; no semantic interpretation.
    if v23.unresolved(p, p['schemas']) == 0:
        return None
    keys = p['keys']
    buckets = {}
    for i, s in enumerate(p['states']):
        sig = tuple(bool(s['obs'][k]) for k in keys)
        buckets.setdefault(sig, []).append(i)
    for inds in buckets.values():
        pos = next((i for i in inds if p['demo'][i]), None)
        neg = next((i for i in inds if not p['demo'][i]), None)
        if pos is not None and neg is not None:
            return {
                'positive_audit': p['states'][pos].get('program_audit'),
                'negative_audit': p['states'][neg].get('program_audit'),
            }
    return None


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v23b_fresh_carrier_census.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    rows = []
    scanned = 0
    for tid in sorted(ev):
        if tid in v23.EXCLUDE_EVAL:
            continue
        if scanned >= MAX_SCAN:
            break
        scanned += 1
        p = v23.audit_task(tid, ev[tid])
        if not v23.mixed(p) or p['truncated']:
            rows.append({'task': tid, 'states': len(p['states']), 'mixed': v23.mixed(p), 'truncated': p['truncated']})
            continue
        oracle5, trace5 = v23.oracle_select(p, v23.SCHEMA_BUDGET)
        greedy, gtrace = greedy_all_schemas(p)
        full_demo = v23.unresolved(p, p['schemas'])
        full_held = v23.unresolved(p, p['schemas'], p['held'])
        rows.append({
            'task': tid,
            'states': len(p['states']),
            'mixed': True,
            'truncated': False,
            'schemas': len(p['schemas']),
            'atoms': len(p['keys']),
            'future_positive': sum(p['demo']),
            'full_demo_unresolved': full_demo,
            'full_heldout_unresolved': full_held,
            'full_exact': full_demo == 0 and full_held == 0,
            'oracle5_schemas': oracle5,
            'oracle5_demo_unresolved': v23.unresolved(p, oracle5),
            'oracle5_heldout_unresolved': v23.unresolved(p, oracle5, p['held']),
            'oracle5_exact': v23.sufficient(p, oracle5) and v23.sufficient(p, oracle5, p['held']),
            'greedy_all_schema_count': len(greedy),
            'greedy_all_exact': v23.sufficient(p, greedy) and v23.sufficient(p, greedy, p['held']),
            'representative_full_collision': representative_collision(p),
            'oracle5_trace': trace5,
            'greedy_all_trace': gtrace,
        })
    mixed = [r for r in rows if r.get('mixed') and not r.get('truncated')]
    full_exact = [r for r in mixed if r.get('full_exact')]
    oracle5 = [r for r in mixed if r.get('oracle5_exact')]
    decision = (
        'FRESH_V17_LANGUAGE_EXHAUSTED' if mixed and not full_exact
        else 'FRESH_V17_FULL_LANGUAGE_HAS_EXACT_CARRIERS_BUT_SCHEMA5_EXHAUSTED' if full_exact and not oracle5
        else 'FRESH_V17_SCHEMA5_HAS_EXACT_CARRIERS'
    )
    result = {
        'schema': 'verified-developmental-navigation.arc-fresh-carrier-census.v23b',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': v23.ARC_COMMIT},
        'exclusions': sorted(v23.EXCLUDE_EVAL),
        'max_scan': MAX_SCAN,
        'scanned': scanned,
        'mixed_nontruncated': len(mixed),
        'full_v17_exact': len(full_exact),
        'oracle5_exact': len(oracle5),
        'full_v17_exact_tasks': [r['task'] for r in full_exact],
        'oracle5_exact_tasks': [r['task'] for r in oracle5],
        'decision': decision,
        'rows': rows,
    }
    out = HERE / 'results_v23b_fresh_carrier_census'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
