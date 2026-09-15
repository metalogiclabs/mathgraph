#!/usr/bin/env python3
"""V61 opened-data calibration: verified proof compilation.

Train:      V58-opened rows 2628:2756 from both pinned external books.
Validation: V59-opened rows 2756:2820 from both books.
Fresh rows >= 2820 are never read by this workflow.

For an implication S => T, search equational logic directly:
  - S may rewrite any matching subterm in either direction under substitution.
  - A found chain from T.lhs to T.rhs is an exact proof certificate.
  - A separate replay checker verifies every adjacent rewrite.

Every verified TRAIN target theorem is retained as a source-specific macro rule.
Validation compares the same bounded search:
  (A) source identity only
  (B) source identity + previously verified TRAIN macros

A macro is admitted only after its original proof is independently replayed
using the source identity alone. Thus macro use is proof compression, not an
additional axiom.

No upstream proof file, verdict label, or fresh row is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Reuse only the parser representation, not any proof result.
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
_FMW_PATH = ROOT / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v61_fmw", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load finite_magma_world")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)

EXTERNAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
EXPECTED_3000_SHA256 = "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256 = "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"

TRAIN_START = 2628
TRAIN_COUNT = 128
VALID_START = 2756
VALID_COUNT = 64

MAX_STEPS = 6
MAX_TERMS = 5000
MAX_MACROS_PER_SOURCE = 24


def norm_eq_text(text: str) -> str:
    out = str(text)
    for op in ("◇", "⋄", "·", "∙", "∗", "＊", "×"):
        out = out.replace(op, "*")
    return out


def term_tuple(term):
    if term.name is not None:
        return ("v", term.name)
    return ("*", term_tuple(term.left), term_tuple(term.right))


def parse_equation(text: str):
    eq = _FMW.parse_equation(norm_eq_text(text))
    return term_tuple(eq.lhs), term_tuple(eq.rhs)


def term_key(term) -> str:
    if term[0] == "v":
        return term[1]
    return "(" + term_key(term[1]) + "*" + term_key(term[2]) + ")"


def alpha_equation(lhs, rhs):
    mapping = {}
    counter = [0]

    def go(term):
        if term[0] == "v":
            name = term[1]
            if name not in mapping:
                mapping[name] = f"v{counter[0]}"
                counter[0] += 1
            return ("v", mapping[name])
        return ("*", go(term[1]), go(term[2]))

    return go(lhs), go(rhs)


def source_key(lhs, rhs) -> str:
    candidates = []
    for a, b in ((lhs, rhs), (rhs, lhs)):
        x, y = alpha_equation(a, b)
        candidates.append(term_key(x) + "=" + term_key(y))
    return min(candidates)


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


def apply_subst(term, subst):
    if term[0] == "v":
        return subst.get(term[1], term)
    return ("*", apply_subst(term[1], subst), apply_subst(term[2], subst))


@dataclass(frozen=True)
class Rule:
    lhs: tuple
    rhs: tuple
    label: str


def rewrites_root(term, pattern, replacement):
    subst = match_pattern(pattern, term)
    if subst is None:
        return None
    return apply_subst(replacement, subst)


def all_single_rewrites(term, rules: list[Rule]):
    """Generator-side rewrite enumerator."""
    out = []
    seen = set()

    def add(candidate, label):
        if candidate != term and candidate not in seen:
            seen.add(candidate)
            out.append((candidate, label))

    for rule in rules:
        for pattern, replacement, direction in (
            (rule.lhs, rule.rhs, ">"),
            (rule.rhs, rule.lhs, "<"),
        ):
            root = rewrites_root(term, pattern, replacement)
            if root is not None:
                add(root, rule.label + direction)

            if term[0] == "*":
                for child, _lab in all_single_rewrites(term[1], [rule]):
                    add(("*", child, term[2]), rule.label + direction)
                for child, _lab in all_single_rewrites(term[2], [rule]):
                    add(("*", term[1], child), rule.label + direction)

    return out


def _replace_at_one_position(term, pattern, replacement):
    """Verifier-side implementation, intentionally separate from generator."""
    results = []

    def visit(node):
        subst = match_pattern(pattern, node)
        if subst is not None:
            results.append(apply_subst(replacement, subst))

        if node[0] != "*":
            return
        left_results_before = len(results)
        # Collect rewrites strictly inside left.
        child_results = _replace_at_one_position(node[1], pattern, replacement)
        for child in child_results:
            results.append(("*", child, node[2]))
        # Collect rewrites strictly inside right.
        child_results = _replace_at_one_position(node[2], pattern, replacement)
        for child in child_results:
            results.append(("*", node[1], child))

    visit(term)
    # Stable dedupe.
    unique = []
    seen = set()
    for x in results:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


def verifier_one_step(before, after, rules: list[Rule]) -> bool:
    for rule in rules:
        for pattern, replacement in ((rule.lhs, rule.rhs), (rule.rhs, rule.lhs)):
            if after in _replace_at_one_position(before, pattern, replacement):
                return True
    return False


def verify_path(path, rules: list[Rule]) -> bool:
    if not path:
        return False
    return all(verifier_one_step(a, b, rules) for a, b in zip(path, path[1:]))


def bfs_proof(start, goal, rules: list[Rule], max_steps=MAX_STEPS, max_terms=MAX_TERMS):
    if start == goal:
        return {
            "proved": True,
            "path": [start],
            "expansions": 0,
            "seen": 1,
            "steps": 0,
        }

    queue = deque([start])
    parent = {start: None}
    depth = {start: 0}
    expansions = 0

    while queue and len(parent) < max_terms:
        current = queue.popleft()
        d = depth[current]
        if d >= max_steps:
            continue
        expansions += 1

        for nxt, _label in all_single_rewrites(current, rules):
            if nxt in parent:
                continue
            parent[nxt] = current
            depth[nxt] = d + 1
            if nxt == goal:
                path = [nxt]
                cur = current
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return {
                    "proved": True,
                    "path": path,
                    "expansions": expansions,
                    "seen": len(parent),
                    "steps": len(path) - 1,
                }
            if len(parent) >= max_terms:
                break
            queue.append(nxt)

    return {
        "proved": False,
        "path": [],
        "expansions": expansions,
        "seen": len(parent),
        "steps": None,
    }


def load_slice(path: Path, expected_sha: str, start: int, count: int):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch for {path}: {digest}")
    lines = data.decode("utf-8").splitlines()
    chosen = lines[start:start + count]
    if len(chosen) != count:
        raise RuntimeError(f"expected {count} rows from {start}, got {len(chosen)}")
    return [json.loads(line) for line in chosen], digest


def problem_terms(problem):
    src_l, src_r = parse_equation(problem["equation1"])
    tgt_l, tgt_r = parse_equation(problem["equation2"])
    return src_l, src_r, tgt_l, tgt_r


def macro_json(macro):
    return {
        "source_key": macro["source_key"],
        "problem_id": macro["problem_id"],
        "lhs": term_key(macro["lhs"]),
        "rhs": term_key(macro["rhs"]),
        "steps": macro["steps"],
        "expansions_when_discovered": macro["expansions_when_discovered"],
        "certificate_path": [term_key(t) for t in macro["path"]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    train_a, sha3000 = load_slice(Path(args.book3000), EXPECTED_3000_SHA256, TRAIN_START, TRAIN_COUNT)
    train_b, sha3500 = load_slice(Path(args.book3500), EXPECTED_3500_SHA256, TRAIN_START, TRAIN_COUNT)
    valid_a, _ = load_slice(Path(args.book3000), EXPECTED_3000_SHA256, VALID_START, VALID_COUNT)
    valid_b, _ = load_slice(Path(args.book3500), EXPECTED_3500_SHA256, VALID_START, VALID_COUNT)
    train = train_a + train_b
    valid = valid_a + valid_b

    macros_by_source = {}
    train_records = []
    all_train_certificates_ok = True

    for idx, problem in enumerate(train, 1):
        src_l, src_r, tgt_l, tgt_r = problem_terms(problem)
        skey = source_key(src_l, src_r)
        source_rule = Rule(src_l, src_r, "SOURCE")
        result = bfs_proof(tgt_l, tgt_r, [source_rule])
        verified = bool(result["proved"] and verify_path(result["path"], [source_rule]))
        if result["proved"] and not verified:
            raise RuntimeError(f"generator proof failed independent replay: {problem['id']}")

        record = {
            "problem_id": problem["id"],
            "source_key": skey,
            "proved": verified,
            "steps": result["steps"],
            "expansions": result["expansions"],
            "seen": result["seen"],
        }
        train_records.append(record)

        if verified:
            macro = {
                "source_key": skey,
                "problem_id": problem["id"],
                "lhs": tgt_l,
                "rhs": tgt_r,
                "path": result["path"],
                "steps": result["steps"],
                "expansions_when_discovered": result["expansions"],
            }
            bucket = macros_by_source.setdefault(skey, [])
            if len(bucket) < MAX_MACROS_PER_SOURCE:
                bucket.append(macro)

        if idx % 32 == 0:
            print(json.dumps({
                "phase": "TRAIN",
                "index": idx,
                "proved_so_far": sum(r["proved"] for r in train_records),
                "macro_sources": len(macros_by_source),
            }, sort_keys=True), flush=True)

    # Re-verify every installed macro from the source identity alone.
    verified_macro_count = 0
    for skey, bucket in macros_by_source.items():
        for macro in bucket:
            # Find the originating source law in train.
            problem = next(p for p in train if p["id"] == macro["problem_id"])
            src_l, src_r, _tl, _tr = problem_terms(problem)
            source_rule = Rule(src_l, src_r, "SOURCE")
            if not verify_path(macro["path"], [source_rule]):
                raise RuntimeError(f"retained macro certificate invalid: {macro['problem_id']}")
            verified_macro_count += 1

    validation_records = []
    macro_only = 0
    common = 0
    expansion_baseline_common = 0
    expansion_macro_common = 0
    all_validation_certificates_ok = True

    for idx, problem in enumerate(valid, 1):
        src_l, src_r, tgt_l, tgt_r = problem_terms(problem)
        skey = source_key(src_l, src_r)
        source_rule = Rule(src_l, src_r, "SOURCE")

        baseline = bfs_proof(tgt_l, tgt_r, [source_rule])
        baseline_ok = bool(baseline["proved"] and verify_path(baseline["path"], [source_rule]))
        if baseline["proved"] and not baseline_ok:
            raise RuntimeError(f"baseline validation certificate invalid: {problem['id']}")

        retained = macros_by_source.get(skey, [])
        macro_rules = [Rule(m["lhs"], m["rhs"], "MACRO:" + m["problem_id"]) for m in retained]
        rules = [source_rule] + macro_rules
        warm = bfs_proof(tgt_l, tgt_r, rules)
        warm_ok = bool(warm["proved"] and verify_path(warm["path"], rules))
        if warm["proved"] and not warm_ok:
            raise RuntimeError(f"macro validation certificate invalid: {problem['id']}")

        if warm_ok and not baseline_ok:
            macro_only += 1
        if warm_ok and baseline_ok:
            common += 1
            expansion_baseline_common += baseline["expansions"]
            expansion_macro_common += warm["expansions"]

        validation_records.append({
            "problem_id": problem["id"],
            "source_key": skey,
            "available_macros": len(retained),
            "baseline_proved": baseline_ok,
            "baseline_steps": baseline["steps"],
            "baseline_expansions": baseline["expansions"],
            "macro_proved": warm_ok,
            "macro_steps": warm["steps"],
            "macro_expansions": warm["expansions"],
        })

        if idx % 32 == 0:
            print(json.dumps({
                "phase": "VALID",
                "index": idx,
                "baseline_proved": sum(r["baseline_proved"] for r in validation_records),
                "macro_proved": sum(r["macro_proved"] for r in validation_records),
                "macro_only": macro_only,
            }, sort_keys=True), flush=True)

    train_proved = sum(r["proved"] for r in train_records)
    valid_baseline = sum(r["baseline_proved"] for r in validation_records)
    valid_macro = sum(r["macro_proved"] for r in validation_records)
    validation_with_macros = sum(r["available_macros"] > 0 for r in validation_records)

    expansion_ratio = (
        expansion_baseline_common / expansion_macro_common
        if expansion_macro_common > 0 else
        (float("inf") if expansion_baseline_common > 0 else 1.0)
    )

    memory = {
        "schema": "mathgraph.verified-rewrite-macro-memory.v61",
        "external_commit": EXTERNAL_COMMIT,
        "train_start": TRAIN_START,
        "train_count_each": TRAIN_COUNT,
        "max_steps": MAX_STEPS,
        "max_terms": MAX_TERMS,
        "macro_sources": {
            skey: [macro_json(m) for m in bucket]
            for skey, bucket in sorted(macros_by_source.items())
        },
    }
    memory_raw = json.dumps(memory, sort_keys=True, separators=(",", ":")).encode()
    memory_sha = hashlib.sha256(memory_raw).hexdigest()
    memory["sha256"] = memory_sha

    checks = {
        "datasets_exact": sha3000 == EXPECTED_3000_SHA256 and sha3500 == EXPECTED_3500_SHA256,
        "train_proofs_exist": train_proved > 0,
        "retained_macros_independently_verified": verified_macro_count == train_proved,
        "validation_has_applicable_retained_macros": validation_with_macros > 0,
        "validation_proofs_exist": valid_macro > 0,
        "retained_proofs_do_not_reduce_coverage": valid_macro >= valid_baseline,
        "retained_proofs_improve_future_search": (
            macro_only > 0 or expansion_ratio >= 1.10
        ),
    }

    result = {
        "schema": "mathgraph.external-capability-compounding.v61.calibration",
        "classification": "OPENED_DATA_TRAIN_VALIDATION_NOT_FRESH_EVIDENCE",
        "protocol": {
            "train_rows_each": [TRAIN_START, TRAIN_START + TRAIN_COUNT],
            "validation_rows_each": [VALID_START, VALID_START + VALID_COUNT],
            "max_steps": MAX_STEPS,
            "max_terms": MAX_TERMS,
            "max_macros_per_source": MAX_MACROS_PER_SOURCE,
        },
        "train": {
            "tasks": len(train),
            "proved": train_proved,
            "verified_macros": verified_macro_count,
            "macro_sources": len(macros_by_source),
        },
        "validation": {
            "tasks": len(valid),
            "tasks_with_applicable_macros": validation_with_macros,
            "baseline_proved": valid_baseline,
            "macro_proved": valid_macro,
            "macro_only_proved": macro_only,
            "common_proved": common,
            "baseline_expansions_on_common": expansion_baseline_common,
            "macro_expansions_on_common": expansion_macro_common,
            "expansion_reduction_factor": expansion_ratio,
        },
        "memory_sha256": memory_sha,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), encoding="utf-8")
    (out / "rewrite_macro_memory.json").write_text(json.dumps(memory, indent=2, sort_keys=True), encoding="utf-8")
    (out / "train_records.json").write_text(json.dumps(train_records, indent=2, sort_keys=True), encoding="utf-8")
    (out / "validation_records.json").write_text(json.dumps(validation_records, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), flush=True)
    if not result["all_checks_pass"]:
        raise SystemExit("V61 proof-compilation calibration failed")


if __name__ == "__main__":
    main()
