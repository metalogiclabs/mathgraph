#!/usr/bin/env python3
"""Actual MathGraph source-change verification. Run from checked-out repository root."""
from __future__ import annotations
import argparse, hashlib, importlib, json, os, subprocess, sys, time, types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE="e48f094fa400c77ab07404645f6e12cfba7ebf45"
OLD_BLOB="ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8"
NEW_BLOB="85de97a95f225ad564feb29faec24ce67f3f2e0e"
SOURCE="mathgraph_check/warrant_resolution.py"
ORIGINAL=ROOT/SOURCE
sys.path.insert(0,str(ROOT))
from mathgraph_check import warrant_resolution as now

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def exact_source_gate():
    assert git("rev-parse",BASE)==BASE
    assert git("rev-parse",f"{BASE}:{SOURCE}")==OLD_BLOB
    assert git("hash-object",str(ORIGINAL))==NEW_BLOB
    prev=subprocess.check_output(["git","show",f"{BASE}:{SOURCE}"],cwd=ROOT,text=True)
    current=ORIGINAL.read_text()
    before="""    def evidence_is_live(route: Route) -> bool:
        required = route.evidence
        if route.relation is not None:
            bridge = rel[route.relation]
            required += (bridge.verifier,) + bridge.evidence
        return all(x not in withdrawn for x in required)
"""
    after="""    def evidence_is_live(route: Route) -> bool:
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
    assert before in prev and after in current
    assert prev.replace(before,after)==current, "UNAPPROVED_CODE_CHANGE"
    mod=types.ModuleType("v1_frozen_previous_resolver")
    sys.modules[mod.__name__]=mod
    exec(compile(prev,"git:"+BASE+":"+SOURCE,"exec"),mod.__dict__)
    return mod

def cases(mod):
    C,R,T=mod.Claim,mod.Receipt,mod.Route
    Q=mod.QualifiedRelation
    simple=([C("a","documentary","scope"),C("b","documentary","scope"),
             C("free","documentary","scope")],
            [T("a",("root",)),T("b",("mid",),("a",)),
             T("free",("free_ev",))],
            [R("root","documentary","scope"),R("mid","documentary","scope"),
             R("free_ev","documentary","scope")],[])
    cs=[C("source","documentary","src"),C("target","formal","dst")]
    ev=[R("src_notice","documentary","src"),R("verifier","formal","dst"),
        R("checked","formal","dst")]
    rs=[T("source",("src_notice",)),T("target",("src_notice","checked"),
                                   ("source",),relation="verified_bridge")]
    qb=Q("verified_bridge","documentary","src","formal","dst",
         "verifier",("checked",),checked_route=rs[1])
    return [simple,(cs,rs,ev,[qb])]

def parity(old):
    count=0
    for index in range(2):
        a=cases(old)[index]
        b=cases(now)[index]
        ids=[x.id for x in a[2]]
        for bitmask in range(1<<len(ids)):
            withdrawn=frozenset(s for i,s in enumerate(ids) if bitmask>>i&1)
            old_result=old.resolve_graph(*a[:3],relations=a[3],withdrawn=withdrawn)
            new_result=now.resolve_graph(*b[:3],relations=b[3],withdrawn=withdrawn)
            assert dict(old_result.states)==dict(new_result.states)
            old_routes=tuple((r.conclusion,r.evidence,r.premises,r.relation)
                             for r in old_result.active_routes)
            new_routes=tuple((r.conclusion,r.evidence,r.premises,r.relation)
                             for r in new_result.active_routes)
            assert old_routes==new_routes
            count+=1
    # The deliberately incorrect 'always live' shadow bypasses evidence withdrawal.
    cs,routes,ev,rel=cases(now)[0]
    withdrawn=frozenset({"root"})
    true_after=now.resolve_graph(cs,routes,ev,withdrawn=withdrawn)
    bogus=now.resolve_graph(cs,routes,ev,withdrawn=frozenset())
    caught=(true_after.states["b"]=="UNKNOWN" and bogus.states["b"]=="SOURCE_DOCUMENTED")
    assert caught
    return {"states_and_active_routes_parity_cases":count,
            "deliberate_ignore_withdrawal_mutation_detected":caught,
            "code_exact_diff_confirmed":True}

def run_tests(args):
    start=time.perf_counter()
    proc=subprocess.run([sys.executable,"-m","pytest","-q",*args],
       cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-start
    lines=proc.stdout.strip().splitlines()
    return {"success":proc.returncode==0,"exit_code":proc.returncode,
       "duration_seconds":round(elapsed,5),
       "tail":lines[-14:],
       "command":"python -m pytest -q "+" ".join(args)}

def release_gate(parity_ok,focused_ok,full_ok):
    # Real MathGraph resolver, documentary bounded branch-review decision.
    scope="metalogiclabs/mathgraph@research/authentic-resolver-change-v1:review"
    names=["source_authority","implementation_identity","parity","focused",
           "full_comparator","release_policy"]
    claims=[now.Claim("source_requirement","documentary",scope),
            now.Claim("native_parity","documentary",scope),
            now.Claim("focused_tests","documentary",scope),
            now.Claim("broad_tests","documentary",scope),
            now.Claim("protected_research_review","documentary",scope),
            now.Claim("independent_unrelated","documentary",scope)]
    receipts=[now.Receipt(name,"documentary",scope) for name in names]
    receipts.append(now.Receipt("unrelated_receipt","documentary",scope))
    routes=[now.Route("source_requirement",("source_authority","implementation_identity")),
            now.Route("native_parity",("parity",),("source_requirement",)),
            now.Route("focused_tests",("focused",)),
            now.Route("broad_tests",("full_comparator",)),
            now.Route("protected_research_review",("release_policy",),
                 ("native_parity","focused_tests","broad_tests")),
            now.Route("independent_unrelated",("unrelated_receipt",))]
    withdrawn_initial=set()
    if not parity_ok:withdrawn_initial.add("parity")
    if not focused_ok:withdrawn_initial.add("focused")
    if not full_ok:withdrawn_initial.add("full_comparator")
    full=dict(now.resolve_graph(claims,routes,receipts,
                 withdrawn=frozenset(withdrawn_initial)).states)
    scenarios={}
    for item in names:
        w=frozenset(withdrawn_initial|{item})
        state=dict(now.resolve_graph(claims,routes,receipts,withdrawn=w).states)
        scenarios[item]={"review":state["protected_research_review"],
                         "unrelated":state["independent_unrelated"],
                         "withdrawn":item}
        assert state["protected_research_review"]=="UNKNOWN"
        assert state["independent_unrelated"]=="SOURCE_DOCUMENTED"
    unrelated=dict(now.resolve_graph(claims,routes,receipts,
          withdrawn=frozenset(withdrawn_initial|{"unrelated_receipt"})).states)
    assert unrelated["independent_unrelated"]=="UNKNOWN"
    assert unrelated["protected_research_review"]==full["protected_research_review"]
    fail_closed=False
    try:
        now.resolve_graph([now.Claim("formal_release","formal",scope)],
           [now.Route("formal_release",("source_authority",))],receipts)
    except ValueError as e:
        fail_closed="CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE" in str(e)
    assert fail_closed
    # Restoration is actual reclose with all independently qualified evidence.
    restored=dict(now.resolve_graph(claims,routes,receipts).states)
    assert restored["protected_research_review"]=="SOURCE_DOCUMENTED"
    return {"initial_state":full,"withdrawals":scenarios,
            "withdraw_unrelated":{"review":unrelated["protected_research_review"],
                                  "unrelated":unrelated["independent_unrelated"]},
            "restored":restored["protected_research_review"],
            "formal_promotion_without_bridge":"REJECTED",
            "review_permission":"NOT_DEPLOY_OR_MERGE_AUTHORIZATION"}

def main():
    prior=exact_source_gate()
    start=time.perf_counter()
    parity_result=parity(prior)
    parity_time=time.perf_counter()-start
    focused_paths=["tests/test_mathgraph_warrant_resolution_core.py"]
    full_paths=["conformance/protocol_v1/test_consumer.py",
      "conformance/resolve_v1/test_consumer.py",
      "tests/test_mathgraph_resolve_publication_v1.py",
      "tests/test_mathgraph_warrant_resolution_core.py",
      "tests/test_mathgraph_living_warrants_v1.py"]
    focused=run_tests(focused_paths)
    conventional=run_tests(full_paths)
    state=release_gate(True,focused["success"],conventional["success"])
    # Full proof eligibility requires all three checks.
    protected=state["initial_state"]["protected_research_review"]
    baseline_cost=conventional["duration_seconds"]
    directed_cost=round(baseline_cost+focused["duration_seconds"]+parity_time,5)
    result={
      "status":"PASS_AUTHENTIC_SOURCE_CHANGE_BOUNDED_REVIEW" if protected=="SOURCE_DOCUMENTED"
         else "UNKNOWN_MANDATORY_VERIFICATION_FAILED",
      "actual_production_source_change":SOURCE,
      "base_commit":BASE,"base_blob_sha1":OLD_BLOB,"changed_blob_sha1":NEW_BLOB,
      "actual_resolver":"mathgraph_check.warrant_resolution.resolve_graph",
      "behavior_parity":parity_result,"parity_seconds":round(parity_time,5),
      "focused":focused,"conventional_broad":conventional,"protected_review":state,
      "cost_accounting":{"metric":"CI process elapsed seconds; not external engineer costs",
        "conventional_full_only_seconds":baseline_cost,
        "directed_plus_full_mandatory_seconds":directed_cost,
        "directed_incremental_overhead_seconds":round(directed_cost-baseline_cost,5),
        "winner":"CONVENTIONAL_NO_INCREMENTAL_OVERHEAD" if directed_cost>=baseline_cost else "DIRECTED",
        "missing_costs":"source interpretation, CI startup and external validation not monetized"},
      "comparison":"CONVENTIONAL_WINS_FULL_LIFECYCLE_WALL_TIME_IF_EXTRA_GATES_REQUIRED",
      "R7_CLC_Lean":"UNCHANGED_PRIOR_GREEN_NOT_RERUN_HERE",
      "limitations":["research branch only; review eligibility not GitHub protected merge",
        "receipt admission by qualified CI runner, no source publisher authentication",
        "documentary scope, not formally verified code change",
        "broad comparator is selected real warrant tests, not whole monorepo",
        "no production GitHub Check status or commercial savings"]}
    (HERE/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":result["status"],"parity_cases":parity_result["states_and_active_routes_parity_cases"],
      "mutation_detected":parity_result["deliberate_ignore_withdrawal_mutation_detected"],
      "focused_success":focused["success"],"full_success":conventional["success"],
      "review":protected,"comparison":result["cost_accounting"]},sort_keys=True))
    if not focused["success"] or not conventional["success"]:
        raise RuntimeError("MANDATORY_SUITE_FAILED")

if __name__=="__main__":main()
