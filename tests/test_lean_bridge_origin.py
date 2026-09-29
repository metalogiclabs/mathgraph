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
    assert by["v.IsReal"]["origin_class"] == "UPSTREAM_DEPENDENT_MEMBER_REFERENCE"
    assert by["HeckeAlgebra"]["origin_class"] == "SHORT_NAME_COLLISION"
    assert out["project_bridge_residual_count"] == 0
    assert out["short_name_collision_count"] == 1


def test_multiple_upstream_short_definitions_reject_name_only_equivalence():
    from mathgraph.lean_bridge_origin import refine_origin_classification

    base = {
        "candidates":[{
            "symbol":"LiesOver",
            "candidate_id":"equiv:LiesOver",
            "origin_class":"AMBIGUOUS",
            "bridge_action":"RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH",
            "local_definitions":[],
            "already_qualified_reusable":False,
        }]
    }
    presence={"LiesOver":{"a":True,"b":True,"c":True}}
    counts={"LiesOver":{"a":3,"b":3,"c":3}}
    out=refine_origin_classification(
        base,
        short_declaration_presence_by_symbol=presence,
        short_declaration_count_by_symbol=counts,
    )
    row=out["candidates"][0]
    assert row["origin_class"]=="UPSTREAM_SHORT_NAME_COLLISION"
    assert out["short_name_collision_count"]==1
    assert out["project_bridge_residual_count"]==0


def test_unique_common_upstream_full_name_closes_namespace_residual():
    from mathgraph.lean_bridge_origin import refine_origin_classification

    base={
        "candidates":[{
            "symbol":"FiniteIndex",
            "candidate_id":"equiv:FiniteIndex",
            "origin_class":"AMBIGUOUS",
            "bridge_action":"RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH",
            "local_definitions":[],
            "already_qualified_reusable":False,
        }]
    }
    presence={"FiniteIndex":{"a":True,"b":True,"c":True}}
    counts={"FiniteIndex":{"a":2,"b":2,"c":2}}
    names={"FiniteIndex":{
        "a":["AddSubgroup.FiniteIndex","Subgroup.FiniteIndex"],
        "b":["AddSubgroup.FiniteIndex","Subgroup.FiniteIndex"],
        "c":["AddSubgroup.FiniteIndex","Subgroup.FiniteIndex"],
    }}
    out=refine_origin_classification(
        base,
        short_declaration_presence_by_symbol=presence,
        short_declaration_count_by_symbol=counts,
        short_declaration_names_by_symbol=names,
    )
    row=out["candidates"][0]
    assert row["origin_class"]=="UPSTREAM_SHORT_NAME_COLLISION"
    assert out["project_bridge_residual_count"]==0


def test_single_exact_upstream_referent_is_not_a_bridge():
    from mathgraph.lean_bridge_origin import refine_origin_classification

    base={
        "candidates":[{
            "symbol":"AdeleRing",
            "candidate_id":"equiv:AdeleRing",
            "origin_class":"AMBIGUOUS",
            "bridge_action":"RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH",
            "local_definitions":[],
            "already_qualified_reusable":False,
        }]
    }
    presence={"AdeleRing":{"a":False,"b":False,"c":False}}
    short={"AdeleRing":{"a":True,"b":True,"c":True}}
    counts={"AdeleRing":{"a":1,"b":1,"c":1}}
    names={"AdeleRing":{
        "a":["NumberField.AdeleRing"],
        "b":["NumberField.AdeleRing"],
        "c":["NumberField.AdeleRing"],
    }}
    # Exact-name presence is false because the scout emitted a short reference;
    # the source environment nevertheless has one identical fully-qualified referent.
    base["candidates"][0]["origin_class"]="AMBIGUOUS"
    out=refine_origin_classification(
        base,
        short_declaration_presence_by_symbol=short,
        short_declaration_count_by_symbol=counts,
        short_declaration_names_by_symbol=names,
    )
    row=out["candidates"][0]
    assert row["origin_class"]=="SAME_UPSTREAM_RESOLVED_REFERENCE"
    assert row["resolved_upstream_name"]=="NumberField.AdeleRing"
    assert out["no_project_bridge_needed_count"]==1


def test_origin_scope_ignores_nonparticipant_mathlib_environment():
    report={
        "top_equivalence_candidates":[{
            "canonical_symbol":"SharedThing",
            "corpora":["a","c"],
            "rank":1,
        }]
    }
    upstream={
        "SharedThing":{
            "env-a":True,
            "env-b":False,
            "env-c":True,
        }
    }
    out=classify_report(
        report,
        upstream_presence_by_symbol=upstream,
        local_definition_evidence={},
        environment_by_corpus={"a":"env-a","b":"env-b","c":"env-c"},
    )
    row=out["candidates"][0]
    assert row["origin_class"]=="SAME_UPSTREAM"
    assert row["upstream_environments"]==["env-a","env-c"]
