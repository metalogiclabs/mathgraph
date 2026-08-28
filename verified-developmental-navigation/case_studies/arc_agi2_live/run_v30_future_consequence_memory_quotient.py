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

v29 = load('v29', 'run_v29_minimal_causal_observation_basis.py')
v28 = v29.v28
v27 = v28.v27
v23 = v27.v23
v19 = v27.v19
v13 = v27.v13
SOURCE = v27.SOURCE
TARGET = v27.TARGET
MAXQ = v27.MAXQ


def prepare_target(ev):
    return v23.prepare(ev[TARGET])


def source_atoms(ev):
    model = v27.learn_quotient(ev, sham=False)
    return sorted(set(model['source_atoms'])), model


def reachable_residual_snapshots(states, keys, demo, held, true_atoms):
    snaps = []
    warm = v28.make_arm(states, keys, demo, held, true_atoms)
    _, cold_trace = v19.run_history(states, keys, demo, False)
    prefixes = [()]
    warm_atoms = [t['atom'] for t in warm.get('trace', [])]
    cold_atoms = [t['atom'] for t in cold_trace]
    for seq in (warm_atoms, cold_atoms):
        for i in range(1, len(seq) + 1):
            prefixes.append(tuple(seq[:i]))

    seen = set()
    for pref in prefixes:
        cols = [keys.index(a) for a in pref if a in keys]
        buckets = {}
        for i, s in enumerate(states):
            sig = tuple(bool(s['obs'][j]) for j in cols)
            buckets.setdefault(sig, []).append(i)
        unresolved_pairs = []
        for ids in buckets.values():
            pos = [i for i in ids if demo[i]]
            neg = [i for i in ids if not demo[i]]
            for a in pos:
                for b in neg:
                    unresolved_pairs.append((a, b))
        fingerprint = tuple(unresolved_pairs)
        if fingerprint not in seen:
            seen.add(fingerprint)
            snaps.append({'prefix': list(pref), 'pairs': unresolved_pairs})
    return snaps


def consequence_vector(atom, states, keys, snapshots):
    if atom not in keys:
        return tuple(('ABSENT', 0, 0) for _ in snapshots)
    j = keys.index(atom)
    vec = []
    for snap in snapshots:
        pairs = snap['pairs']
        sep = [(a, b) for (a, b) in pairs if bool(states[a]['obs'][j]) != bool(states[b]['obs'][j])]
        if not sep:
            vec.append(('NOSEP', len(pairs), len(pairs)))
        else:
            vec.append(('SEP', len(pairs), len(pairs) - len(sep)))
    return tuple(vec)


def eval_atoms(states, keys, demo, held, atoms):
    return v28.make_arm(states, keys, demo, held, list(atoms))


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: run_v30_future_consequence_memory_quotient.py EVAL')
    ev = v13.v2.v1.load_tasks(sys.argv[1])
    atoms, model = source_atoms(ev)
    states, keys, demo, held = prepare_target(ev)

    target_supported = [a for a in atoms if a in set(keys)]
    snapshots = reachable_residual_snapshots(states, keys, demo, held, atoms)

    classes = {}
    for a in target_supported:
        vec = consequence_vector(a, states, keys, snapshots)
        classes.setdefault(vec, []).append(a)

    quotient_classes = []
    reps = []
    for idx, (vec, members) in enumerate(sorted(classes.items(), key=lambda kv: kv[1])):
        members = sorted(members)
        rep = members[0]
        reps.append(rep)
        quotient_classes.append({
            'class_id': idx,
            'members': members,
            'representative': rep,
            'consequence_vector': [list(x) for x in vec],
        })

    full_warm = eval_atoms(states, keys, demo, held, atoms)
    quotient_all = eval_atoms(states, keys, demo, held, reps)
    cc, ct = v19.run_history(states, keys, demo, False)
    cold = v27.arm(states, cc, ct, 0, demo, held)

    successful = []
    for r in range(len(reps) + 1):
        for sub in itertools.combinations(reps, r):
            arm = eval_atoms(states, keys, demo, held, sub)
            if arm['demo_exact'] and arm['heldout_exact'] and arm['queries'] <= full_warm['queries']:
                successful.append((sub, arm))
        if successful:
            break

    minimal = []
    if successful:
        best_q = min(a['queries'] for _, a in successful)
        for sub, arm in successful:
            if arm['queries'] == best_q:
                minimal.append({'representatives': list(sub), **{k: arm[k] for k in ['queries','transfer_hits','demo_exact','heldout_exact','unresolved']}})

    best_card = len(successful[0][0]) if successful else None
    decision = 'PASS_AUTOMATIC_FUTURE_CONSEQUENCE_RECOMPRESSION' if (
        successful
        and best_card < len(target_supported)
        and min(a['queries'] for _, a in successful) <= full_warm['queries']
        and full_warm['queries'] < cold['queries']
        and not model['truncated']
        and not any(s['truncated'] for s in states)
    ) else 'FAIL_AUTOMATIC_FUTURE_CONSEQUENCE_RECOMPRESSION'

    result = {
        'schema': 'verified-developmental-navigation.arc-future-consequence-memory-quotient.v30',
        'source': {'repository': 'fchollet/ARC-AGI', 'commit': '399030444e0ab0cc8b4e199870fb20b863846f34'},
        'precommit': {
            'source_tasks': SOURCE,
            'target_task': TARGET,
            'candidate_language': 'unchanged V17 observation language and V13 continuation language',
            'equivalence': 'two retained atoms equivalent iff their complete verified separating/nonseparating unresolved-count consequence vector agrees on every residual snapshot from frozen WARM and COLD target trajectories',
            'representative_choice': 'lexicographically first atom in each equivalence class',
            'recompression_search': 'exhaustive subsets over quotient representatives, increasing cardinality',
            'success': 'smallest representative subset preserving full-WARM query count or better with exact demo+heldout',
            'semantic_atom_names_used_for_selection': False,
        },
        'source_memory': {
            'unique_source_atoms': len(atoms),
            'target_supported_atoms': len(target_supported),
            'target_supported_atom_names': target_supported,
        },
        'future_snapshots': len(snapshots),
        'quotient': {
            'class_count': len(quotient_classes),
            'classes': quotient_classes,
            'all_representatives': reps,
        },
        'arms': {
            'FULL_WARM': {k: full_warm[k] for k in ['queries','transfer_hits','demo_exact','heldout_exact','unresolved']},
            'QUOTIENT_ALL_REPS': {k: quotient_all[k] for k in ['queries','transfer_hits','demo_exact','heldout_exact','unresolved']},
            'COLD': {k: cold[k] for k in ['queries','transfer_hits','demo_exact','heldout_exact','unresolved']},
        },
        'automatic_recompression': {
            'minimum_cardinality': best_card,
            'best_subsets': minimal,
            'successful_subsets_at_min_cardinality': len(successful),
        },
        'strict_gate': decision,
        'claim_boundary': 'Post-V28 mechanism audit on the already-known target. Shows whether future-consequence equivalence can automatically compress retained source memory while preserving the verified transfer advantage; not blind evidence of broad ARC generalization.',
    }

    out = HERE / 'results_v30_future_consequence_memory_quotient'
    out.mkdir(exist_ok=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
