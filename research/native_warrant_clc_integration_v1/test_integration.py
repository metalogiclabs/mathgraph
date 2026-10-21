#!/usr/bin/env python3
"""Actual MathGraph resolver integration with native Python; no replica resolver."""
import functools, hashlib, json
from pathlib import Path

from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, resolve_graph, compare_snapshots,
)

OUT=Path(__file__).with_name("result.json")
DOC="python.functools:source:20261021"
NATIVE="python.functools:native:33cases"
SOURCE_PIN="29db6bef935f8536636443f26e842a399ed2d74d456e75b6f836b068e0446b9e"

def native_check(maxsize):
    count={"n":0}
    def f(x):
        count["n"]+=1
        return 7*x+1
    wrapped=functools.lru_cache(maxsize=maxsize)(f)
    first=wrapped(0)
    for x in range(1,33):
        wrapped(x)
    last=wrapped(0)
    return {"evaluations":count["n"],"same_value":first==last,
            "no_recomputation":count["n"]==33}

def graph():
    claims=[
        Claim("owner.cache","documentary",DOC),
        Claim("owner.lru","documentary",DOC),
        Claim("statement.noeviction","documentary",DOC),
        Claim("relation.equivalence","documentary",DOC),
        Claim("conclusion.source_scoped","documentary",DOC),
        Claim("conclusion.alternatively_supported","documentary",DOC),
        Claim("control.independent","documentary",DOC),
        Claim("native.33key_result","formal",NATIVE),
        Claim("native.independent_control","formal",NATIVE),
    ]
    receipts=[
        Receipt("source.cache_owner@"+SOURCE_PIN,"documentary",DOC),
        Receipt("source.lru_owner@"+SOURCE_PIN,"documentary",DOC),
        Receipt("source.noeviction@"+SOURCE_PIN,"documentary",DOC),
        Receipt("source.equivalence@"+SOURCE_PIN,"documentary",DOC),
        Receipt("source.alternative@"+SOURCE_PIN,"documentary",DOC),
        Receipt("source.independent@"+SOURCE_PIN,"documentary",DOC),
        Receipt("native.actual_33keys","formal",NATIVE),
        Receipt("native.independent_case","formal",NATIVE),
    ]
    routes=[
        Route("owner.cache",(receipts[0].id,)),
        Route("owner.lru",(receipts[1].id,)),
        Route("statement.noeviction",(receipts[2].id,),("owner.cache",)),
        Route("relation.equivalence",(receipts[3].id,),("owner.cache","owner.lru")),
        Route("conclusion.source_scoped",(receipts[2].id,),("relation.equivalence","statement.noeviction")),
        Route("conclusion.alternatively_supported",(receipts[2].id,),("statement.noeviction",)),
        Route("conclusion.alternatively_supported",(receipts[4].id,)), # independent route
        Route("control.independent",(receipts[5].id,)),
        Route("native.33key_result",(receipts[6].id,)),
        Route("native.independent_control",(receipts[7].id,)),
    ]
    return claims,routes,receipts

def main():
    native_good=native_check(None)
    native_bad=native_check(8)
    assert native_good["no_recomputation"] and native_good["evaluations"]==33
    assert not native_bad["no_recomputation"] and native_bad["evaluations"]==34

    claims,routes,receipts=graph()
    root=resolve_graph(claims,routes,receipts)
    assert all(x!="UNKNOWN" for x in root.states.values())

    revoked_cache=receipts[0].id
    revoked_lru=receipts[1].id
    revoked_equiv=receipts[3].id
    revoked_clause=receipts[2].id
    alternative=receipts[4].id
    experiments={
       "cache_owner":frozenset((revoked_cache,)),
       "lru_owner":frozenset((revoked_lru,)),
       "equivalence":frozenset((revoked_equiv,)),
       "noeviction":frozenset((revoked_clause,)),
       "both_source_routes":frozenset((revoked_clause,alternative)),
    }
    snapshots={}
    for label,withdrawn in experiments.items():
        after=resolve_graph(claims,routes,receipts,withdrawn=withdrawn)
        repeated=resolve_graph(claims,routes,receipts,withdrawn=withdrawn)
        assert dict(after.states)==dict(repeated.states),"NONDETERMINISTIC_RECLOSURE"
        snapshots[label]=dict(after.states)

    mainclaim="conclusion.source_scoped"
    altclaim="conclusion.alternatively_supported"
    assert snapshots["cache_owner"][mainclaim]=="UNKNOWN"
    assert snapshots["lru_owner"][mainclaim]=="UNKNOWN"
    assert snapshots["equivalence"][mainclaim]=="UNKNOWN"
    assert snapshots["noeviction"][mainclaim]=="UNKNOWN"
    assert snapshots["noeviction"][altclaim]=="SOURCE_DOCUMENTED"
    assert snapshots["both_source_routes"][altclaim]=="UNKNOWN"
    for case in snapshots.values():
        assert case["native.33key_result"]=="WARRANTED_BOUNDED"
        assert case["native.independent_control"]=="WARRANTED_BOUNDED"
        assert case["control.independent"]=="SOURCE_DOCUMENTED"

    # A graph crossing documentary->formal types WITHOUT independently verified
    # QualifiedRelation MUST be rejected, not silently accepted.
    bridge_denied=False
    try:
        resolve_graph(
            claims+[Claim("forbidden.cross_kind","formal",NATIVE)],
            routes+[Route("forbidden.cross_kind",("native.actual_33keys",),("owner.cache",))],
            receipts,
        )
    except ValueError as exc:
        bridge_denied=str(exc)=="CROSS_BOUNDARY_PREMISE_WITHOUT_BRIDGE"
    assert bridge_denied,"UNQUALIFIED_DOC_TO_FORMAL_BRIDGE_WAS_ADMITTED"

    change=compare_snapshots(dict(root.states),snapshots["equivalence"])
    assert change[mainclaim]["after"]=="STALE"
    assert not change["native.33key_result"]["changed"]
    assert not change["control.independent"]["changed"]

    # Full-information conventional control preserves already recorded native
    # observation, so it also needs 0 NEW native evaluations on source-only
    # withdrawals. MathGraph's actual resolve_graph is FULLY recomputed.
    results={
        "status":"PASS_ACTUAL_MATHGRAPH_WARRANT_RESOLVER",
        "source_pin_sha256":SOURCE_PIN,
        "source_authenticated_by_this_script":False,
        "native_positive":native_good,
        "native_negative":native_bad,
        "initial":dict(root.states),
        "withdrawal_snapshots":snapshots,
        "snapshots_compared":change,
        "invalid_cross_type_route_denied":bridge_denied,
        "resolver_original_module":resolve_graph.__module__,
        "native_additional_calls_withdrawal_candidate":0,
        "native_additional_calls_withdrawal_fair_baseline":0,
        "resolver_call_count_candidate":1+len(experiments)*2,
        "resolver_recomputation_method":"FULL_GRAPH_AFTER_EACH_WITHDRAWAL",
        "comparative_result":"TIE_ON_RETAINED_NATIVE_OBSERVATION; NO_INCREMENTAL_GRAPH_SPEEDUP",
        "R7_CLC_link":"separate unchanged Lean theorem job; NOT a formal proof of Python graph",
        "source_to_formal_permission":"UNKNOWN_NO_INDEPENDENT_QUALIFIED_RELATION",
    }
    OUT.write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:results[k] for k in ("status","native_positive",
          "native_negative","invalid_cross_type_route_denied","resolver_original_module",
          "comparative_result","source_to_formal_permission")},sort_keys=True))
if __name__=="__main__":main()
