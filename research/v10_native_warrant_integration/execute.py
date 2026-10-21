#!/usr/bin/env python3
"""Actual MathGraph warrant_resolution + historical V10 receipt and native controls.

No reimplementation of graph closure. Neither documentary authority nor a
Python unit test is a formal verification receipt. The whole bounded study is
explicitly in ONE documentary scope; cross-kind escalation must be rejected.
"""
from __future__ import annotations
import functools, hashlib, json
from pathlib import Path
from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, resolve_graph, compare_snapshots
)

HERE=Path(__file__).resolve().parent
FIXTURE=HERE/"v10_admission.json"
SOURCE_SHA="29db6bef935f8536636443f26e842a399ed2d74d456e75b6f836b068e0446b9e"
ARTIFACT_SHA="28bfb0cf833d9eb3d5945e4e96683a37a305ef17f0ae4046ce1cd16861b852f7"
HEAD="7594e38fc1fa1e17128f3d98ce71fe938b62d300"
SCOPE="python/functools:source-sha256:"+SOURCE_SHA+":native-33keys:v10:bounded-documentary"

def admit_historical_profile():
    item=json.loads(FIXTURE.read_text())
    p=item["provenance"];a=item["admitted_claims"];n=item["native_observation"]
    assert item["schema"]=="mathgraph.v10.external-receipt-admission.v1"
    assert p["source_sha256"]==SOURCE_SHA and p["artifact_zip_sha256"]==ARTIFACT_SHA
    assert p["head_sha"]==HEAD and p["run_id"]==39567659722
    assert p["source_url"]=="https://docs.python.org/3/library/functools.html"
    assert a=={
        "cache_owner":"functools.cache",
        "lru_owner":"functools.lru_cache",
        "equivalence":"same as lru_cache(maxsize=None)",
        "no_eviction":"never needs to evict old values"
    }
    assert n["test_keys"]==33 and n["cache_function_evaluations"]==33
    assert n["unbounded_lru_function_evaluations"]==33 and n["first_result"]==1
    return item

def measure(decorator):
    calls={"n":0}
    def f(value):
        calls["n"]+=1
        return value*7+1
    wrapped=decorator(f)
    first=wrapped(0)
    for x in range(1,33):
        wrapped(x)
    repeat=wrapped(0)
    return {"evaluations":calls["n"],"first":first,"repeat":repeat,
            "reused_without_recomputation":calls["n"]==33 and first==repeat}

def native_check():
    cache=measure(functools.cache)
    unbounded=measure(functools.lru_cache(maxsize=None))
    bounded=measure(functools.lru_cache(maxsize=8))
    assert cache=={"evaluations":33,"first":1,"repeat":1,
                   "reused_without_recomputation":True}
    assert unbounded==cache
    assert bounded["evaluations"]==34 and bounded["first"]==bounded["repeat"]
    assert not bounded["reused_without_recomputation"]
    return {"cache":cache,"unbounded":unbounded,"bounded_counterexample":bounded}

CLAIM_IDS=("cache_owner","lru_owner","equivalence","direct_no_eviction",
           "transported_no_eviction","native_33key_sample","protected_cache_reuse_on_33_cases",
           "unrelated_control")
RECEIPT_IDS=("src_cache","src_lru","src_equivalence","src_no_eviction",
             "qualified_native_sample","declared_protected_decision",
             "independent_unrelated_receipt")
SOURCE_RECEIPTS=frozenset(("src_cache","src_lru","src_equivalence","src_no_eviction"))
def graph():
    claims=[Claim(name,"documentary",SCOPE) for name in CLAIM_IDS]
    receipts=[Receipt(name,"documentary",SCOPE) for name in RECEIPT_IDS]
    routes=[
      Route("cache_owner",("src_cache",)),
      Route("lru_owner",("src_lru",)),
      Route("equivalence",("src_equivalence",),("cache_owner","lru_owner")),
      Route("direct_no_eviction",("src_no_eviction",),("cache_owner",)),
      Route("transported_no_eviction",("src_equivalence",),
            ("equivalence","direct_no_eviction")),
      Route("native_33key_sample",("qualified_native_sample",)),
      Route("protected_cache_reuse_on_33_cases",("declared_protected_decision",),
            ("transported_no_eviction","native_33key_sample")),
      Route("unrelated_control",("independent_unrelated_receipt",)),
    ]
    return claims,routes,receipts

def conventional_baseline(withdrawn):
    """Independent direct rulebook on identical admitted roots; not a human test."""
    live=lambda x:x not in withdrawn
    cache=live("src_cache")
    lru=live("src_lru")
    relation=cache and lru and live("src_equivalence")
    direct=cache and live("src_no_eviction")
    transported=relation and direct
    native=live("qualified_native_sample")
    qualified=live("declared_protected_decision") and transported and native
    unrelated=live("independent_unrelated_receipt")
    booleans=(cache,lru,relation,direct,transported,native,qualified,unrelated)
    return {key:("SOURCE_DOCUMENTED" if active else "UNKNOWN")
            for key,active in zip(CLAIM_IDS,booleans)}

