#!/usr/bin/env python3
"""V53 finite developmental-ratchet crown-jewel calibration.

Purpose
-------
Test, exhaustively in the 3-state / 3-continuation binary world, whether the
relational core + quotient-capability compatibility can support the causal
shape required by developmental capability growth:

  exhausted K0 closure
    -> verifier-residual-selected O1
    -> strict closure expansion (+ transfer to another start)
    -> O1-exposed separator c*
    -> refined observational interface
    -> O2 becomes quotient-well-defined / discoverable
    -> O1+O2 adds capability
    -> ancestor ablation removes c* and therefore O2 discoverability.

This is a FINITE EXHAUSTIVE CALIBRATION, not the natural external-task crown
jewel. O1/O2 are unlabeled deterministic maps over X; selection uses only
verified continuation profiles and fixed lexical/MDL tie-breaking.
"""

import itertools
import json
import os
from collections import defaultdict

X = tuple(range(3))
C = tuple(range(3))
IDENTITY = tuple(X)
ALL_FUNCTIONS = tuple(itertools.product(X, repeat=len(X)))


def all_tables():
    for bits in itertools.product((0, 1), repeat=len(X) * len(C)):
        yield tuple(tuple(bits[i * len(C):(i + 1) * len(C)]) for i in X)


def profile(table, x, B):
    return tuple(table[x][c] for c in B)


def full_profile(table, x):
    return tuple(table[x])


def classes(table, B):
    buckets = defaultdict(list)
    for x in X:
        buckets[profile(table, x, B)].append(x)
    return tuple(sorted(tuple(v) for v in buckets.values()))


def class_id(cls):
    out = {}
    for i, block in enumerate(cls):
        for x in block:
            out[x] = i
    return out


def congruent(table, B, f):
    cls = classes(table, B)
    cid = class_id(cls)
    for block in cls:
        images = {cid[f[x]] for x in block}
        if len(images) != 1:
            return False
    return True


def closure(seed, ops):
    seen = {seed}
    frontier = [seed]
    while frontier:
        x = frontier.pop()
        for f in ops:
            y = f[x]
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return frozenset(seen)


def residual_loss(table, reached_state, target_state):
    """Verifier-visible loss only: Hamming distance of full continuation profile."""
    a = full_profile(table, reached_state)
    b = full_profile(table, target_state)
    return sum(u != v for u, v in zip(a, b))


def mdl_key(f):
    """Fixed semantic-free simplicity preference: changes from identity, then tuple."""
    return (sum(f[i] != i for i in X), f)


def induce_o1(table, B0, seed, target):
    """Select O1 using only target residual reduction + frozen simplicity tie-break.

    K0 is exhaustively closed (identity only). Candidates must be lawful on the
    current quotient. No operator labels or target-specific repair families exist.
    """
    ranked = []
    for f in ALL_FUNCTIONS:
        if f == IDENTITY or not congruent(table, B0, f):
            continue
        loss = residual_loss(table, f[seed], target)
        ranked.append((loss, mdl_key(f), f))
    if not ranked:
        return None
    ranked.sort()
    best = ranked[0]
    return best[2], best[0]


def exposed_separator(table, B0, reached_union):
    """First lawful continuation that separates a currently merged reached pair."""
    cls = classes(table, B0)
    for c in C:
        if c in B0:
            continue
        for block in cls:
            rs = [x for x in block if x in reached_union]
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    x, y = rs[i], rs[j]
                    if table[x][c] != table[y][c]:
                        return c, (x, y)
    return None, None


def find_o2(table, B0, B1, seed, o1):
    """Find simplest operator unlearnable at ancestor, lawful after refinement,
    and capability-expanding when composed with retained O1.
    """
    c1 = closure(seed, (IDENTITY, o1))
    candidates = []
    for g in ALL_FUNCTIONS:
        if g in (IDENTITY, o1):
            continue
        if congruent(table, B0, g):
            continue  # already learnable at ancestor: not developmental
        if not congruent(table, B1, g):
            continue
        both = closure(seed, (IDENTITY, o1, g))
        if not (c1 < both):
            continue
        # Prefer a genuinely compositional gain when possible: combined closure
        # contains something not present in either single-operator closure.
        g_only = closure(seed, (IDENTITY, g))
        synergy = len(both - (c1 | g_only))
        candidates.append((-synergy, mdl_key(g), g, both, g_only))
    if not candidates:
        return None
    candidates.sort()
    _, _, g, both, g_only = candidates[0]
    return g, both, g_only


summary = {
    "schema": "verified-developmental-navigation.developmental-ratchet-crown-jewel.v53",
    "classification": "FINITE_EXHAUSTIVE_CALIBRATION",
    "tables": 0,
    "contexts": 0,
    "seed_target_attempts": 0,
    "o1_exact_residual_successes": 0,
    "o1_strict_closure_expansions": 0,
    "o1_transfer_successes": 0,
    "separator_exposures": 0,
    "o2_developmental_discoveries": 0,
    "ancestor_ablation_failures": 0,
    "worlds_with_full_chain": 0,
    "full_chains": 0,
    "first_witness": None,
    "gates": {
        "k0_closure_exhausted": True,
        "o1_selected_from_verifier_residual_only": True,
        "o1_strictly_expands_closure": False,
        "o1_transfers_to_second_start": False,
        "o1_exposes_lawful_separator": False,
        "separator_strictly_refines_interface": False,
        "o2_not_discoverable_at_ancestor": False,
        "o2_discoverable_after_o1_refinement": False,
        "o1_o2_combination_expands_capability": False,
        "ancestor_ablation_removes_o2_discoverability": False,
    },
}

