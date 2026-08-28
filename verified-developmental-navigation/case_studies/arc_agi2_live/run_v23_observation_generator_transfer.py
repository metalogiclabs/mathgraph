import hashlib
import importlib.util
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


v19 = load('v19', 'run_v19_residual_history_policy.py')
v17 = v19.v17
v13 = v19.v13

ARC_COMMIT = '399030444e0ab0cc8b4e199870fb20b863846f34'
SOURCE_N = 12
TARGET_N = 6
MAX_TARGET_SCAN = 100
SCHEMA_BUDGET = 5
SHAM_SEED = 20260828
EXCLUDE_EVAL = set(v13.TARGETS) | {'60c09cac'}


def schema(k):
    """Mechanically quotient a V17 observation-program identity to a generator schema.

    Demo and literal placement coordinates are erased. Executable primitive/relation
    identity and discrete generator parameters are retained. This is selection among
    the already-frozen V17 meta-language, not invention of a new primitive.
    """
    parts = k.split(':')
    out = []
    for p in parts:
        if re.fullmatch(r'd\d+', p):
            out.append('d*')
        elif re.fullmatch(r'r\d+', p):
            out.append('r*')
        elif re.fullmatch(r'c\d+', p):
            out.append('c*')
        else:
            out.append(p)
    return ':'.join(out)


def audit_task(tid, task):
    states, keys = v17.states_for(task)
    for s in states:
        df, hs, _, _, trunc = v13.future_audit(task, s)
        s['demo_future_success'] = bool(df)
        s['heldout_success'] = bool(hs)
        s['truncated'] = bool(trunc)
    demo = [s['demo_future_success'] for s in states]
    held = [s['heldout_success'] for s in states]
    schemas = sorted({schema(k) for k in keys})
    groups = {g: [k for k in keys if schema(k) == g] for g in schemas}
    return {
        'task': tid,
        'states': states,
        'keys': keys,
        'schemas': schemas,
        'groups': groups,
        'demo': demo,
        'held': held,
        'truncated': any(s['truncated'] for s in states),
    }


def unresolved(p, chosen_schemas, labels=None):
    labels = p['demo'] if labels is None else labels
    keys = [k for g in chosen_schemas for k in p['groups'].get(g, ())]
    return v19.unresolved(p['states'], keys, labels)


def sufficient(p, chosen_schemas, labels=None):
    return unresolved(p, chosen_schemas, labels) == 0


def full_sufficient(p):
    return unresolved(p, p['schemas']) == 0 and unresolved(p, p['schemas'], p['held']) == 0


def mixed(p):
    return bool(p['states']) and any(p['demo']) and not all(p['demo'])


def source_basis(p):
    if p['truncated'] or not mixed(p) or not full_sufficient(p):
        return None
    basis, status, _, _ = v17.irreducible_basis(p['states'], p['keys'], 'demo_future_success')
    if basis is None or status not in ('IRREDUCIBLE_FOUND', 'EMPTY_SUFFICIENT'):
        return None
    # Source evidence must survive held-out examples before it may be retained.
    if v19.unresolved(p['states'], basis, p['held']) != 0:
        return None
    return basis


def collect_source(train):
    rows = []
    scan = []
    for tid in sorted(train):
        p = audit_task(tid, train[tid])
        basis = source_basis(p)
        scan.append({'task': tid, 'states': len(p['states']), 'mixed': mixed(p), 'truncated': p['truncated'], 'full_sufficient': full_sufficient(p) if mixed(p) and not p['truncated'] else False, 'retained': basis is not None})
        if basis is None:
            continue
        p['basis'] = basis
        rows.append(p)
        if len(rows) == SOURCE_N:
            break
    if len(rows) != SOURCE_N:
        raise RuntimeError(f'needed {SOURCE_N} source carriers, found {len(rows)}')
    return rows, scan


def compile_generator_policy(source_rows):
    hits = defaultdict(int)
    seen = defaultdict(int)
    literal_basis_ids = []
    evidence = []
    for p in source_rows:
        basis_schemas = {schema(k) for k in p['basis']}
        for g in p['schemas']:
            seen[g] += 1
            if g in basis_schemas:
                hits[g] += 1
        literal_basis_ids.extend((p['task'], k) for k in p['basis'])
        evidence.append({'task': p['task'], 'basis_size': len(p['basis']), 'basis_schemas': sorted(basis_schemas)})
    score = {g: (hits[g] + 1) / (seen[g] + 2) for g in seen}
    order = sorted(score, key=lambda g: (-score[g], g))
    return score, order, literal_basis_ids, evidence


