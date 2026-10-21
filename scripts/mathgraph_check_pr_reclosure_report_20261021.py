"""Produce advisory before/after evidence authority deltas for one declared PR.
This fixture is illustrative. Caller-admitted receipts are not authenticated here.
"""
import json
from pathlib import Path
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph, compare_snapshots

SCOPE = "metalogiclabs/mathgraph@dc2637e697d1451c6936fce0c8f2c4c4f067b80f"
OTHER = "independent/source@stable-001"
CLAIMS = [
    Claim("ci_unit", "formal", SCOPE),
    Claim("integration", "formal", SCOPE),
    Claim("proposed_merge", "formal", SCOPE),
    Claim("unrelated", "formal", OTHER),
]
RECEIPTS = [
    Receipt("unit_ci", "formal", SCOPE),
    Receipt("integration_ci", "formal", SCOPE),
    Receipt("alternative_native_ci", "formal", SCOPE),
    Receipt("human_scope_approval", "formal", SCOPE),
    Receipt("unrelated_receipt", "formal", OTHER),
]
ROUTES = [
    Route("ci_unit", ("unit_ci",)),
    Route("integration", ("integration_ci",), ("ci_unit",)),
    Route("integration", ("alternative_native_ci",)),
    Route("proposed_merge", ("human_scope_approval",), ("integration",)),
    Route("unrelated", ("unrelated_receipt",)),
]


def resolve(withdrawn=frozenset()):
    return resolve_graph(CLAIMS, ROUTES, RECEIPTS, withdrawn=withdrawn)


def main():
    before = resolve()
    events = [
        {"label": "unit_receipt_lost_but_alternate_survives",
         "withdrawn": ["unit_ci"],
         "expected_unknown": ["ci_unit"]},
        {"label": "both_native_supports_lost",
         "withdrawn": ["unit_ci", "alternative_native_ci"],
         "expected_unknown": ["ci_unit", "integration", "proposed_merge"]},
        {"label": "policy_authority_lost",
         "withdrawn": ["human_scope_approval"],
         "expected_unknown": ["proposed_merge"]},
        {"label": "all_receipts_restored",
         "withdrawn": [],
         "expected_unknown": []},
    ]
    records = []
    for event in events:
        after = resolve(frozenset(event["withdrawn"]))
        actual = sorted(k for k,v in after.states.items() if v == "UNKNOWN")
        if actual != sorted(event["expected_unknown"]):
            raise AssertionError((event["label"], actual))
        if after.states["unrelated"] != "WARRANTED_BOUNDED":
            raise AssertionError("UNRELATED_CLAIM_CHANGED")
        delta = compare_snapshots(before.states, after.states)
        records.append({
            "event":event["label"],
            "withdrawn_receipts":event["withdrawn"],
            "states":dict(after.states),
            "delta":delta,
            "reviewer_action":"DEFER_OR_REQUEST_EXACT_EVIDENCE" if
               after.states["proposed_merge"]=="UNKNOWN" else
               "NO_AUTHORIZATION_CONCLUSION",
        })
    report = {
        "schema":"mathgraph.pr-warrant-delta.fixture.v1",
        "authority":"ADVISORY_ILLUSTRATIVE_EXTERNALLY_ADMITTED_RECEIPTS",
        "source_scope":SCOPE,
        "limitations":[
            "not a real PR source-native defect finding",
            "receipt identity and CI status not independently authenticated",
            "WARRANTED_BOUNDED is conditional on accepted evidence",
            "green ordinary CI does not prove semantic coverage",
            "not a merge permission, risk score or customer-value claim",
        ],
        "events":records,
    }
    path = Path("mathgraph-pr-reclosure-report.json")
    path.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(f"Verified {len(records)} authority transitions; wrote {path}")


if __name__=="__main__":
    main()
