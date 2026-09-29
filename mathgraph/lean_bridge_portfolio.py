"""Reconcile scout candidates against independent qualification evidence."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

def reconcile_bridge_portfolio(
    scout: Mapping[str, Any],
    directional: Mapping[str, Any],
    cross_version: Mapping[str, Any],
) -> dict[str, Any]:
    if scout.get("status") != "CANDIDATE_SCOUT_ONLY":
        raise ValueError("candidate scout report required")
    if directional.get("status") != "WARRANTED_BOUNDED_REUSABLE":
        raise ValueError("warranted directional evidence required")
    if cross_version.get("status") != "WARRANTED_BOUNDED_CROSS_VERSION_INTERFACE":
        raise ValueError("warranted cross-version evidence required")

    all_ids=list(scout["all_candidate_ids"])
    qualified=set()
    rows=[]

    symbol=str(cross_version["candidate_lineage"]["canonical_symbol"])
    hits=[x for x in scout["top_equivalence_candidates"] if x["canonical_symbol"]==symbol]
    if len(hits)!=1:
        raise AssertionError(f"equivalence match count for {symbol}: {len(hits)}")
    cid=str(hits[0]["candidate_id"])
    qualified.add(cid)
    rows.append({"candidate_id":cid,"kind":"equivalence","status":"QUALIFIED_REUSABLE"})

    law=directional["bridge_law"]
    consumer=directional["qualification"]["consumer_surface"]["declaration"]
    producers={str(x["producer"]) for x in directional["promoted"]}
    matched=[]
    for x in scout["top_implication_candidates"]:
        if x["source_symbol"] != law["source_interface"]:
            continue
        if x["target_symbol"] != law["target_interface"]:
            continue
        if x["consumer"]["declaration"] != consumer:
            continue
        if str(x["producer"]["declaration"]) not in producers:
            continue
        matched.append(x)
    found={str(x["producer"]["declaration"]) for x in matched}
    if found != producers:
        raise AssertionError(f"directional mismatch missing={sorted(producers-found)}")
    for x in matched:
        cid=str(x["candidate_id"])
        qualified.add(cid)
        rows.append({
            "candidate_id":cid,
            "kind":"implication",
            "producer":x["producer"]["declaration"],
            "status":"QUALIFIED_REUSABLE",
        })

    unknown=[x for x in all_ids if x not in qualified]
    implication_ids={str(x["candidate_id"]) for x in scout["top_implication_candidates"]}
    unknown_imp=sorted(implication_ids-qualified)
    unknown_eq=sum(1 for x in unknown if x.startswith("equiv:"))
    return {
        "schema":"mathgraph.crystal-bridge-portfolio-state.v1",
        "candidate_total":len(all_ids),
        "qualified_reusable_count":len(qualified),
        "unknown_unqualified_count":len(unknown),
        "qualified_candidate_ids":sorted(qualified),
        "unknown_candidate_ids":unknown,
        "qualified":rows,
        "directional_candidate_total":len(implication_ids),
        "directional_unknown_count":len(unknown_imp),
        "directional_unknown_ids":unknown_imp,
        "equivalence_unknown_count":unknown_eq,
        "residual":"qualify equivalence candidates" if unknown_eq and not unknown_imp else "mixed residual",
        "trust_boundary":"Ledger only; qualification authority remains external.",
    }

def reconcile_files(scout_path, directional_path, cross_version_path, out_path=None):
    result=reconcile_bridge_portfolio(
        json.loads(Path(scout_path).read_text()),
        json.loads(Path(directional_path).read_text()),
        json.loads(Path(cross_version_path).read_text()),
    )
    if out_path:
        Path(out_path).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result