def sham_order(score):
    names = sorted(score)
    vals = [score[g] for g in names]
    rng = random.Random(SHAM_SEED)
    rng.shuffle(vals)
    sham = dict(zip(names, vals))
    return sorted(sham, key=lambda g: (-sham[g], g)), sham


def cold_order(p):
    return list(sorted(p['schemas']))


def select_present(order, p, budget=SCHEMA_BUDGET):
    # A generated schema consumes budget even if it has no target instance: this
    # is intentional; a wrong inherited generator should be allowed to waste budget.
    return list(order[:budget])


def oracle_select(p, budget=SCHEMA_BUDGET):
    chosen = []
    trace = []
    remaining = list(p['schemas'])
    cur = unresolved(p, chosen)
    for step in range(budget):
        if cur == 0:
            break
        best = None
        for g in remaining:
            nxt = unresolved(p, chosen + [g])
            cand = (cur - nxt, -nxt, g)
            if best is None or cand > best[0]:
                best = (cand, g, nxt)
        if best is None or best[0][0] <= 0:
            break
        _, g, nxt = best
        chosen.append(g)
        remaining.remove(g)
        trace.append({'step': step + 1, 'schema': g, 'unresolved_before': cur, 'unresolved_after': nxt})
        cur = nxt
    return chosen, trace


def collect_targets(ev):
    rows = []
    scan = []
    scanned = 0
    for tid in sorted(ev):
        if tid in EXCLUDE_EVAL:
            continue
        if scanned >= MAX_TARGET_SCAN or len(rows) >= TARGET_N:
            break
        scanned += 1
        p = audit_task(tid, ev[tid])
        oracle, trace = oracle_select(p)
        legal = mixed(p) and not p['truncated'] and sufficient(p, oracle) and sufficient(p, oracle, p['held'])
        scan.append({'task': tid, 'states': len(p['states']), 'mixed': mixed(p), 'truncated': p['truncated'], 'schemas': len(p['schemas']), 'oracle_exact_within_budget': legal, 'oracle_schemas': oracle})
        if legal:
            p['oracle'] = oracle
            p['oracle_trace'] = trace
            rows.append(p)
    if len(rows) != TARGET_N:
        raise RuntimeError(f'needed {TARGET_N} oracle-feasible fresh targets within first {MAX_TARGET_SCAN}, found {len(rows)}')
    return rows, scan, scanned


