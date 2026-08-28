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

v21 = load('v21', 'run_v21_transfer_frontier_census.py')
v13 = v21.v13
EXCLUDE = set(v13.TARGETS) | {'60c09cac'}


def audit_split(split_name, tasks):
    rows = []
    for tid in sorted(tasks):
        if tid in EXCLUDE:
            continue
        try:
            r = v21.audit_task(tid, tasks[tid])
            r['split'] = split_name
            rows.append(r)
        except Exception as e:
            rows.append({'task': tid, 'split': split_name, 'status': 'UNSUPPORTED', 'error': type(e).__name__ + ': ' + str(e)[:240]})
    return rows


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: run_v31_cross_split_fresh_frontier_census.py TRAIN EVAL')
    train = v13.v2.v1.load_tasks(sys.argv[1])
    ev = v13.v2.v1.load_tasks(sys.argv[2])
    rows = audit_split('training', train) + audit_split('evaluation', ev)
    audited = [r for r in rows if r.get('status') == 'AUDITED']
    positive = [r for r in audited if r.get('future_positive', 0) > 0]
    eligible = [r for r in positive if r.get('oracle', {}).get('exact') and not r.get('any_truncation') and (r.get('headroom_queries') or 0) > 0]
    eligible = sorted(eligible, key=lambda r: (-r['headroom_queries'], r['oracle']['queries'], r['split'], r['task']))
    fresh = eligible[0] if eligible else None
    result = {
        'schema': 'verified-developmental-navigation.arc-cross-split-fresh-frontier-census.v31',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'pool': 'all ARC training + evaluation tasks excluding four V13 lineage source tasks and previously used target 60c09cac',
            'max_states': v21.MAX_STATES,
            'continuation_language': 'unchanged V13 one-further-base continuation',
            'candidate_language': 'unchanged V17 observation language',
            'warm_or_v30_evaluated_for_selection': False,
            'selection': 'largest COLD-minus-oracle query headroom; then fewer oracle queries; then split; then task ID'
        },
        'summary': {
            'pool': len(rows),
            'audited': len(audited),
            'positive_support_tasks': len(positive),
            'eligible_frontier': len(eligible),
            'unsupported': sum(r.get('status') == 'UNSUPPORTED' for r in rows),
            'state_capped': sum(r.get('status') == 'STATE_CAP' for r in rows),
            'full_language_collisions': sum(r.get('status') == 'FULL_LANGUAGE_COLLISION' for r in rows),
        },
        'eligible_frontier': [
            {'split': r['split'], 'task': r['task'], 'future_positive': r['future_positive'], 'states': r['states'], 'cold': r['cold'], 'oracle': r['oracle'], 'headroom_queries': r['headroom_queries']}
            for r in eligible
        ],
        'frozen_fresh_target': None if fresh is None else {
            'split': fresh['split'], 'task': fresh['task'], 'future_positive': fresh['future_positive'], 'states': fresh['states'], 'cold': fresh['cold'], 'oracle': fresh['oracle'], 'headroom_queries': fresh['headroom_queries']
        },
        'decision': 'FRESH_TRANSFER_FRONTIER_FOUND' if fresh else ('POSITIVE_SUPPORT_BUT_NO_FRESH_HEADROOM' if positive else 'FRESH_CONTINUATION_SUPPORT_COLLAPSE')
    }
    out = HERE / 'results_v31_cross_split_fresh_frontier_census'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
