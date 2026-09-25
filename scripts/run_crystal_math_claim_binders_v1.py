#!/usr/bin/env python3
"""Binder/type-sensitive dual-dialect qualification for Crystal claim objects."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from mathgraph.crystal import SemanticObject
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation, quotient_by_verified_equivalence

ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "experiments" / "crystal_math_claim_binders_v1.lean"
SMT = ROOT / "experiments" / "crystal_math_claim_binders_v1.smt2"
EVIDENCE = ROOT / "evidence" / "crystal-math-claim-binders-v1" / "result.json"
PARENT = "68f30f828840977ec1bac9ea04288438627b8a37"

CLAIMS = tuple(
    f"f{family}.{variant}"
    for family in range(1, 6)
    for variant in ("base", "equiv", "stronger", "weaker")
)
COUNTS = {**{f"f{i}.{v}": 512 for i in (1, 2, 3) for v in ("base","equiv","stronger","weaker")},
          **{f"f4.{v}": 27 for v in ("base","equiv","stronger","weaker")},
          **{f"f5.{v}": 64 for v in ("base","equiv","stronger","weaker")}}

LEAN_STATEMENTS = {
    "f1.base": "∀ x : Tri, P x → Q x",
    "f1.equiv": "∀ y : Tri, Q y ∨ ¬ P y",
    "f1.stronger": "∀ x : Tri, P x → (Q x ∧ R x)",
    "f1.weaker": "∀ x : Tri, (P x ∧ R x) → Q x",
    "f2.base": "∃ x : Tri, P x ∧ Q x",
    "f2.equiv": "¬ ∀ z : Tri, ¬ P z ∨ ¬ Q z",
    "f2.stronger": "∃ x : Tri, P x ∧ Q x ∧ R x",
    "f2.weaker": "∃ x : Tri, P x",
    "f3.base": "∀ x y : Tri, E x y → E y x",
    "f3.equiv": "∀ a b : Tri, E b a ∨ ¬ E a b",
    "f3.stronger": "(∀ x y : Tri, E x y → E y x) ∧ (∀ x : Tri, E x x)",
    "f3.weaker": "∀ y : Tri, E a y → E y a",
    "f4.base": "∀ x y : Tri, F x = F y → x = y",
    "f4.equiv": "F a ≠ F b ∧ F a ≠ F c ∧ F b ≠ F c",
    "f4.stronger": "∀ x : Tri, F x = x",
    "f4.weaker": "F a ≠ F b",
    "f5.base": "∀ b : Bit, ∃ x : Tri, H b x",
    "f5.equiv": "∀ b : Bit, ¬ ∀ x : Tri, ¬ H b x",
    "f5.stronger": "∃ x : Tri, ∀ b : Bit, H b x",
    "f5.weaker": "∃ b : Bit, ∃ x : Tri, H b x",
}
SMT_STATEMENTS = {
    "f1.base": "(forall ((x Tri)) (=> (P x) (Q x)))",
    "f1.equiv": "(forall ((y Tri)) (or (Q y) (not (P y))))",
    "f1.stronger": "(forall ((x Tri)) (=> (P x) (and (Q x) (R x))))",
    "f1.weaker": "(forall ((x Tri)) (=> (and (P x) (R x)) (Q x)))",
    "f2.base": "(exists ((x Tri)) (and (P x) (Q x)))",
    "f2.equiv": "(not (forall ((z Tri)) (or (not (P z)) (not (Q z)))))",
    "f2.stronger": "(exists ((x Tri)) (and (P x) (Q x) (R x)))",
    "f2.weaker": "(exists ((x Tri)) (P x))",
    "f3.base": "(forall ((x Tri) (y Tri)) (=> (E x y) (E y x)))",
    "f3.equiv": "(forall ((a Tri) (b Tri)) (or (E b a) (not (E a b))))",
    "f3.stronger": "(and f3_base (forall ((x Tri)) (E x x)))",
    "f3.weaker": "(forall ((y Tri)) (=> (E A y) (E y A)))",
    "f4.base": "(forall ((x Tri) (y Tri)) (=> (= (F x) (F y)) (= x y)))",
    "f4.equiv": "(and (distinct (F A) (F B)) (distinct (F A) (F C)) (distinct (F B) (F C)))",
    "f4.stronger": "(forall ((x Tri)) (= (F x) x))",
    "f4.weaker": "(distinct (F A) (F B))",
    "f5.base": "(forall ((b Bit)) (exists ((x Tri)) (H b x)))",
    "f5.equiv": "(forall ((b Bit)) (not (forall ((x Tri)) (not (H b x)))))",
    "f5.stronger": "(exists ((x Tri)) (forall ((b Bit)) (H b x)))",
    "f5.weaker": "(exists ((b Bit) (x Tri)) (H b x))",
}
CONTEXTS = {
    1: (("P","Tri→Bool"),("Q","Tri→Bool"),("R","Tri→Bool")),
    2: (("P","Tri→Bool"),("Q","Tri→Bool"),("R","Tri→Bool")),
    3: (("E","Tri→Tri→Bool"),),
    4: (("F","Tri→Tri"),),
    5: (("H","Bit→Tri→Bool"),),
}

def run(command: list[str], input_text: str | None = None) -> str:
    p = subprocess.run(command, cwd=ROOT, input=input_text, text=True, capture_output=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit(f"command failed: {command}")
    return p.stdout

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def lean_signatures() -> dict[str, int]:
    out = run(["lean","--run",str(LEAN)])
    result = {}
    for line in out.splitlines():
        if "=" in line:
            name, value = line.strip().split("=",1)
            if name in CLAIMS:
                result[name] = int(value)
    if set(result) != set(CLAIMS):
        raise AssertionError(f"missing Lean claims: {set(CLAIMS)-set(result)}")
    return result

def b(v: bool) -> str:
    return "true" if v else "false"

def tri(n: int) -> str:
    return ("A","B","C")[n]

def model_assertions(family: int, model: int) -> list[str]:
    if family in (1,2):
        p, q, r = model % 8, (model // 8) % 8, (model // 64) % 8
        lines=[]
        for fn,mask in (("P",p),("Q",q),("R",r)):
            for i,name in enumerate(("A","B","C")):
                lines.append(f"(assert (= ({fn} {name}) {b(bool(mask & (1<<i)))}))")
        return lines
    if family == 3:
        lines=[]
        for i,x in enumerate(("A","B","C")):
            for j,y in enumerate(("A","B","C")):
                lines.append(f"(assert (= (E {x} {y}) {b(bool(model & (1<<(i*3+j))))}))")
        return lines
    if family == 4:
        a, rem = model % 3, model // 3
        bb, c = rem % 3, (rem // 3) % 3
        return [f"(assert (= (F A) {tri(a)}))",f"(assert (= (F B) {tri(bb)}))",f"(assert (= (F C) {tri(c)}))"]
    if family == 5:
        lines=[]
        for i,x in enumerate(("Z","O")):
            for j,y in enumerate(("A","B","C")):
                lines.append(f"(assert (= (H {x} {y}) {b(bool(model & (1<<(i*3+j))))}))")
        return lines
    raise AssertionError(family)

def z3_signatures_and_relations() -> tuple[dict[str,int],dict[str,str],str]:
    parts=[SMT.read_text()]
    for family in range(1,6):
        count=COUNTS[f"f{family}.base"]
        for model in range(count):
            parts.append("(push)")
            parts.extend(model_assertions(family,model))
            for variant in ("base","equiv","stronger","weaker"):
                name=f"f{family}.{variant}"
                sym=name.replace(".","_")
                parts.extend([f'(echo "VAL {name} {model}")',"(push)",f"(assert (not {sym}))","(check-sat)","(pop)"])
            parts.append("(pop)")
    for family in range(1,6):
        base=f"f{family}_base"; eq=f"f{family}_equiv"; strong=f"f{family}_stronger"; weak=f"f{family}_weaker"
        checks=(
            ("equiv",f"(xor {base} {eq})"),
            ("stronger_implies_base",f"(and {strong} (not {base}))"),
            ("base_not_implies_stronger",f"(and {base} (not {strong}))"),
            ("base_implies_weaker",f"(and {base} (not {weak}))"),
            ("weaker_not_implies_base",f"(and {weak} (not {base}))"),
            ("stronger_non_equiv_weaker",f"(xor {strong} {weak})"),
        )
        for label,formula in checks:
            parts.extend([f'(echo "REL f{family} {label}")',"(push)",f"(assert {formula})","(check-sat)","(pop)"])
    text="\n".join(parts)+"\n"
    out=run(["z3","-in","-smt2"],text)
    truth={name:0 for name in CLAIMS}
    relations={}
    pending=None
    for raw in out.splitlines():
        line=raw.strip().strip('"')
        if line.startswith("VAL "):
            _,name,model=line.split(); pending=("VAL",name,int(model))
        elif line.startswith("REL "):
            _,family,label=line.split(); pending=("REL",family,label)
        elif line in {"sat","unsat","unknown"} and pending:
            if line=="unknown":
                raise AssertionError(f"Z3 UNKNOWN at {pending}")
            if pending[0]=="VAL":
                _,name,model=pending
                if line=="unsat":
                    truth[name] |= 1 << model
            else:
                _,family,label=pending
                relations[f"{family}.{label}"]=line
            pending=None
    if len(relations)!=30:
        raise AssertionError(f"expected 30 relation checks, got {len(relations)}")
    return truth,relations,text

def main() -> None:
    lean=lean_signatures()
    z3,relations,query=z3_signatures_and_relations()
    mismatches={name:(lean[name],z3[name]) for name in CLAIMS if lean[name]!=z3[name]}
    if mismatches:
        raise AssertionError(f"cross-dialect signature mismatch: {mismatches}")

    unsat={"equiv","stronger_implies_base","base_implies_weaker"}
    sat={"base_not_implies_stronger","weaker_not_implies_base","stronger_non_equiv_weaker"}
    for family in range(1,6):
        for label in unsat:
            assert relations[f"f{family}.{label}"]=="unsat"
        for label in sat:
            assert relations[f"f{family}.{label}"]=="sat"

    objects={}
    for claim in CLAIMS:
        family=int(claim[1])
        for dialect,statement,source in (
            ("lean4-finite-binders-v1",LEAN_STATEMENTS[claim],f"{LEAN.relative_to(ROOT)}#{claim}"),
            ("smtlib2-finite-binders-v1",SMT_STATEMENTS[claim],f"{SMT.relative_to(ROOT)}#{claim}"),
        ):
            obj=MathClaimPayload(
                claim_id=claim,
                dialect=dialect,
                context=CONTEXTS[family],
                assumptions=(),
                statement=statement,
                source_ref=source,
            ).semantic_object()
            assert SemanticObject.from_bytes(obj.to_bytes())==obj
            objects[(claim,dialect)]=obj

    relations_verified=[]
    ev="hosted:crystal-math-claim-binders-v1"
    for claim in CLAIMS:
        relations_verified.append(VerifiedClaimRelation(
            objects[(claim,"lean4-finite-binders-v1")].id,
            objects[(claim,"smtlib2-finite-binders-v1")].id,
            "equivalent",(ev,)
        ))
    for family in range(1,6):
        for dialect in ("lean4-finite-binders-v1","smtlib2-finite-binders-v1"):
            base=objects[(f"f{family}.base",dialect)]
            eq=objects[(f"f{family}.equiv",dialect)]
            strong=objects[(f"f{family}.stronger",dialect)]
            weak=objects[(f"f{family}.weaker",dialect)]
            relations_verified += [
                VerifiedClaimRelation(base.id,eq.id,"equivalent",(ev,)),
                VerifiedClaimRelation(strong.id,base.id,"implies",(ev,)),
                VerifiedClaimRelation(base.id,weak.id,"implies",(ev,)),
                VerifiedClaimRelation(base.id,strong.id,"separated",(ev,)),
                VerifiedClaimRelation(weak.id,base.id,"separated",(ev,)),
            ]

    classes=quotient_by_verified_equivalence((o.id for o in objects.values()),relations_verified)
    if len(objects)!=40 or len(classes)!=15:
        raise AssertionError(f"unexpected quotient size objects={len(objects)} classes={len(classes)}")
    sig_by_id={objects[(claim,d)].id:lean[claim] for claim in CLAIMS for d in ("lean4-finite-binders-v1","smtlib2-finite-binders-v1")}
    false_merges=[group for group in classes if len({sig_by_id[x] for x in group})!=1]
    if false_merges:
        raise AssertionError(f"false semantic merges: {false_merges}")

    evidence={
      "schema":"mathgraph.crystal-math-claim-binders-v1.qualified",
      "status":"QUALIFIED_BOUNDED",
      "parent_claim_dialect_head":PARENT,
      "crystal_waist_changed":False,
      "claim_dialect_code_changed":False,
      "scope":{
        "families":5,"claims":20,"source_objects":40,
        "free_symbol_model_counts":{"f1":512,"f2":512,"f3":512,"f4":27,"f5":64},
        "features":["forall","exists","nested-binders","two-sorts","free-predicates","binary-relations","typed-functions","alternating-quantifiers"],
      },
      "results":{
        "cross_dialect_signature_matches":20,
        "z3_relation_checks":30,
        "warranted_equivalence_classes":15,
        "false_merges":0,
        "strict_strengthening_families":5,
        "strict_weakening_families":5,
      },
      "source_digests":{
        "lean_sha256":digest(LEAN),
        "smtlib_sha256":digest(SMT),
        "generated_z3_queries_sha256":hashlib.sha256(query.encode()).hexdigest(),
      },
      "tool_versions":{
        "lean":run(["lean","--version"]).strip(),
        "z3":run(["z3","--version"]).strip(),
        "python":sys.version.split()[0],
      },
      "boundary":"Finite typed domains only. This qualifies binder/type-sensitive mathematical claims as payloads behind the unchanged Crystal/claim-dialect waist. It does not establish infinite-domain completeness, dependent-type normalization, arbitrary foundations, or literature extraction.",
    }
    EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("CRYSTAL_MATH_CLAIM_BINDERS_V1=QUALIFIED_BOUNDED")
    print(json.dumps(evidence,sort_keys=True))

if __name__=="__main__":
    main()