def arm_result(p, selected):
    keys = [k for g in selected for k in p['groups'].get(g, ())]
    return {
        'schemas_selected': selected,
        'generated_atoms': len(keys),
        'demo_exact': v19.unresolved(p['states'], keys, p['demo']) == 0,
        'heldout_exact': v19.unresolved(p['states'], keys, p['held']) == 0,
        'demo_unresolved': v19.unresolved(p['states'], keys, p['demo']),
        'heldout_unresolved': v19.unresolved(p['states'], keys, p['held']),
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage run_v23_observation_generator_transfer.py TRAIN EVAL')
    train = v13.v2.v1.load_tasks(sys.argv[1])
    ev = v13.v2.v1.load_tasks(sys.argv[2])
    if len(train) != 400 or len(ev) != 400:
        raise SystemExit('unexpected ARC counts')

    source_rows, source_scan = collect_source(train)
    score, warm_order, raw_literal, source_evidence = compile_generator_policy(source_rows)
    sham_rank, sham_score = sham_order(score)
    target_rows, target_scan, scanned = collect_targets(ev)

    rows = []
    for p in target_rows:
        warm = select_present(warm_order, p)
        cold = select_present(cold_order(p), p)
        sham = select_present(sham_rank, p)
        # Raw source basis identities are task-qualified, so none can instantiate a
        # fresh target. RAW therefore has no generated schema unless a transferable
        # generator abstraction has been retained.
        raw = []
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
        rows.append({'task': p['task'], 'states': len(p['states']), 'candidate_schemas': len(p['schemas']), 'candidate_atoms': len(p['keys']), 'future_positive': sum(p['demo']), 'arms': arms, 'oracle_trace': p['oracle_trace']})

    names = ['WARM_GENERATOR', 'COLD_LEXICOGRAPHIC', 'RAW_LITERAL_HISTORY', 'SHAM_GENERATOR', 'ANCESTOR_ABLATION', 'ORACLE_CEILING']
    summary = {}
    for name in names:
        vals = [r['arms'][name] for r in rows]
        summary[name] = {
            'exact_tasks': sum(int(x['demo_exact'] and x['heldout_exact']) for x in vals),
            'demo_unresolved_total': sum(x['demo_unresolved'] for x in vals),
            'heldout_unresolved_total': sum(x['heldout_unresolved'] for x in vals),
            'generated_atoms_total': sum(x['generated_atoms'] for x in vals),
        }

    controls = ['COLD_LEXICOGRAPHIC', 'RAW_LITERAL_HISTORY', 'SHAM_GENERATOR', 'ANCESTOR_ABLATION']
    warm_only = [r['task'] for r in rows if r['arms']['WARM_GENERATOR']['demo_exact'] and r['arms']['WARM_GENERATOR']['heldout_exact'] and not any(r['arms'][c]['demo_exact'] and r['arms'][c]['heldout_exact'] for c in controls)]
    W = summary['WARM_GENERATOR']
    strict = (
        bool(warm_only)
        and W['exact_tasks'] > max(summary[c]['exact_tasks'] for c in controls)
        and W['demo_unresolved_total'] < min(summary[c]['demo_unresolved_total'] for c in controls)
        and W['heldout_unresolved_total'] <= min(summary[c]['heldout_unresolved_total'] for c in controls)
        and summary['ANCESTOR_ABLATION'] == summary['COLD_LEXICOGRAPHIC']
    )

    result = {
        'schema': 'verified-developmental-navigation.arc-observation-generator-transfer.v23',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': ARC_COMMIT},
        'precommit': {
            'source_selection': f'first {SOURCE_N} ARC training tasks in lexicographic id order with mixed future labels, no truncation, full V17 sufficiency, and a demo irreducible basis that is heldout-sufficient',
            'target_selection': f'first {TARGET_N} fresh ARC evaluation tasks (excluding V13-V22 observed targets) among first {MAX_TARGET_SCAN} scanned, with mixed labels, no truncation, and an oracle-exact V17 generator solution within {SCHEMA_BUDGET} schemas',
            'schema_budget': SCHEMA_BUDGET,
            'transfer_object': 'source-frequency estimate of which mechanically anonymized V17 observation-generator schemas occur in heldout-valid irreducible source bases',
            'schema_quotient': 'erase demo and literal row/column indices; retain executable primitive/relation and other generator parameters',
            'warm_selection': 'global source-derived generator ranking frozen before target evaluation',
            'cold_selection': 'lexicographic generator ranking',
            'raw_control': 'task-qualified literal source basis atoms only; cannot instantiate fresh target',
            'sham_control': 'same source generator scores deterministically permuted across generator identities',
            'ablation': 'remove inherited generator policy and revert exactly to cold',
            'oracle': 'target-label greedy generator selection; ceiling only',
            'strict_gate': 'at least one WARM-only exact target; WARM exact count above every non-oracle control; WARM demo unresolved total below every non-oracle control; WARM heldout unresolved no worse than every control; exact ablation equals cold',
        },
        'claim_boundary': 'Tests transfer of an observation-language generator selection policy inside the already-supplied V17 meta-language. A pass would establish source-distinct developmental change at the language-selection boundary, not invention of new primitive observation constructors.',
        'source_tasks': [p['task'] for p in source_rows],
        'source_evidence': source_evidence,
        'generator_scores': score,
        'warm_generator_order': warm_order,
        'sham_generator_scores': sham_score,
        'raw_literal_source_basis_count': len(raw_literal),
        'target_tasks': [p['task'] for p in target_rows],
        'source_scan': source_scan,
        'target_scan': target_scan,
        'targets_scanned': scanned,
        'tasks': rows,
        'summary': summary,
        'warm_only_exact_targets': warm_only,
        'strict_gate': 'PASS_OBSERVATION_GENERATOR_CROSS_TASK_COMPOUNDING' if strict else 'FAIL_OBSERVATION_GENERATOR_CROSS_TASK_COMPOUNDING',
    }
    out = HERE / 'results_v23_observation_generator_transfer'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'source_tasks': result['source_tasks'], 'target_tasks': result['target_tasks'], 'warm_generator_order': warm_order[:12], 'summary': summary, 'warm_only_exact_targets': warm_only, 'strict_gate': result['strict_gate']}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
