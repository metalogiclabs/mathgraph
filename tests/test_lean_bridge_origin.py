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


def test_refinement_routes_namespaced_upstream_and_rejects_collisions():
    from mathgraph.lean_bridge_origin import refine_origin_classification

    base = {
        "candidates": [
            {
                "symbol":"FiniteIndex",
                "candidate_id":"equiv:FiniteIndex",
                "origin_class":"AMBIGUOUS",
                "bridge_action":"RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH",
                "local_definitions":[],
                "already_qualified_reusable":False,
            },
            {
                "symbol":"v.IsReal",
                "candidate_id":"equiv:v.IsReal",
                "origin_class":"AMBIGUOUS",
                "bridge_action":"RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH",
                "local_definitions":[],
                "already_qualified_reusable":False,
            },
            {
                "symbol":"HeckeAlgebra",
                "candidate_id":"equiv:HeckeAlgebra",
                "origin_class":"PROJECT_LOCAL_SHARED",
                "bridge_action":"QUALIFY_PROJECT_LOCAL_RECONCILIATION",
                "local_definitions":[
                    {"declaration":"HeckePair.HeckeAlgebra"},
                    {"declaration":"HeckeAlgebra"},
                ],
                "already_qualified_reusable":False,
            },
        ]
    }
    short = {
        "FiniteIndex":{"a":True,"b":True,"c":True},
        "v.IsReal":{"a":True,"b":True,"c":True},
        "HeckeAlgebra":{"a":False,"b":False,"c":False},
    }
    out = refine_origin_classification(
        base, short_declaration_presence_by_symbol=short
    )
    by = {x["symbol"]:x for x in out["candidates"]}
    assert by["FiniteIndex"]["origin_class"] == "SAME_UPSTREAM_NAMESPACE_REFERENCE"
    assert by["v.IsReal"]["origin_class"] == "SAME_UPSTREAM_DEPENDENT_REFERENCE"
    assert by["HeckeAlgebra"]["origin_class"] == "SHORT_NAME_COLLISION"
    assert out["project_bridge_residual_count"] == 0
    assert out["short_name_collision_count"] == 1
