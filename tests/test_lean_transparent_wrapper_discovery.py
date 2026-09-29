from mathgraph.lean_bridge_discovery import SourcePin
from mathgraph.lean_transparent_wrapper_discovery import (
    discover_transparent_wrapper_candidates,
    extract_transparent_wrappers,
)


def pin(corpus,path):
    return SourcePin(corpus,"consumer","x/y","0"*40,path,"0"*40)


def test_discovers_different_name_finite_range_bridge():
    source=(pin("pfr","PFR/Defs.lean"), """
class FiniteRange {Ω G : Type*} (X : Ω → G) : Prop where
  finite : (Set.range X).Finite
""")
    consumer=(pin("anthropic","Definitions/C.lean"), """
theorem consume {X V : Type*} {F : X → V}
    (h : (Set.range F).Finite) : True := by trivial
""")
    out=discover_transparent_wrapper_candidates([source,consumer],source_corpora=["pfr"])
    assert out["candidate_count"]==1
    row=out["candidates"][0]
    assert row["wrapper"]=="FiniteRange"
    assert row["consumer_declaration"]=="consume"
    assert row["fingerprint"]=="(Set.range□).Finite"


def test_one_field_requirement_rejects_multi_field_prop():
    src=pin("pfr","PFR/Defs.lean")
    wrappers=extract_transparent_wrappers(src, """
structure TwoFacts (X : Type*) : Prop where
  a : Nonempty X
  b : Subsingleton X
""")
    assert wrappers==[]


def test_semantically_unanchored_wrapper_is_not_mined():
    src=pin("pfr","PFR/Defs.lean")
    wrappers=extract_transparent_wrappers(src, """
class Bare (p : Prop) : Prop where
  out : p
""")
    assert wrappers==[]


def test_same_corpus_does_not_create_cross_corpus_candidate():
    source=(pin("pfr","PFR/Defs.lean"), """
class FiniteRange {Ω G : Type*} (X : Ω → G) : Prop where
  finite : (Set.range X).Finite
theorem local {Ω G : Type*} {X : Ω → G} (h : (Set.range X).Finite) : True := by trivial
""")
    out=discover_transparent_wrapper_candidates([source],source_corpora=["pfr"])
    assert out["candidate_count"]==0
