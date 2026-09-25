#!/usr/bin/env python3
"""Hosted qualification for Crystal Mathematical Claim Dialect V0."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
import subprocess
import sys

from mathgraph.crystal import SemanticObject, UnknownSemantics, interpret_semantic_object
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation, quotient_by_verified_equivalence

ROOT = Path(__file__).resolve().parents[1]
LEAN_SOURCE = ROOT / "experiments" / "crystal_math_claim_dialect_v0.lean"
SMT_SOURCE = ROOT / "experiments" / "crystal_math_claim_dialect_v0.smt2"
EVIDENCE = ROOT / "evidence" / "crystal-math-claim-dialect-v0" / "result.json"
PARENT_CRYSTAL = "a2c66bb6bad37188a7d54a527b9db2fc5785524d"

CLAIMS = tuple(
    f"f{family}.{variant}"
    for family in range(1, 6)
    for variant in ("base", "equiv", "stronger", "weaker")
)

LEAN_NAMES = {claim: claim.replace(".", "_") for claim in CLAIMS}
SMT_NAMES = dict(LEAN_NAMES)

LEAN_STATEMENTS = {
    "f1.base": "p",
    "f1.equiv": "p && (q || !q)",
    "f1.stronger": "p && q && !r",
    "f1.weaker": "p || r",
    "f2.base": "!p",
    "f2.equiv": "!(p || false)",
    "f2.stronger": "(!p) && r",
    "f2.weaker": "(!p) || q",
    "f3.base": "p || q",
    "f3.equiv": "q || p",
    "f3.stronger": "p && (!q)",
    "f3.weaker": "(p || q) || r",
    "f4.base": "p && q",
    "f4.equiv": "q && p",
    "f4.stronger": "(p && q) && r",
    "f4.weaker": "p || (q && r)",
    "f5.base": "(p && !q) || ((!p) && q)",
    "f5.equiv": "((!q) && p) || (q && (!p))",
    "f5.stronger": "((!p) && q) && r",
    "f5.weaker": "((p && !q) || ((!p) && q)) || r",
}

SMT_STATEMENTS = {
    "f1.base": "p",
    "f1.equiv": "(and p (or q (not q)))",
    "f1.stronger": "(and p q (not r))",
    "f1.weaker": "(or p r)",
    "f2.base": "(not p)",
    "f2.equiv": "(not (or p false))",
    "f2.stronger": "(and (not p) r)",
    "f2.weaker": "(or (not p) q)",
    "f3.base": "(or p q)",
    "f3.equiv": "(or q p)",
    "f3.stronger": "(and p (not q))",
    "f3.weaker": "(or p q r)",
    "f4.base": "(and p q)",
    "f4.equiv": "(and q p)",
    "f4.stronger": "(and p q r)",
    "f4.weaker": "(or p (and q r))",
    "f5.base": "(or (and p (not q)) (and (not p) q))",
    "f5.equiv": "(or (and (not q) p) (and q (not p)))",
    "f5.stronger": "(and (not p) q r)",
    "f5.weaker": "(or (or (and p (not q)) (and (not p) q)) r)",
}

VALUATIONS = tuple(product((False, True), repeat=3))


def run(command: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(command)}")
    return result.stdout


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_lean_truth() -> dict[str, tuple[bool, ...]]:
    output = run(["lean", "--run", str(LEAN_SOURCE)])
    found: dict[str, tuple[bool, ...]] = {}
    for raw in output.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        name, payload = line.split("=", 1)
        if name not in CLAIMS:
            continue
        tokens = [part.strip() for part in payload.strip().strip("[]").split(",")]
        values = tuple(token == "true" for token in tokens if token)
        if len(values) != 8 or any(token not in {"true", "false"} for token in tokens):
            raise AssertionError(f"malformed Lean truth table for {name}: {payload}")
        found[name] = values
    if set(found) != set(CLAIMS):
        raise AssertionError(f"Lean output missing claims: {sorted(set(CLAIMS) - set(found))}")
    return found


def bool_atom(value: bool) -> str:
    return "true" if value else "false"


def z3_batch() -> tuple[str, dict[str, tuple[bool, ...]], dict[str, str]]:
    definitions = SMT_SOURCE.read_text()
    blocks = [definitions]
    for claim in CLAIMS:
        fn = SMT_NAMES[claim]
        for index, valuation in enumerate(VALUATIONS):
            args = " ".join(bool_atom(v) for v in valuation)
            blocks += [
                f'(echo "VAL {claim} {index}")',
                "(push)",
                f"(assert (not ({fn} {args})))",
                "(check-sat)",
                "(pop)",
            ]

    blocks += ["(declare-const p Bool)", "(declare-const q Bool)", "(declare-const r Bool)"]
    for family in range(1, 6):
        base = f"f{family}_base"
        equiv = f"f{family}_equiv"
        stronger = f"f{family}_stronger"
        weaker = f"f{family}_weaker"
        queries = (
            ("equiv", f"(xor ({base} p q r) ({equiv} p q r))"),
            ("stronger_implies_base", f"(and ({stronger} p q r) (not ({base} p q r)))"),
            ("base_not_implies_stronger", f"(and ({base} p q r) (not ({stronger} p q r)))"),
            ("base_implies_weaker", f"(and ({base} p q r) (not ({weaker} p q r)))"),
            ("weaker_not_implies_base", f"(and ({weaker} p q r) (not ({base} p q r)))"),
            ("stronger_non_equiv_weaker", f"(xor ({stronger} p q r) ({weaker} p q r))"),
        )
        for label, formula in queries:
            blocks += [
                f'(echo "REL f{family} {label}")',
                "(push)",
                f"(assert {formula})",
                "(check-sat)",
                "(pop)",
            ]

    query_text = "\n".join(blocks) + "\n"
    output = run(["z3", "-in", "-smt2"], input_text=query_text)

    truth: dict[str, list[bool | None]] = {claim: [None] * 8 for claim in CLAIMS}
    relations: dict[str, str] = {}
    pending: tuple[str, ...] | None = None
    for raw in output.splitlines():
        line = raw.strip().strip('"')
        if line.startswith("VAL "):
            _, claim, index = line.split()
            pending = ("VAL", claim, index)
        elif line.startswith("REL "):
            _, family, label = line.split()
            pending = ("REL", family, label)
        elif line in {"sat", "unsat", "unknown"} and pending:
            if pending[0] == "VAL":
                _, claim, index = pending
                truth[claim][int(index)] = line == "unsat"
            else:
                _, family, label = pending
                relations[f"{family}.{label}"] = line
            pending = None

    frozen_truth = {
        claim: tuple(value for value in values if value is not None)
        for claim, values in truth.items()
    }
    if any(len(values) != 8 for values in frozen_truth.values()):
        raise AssertionError("Z3 truth-table output incomplete")
    if len(relations) != 30:
        raise AssertionError(f"expected 30 Z3 relation checks, got {len(relations)}")
    return query_text, frozen_truth, relations


def implication(left: tuple[bool, ...], right: tuple[bool, ...]) -> bool:
    return all((not a) or b for a, b in zip(left, right))


def first_separator(left: tuple[bool, ...], right: tuple[bool, ...]) -> tuple[tuple[str, bool], ...]:
    for valuation, a, b in zip(VALUATIONS, left, right):
        if a != b:
            return tuple(zip(("p", "q", "r"), valuation))
    raise AssertionError("requested separator for equivalent truth tables")


def main() -> None:
    lean_truth = parse_lean_truth()
    smt_queries, smt_truth, smt_relations = z3_batch()

    for claim in CLAIMS:
        if lean_truth[claim] != smt_truth[claim]:
            raise AssertionError(
                f"cross-dialect semantic mismatch for {claim}: "
                f"Lean={lean_truth[claim]} SMT={smt_truth[claim]}"
            )

    expected_unsat = {"equiv", "stronger_implies_base", "base_implies_weaker"}
    expected_sat = {"base_not_implies_stronger", "weaker_not_implies_base", "stronger_non_equiv_weaker"}
    for family in range(1, 6):
        for label in expected_unsat:
            assert smt_relations[f"f{family}.{label}"] == "unsat"
        for label in expected_sat:
            assert smt_relations[f"f{family}.{label}"] == "sat"

    for family in range(1, 6):
        base = lean_truth[f"f{family}.base"]
        equiv = lean_truth[f"f{family}.equiv"]
        stronger = lean_truth[f"f{family}.stronger"]
        weaker = lean_truth[f"f{family}.weaker"]
        assert base == equiv
        assert implication(stronger, base) and not implication(base, stronger)
        assert implication(base, weaker) and not implication(weaker, base)

    objects: dict[tuple[str, str], SemanticObject] = {}
    for claim in CLAIMS:
        for dialect, statement, source in (
            ("lean4-bool-v0", LEAN_STATEMENTS[claim], f"{LEAN_SOURCE.relative_to(ROOT)}#{LEAN_NAMES[claim]}"),
            ("smtlib2-bool-v0", SMT_STATEMENTS[claim], f"{SMT_SOURCE.relative_to(ROOT)}#{SMT_NAMES[claim]}"),
        ):
            payload = MathClaimPayload(
                claim_id=claim,
                dialect=dialect,
                context=(("p", "Bool"), ("q", "Bool"), ("r", "Bool")),
                assumptions=(),
                statement=statement,
                source_ref=source,
            )
            obj = payload.semantic_object()
            roundtrip = SemanticObject.from_bytes(obj.to_bytes())
            assert roundtrip == obj and roundtrip.id == obj.id
            unknown = interpret_semantic_object(obj, "math.claim.statement@1", {})
            assert isinstance(unknown, UnknownSemantics)
            before = obj.id
            interpreted = interpret_semantic_object(
                obj,
                "math.claim.statement@1",
                {"math.claim.statement@1": lambda x: json.loads(x.payload)["statement"]},
            )
            assert interpreted == statement and obj.id == before
            objects[(claim, dialect)] = obj

    relations: list[VerifiedClaimRelation] = []
    evidence_ref = "hosted:crystal-math-claim-dialect-v0"
    for claim in CLAIMS:
        relations.append(
            VerifiedClaimRelation(
                objects[(claim, "lean4-bool-v0")].id,
                objects[(claim, "smtlib2-bool-v0")].id,
                "equivalent",
                (evidence_ref,),
            )
        )
    for family in range(1, 6):
        for dialect in ("lean4-bool-v0", "smtlib2-bool-v0"):
            base_name = f"f{family}.base"
            eq_name = f"f{family}.equiv"
            strong_name = f"f{family}.stronger"
            weak_name = f"f{family}.weaker"
            base = objects[(base_name, dialect)]
            eq = objects[(eq_name, dialect)]
            strong = objects[(strong_name, dialect)]
            weak = objects[(weak_name, dialect)]
            relations += [
                VerifiedClaimRelation(base.id, eq.id, "equivalent", (evidence_ref,)),
                VerifiedClaimRelation(strong.id, base.id, "implies", (evidence_ref,)),
                VerifiedClaimRelation(base.id, weak.id, "implies", (evidence_ref,)),
                VerifiedClaimRelation(
                    base.id, strong.id, "separated", (evidence_ref,),
                    first_separator(lean_truth[base_name], lean_truth[strong_name]),
                ),
                VerifiedClaimRelation(
                    weak.id, base.id, "separated", (evidence_ref,),
                    first_separator(lean_truth[weak_name], lean_truth[base_name]),
                ),
            ]

    classes = quotient_by_verified_equivalence((obj.id for obj in objects.values()), relations)
    if len(objects) != 40:
        raise AssertionError(f"expected 40 source objects, got {len(objects)}")
    if len(classes) != 15:
        raise AssertionError(f"expected 15 warranted semantic classes, got {len(classes)}")

    signature_by_object = {
        objects[(claim, dialect)].id: lean_truth[claim]
        for claim in CLAIMS
        for dialect in ("lean4-bool-v0", "smtlib2-bool-v0")
    }
    false_merges = []
    for group in classes:
        signatures = {signature_by_object[item] for item in group}
        if len(signatures) != 1:
            false_merges.append(group)
    if false_merges:
        raise AssertionError(f"false semantic merges: {false_merges}")

    evidence = {
        "schema": "mathgraph.crystal-math-claim-dialect-v0.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_crystal_head": PARENT_CRYSTAL,
        "waist_changed": False,
        "scope": {
            "families": 5,
            "claims": 20,
            "dialects": ["Lean4/Bool executable semantics", "SMT-LIB2/Z3"],
            "finite_valuations_per_claim": 8,
        },
        "results": {
            "source_objects": len(objects),
            "cross_dialect_truth_matches": 20,
            "z3_relation_checks": len(smt_relations),
            "warranted_equivalence_classes": len(classes),
            "false_merges": 0,
            "strict_strengthening_families": 5,
            "strict_weakening_families": 5,
        },
        "source_digests": {
            "lean_sha256": sha256_file(LEAN_SOURCE),
            "smtlib_sha256": sha256_file(SMT_SOURCE),
            "generated_smt_queries_sha256": hashlib.sha256(smt_queries.encode()).hexdigest(),
        },
        "tool_versions": {
            "lean": run(["lean", "--version"]).strip(),
            "z3": run(["z3", "--version"]).strip(),
            "python": sys.version.split()[0],
        },
        "claim_truth_signatures": {
            claim: "".join("1" if x else "0" for x in lean_truth[claim])
            for claim in CLAIMS
        },
        "claim_object_ids": {
            f"{claim}:{dialect}": obj.id
            for (claim, dialect), obj in sorted(objects.items())
        },
        "relation_ids": [relation.id for relation in relations],
        "boundary": (
            "Finite propositional Bool fragment only. This qualifies the existing Crystal "
            "SemanticObject waist as sufficient to carry two independently executed claim "
            "dialects plus verified equivalence/implication/separation relations. It does "
            "not establish a universal mathematical claim language, cross-foundation "
            "equivalence, quantifier/dependent-type normalization, or unrestricted theorem "
            "extraction from prose."
        ),
    }

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_MATH_CLAIM_DIALECT_V0=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
