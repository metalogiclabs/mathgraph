"""Compile origin-refined bridge candidates into an exact Crystal residual.

This module does not prove semantic equivalence. It performs only epistemic
accounting:

* already-qualified candidates remain REUSABLE;
* common-upstream references are DISCHARGED_AS_NON_BRIDGE;
* short-name collisions are REJECTED_AS_FALSE_CANDIDATE;
* only genuinely unresolved project/version cases remain UNKNOWN.

That distinction is crucial: a rejected candidate is not an unknown theorem.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


NON_BRIDGE_CLASSES = {
    "SAME_UPSTREAM",
    "SAME_UPSTREAM_NAMESPACE_REFERENCE",
    "SAME_UPSTREAM_RESOLVED_REFERENCE",
    "SAME_UPSTREAM_DEPENDENT_REFERENCE",
    "UPSTREAM_DEPENDENT_MEMBER_REFERENCE",
}

COLLISION_CLASSES = {
    "SHORT_NAME_COLLISION",
    "MIXED_LOCAL_UPSTREAM_COLLISION",
    "UPSTREAM_SHORT_NAME_COLLISION",
}

ACTIONABLE_CLASSES = {
    "PORTED_LINEAGE",
    "PROJECT_LOCAL_SHARED",
    "PROJECT_LOCAL_SINGLE",
    "UPSTREAM_VERSION_SKEW",
    "UPSTREAM_SHORTNAME_VERSION_SKEW",
    "AMBIGUOUS",
}


def compile_origin_residual(classification: Mapping[str, Any]) -> dict[str, Any]:
    rows = [dict(x) for x in classification["candidates"]]

    ledger: list[dict[str, Any]] = []
    for row in rows:
        cid = str(row["candidate_id"])
        origin = str(row["origin_class"])
        if row.get("already_qualified_reusable"):
            disposition = "REUSABLE"
        elif origin in NON_BRIDGE_CLASSES:
            disposition = "DISCHARGED_AS_NON_BRIDGE"
        elif origin in COLLISION_CLASSES:
            disposition = "REJECTED_AS_FALSE_CANDIDATE"
        elif origin in ACTIONABLE_CLASSES:
            disposition = "UNKNOWN_ACTIONABLE"
        else:
            disposition = "UNKNOWN_ACTIONABLE"

        ledger.append({
            "candidate_id": cid,
            "symbol": row["symbol"],
            "origin_class": origin,
            "disposition": disposition,
            "bridge_action": row.get("bridge_action"),
            "resolved_upstream_name": row.get("resolved_upstream_name"),
            "collision_full_names": row.get("collision_full_names", []),
        })

    counts = Counter(x["disposition"] for x in ledger)
    actionable = [x for x in ledger if x["disposition"] == "UNKNOWN_ACTIONABLE"]
    rejected = [x for x in ledger if x["disposition"] == "REJECTED_AS_FALSE_CANDIDATE"]
    discharged = [x for x in ledger if x["disposition"] == "DISCHARGED_AS_NON_BRIDGE"]
    reusable = [x for x in ledger if x["disposition"] == "REUSABLE"]

    return {
        "schema": "mathgraph.crystal-origin-compiled-residual.v1",
        "status": "EXACT_ROUTING_STATE",
        "candidate_count": len(ledger),
        "reusable_count": len(reusable),
        "discharged_non_bridge_count": len(discharged),
        "rejected_false_candidate_count": len(rejected),
        "unknown_actionable_count": len(actionable),
        "disposition_counts": dict(sorted(counts.items())),
        "unknown_actionable": actionable,
        "rejected_false_candidates": rejected,
        "discharged_non_bridges": discharged,
        "reusable": reusable,
        "invariant": (
            "candidate_count = reusable + discharged_non_bridge + "
            "rejected_false_candidate + unknown_actionable"
        ),
        "trust_boundary": (
            "Origin routing can discharge or reject bridge-search obligations, "
            "but only verifier-backed evidence may promote semantic reuse."
        ),
    }
