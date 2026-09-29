from mathgraph.lean_incremental_corpus_linker import (
    equivalence_report,
    extract_incremental_frontier,
)


def test_frontier_reopens_only_candidates_touching_new_corpus():
    report={
        "top_equivalence_candidates":[
            {"candidate_id":"equiv:A","canonical_symbol":"A","corpora":["old-a","old-b"]},
            {"candidate_id":"equiv:B","canonical_symbol":"B","corpora":["old-a","new"]},
        ],
        "top_implication_candidates":[
            {
                "candidate_id":"impl:old",
                "producer":{"corpus":"old-a"},
                "consumer":{"corpus":"old-b"},
            },
            {
                "candidate_id":"impl:new",
                "producer":{"corpus":"old-a"},
                "consumer":{"corpus":"new"},
            },
        ],
    }
    out=extract_incremental_frontier(report,new_corpus="new")
    assert out["candidate_ids"]==["equiv:B","impl:new"]
    assert out["candidate_count"]==2
    eq=equivalence_report(out)
    assert eq["top_equivalence_candidates"][0]["canonical_symbol"]=="B"


def test_empty_expansion_frontier_is_valid_closed_result():
    report={"top_equivalence_candidates":[],"top_implication_candidates":[]}
    out=extract_incremental_frontier(report,new_corpus="new")
    assert out["candidate_count"]==0