for table in all_tables():
    summary["tables"] += 1
    table_has_chain = False
    for c0 in C:
        B0 = (c0,)
        summary["contexts"] += 1
        cls0 = classes(table, B0)
        # We need a nontrivial interface; otherwise there is nothing to refine.
        if len(cls0) == len(X):
            continue
        for seed in X:
            k0 = closure(seed, (IDENTITY,))
            assert k0 == frozenset({seed})
            for target in X:
                if target == seed or full_profile(table, target) == full_profile(table, seed):
                    continue
                summary["seed_target_attempts"] += 1
                induced = induce_o1(table, B0, seed, target)
                if induced is None:
                    continue
                o1, loss = induced
                if loss != 0:
                    continue
                summary["o1_exact_residual_successes"] += 1
                c_seed = closure(seed, (IDENTITY, o1))
                if not (k0 < c_seed):
                    continue
                summary["o1_strict_closure_expansions"] += 1

                # Natural-transfer analogue in the finite calibration: the same
                # retained O1 must strictly expand closure from another start.
                transfer_starts = []
                reached_union = set(c_seed)
                for s2 in X:
                    if s2 == seed:
                        continue
                    before = closure(s2, (IDENTITY,))
                    after = closure(s2, (IDENTITY, o1))
                    if before < after:
                        transfer_starts.append(s2)
                        reached_union.update(after)
                if not transfer_starts:
                    continue
                summary["o1_transfer_successes"] += 1

                cstar, sep_pair = exposed_separator(table, B0, reached_union)
                if cstar is None:
                    continue
                summary["separator_exposures"] += 1
                B1 = tuple(sorted(set(B0) | {cstar}))
                cls1 = classes(table, B1)
                if not (len(cls1) > len(cls0)):
                    continue

                found = find_o2(table, B0, B1, seed, o1)
                if found is None:
                    continue
                o2, combined, o2_only = found
                summary["o2_developmental_discoveries"] += 1

                # Ancestor ablation: without O1, no new state is reached by K0,
                # so the separator-acquisition rule cannot fire. Basis remains B0.
                ancestor_reached = closure(seed, (IDENTITY,))
                abl_c, _ = exposed_separator(table, B0, ancestor_reached)
                if abl_c is not None:
                    summary["ancestor_ablation_failures"] += 1
                    continue
                if congruent(table, B0, o2):
                    summary["ancestor_ablation_failures"] += 1
                    continue

                table_has_chain = True
                summary["full_chains"] += 1
                if summary["first_witness"] is None:
                    summary["first_witness"] = {
                        "table": table,
                        "B0": B0,
                        "classes_B0": cls0,
                        "seed": seed,
                        "target": target,
                        "target_profile": full_profile(table, target),
                        "O1": o1,
                        "O1_seed_closure": sorted(c_seed),
                        "transfer_starts": transfer_starts,
                        "reached_union": sorted(reached_union),
                        "separator": cstar,
                        "separator_pair": sep_pair,
                        "B1": B1,
                        "classes_B1": cls1,
                        "O2": o2,
                        "O2_congruent_B0": congruent(table, B0, o2),
                        "O2_congruent_B1": congruent(table, B1, o2),
                        "O1_only_closure": sorted(c_seed),
                        "O2_only_counterfactual_closure": sorted(o2_only),
                        "O1_O2_closure": sorted(combined),
                    }
    if table_has_chain:
        summary["worlds_with_full_chain"] += 1

w = summary["first_witness"]
g = summary["gates"]
if w is not None:
    g["o1_strictly_expands_closure"] = len(w["O1_seed_closure"]) > 1
    g["o1_transfers_to_second_start"] = bool(w["transfer_starts"])
    g["o1_exposes_lawful_separator"] = w["separator"] not in w["B0"]
    g["separator_strictly_refines_interface"] = len(w["classes_B1"]) > len(w["classes_B0"])
    g["o2_not_discoverable_at_ancestor"] = not w["O2_congruent_B0"]
    g["o2_discoverable_after_o1_refinement"] = w["O2_congruent_B1"]
    g["o1_o2_combination_expands_capability"] = set(w["O1_only_closure"]) < set(w["O1_O2_closure"])
    # By construction ancestor K0 reaches only the seed, so cannot expose a pair;
    # plus O2 is noncongruent under B0.
    g["ancestor_ablation_removes_o2_discoverability"] = not w["O2_congruent_B0"]

summary["all_crown_calibration_gates_pass"] = all(g.values()) and summary["full_chains"] > 0
summary["verdict"] = (
    "PASS_FINITE_DEVELOPMENTAL_RATCHET_V53"
    if summary["all_crown_calibration_gates_pass"]
    else "NO_FINITE_DEVELOPMENTAL_RATCHET_V53"
)
summary["claim_boundary"] = (
    "A PASS establishes existence, by exhaustive census in the frozen 3x3 binary continuation world, "
    "of the full causal dependency shape K0-exhaustion -> verifier-residual-selected O1 -> closure expansion/transfer -> "
    "separator-induced quotient refinement -> O2 newly quotient-well-defined -> added capability, with ancestor ablation. "
    "It does NOT establish natural external-task O1 genesis; that remains the next protected experiment."
)

out = "verified-developmental-navigation/case_studies/finite_inevitability/results_v53_developmental_ratchet_crown_jewel/result.json"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
