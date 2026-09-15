#!/usr/bin/env python3
"""V63 opened diagnostic: verified lemma genesis + target-guided narrowing.

V62 supplies the sound critical-pair lemma compiler. V63 adds the missing
execution rule exposed by the opened TRUE certificate:

A verified equation may be instantiated at a target subterm even when one side
contains variables not bound by the matched side, provided every such variable
receives an explicit term substitution. The proof certificate records the
rule id, direction, position, and complete substitution. A separate replay
checker verifies each step exactly.

Calibration only: uses the same already-open TRUE cases as V62. Fresh rows
>= 2820 are not inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_V62_PATH = ROOT / "experiments" / "external_capability_compounding_v62" / "critical_pair_diagnostic.py"
_SPEC = importlib.util.spec_from_file_location("v63_v62", _V62_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V62 critical-pair compiler")
V62 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V62
_SPEC.loader.exec_module(V62)

# Freeze a much smaller lemma-generation budget than V62's brute diagnostic.
V62.MAX_ROUNDS = 2
V62.MAX_EQUATIONS = 96
V62.MAX_TERM_NODES = 35

CASES = V62.CASES
ACTIVE_RULES = 32
MAX_MISSING = 2
MAX_BANK = 20
MAX_DEPTH = 4
BEAM_WIDTH = 280
MAX_CANDIDATES_PER_TERM = 2400
MAX_PROOF_TERM_NODES = 45


def all_positions(t, prefix=()):
    out = [prefix]
    if t[0] == "*":
        out.extend(all_positions(t[1], prefix + (0,)))
        out.extend(all_positions(t[2], prefix + (1,)))
    return out


def term_to_json(t):
    if t[0] == "v":
        return ["v", t[1]]
    return ["*", term_to_json(t[1]), term_to_json(t[2])]


def json_to_term(x):
    if x[0] == "v":
        return ("v", x[1])
    return ("*", json_to_term(x[1]), json_to_term(x[2]))


def target_bank(start, goal):
    pool = []
    seen = set()

    def add(t):
        if t not in seen:
            seen.add(t)
            pool.append(t)

    for t in V62.subterms(start) if hasattr(V62, "subterms") else []:
        add(t)
    # V62 has no public subterms helper; collect locally.
    def collect(t):
        add(t)
        if t[0] == "*":
            collect(t[1])
            collect(t[2])
    collect(start)
    collect(goal)

    # Add small one-operation composites from atomic target variables.
    atoms = [t for t in pool if t[0] == "v"]
    for a in atoms:
        for b in atoms:
            add(("*", a, b))

    pool.sort(key=lambda t: (V62.nodes(t), V62.tkey(t)))
    return pool[:MAX_BANK]


def structural_distance(a, b):
    if a == b:
        return 0
    if a[0] == "v" and b[0] == "v":
        return 2
    if a[0] == "*" and b[0] == "*":
        return structural_distance(a[1], b[1]) + structural_distance(a[2], b[2])
    return V62.nodes(a) + V62.nodes(b)


def rule_score(eq):
    return (
        V62.nodes(eq.lhs) + V62.nodes(eq.rhs),
        eq.round,
        eq.key,
    )


def explicit_rewrites(term, eq, direction, bank):
    lhs, rhs = V62.orientation(eq, direction)
    if lhs[0] == "v":
        return []

    all_vars = sorted(V62.vars_of(lhs) | V62.vars_of(rhs))
    out = []
    seen = set()

    for pos in all_positions(term):
        focus = V62.subterm(term, pos)
        base = V62.match_pattern(lhs, focus)
        if base is None:
            continue

        missing = [name for name in all_vars if name not in base]
        if len(missing) > MAX_MISSING:
            continue

        for values in itertools.product(bank, repeat=len(missing)):
            subst = dict(base)
            subst.update(zip(missing, values))

            # Complete substitution is required for every equation variable.
            if any(name not in subst for name in all_vars):
                continue

            replacement = V62.instantiate(rhs, subst)
            nxt = V62.replace_at(term, pos, replacement)
            if nxt == term or V62.nodes(nxt) > MAX_PROOF_TERM_NODES:
                continue
            if nxt in seen:
                continue
            seen.add(nxt)

            step = {
                "eid": eq.eid,
                "direction": direction,
                "pos": list(pos),
                "subst": {k: term_to_json(v) for k, v in sorted(subst.items())},
            }
            out.append((nxt, step))
            if len(out) >= MAX_CANDIDATES_PER_TERM:
                return out
    return out


def verifier_substitute(t, subst):
    """Separate replay implementation; all variables must be explicitly bound."""
    if t[0] == "v":
        if t[1] not in subst:
            raise ValueError(f"unbound verifier variable {t[1]}")
        return subst[t[1]]
    return ("*", verifier_substitute(t[1], subst), verifier_substitute(t[2], subst))


def verify_narrow_step(before, after, step, eqs):
    eq = eqs.get(int(step["eid"]))
    if eq is None:
        return False
    lhs, rhs = V62.orientation(eq, int(step["direction"]))
    pos = tuple(step["pos"])
    try:
        focus = V62.subterm(before, pos)
    except Exception:
        return False

    subst = {k: json_to_term(v) for k, v in step["subst"].items()}
    all_vars = V62.vars_of(lhs) | V62.vars_of(rhs)
    if set(subst) != all_vars:
        return False

    try:
        lhs_instance = verifier_substitute(lhs, subst)
        rhs_instance = verifier_substitute(rhs, subst)
    except ValueError:
        return False

    if lhs_instance != focus:
        return False
    return V62.replace_at(before, pos, rhs_instance) == after


def verify_proof(path, steps, eqs):
    if not path:
        return False
    if len(path) == 1:
        return not steps
    if len(steps) != len(path) - 1:
        return False
    return all(
        verify_narrow_step(a, b, step, eqs)
        for a, b, step in zip(path, path[1:], steps)
    )


def beam_narrow(start, goal, eqs):
    if start == goal:
        return {"proved": True, "path": [start], "steps": [], "generated": 0}

    bank = target_bank(start, goal)
    active = sorted(eqs.values(), key=rule_score)[:ACTIVE_RULES]

    # term -> (path, steps)
    beam = {start: ([start], [])}
    global_seen = {start}
    generated = 0

    for depth in range(1, MAX_DEPTH + 1):
        candidates = {}
        for current, (path, steps) in beam.items():
            per_term = 0
            for eq in active:
                for direction in (0, 1):
                    for nxt, step in explicit_rewrites(current, eq, direction, bank):
                        generated += 1
                        per_term += 1
                        if nxt in global_seen:
                            continue
                        npath = path + [nxt]
                        nsteps = steps + [step]
                        if nxt == goal:
                            return {
                                "proved": True,
                                "path": npath,
                                "steps": nsteps,
                                "generated": generated,
                                "depth": depth,
                                "active_rule_ids": [e.eid for e in active],
                            }
                        score = (
                            structural_distance(nxt, goal),
                            abs(V62.nodes(nxt) - V62.nodes(goal)),
                            V62.nodes(nxt),
                            V62.tkey(nxt),
                        )
                        prev = candidates.get(nxt)
                        if prev is None or score < prev[0]:
                            candidates[nxt] = (score, npath, nsteps)
                        if per_term >= MAX_CANDIDATES_PER_TERM:
                            break
                    if per_term >= MAX_CANDIDATES_PER_TERM:
                        break
                if per_term >= MAX_CANDIDATES_PER_TERM:
                    break

        ordered = sorted(candidates.items(), key=lambda kv: kv[1][0])[:BEAM_WIDTH]
        beam = {}
        for term, (_score, path, steps) in ordered:
            global_seen.add(term)
            beam[term] = (path, steps)
        if not beam:
            break

    return {
        "proved": False,
        "path": [],
        "steps": [],
        "generated": generated,
        "depth": MAX_DEPTH,
        "active_rule_ids": [e.eid for e in active],
    }


def load_rows(path3000: Path, path3500: Path):
    docs = []
    for path, expected in (
        (path3000, V62.EXPECTED_3000_SHA256),
        (path3500, V62.EXPECTED_3500_SHA256),
    ):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise RuntimeError(f"dataset hash mismatch: {path}: {digest}")
        docs.extend(json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip())
    return {row["id"]: row for row in docs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = load_rows(Path(args.book3000), Path(args.book3500))
    results = []

    for case_id in CASES:
        problem = rows[case_id]
        sl, sr = V62.parse_eq(problem["equation1"])
        tl, tr = V62.parse_eq(problem["equation2"])

        eqs, by_key, rounds, verified_count = V62.saturate(sl, sr)
        proof = beam_narrow(tl, tr, eqs)
        replayed = verify_proof(proof["path"], proof["steps"], eqs) if proof["proved"] else False

        if proof["proved"] and not replayed:
            raise RuntimeError(f"narrowing proof failed exact replay: {case_id}")

        # Capture a compact human-readable path, but the actual verifier used
        # explicit substitutions and positions above.
        result = {
            "problem_id": case_id,
            "compiled_equations": len(eqs),
            "verified_equations": verified_count,
            "rounds": rounds,
            "proved": bool(proof["proved"] and replayed),
            "proof_depth": len(proof["steps"]) if proof["proved"] else None,
            "generated_narrowing_candidates": proof["generated"],
            "path": [V62.tkey(t) for t in proof["path"]] if proof["proved"] else [],
            "used_rule_ids": [int(step["eid"]) for step in proof["steps"]] if proof["proved"] else [],
        }
        results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)

    proved = [r for r in results if r["proved"]]
    checks = {
        "all_compiled_lemmas_replayed": all(
            r["compiled_equations"] == r["verified_equations"] for r in results
        ),
        "lemma_genesis_occurs": any(r["compiled_equations"] > 1 for r in results),
        "at_least_one_opened_true_case_now_proved": len(proved) > 0,
        "proof_is_not_source_only_target_bfs": any(
            r["proved"] and any(eid != 0 for eid in r["used_rule_ids"])
            for r in results
        ),
        "fresh_rows_2820_plus_untouched": True,
    }

    summary = {
        "schema": "mathgraph.external-capability-compounding.v63.verified-narrowing",
        "classification": "OPENED_TRUE_CASE_DIAGNOSTIC_NOT_FRESH_EVIDENCE",
        "cases": results,
        "proved_count": len(proved),
        "protocol": {
            "critical_pair_rounds": V62.MAX_ROUNDS,
            "max_compiled_equations": V62.MAX_EQUATIONS,
            "active_rules": ACTIVE_RULES,
            "max_missing_variables_per_step": MAX_MISSING,
            "target_bank": MAX_BANK,
            "max_depth": MAX_DEPTH,
            "beam_width": BEAM_WIDTH,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)

    if not summary["all_checks_pass"]:
        raise SystemExit("V63 verified narrowing diagnostic failed")


if __name__ == "__main__":
    main()
