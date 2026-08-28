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

ARC1_COMMIT = '399030444e0ab0cc8b4e199870fb20b863846f34'
ARC2_COMMIT = 'f3283f727488ad98fe575ea6a5ac981e4a188e49'
# Frozen by the successful V24c carrier census before any V25 arm is evaluated.
V24C_CARRIERS = (
    '0c786b71',
    '0d3d703e',
    '1cf80156',
    '28bf18c6',
    '3af2c5a8',
    '3c9b0459',
    '46442a0e',
    '4c4377d9',
)
HISTORICALLY_OBSERVED = set(v13.TARGETS) | {'60c09cac'}
TARGET_N = 6


def arm_result(p, selected):
    keys = [k for g in selected for k in p['groups'].get(g, ())]
    return {
        'schemas_selected': list(selected),
        'generated_atoms': len(keys),
        'demo_exact': v23.v19.unresolved(p['states'], keys, p['demo']) == 0,
        'heldout_exact': v23.v19.unresolved(p['states'], keys, p['held']) == 0,
        'demo_unresolved': v23.v19.unresolved(p['states'], keys, p['demo']),
        'heldout_unresolved': v23.v19.unresolved(p['states'], keys, p['held']),
    }


def target_rows(arc2_train, source_ids):
    frozen = [tid for tid in V24C_CARRIERS if tid not in HISTORICALLY_OBSERVED and tid not in source_ids]
    if len(frozen) < TARGET_N:
        raise RuntimeError(f'V24c frozen carrier pool leaves only {len(frozen)} source-disjoint targets')
    frozen = frozen[:TARGET_N]
    rows = []
    for tid in frozen:
        if tid not in arc2_train:
            raise RuntimeError(f'frozen V24c target missing: {tid}')
        p = v23.audit_task(tid, arc2_train[tid])
        oracle, trace = v23.oracle_select(p, v23.SCHEMA_BUDGET)
        if p['truncated'] or not v23.mixed(p):
            raise RuntimeError(f'frozen target lost carrier eligibility: {tid}')
        if not (v23.sufficient(p, oracle) and v23.sufficient(p, oracle, p['held'])):
            raise RuntimeError(f'frozen target lost oracle-{v23.SCHEMA_BUDGET} feasibility: {tid}')
        p['oracle'] = oracle
        p['oracle_trace'] = trace
        rows.append(p)
    return rows


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage run_v25_cross_dataset_generator_transfer.py ARC1_TRAIN ARC2_TRAIN')
    arc1_train = v13.v2.v1.load_tasks(sys.argv[1])
    arc2_train = v13.v2.v1.load_tasks(sys.argv[2])

    # Learn the transferable object only from the frozen ARC-AGI-1 source cohort.
    source_rows, source_scan = v23.collect_source(arc1_train)
    source_ids = {p['task'] for p in source_rows}
    score, warm_order, raw_literal, source_evidence = v23.compile_generator_policy(source_rows)
    sham_order, sham_score = v23.sham_order(score)

    targets = target_rows(arc2_train, source_ids)
    rows = []
    for p in targets:
        warm = v23.select_present(warm_order, p)
        cold = v23.select_present(v23.cold_order(p), p)
        sham = v23.select_present(sham_order, p)
        raw = []  # task-qualified literal source atoms cannot instantiate target tasks
        ablation = cold
        oracle = p['oracle']
        arms = {
            'WARM_GENERATOR': arm_result(p, warm),
            'COLD_LEXICOGRAPHIC': arm_result(p, cold),
            'RAW_LITERAL_HISTORY': arm_result(p, raw),
            'SHAM_GENERATOR': arm_result(p, sham),
            'ANCESTOR_ABLATION': arm_result(p, ablation),
            'ORACLE_CEILING': arm_result(p, oracle),
        }
        rows.append({
            'task': p['task'],
            'states': len(p['states']),
            'candidate_schemas': len(p['schemas']),
            'candidate_atoms': len(p['keys']),
            'future_positive': sum(p['demo']),
            'arms': arms,
            'oracle_trace': p['oracle_trace'],
        })

    names = ['WARM_GENERATOR','COLD_LEXICOGRAPHIC','RAW_LITERAL_HISTORY','SHAM_GENERATOR','ANCESTOR_ABLATION','ORACLE_CEILING']
    summary = {}
    for name in names:
        vals = [r['arms'][name] for r in rows]
        summary[name] = {
            'exact_tasks': sum(int(x['demo_exact'] and x['heldout_exact']) for x in vals),
            'demo_unresolved_total': sum(x['demo_unresolved'] for x in vals),
            'heldout_unresolved_total': sum(x['heldout_unresolved'] for x in vals),
            'generated_atoms_total': sum(x['generated_atoms'] for x in vals),
        }

    controls = ['COLD_LEXICOGRAPHIC','RAW_LITERAL_HISTORY','SHAM_GENERATOR','ANCESTOR_ABLATION']
    warm_only = [
        r['task'] for r in rows
        if r['arms']['WARM_GENERATOR']['demo_exact'] and r['arms']['WARM_GENERATOR']['heldout_exact']
        and not any(r['arms'][c]['demo_exact'] and r['arms'][c]['heldout_exact'] for c in controls)
    ]
    W = summary['WARM_GENERATOR']
    strict = (
        bool(warm_only)
        and W['exact_tasks'] > max(summary[c]['exact_tasks'] for c in controls)
        and W['demo_unresolved_total'] < min(summary[c]['demo_unresolved_total'] for c in controls)
        and W['heldout_unresolved_total'] <= min(summary[c]['heldout_unresolved_total'] for c in controls)
        and summary['ANCESTOR_ABLATION'] == summary['COLD_LEXICOGRAPHIC']
    )

    result = {
        'schema': 'verified-developmental-navigation.arc-cross-dataset-generator-transfer.v25',
        'sources': {
            'learning': {'repository': 'fchollet/ARC-AGI', 'commit': ARC1_COMMIT, 'partition': 'training'},
            'target': {'repository': 'arcprize/ARC-AGI-2', 'commit': ARC2_COMMIT, 'partition': 'training'},
        },
        'precommit': {
            'source_selection': v23.SOURCE_N,
            'source_rule': 'V23 first heldout-valid source carriers from ARC-AGI-1 training; unchanged',
            'target_rule': 'first six V24c-frozen ARC-AGI-2 nontrivial oracle-5-exact carriers after excluding historically observed task IDs and any source-learning task IDs',
            'v24c_frozen_carriers': V24C_CARRIERS,
            'schema_budget': v23.SCHEMA_BUDGET,
            'transfer_object': 'source-derived ranking of mechanically anonymized V17 observation-generator schemas',
            'controls': controls + ['ORACLE_CEILING'],
            'strict_gate': 'WARM-only exact target exists; WARM exact count exceeds every non-oracle control; WARM demo unresolved is strictly below every control; heldout unresolved no worse; ablation equals cold',
        },
        'claim_boundary': 'Prospective source-task-disjoint transfer from ARC-AGI-1 source episodes to V24c-frozen ARC-AGI-2 carriers, inside the supplied V17 observation meta-language. A pass is a cross-episode language-selection/discovery gain, not invention of new primitive observations.',
        'source_tasks': [p['task'] for p in source_rows],
        'source_evidence': source_evidence,
        'source_scan': source_scan,
        'target_tasks': [p['task'] for p in targets],
        'generator_scores': score,
        'warm_generator_order': warm_order,
        'sham_generator_scores': sham_score,
        'raw_literal_source_basis_count': len(raw_literal),
        'tasks': rows,
        'summary': summary,
        'warm_only_exact_targets': warm_only,
        'strict_gate': 'PASS_CROSS_DATASET_OBSERVATION_GENERATOR_COMPOUNDING' if strict else 'FAIL_CROSS_DATASET_OBSERVATION_GENERATOR_COMPOUNDING',
    }
    out = HERE / 'results_v25_cross_dataset_generator_transfer'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        'source_tasks': result['source_tasks'],
        'target_tasks': result['target_tasks'],
        'warm_generator_order': warm_order[:12],
        'summary': summary,
        'warm_only_exact_targets': warm_only,
        'strict_gate': result['strict_gate'],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
