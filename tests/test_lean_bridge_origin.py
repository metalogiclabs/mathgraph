from mathgraph.lean_bridge_origin import (
    LocalDefinitionEvidence,
    classify_origin,
    classify_report,
)


def test_same_upstream_routes_away_from_bridge_proving():
    out = classify_origin(
        "LinearIndependent",
        corpus_uses=["a","b","c"],
        upstream_presence={"old":True,"mid":True,"new":True},
        local_definitions=[],
    )
    assert out["origin_class"] == "SAME_UPSTREAM"
    assert out["bridge_action"] == "NO_PROJECT_BRIDGE_NEEDED"


def test_ported_project_local_definition_is_not_called_independent():
    defs = [
        LocalDefinitionEvidence("a","A.lean","FreyPackage","structure",True),
        LocalDefinitionEvidence("b","B.lean","FreyPackage","structure",False),
    ]
    out = classify_origin(
        "FreyPackage",
        corpus_uses=["a","b"],
        upstream_presence={"old":False,"new":False},
        local_definitions=defs,
    )
    assert out["origin_class"] == "PORTED_LINEAGE"
    assert "INDEPENDENT" in out["bridge_action"]


def test_report_separates_upstream_noise_from_real_bridge_residual():
    report = {
        "top_equivalence_candidates":[
            {"canonical_symbol":"LinearIndependent","corpora":["a","b"],"rank":1},
            {"canonical_symbol":"FreyPackage","corpora":["a","b"],"rank":2},
            {"canonical_symbol":"Mystery","corpora":["a","b"],"rank":3},
        ]
    }
    defs = {
        "FreyPackage":[
            LocalDefinitionEvidence("a","A.lean","FreyPackage","structure",True),
            LocalDefinitionEvidence("b","B.lean","FreyPackage","structure",False),
        ]
    }
    upstream = {
        "LinearIndependent":{"old":True,"new":True},
        "FreyPackage":{"old":False,"new":False},
        "Mystery":{"old":False,"new":False},
    }
    out = classify_report(
        report,
        upstream_presence_by_symbol=upstream,
        local_definition_evidence=defs,
        qualified_candidate_ids=["equiv:FreyPackage"],
    )
    assert out["same_upstream_non_bridge_count"] == 1
    assert out["genuine_bridge_residual_count"] == 1
    assert out["genuine_bridge_residual"][0]["symbol"] == "Mystery"
