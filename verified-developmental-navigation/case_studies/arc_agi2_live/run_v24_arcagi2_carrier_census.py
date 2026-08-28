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
v13 = v23.v13

ARC2_COMMIT = 'f3283f727488ad98fe575ea6a5ac981e4a188e49'


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v24_arcagi2_carrier_census.py ARC2_EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    rows = []
    for tid in sorted(ev):
        p = v23.audit_task(tid, ev[tid])
        row = {
            'task': tid,
            'states': len(p['states']),
            'mixed': v23.mixed(p),
            'truncated': p['truncated'],
            'schemas': len(p['schemas']),
            'atoms': len(p['keys']),
            'future_positive': sum(p['demo']),
        }
        if v23.mixed(p) and not p['truncated']:
            oracle5, trace5 = v23.oracle_select(p, v23.SCHEMA_BUDGET)
            row.update({
                'full_demo_unresolved': v23.unresolved(p, p['schemas']),
                'full_heldout_unresolved': v23.unresolved(p, p['schemas'], p['held']),
                'full_exact': v23.full_sufficient(p),
                'oracle5_schemas': oracle5,
                'oracle5_demo_unresolved': v23.unresolved(p, oracle5),
                'oracle5_heldout_unresolved': v23.unresolved(p, oracle5, p['held']),
                'oracle5_exact': v23.sufficient(p, oracle5) and v23.sufficient(p, oracle5, p['held']),
                'oracle5_trace': trace5,
            })
        rows.append(row)
    mixed = [r for r in rows if r['mixed'] and not r['truncated']]
    full_exact = [r for r in mixed if r.get('full_exact')]
    oracle5 = [r for r in mixed if r.get('oracle5_exact')]
    result = {
        'schema': 'verified-developmental-navigation.arcagi2-carrier-census.v24',
        'source': {'repository': 'arcprize/ARC-AGI-2', 'commit': ARC2_COMMIT},
        'tasks_total': len(rows),
        'mixed_nontruncated': len(mixed),
        'full_v17_exact': len(full_exact),
        'oracle5_exact': len(oracle5),
        'mixed_tasks': [r['task'] for r in mixed],
        'full_v17_exact_tasks': [r['task'] for r in full_exact],
        'oracle5_exact_tasks': [r['task'] for r in oracle5],
        'decision': 'ARC2_HAS_TRANSFER_CARRIERS' if mixed else 'ARC2_NO_NONTRIVIAL_V13_CARRIERS',
        'rows': rows,
    }
    out = HERE / 'results_v24_arcagi2_carrier_census'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
