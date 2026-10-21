#!/usr/bin/env python3
"""Independent finite old-vs-new predicate checker, original resolver warrant gate.

This finite exhaustive check is NOT a general theorem about the entire resolver.
"""
import ast
import hashlib
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PRE="e48f094fa400c77ab07404645f6e12cfba7ebf45"
SOURCE="mathgraph_check/warrant_resolution.py"
OLD_BLOB="ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8"
NEW_BLOB="85de97a95f225ad564feb29faec24ce67f3f2e0e"
sys.path.insert(0,str(ROOT))
from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph

BEFORE="""    def evidence_is_live(route: Route) -> bool:
        required = route.evidence
        if route.relation is not None:
            bridge = rel[route.relation]
            required += (bridge.verifier,) + bridge.evidence
        return all(x not in withdrawn for x in required)
"""
AFTER="""    def evidence_is_live(route: Route) -> bool:
        # Short-circuit withdrawn route evidence before inspecting relation
        # qualifications, without materializing a joined receipt tuple.
        if not all(x not in withdrawn for x in route.evidence):
            return False
        if route.relation is None:
            return True
        bridge = rel[route.relation]
        return (bridge.verifier not in withdrawn
                and all(x not in withdrawn for x in bridge.evidence))
"""
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def pinned_sources():
    before=subprocess.check_output(["git","show",f"{PRE}:{SOURCE}"],
                                    cwd=ROOT,text=True)
    after=(ROOT/SOURCE).read_text()
    assert git("rev-parse",PRE)==PRE
    assert git("rev-parse",f"{PRE}:{SOURCE}")==OLD_BLOB
    assert git("hash-object",str(ROOT/SOURCE))==NEW_BLOB
    assert before.count(BEFORE)==1 and after.count(AFTER)==1
    assert before.replace(BEFORE,AFTER)==after,"CODE_SCOPE_VIOLATION"
    return before,after

def nested_predicate(source,rel,withdrawn):
    """Compile just the source-code nested predicate under supplied typed inputs."""
    module=ast.parse(source)
    top=next(x for x in module.body if isinstance(x,ast.FunctionDef)
             and x.name=="resolve_graph")
    nested=next(x for x in top.body if isinstance(x,ast.FunctionDef)
                and x.name=="evidence_is_live")
    node=ast.fix_missing_locations(ast.Module(body=[nested],type_ignores=[]))
    variables={"rel":rel,"withdrawn":withdrawn,"Route":object}
    exec(compile(node,"pinned-original-nested-function","exec"),variables)
    return variables["evidence_is_live"]

def oracle(route,bridge,withdrawn):
    """Source-independent declarative liveness contract, not executable graph logic."""
    eligible=lambda r:r not in withdrawn
    return (all(map(eligible,route.evidence)) and
            (route.relation is None or (
                eligible(bridge.verifier) and all(map(eligible,bridge.evidence)))))

def enumerate_contract(old,new):
    tested=0
    for route_count in range(4):
        for qualified_count in range(3):
            route_ids=tuple(f"route{i}" for i in range(route_count))
            qual_ids=tuple(f"qual{i}" for i in range(qualified_count))
            for relation_used in (False,True):
                all_ids=route_ids+(("verifier",)+qual_ids if relation_used else ())
                bridge=SimpleNamespace(verifier="verifier",evidence=qual_ids)
                route=SimpleNamespace(evidence=route_ids,
                        relation="bridge" if relation_used else None)
                rel={"bridge":bridge} if relation_used else {}
                for states in itertools.product((False,True),repeat=len(all_ids)):
                    withdrawn=frozenset(k for k,flag in zip(all_ids,states) if flag)
                    prior=nested_predicate(old,rel,withdrawn)(route)
                    candidate=nested_predicate(new,rel,withdrawn)(route)
                    declared=oracle(route,bridge,withdrawn)
                    assert prior==candidate==declared,(route_count,qualified_count,
                         relation_used,withdrawn,prior,candidate,declared)
                    tested+=1
    # Deliberately dangerous edit, rejection of withdrawn route receipt lost.
    mutated=new.replace("            return False\n        if route.relation is None:",
                        "            return True\n        if route.relation is None:")
    assert mutated != new
    route=SimpleNamespace(evidence=("critical",),relation=None)
    bad=nested_predicate(mutated,{},frozenset({"critical"}))(route)
    good=nested_predicate(new,{},frozenset({"critical"}))(route)
    assert bad is True and good is False
    return {"finite_exhaustive_assignments":tested,"source_only_allowed_rewrite":True,
        "malicious_mutation_detected":True,
        "unbounded_generalization":"NOT_PROVED"}

def scoped_gate():
    scope="mathgraph:predicate-evidence-is-live:finite-domain:v2"
    claims=[Claim(x,"documentary",scope) for x in ("source","checker","protected_property","independent")]
    rec=[Receipt(x,"documentary",scope) for x in ("source_identity","independent_checker",
            "property_policy","independent_receipt")]
    routes=[Route("source",("source_identity",)),Route("checker",("independent_checker",)),
        Route("protected_property",("property_policy",),("source","checker")),
        Route("independent",("independent_receipt",))]
    full=dict(resolve_graph(claims,routes,rec).states)
    assert full["protected_property"]=="SOURCE_DOCUMENTED"
    withdrawal={}
    for r in ("source_identity","independent_checker","property_policy"):
        result=dict(resolve_graph(claims,routes,rec,withdrawn=frozenset({r})).states)
        assert result["protected_property"]=="UNKNOWN"
        assert result["independent"]=="SOURCE_DOCUMENTED"
        withdrawal[r]=result["protected_property"]
    # Broad release cannot be derived because no broad-suite route/receipt is admitted.
    broad=Claim("full_application_release","documentary",scope)
    release=dict(resolve_graph(claims+[broad],routes,rec).states)
    assert release["full_application_release"]=="UNKNOWN"
    restored=dict(resolve_graph(claims,routes,rec).states)
    assert restored==full
    formal_rejected=False
    try:
        resolve_graph([Claim("formal_result","formal",scope)],
          [Route("formal_result",("independent_checker",))],rec)
    except ValueError as e:
        formal_rejected="CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE" in str(e)
    assert formal_rejected
    return {"property":full["protected_property"],"withdrawals":withdrawal,
            "full_release":release["full_application_release"],
            "independent":full["independent"],"formal_promotion_rejected":formal_rejected}

def main():
    start=time.perf_counter()
    before,after=pinned_sources()
    proof=enumerate_contract(before,after)
    scoped=scoped_gate()
    duration=time.perf_counter()-start
    report={
      "status":"WARRANTED_BOUNDED_FINITE_PREDICATE_PRESERVATION",
      "original_blob":OLD_BLOB,"new_blob":NEW_BLOB,
      "checker":"independent AST extracted predicate versus finite declared truth table",
      "qualification":proof,"real_mathgraph_review_gate":scoped,
      "checker_internal_seconds":round(duration,6),
      "property_scope":"evidence_is_live for enumerated route/qualified receipt sets",
      "source_admission":"pin checked locally, not remote publisher authentication",
      "full_resolver_correctness":"UNKNOWN_UNCHECKED",
      "whole_application_release":"UNKNOWN",
      "R7_CLC":"UNCHANGED_NOT_REPLAYED",
      "risk":"finite contract not inductive arbitrary-sequence theorem"
    }
    (HERE/"result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":report["status"],"count":proof["finite_exhaustive_assignments"],
       "mutation":proof["malicious_mutation_detected"],"gate":scoped,
       "checker_internal_seconds":report["checker_internal_seconds"]},sort_keys=True))
if __name__=="__main__":main()
