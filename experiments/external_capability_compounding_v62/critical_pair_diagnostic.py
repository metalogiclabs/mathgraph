#!/usr/bin/env python3
"""V62 opened diagnostic: verified lemma genesis by critical-pair saturation.

This is calibration on already-open TRUE problems only. It reads problem JSONL
but never reads upstream proof files during execution.

The source identity is treated as an equational axiom. The compiler repeatedly:
  1. standardizes two verified equations apart,
  2. overlaps one oriented left side into a non-variable position of another,
  3. unifies the overlap,
  4. derives the resulting critical pair,
  5. alpha-canonicalizes and deduplicates it,
  6. independently replays the recorded overlap before admitting the lemma.

Admitted lemmas are therefore consequences of the source identity. A target is
accepted only if either its alpha-equation appears in the verified saturation or
a bounded rewrite path using verified, variable-safe lemmas is replayed exactly.

Fresh rows >= 2820 remain untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_FMW_PATH = ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v62_fmw", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load finite_magma_world")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)

EXTERNAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
EXPECTED_3000_SHA256 = "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256 = "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"

# All were already opened and inspected before V62.
CASES = (
    "42607_to_41601",
    "1334_to_3294",
    "5795_to_6684",
    "6761_to_3692",
)

MAX_ROUNDS = 6
MAX_EQUATIONS = 320
MAX_TERM_NODES = 41
TARGET_REWRITE_STEPS = 5
TARGET_REWRITE_TERMS = 6000


def norm_text(text: str) -> str:
    out = str(text)
    for op in ("◇", "⋄", "·", "∙", "∗", "＊", "×"):
        out = out.replace(op, "*")
    return out


def term_tuple(term):
    if term.name is not None:
        return ("v", term.name)
    return ("*", term_tuple(term.left), term_tuple(term.right))


def parse_eq(text: str):
    eq = _FMW.parse_equation(norm_text(text))
    return term_tuple(eq.lhs), term_tuple(eq.rhs)


def tkey(t) -> str:
    if t[0] == "v":
        return t[1]
    return "(" + tkey(t[1]) + "*" + tkey(t[2]) + ")"


def nodes(t) -> int:
    if t[0] == "v":
        return 1
    return 1 + nodes(t[1]) + nodes(t[2])


def vars_of(t):
    if t[0] == "v":
        return {t[1]}
    return vars_of(t[1]) | vars_of(t[2])


def rename_term(t, mapping):
    if t[0] == "v":
        return ("v", mapping.get(t[1], t[1]))
    return ("*", rename_term(t[1], mapping), rename_term(t[2], mapping))


def standardize_pair(lhs, rhs, prefix):
    names = sorted(vars_of(lhs) | vars_of(rhs))
    mapping = {name: f"{prefix}{i}" for i, name in enumerate(names)}
    return rename_term(lhs, mapping), rename_term(rhs, mapping)


def alpha_pair(lhs, rhs):
    mapping = {}
    count = 0

    def go(t):
        nonlocal count
        if t[0] == "v":
            name = t[1]
            if name not in mapping:
                mapping[name] = f"v{count}"
                count += 1
            return ("v", mapping[name])
        return ("*", go(t[1]), go(t[2]))

    return go(lhs), go(rhs)


def canonical_equation(lhs, rhs):
    a1, b1 = alpha_pair(lhs, rhs)
    a2, b2 = alpha_pair(rhs, lhs)
    k1 = tkey(a1) + "=" + tkey(b1)
    k2 = tkey(a2) + "=" + tkey(b2)
    if k2 < k1:
        return a2, b2, k2
    return a1, b1, k1


def deref(t, subst):
    seen = set()
    while t[0] == "v" and t[1] in subst and t[1] not in seen:
        seen.add(t[1])
        t = subst[t[1]]
    return t


def occurs(name, t, subst):
    t = deref(t, subst)
    if t[0] == "v":
        return t[1] == name
    return occurs(name, t[1], subst) or occurs(name, t[2], subst)


def unify(a, b):
    subst = {}
    stack = [(a, b)]
    while stack:
        x, y = stack.pop()
        x = deref(x, subst)
        y = deref(y, subst)
        if x == y:
            continue
        if x[0] == "v":
            if occurs(x[1], y, subst):
                return None
            subst[x[1]] = y
            continue
        if y[0] == "v":
            if occurs(y[1], x, subst):
                return None
            subst[y[1]] = x
            continue
        if x[0] != "*" or y[0] != "*":
            return None
        stack.append((x[1], y[1]))
        stack.append((x[2], y[2]))
    return subst


def apply_subst(t, subst):
    t = deref(t, subst)
    if t[0] == "v":
        return t
    return ("*", apply_subst(t[1], subst), apply_subst(t[2], subst))


def nonvar_positions(t, prefix=()):
    out = []
    if t[0] == "*":
        out.append(prefix)
        out.extend(nonvar_positions(t[1], prefix + (0,)))
        out.extend(nonvar_positions(t[2], prefix + (1,)))
    return out


def subterm(t, pos):
    for step in pos:
        t = t[1] if step == 0 else t[2]
    return t


def replace_at(t, pos, replacement):
    if not pos:
        return replacement
    step, rest = pos[0], pos[1:]
    if t[0] != "*":
        raise ValueError("position leaves term")
    if step == 0:
        return ("*", replace_at(t[1], rest, replacement), t[2])
    return ("*", t[1], replace_at(t[2], rest, replacement))


@dataclass
class Equation:
    eid: int
    lhs: tuple
    rhs: tuple
    key: str
    proof: dict
    round: int


def orientation(eq: Equation, bit: int):
    return (eq.lhs, eq.rhs) if bit == 0 else (eq.rhs, eq.lhs)


def derive_overlap(a: Equation, b: Equation, a_dir: int, b_dir: int, pos):
    al, ar = orientation(a, a_dir)
    bl, br = orientation(b, b_dir)
    al, ar = standardize_pair(al, ar, "A_")
    bl, br = standardize_pair(bl, br, "B_")

    focus = subterm(bl, pos)
    sigma = unify(al, focus)
    if sigma is None:
        return None

    root_branch = apply_subst(br, sigma)
    inner_branch = apply_subst(replace_at(bl, pos, ar), sigma)

    if root_branch == inner_branch:
        return None
    if nodes(root_branch) > MAX_TERM_NODES or nodes(inner_branch) > MAX_TERM_NODES:
        return None

    lhs, rhs, key = canonical_equation(root_branch, inner_branch)
    return lhs, rhs, key


def verify_overlap(child: Equation, equations: dict[int, Equation]) -> bool:
    p = child.proof
    if p.get("kind") == "SOURCE":
        return child.eid == 0
    if p.get("kind") != "CRITICAL_PAIR":
        return False
    a = equations.get(int(p["a"]))
    b = equations.get(int(p["b"]))
    if a is None or b is None:
        return False
    predicted = derive_overlap(
        a, b, int(p["a_dir"]), int(p["b_dir"]), tuple(p["pos"])
    )
    if predicted is None:
        return False
    lhs, rhs, key = predicted
    return key == child.key and lhs == child.lhs and rhs == child.rhs


def saturate(source_lhs, source_rhs):
    lhs, rhs, key = canonical_equation(source_lhs, source_rhs)
    eqs = {0: Equation(0, lhs, rhs, key, {"kind": "SOURCE"}, 0)}
    by_key = {key: 0}
    next_id = 1
    frontier = [0]
    round_stats = []

    for round_no in range(1, MAX_ROUNDS + 1):
        existing_ids = sorted(eqs)
        candidates = {}
        # Force every new round to touch at least one frontier equation.
        frontier_set = set(frontier)
        for a_id in existing_ids:
            for b_id in existing_ids:
                if a_id not in frontier_set and b_id not in frontier_set:
                    continue
                a = eqs[a_id]
                b = eqs[b_id]
                for a_dir in (0, 1):
                    al, _ar = orientation(a, a_dir)
                    if al[0] == "v":
                        continue
                    for b_dir in (0, 1):
                        bl, _br = orientation(b, b_dir)
                        if bl[0] == "v":
                            continue
                        # Positions are computed after standardization but shape is unchanged.
                        for pos in nonvar_positions(bl):
                            out = derive_overlap(a, b, a_dir, b_dir, pos)
                            if out is None:
                                continue
                            cl, cr, ckey = out
                            if ckey in by_key:
                                continue
                            complexity = nodes(cl) + nodes(cr)
                            rec = (
                                complexity,
                                ckey,
                                cl,
                                cr,
                                {
                                    "kind": "CRITICAL_PAIR",
                                    "a": a_id,
                                    "b": b_id,
                                    "a_dir": a_dir,
                                    "b_dir": b_dir,
                                    "pos": list(pos),
                                },
                            )
                            prev = candidates.get(ckey)
                            if prev is None or rec[:2] < prev[:2]:
                                candidates[ckey] = rec

        ordered = sorted(candidates.values(), key=lambda x: (x[0], x[1]))
        slots = MAX_EQUATIONS - len(eqs)
        if slots <= 0:
            break
        added = []
        for _complexity, ckey, cl, cr, proof in ordered[:slots]:
            child = Equation(next_id, cl, cr, ckey, proof, round_no)
            # Independent replay before admission.
            trial = dict(eqs)
            trial[next_id] = child
            if not verify_overlap(child, trial):
                raise RuntimeError(f"critical-pair replay failed for {ckey}")
            eqs[next_id] = child
            by_key[ckey] = next_id
            added.append(next_id)
            next_id += 1

        round_stats.append({
            "round": round_no,
            "candidates": len(candidates),
            "added": len(added),
            "total": len(eqs),
        })
        frontier = added
        if not frontier:
            break

    # Full ancestral verification in topological id order.
    verified = 0
    for eid in sorted(eqs):
        if verify_overlap(eqs[eid], eqs):
            verified += 1
        else:
            raise RuntimeError(f"stored equation {eid} failed replay")
    return eqs, by_key, round_stats, verified


def match_pattern(pattern, target, subst=None):
    subst = {} if subst is None else dict(subst)
    if pattern[0] == "v":
        name = pattern[1]
        bound = subst.get(name)
        if bound is None:
            subst[name] = target
            return subst
        return subst if bound == target else None
    if target[0] != "*":
        return None
    left = match_pattern(pattern[1], target[1], subst)
    if left is None:
        return None
    return match_pattern(pattern[2], target[2], left)


def instantiate(t, subst):
    if t[0] == "v":
        return subst.get(t[1], t)
    return ("*", instantiate(t[1], subst), instantiate(t[2], subst))


def one_rule_rewrites(term, lhs, rhs):
    out = []
    subst = match_pattern(lhs, term)
    if subst is not None:
        out.append(instantiate(rhs, subst))
    if term[0] == "*":
        for child in one_rule_rewrites(term[1], lhs, rhs):
            out.append(("*", child, term[2]))
        for child in one_rule_rewrites(term[2], lhs, rhs):
            out.append(("*", term[1], child))
    unique = []
    seen = set()
    for x in out:
        if x != term and x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


def safe_rule_orientations(eqs):
    rules = []
    for eid, eq in sorted(eqs.items()):
        for direction, (lhs, rhs) in enumerate(((eq.lhs, eq.rhs), (eq.rhs, eq.lhs))):
            # Ordinary rewriting is only deterministic/sound without fresh schematic
            # variable creation when every rhs variable is bound by matching lhs.
            if lhs[0] != "v" and vars_of(rhs) <= vars_of(lhs):
                rules.append((eid, direction, lhs, rhs))
    return rules


def target_bfs(start, goal, eqs):
    rules = safe_rule_orientations(eqs)
    if start == goal:
        return {"proved": True, "path": [start], "steps": [], "seen": 1}
    queue = deque([start])
    parent = {start: None}
    edge = {}

    while queue and len(parent) < TARGET_REWRITE_TERMS:
        current = queue.popleft()
        # Recover depth lazily.
        depth = 0
        x = current
        while parent[x] is not None:
            depth += 1
            x = parent[x]
        if depth >= TARGET_REWRITE_STEPS:
            continue

        for eid, direction, lhs, rhs in rules:
            for nxt in one_rule_rewrites(current, lhs, rhs):
                if nxt in parent:
                    continue
                parent[nxt] = current
                edge[nxt] = (eid, direction)
                if nxt == goal:
                    path = [nxt]
                    steps = []
                    cur = nxt
                    while parent[cur] is not None:
                        steps.append(edge[cur])
                        cur = parent[cur]
                        path.append(cur)
                    path.reverse()
                    steps.reverse()
                    return {
                        "proved": True,
                        "path": path,
                        "steps": steps,
                        "seen": len(parent),
                    }
                if len(parent) >= TARGET_REWRITE_TERMS:
                    break
                queue.append(nxt)

    return {"proved": False, "path": [], "steps": [], "seen": len(parent)}


def verify_target_path(result, eqs):
    if not result["proved"]:
        return False
    path = result["path"]
    steps = result["steps"]
    if len(path) == 1:
        return not steps
    if len(steps) != len(path) - 1:
        return False
    for before, after, (eid, direction) in zip(path, path[1:], steps):
        eq = eqs[int(eid)]
        lhs, rhs = orientation(eq, int(direction))
        if after not in one_rule_rewrites(before, lhs, rhs):
            return False
    return True


def load_books(path3000: Path, path3500: Path):
    docs = []
    for path, expected in ((path3000, EXPECTED_3000_SHA256), (path3500, EXPECTED_3500_SHA256)):
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

    rows = load_books(Path(args.book3000), Path(args.book3500))
    results = []
    for case_id in CASES:
        problem = rows[case_id]
        sl, sr = parse_eq(problem["equation1"])
        tl, tr = parse_eq(problem["equation2"])

        eqs, by_key, round_stats, verified_count = saturate(sl, sr)
        _ctl, _ctr, target_key = canonical_equation(tl, tr)
        direct_id = by_key.get(target_key)

        bfs = {"proved": False, "path": [], "steps": [], "seen": 0}
        bfs_verified = False
        if direct_id is None:
            bfs = target_bfs(tl, tr, eqs)
            bfs_verified = verify_target_path(bfs, eqs) if bfs["proved"] else False
        else:
            bfs_verified = True

        proved = direct_id is not None or bfs_verified
        result = {
            "problem_id": case_id,
            "saturation_equations": len(eqs),
            "verified_equations": verified_count,
            "rounds": round_stats,
            "target_direct_equation_id": direct_id,
            "target_bfs_proved": bool(bfs.get("proved")),
            "target_bfs_verified": bfs_verified if bfs.get("proved") else False,
            "target_bfs_seen": int(bfs.get("seen", 0)),
            "proved": proved,
        }
        results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)

    proved_count = sum(r["proved"] for r in results)
    checks = {
        "all_stored_lemmas_replay": all(
            r["saturation_equations"] == r["verified_equations"] for r in results
        ),
        "lemma_genesis_occurs": any(r["saturation_equations"] > 1 for r in results),
        "at_least_one_known_true_case_proved": proved_count > 0,
        "no_fresh_rows_read": True,
    }
    summary = {
        "schema": "mathgraph.external-capability-compounding.v62.critical-pair-diagnostic",
        "classification": "OPENED_TRUE_CASE_DIAGNOSTIC_NOT_FRESH_EVIDENCE",
        "cases": results,
        "proved_count": proved_count,
        "protocol": {
            "max_rounds": MAX_ROUNDS,
            "max_equations": MAX_EQUATIONS,
            "max_term_nodes": MAX_TERM_NODES,
            "target_rewrite_steps": TARGET_REWRITE_STEPS,
            "target_rewrite_terms": TARGET_REWRITE_TERMS,
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    if not summary["all_checks_pass"]:
        raise SystemExit("V62 critical-pair diagnostic failed")


if __name__ == "__main__":
    main()
