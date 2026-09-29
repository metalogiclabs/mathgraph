from mathgraph.lean_bridge_residual import compile_origin_residual


def test_origin_compiler_distinguishes_unknown_from_false_candidate():
    classification={
        "candidates":[
            {
                "candidate_id":"equiv:A",
                "symbol":"A",
                "origin_class":"SAME_UPSTREAM_RESOLVED_REFERENCE",
                "already_qualified_reusable":False,
                "bridge_action":"NO_PROJECT_BRIDGE_NEEDED",
                "resolved_upstream_name":"N.A",
            },
            {
                "candidate_id":"equiv:B",
                "symbol":"B",
                "origin_class":"SHORT_NAME_COLLISION",
                "already_qualified_reusable":False,
                "bridge_action":"REJECT_SHORT_NAME_EQUIVALENCE_REDISCOVER_FULL_NAMES",
                "collision_full_names":["X.B","Y.B"],
            },
            {
                "candidate_id":"equiv:C",
                "symbol":"C",
                "origin_class":"PROJECT_LOCAL_SHARED",
                "already_qualified_reusable":False,
                "bridge_action":"QUALIFY_PROJECT_LOCAL_RECONCILIATION",
            },
            {
                "candidate_id":"equiv:D",
                "symbol":"D",
                "origin_class":"PORTED_LINEAGE",
                "already_qualified_reusable":True,
                "bridge_action":"QUALIFY_PRESERVATION_NOT_INDEPENDENT_EQUIVALENCE",
            },
        ]
    }
    out=compile_origin_residual(classification)
    assert out["candidate_count"]==4
    assert out["reusable_count"]==1
    assert out["discharged_non_bridge_count"]==1
    assert out["rejected_false_candidate_count"]==1
    assert out["unknown_actionable_count"]==1
    assert out["unknown_actionable"][0]["symbol"]=="C"


def test_accounting_partition_is_exact():
    classification={"candidates":[]}
    out=compile_origin_residual(classification)
    assert sum(out["disposition_counts"].values())==out["candidate_count"]
