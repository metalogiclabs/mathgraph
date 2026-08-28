import hashlib
import importlib.util
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, file):
    sp = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


v17 = load('v17', 'run_v17_cumulative_future_quotient.py')
v13 = v17.v13

# PRECOMMITTED before this run.
MAX_QUERIES = 8
SHUFFLE_SEED = 20260828


def atom_order(keys):
    # Semantic names do not determine proposal order. Treat each already-admitted
    # executable observation as an opaque program and order by a stable hash.
    return sorted(keys, key=lambda k: hashlib.sha256(k.encode()).hexdigest())


def bucket_indices(states, chosen):
    b = defaultdict(list)
    for i, s in enumerate(states):
        b[tuple(bool(s['obs'][k]) for k in chosen)].append(i)
    return b


def unresolved_pairs(states, chosen, labels):
    n = 0
    for inds in bucket_indices(states, chosen).values():
        p = sum(bool(labels[i]) for i in inds)
        z = len(inds) - p
        n += p * z
    return n


def sufficient(states, chosen, labels):
    return unresolved_pairs(states, chosen, labels) == 0


def first_true_collision(states, chosen, labels):
    # The verifier returns only one currently unresolved counterexample pair,
    # not the full target partition and not a feature name.
    for inds in bucket_indices(states, chosen).values():
        pos = next((i for i in inds if labels[i]), None)
        neg = next((i for i in inds if not labels[i]), None)
        if pos is not None and neg is not None:
            return pos, neg
    return None


def first_atom_separating(states, keys, chosen, pair):
    if pair is None:
        return None
    a, b = pair
    for k in atom_order([x for x in keys if x not in chosen]):
        if bool(states[a]['obs'][k]) != bool(states[b]['obs'][k]):
            return k
    return None


def run_real_residual(states, keys, true_labels):
    chosen = []
    trace = []
    for q in range(MAX_QUERIES):
        before = unresolved_pairs(states, chosen, true_labels)
        if before == 0:
            break
        pair = first_true_collision(states, chosen, true_labels)
        k = first_atom_separating(states, keys, chosen, pair)
        if k is None:
            trace.append({'query': q + 1, 'status': 'NO_SEPARATOR_IN_FULL_LANGUAGE', 'pair': pair})
            break
        chosen.append(k)
        after = unresolved_pairs(states, chosen, true_labels)
        trace.append({'query': q + 1, 'pair': pair, 'atom': k,
                      'true_unresolved_before': before, 'true_unresolved_after': after})
    return chosen, trace


def run_no_residual(states, keys, true_labels):
    chosen = []
    trace = []
    order = atom_order(keys)
    for q, k in enumerate(order[:MAX_QUERIES], 1):
        before = unresolved_pairs(states, chosen, true_labels)
        if before == 0:
            break
        chosen.append(k)
        after = unresolved_pairs(states, chosen, true_labels)
        trace.append({'query': q, 'atom': k,
                      'true_unresolved_before': before, 'true_unresolved_after': after})
    return chosen, trace


def run_shuffled_residual(states, keys, true_labels, task_id):
    rng = random.Random(SHUFFLE_SEED + int(hashlib.sha256(task_id.encode()).hexdigest()[:8], 16))
    fake = list(true_labels)
    rng.shuffle(fake)
    chosen = []
    trace = []
    for q in range(MAX_QUERIES):
        before = unresolved_pairs(states, chosen, true_labels)
        if before == 0:
            break
        pair = first_true_collision(states, chosen, fake)
        k = first_atom_separating(states, keys, chosen, pair)
        if k is None:
            trace.append({'query': q + 1, 'status': 'NO_FAKE_SEPARATOR', 'pair': pair})
            break
        chosen.append(k)
        after = unresolved_pairs(states, chosen, true_labels)
        trace.append({'query': q + 1, 'fake_pair': pair, 'atom': k,
                      'true_unresolved_before': before, 'true_unresolved_after': after})
    return chosen, trace


def run_oracle(states, keys, true_labels):
    # Ceiling only: sees the full true partition and chooses maximum collision reduction.
    chosen = []
    trace = []
    remaining = atom_order(keys)
    for q in range(MAX_QUERIES):
        before = unresolved_pairs(states, chosen, true_labels)
        if before == 0:
            break
        best = None
        for k in remaining:
            after = unresolved_pairs(states, chosen + [k], true_labels)
            gain = before - after
            cand = (gain, -after, hashlib.sha256(k.encode()).hexdigest())
            if best is None or cand > best[0]:
                best = (cand, k, after)
        if best is None or best[0][0] <= 0:
            break
        _, k, after = best
        chosen.append(k)
        remaining.remove(k)
        trace.append({'query': q + 1, 'atom': k,
                      'true_unresolved_before': before, 'true_unresolved_after': after})
    return chosen, trace


