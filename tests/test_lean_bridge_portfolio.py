from mathgraph.lean_bridge_portfolio import reconcile_bridge_portfolio

def fixtures():
    scout={
        "status":"CANDIDATE_SCOUT_ONLY",
        "all_candidate_ids":["equiv:FermatLastTheoremFor","equiv:Other",
            "impl:1","impl:2"],
        "top_equivalence_candidates":[
            {"canonical_symbol":"FermatLastTheoremFor","candidate_id":"equiv:FermatLastTheoremFor"}
        ],
        "top_implication_candidates":[
            {"candidate_id":"impl:1","source_symbol":"Regular","target_symbol":"Weak",
             "producer":{"declaration":"p1"},"consumer":{"declaration":"c"}},
            {"candidate_id":"impl:2","source_symbol":"Regular","target_symbol":"Weak",
             "producer":{"declaration":"p2"},"consumer":{"declaration":"c"}},
        ],
    }
    directional={
        "status":"WARRANTED_BOUNDED_REUSABLE",
        "bridge_law":{"source_interface":"Regular","target_interface":"Weak"},
        "qualification":{"consumer_surface":{"declaration":"c"}},
        "promoted":[{"producer":"p1"},{"producer":"p2"}],
    }
    cross={
        "status":"WARRANTED_BOUNDED_CROSS_VERSION_INTERFACE",
        "candidate_lineage":{"canonical_symbol":"FermatLastTheoremFor"},
    }
    return scout,directional,cross

def test_exact_residual():
    out=reconcile_bridge_portfolio(*fixtures())
    assert out["candidate_total"]==4
    assert out["qualified_reusable_count"]==3
    assert out["unknown_unqualified_count"]==1
    assert out["directional_unknown_count"]==0
    assert out["equivalence_unknown_count"]==1
    assert out["residual"]=="qualify equivalence candidates"

def test_missing_promoted_candidate_fails():
    scout,directional,cross=fixtures()
    directional["promoted"].append({"producer":"missing"})
    try:
        reconcile_bridge_portfolio(scout,directional,cross)
    except AssertionError:
        pass
    else:
        raise AssertionError("missing qualification must fail closed")


def test_one_authority_can_close_multiple_qualified_equivalence_interfaces():
    scout,directional,cross=fixtures()
    scout["all_candidate_ids"].append("equiv:FermatLastTheorem")
    cross["candidate_lineage"]["qualified_symbols"]=[
        "FermatLastTheoremFor",
        "FermatLastTheorem",
    ]
    out=reconcile_bridge_portfolio(scout,directional,cross)
    assert out["qualified_reusable_count"]==4
    assert "equiv:FermatLastTheorem" in out["qualified_candidate_ids"]