def run():
    profile=admit_historical_profile()
    observation=native_check()  # actually reexecute the native verifier
    claims,routes,receipts=graph()
    outcomes={}
    full=dict(resolve_graph(claims,routes,receipts).states)
    assert all(x=="SOURCE_DOCUMENTED" for x in full.values())
    check_sets={
      "withdraw_cache_owner":frozenset({"src_cache"}),
      "withdraw_lru_owner":frozenset({"src_lru"}),
      "withdraw_equivalence_edge":frozenset({"src_equivalence"}),
      "withdraw_source_no_eviction":frozenset({"src_no_eviction"}),
      "withdraw_native_sample":frozenset({"qualified_native_sample"}),
      "withdraw_unrelated":frozenset({"independent_unrelated_receipt"}),
      "wrong_source_snapshot":SOURCE_RECEIPTS,
      "bounded_cache_counterexample":frozenset({"qualified_native_sample"}),
      "withdraw_decision_policy":frozenset({"declared_protected_decision"}),
    }
    for name,withdrawn in check_sets.items():
        actual=dict(resolve_graph(claims,routes,receipts,withdrawn=withdrawn).states)
        expected=conventional_baseline(withdrawn)
        assert actual==expected,(name,actual,expected)
        changes=compare_snapshots(full,actual)
        outcomes[name]={"withdrawn":sorted(withdrawn),
                        "protected":actual["protected_cache_reuse_on_33_cases"],
                        "native":actual["native_33key_sample"],
                        "direct":actual["direct_no_eviction"],
                        "equivalence":actual["equivalence"],
                        "unrelated":actual["unrelated_control"],
                        "stale_claims":[k for k,v in changes.items()
                                        if v["after"]=="STALE"]}
    assert outcomes["withdraw_cache_owner"]["protected"]=="UNKNOWN"
    assert outcomes["withdraw_cache_owner"]["native"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_lru_owner"]["direct"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_equivalence_edge"]["direct"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_source_no_eviction"]["equivalence"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_native_sample"]["equivalence"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_unrelated"]["protected"]=="SOURCE_DOCUMENTED"
    assert outcomes["withdraw_unrelated"]["unrelated"]=="UNKNOWN"
    assert outcomes["wrong_source_snapshot"]["native"]=="SOURCE_DOCUMENTED"
    assert outcomes["wrong_source_snapshot"]["protected"]=="UNKNOWN"
    assert outcomes["bounded_cache_counterexample"]["protected"]=="UNKNOWN"
    # Restoration: same original evidence admission and same finite decision.
    restored=dict(resolve_graph(claims,routes,receipts).states)
    assert restored==full

    # Existing typed boundary prevents any accidental promotion into a formal claim.
    formal_fail_closed=False
    try:
        resolve_graph([Claim("unsupported_formal","formal",SCOPE)],
          [Route("unsupported_formal",("src_cache",))],receipts)
    except ValueError as exc:
        formal_fail_closed=str(exc)=="CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE"
    assert formal_fail_closed

    # Least fixed point rejects circular unrooted documentary "evidence".
    cycle=resolve_graph([Claim("a","documentary",SCOPE),Claim("b","documentary",SCOPE)],
      [Route("a",("declared_protected_decision",),("b",)),
       Route("b",("declared_protected_decision",),("a",))],receipts)
    assert dict(cycle.states)=={"a":"UNKNOWN","b":"UNKNOWN"}

    report={
      "status":"PASS_REAL_MATHGRAPH_WARRANT_CLOSURE_IN_DOCUMENTARY_SCOPE",
      "backend":"mathgraph_check.warrant_resolution.resolve_graph",
      "original_source_sha256":SOURCE_SHA,
      "original_external_zip_sha256":ARTIFACT_SHA,
      "exact_prior_run_id":profile["provenance"]["run_id"],
      "caller_source_admission":"HISTORICAL_EXTERNALLY_REVIEWED_PROFILE_NOT_NATIVE_SOURCE_AUTHENTICATION",
      "native_independent_replay":observation,
      "full":full,"scenarios":outcomes,
      "formal_promotion_without_verified_adapter":"REJECTED",
      "cycle":"UNKNOWN",
      "comparison":"CONVENTIONAL_RULEBOOK_TIE_ON_ALL_SCENARIOS",
      "lean_bridge":"separate pinned native Lean replay, not dynamic formal evidence adapter",
      "limitations":["documentary scope, no global mathematical proof",
         "protected claim is finite 33-key case plus source statement, not release permission",
         "external archived bytes are not authenticated by this fixture",
         "no actual R7.2 CLC theorem instantiation with this Python receipt",
         "no commercial advantage or skilled human baseline"]
    }
    (HERE/"result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":report["status"],
      "withdrawal_cases":len(outcomes),
      "formal_escalation":"REJECTED","cycle":"UNKNOWN",
      "native_cache_calls":observation["cache"]["evaluations"],
      "bounded_bad_calls":observation["bounded_counterexample"]["evaluations"],
      "comparative":report["comparison"]},sort_keys=True))
if __name__=="__main__":run()