def evaluate_arm(states, chosen, true_demo, true_held):
    return {
        'queries_used': len(chosen),
        'demo_exact': sufficient(states, chosen, true_demo),
        'heldout_exact': sufficient(states, chosen, true_held),
        'demo_unresolved_pairs': unresolved_pairs(states, chosen, true_demo),
        'heldout_unresolved_pairs': unresolved_pairs(states, chosen, true_held),
        'selected_atoms': chosen,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage run_v18_residual_induced_query_synthesis.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    rows = []
    for tid in v13.TARGETS:
        task = ev[tid]
        states, keys = v17.states_for(task)
        for s in states:
            df, hs, w, tr, trunc = v13.future_audit(task, s)
            s['demo_future_success'] = bool(df)
            s['heldout_success'] = bool(hs)
            s['truncated'] = bool(trunc)
        demo = [s['demo_future_success'] for s in states]
        held = [s['heldout_success'] for s in states]

        arms = {}
        for name, runner in [
            ('REAL_RESIDUAL', lambda: run_real_residual(states, keys, demo)),
            ('NO_RESIDUAL', lambda: run_no_residual(states, keys, demo)),
            ('SHUFFLED_RESIDUAL', lambda: run_shuffled_residual(states, keys, demo, tid)),
            ('FULL_ORACLE_CEILING', lambda: run_oracle(states, keys, demo)),
        ]:
            chosen, trace = runner()
            arms[name] = {**evaluate_arm(states, chosen, demo, held), 'trace': trace}

        rows.append({
            'task': tid,
            'states': len(states),
            'future_positive': sum(demo),
            'candidate_observation_programs': len(keys),
            'full_language_demo_exact': v17.sufficient(states, 'demo_future_success', keys),
            'any_future_search_truncation': any(s['truncated'] for s in states),
            'arms': arms,
        })

    real_solved = sum(r['arms']['REAL_RESIDUAL']['demo_exact'] for r in rows)
    no_solved = sum(r['arms']['NO_RESIDUAL']['demo_exact'] for r in rows)
    sham_solved = sum(r['arms']['SHUFFLED_RESIDUAL']['demo_exact'] for r in rows)
    oracle_solved = sum(r['arms']['FULL_ORACLE_CEILING']['demo_exact'] for r in rows)
    real_held = sum(r['arms']['REAL_RESIDUAL']['heldout_exact'] for r in rows)

    strict = (
        real_solved > no_solved and
        real_solved > sham_solved and
        real_held == real_solved and
        all(r['full_language_demo_exact'] for r in rows) and
        not any(r['any_future_search_truncation'] for r in rows)
    )

    result = {
        'schema': 'verified-developmental-navigation.arc-residual-induced-query-synthesis.v18',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'frozen_targets': v13.TARGETS,
        'precommit': {
            'max_queries_per_task': MAX_QUERIES,
            'shuffle_seed': SHUFFLE_SEED,
            'candidate_language': 'the cumulative executable low-level observation programs admitted before V18; no new feature family is added',
            'proposal_order': 'SHA256(atom program name), fixed before labels are inspected',
            'real_feedback': 'one unresolved positive/negative verified-future collision only',
            'controls': ['NO_RESIDUAL', 'SHUFFLED_RESIDUAL', 'FULL_ORACLE_CEILING'],
        },
        'claim_boundary': 'Tests whether true verifier residuals make a sufficient observation basis discoverable under a tight query budget inside an already-frozen low-level observation language. It does not establish unrestricted invention of new observation primitives.',
        'tasks': rows,
        'summary': {
            'real_residual_demo_exact_tasks': real_solved,
            'real_residual_heldout_exact_tasks': real_held,
            'no_residual_demo_exact_tasks': no_solved,
            'shuffled_residual_demo_exact_tasks': sham_solved,
            'oracle_demo_exact_tasks': oracle_solved,
        },
        'strict_gate': 'PASS_RESIDUAL_INDUCED_QUERY_SYNTHESIS' if strict else 'FAIL_RESIDUAL_INDUCED_QUERY_SYNTHESIS',
    }
    out = HERE / 'results_v18_residual_induced_query_synthesis'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
