from mathgraph.lean_bridge_discovery import SourcePin, discover


def _pin(corpus: str, role: str, path: str) -> SourcePin:
    return SourcePin(corpus, role, "example/repo", "0"*40, path, "0"*40)


def test_alias_normalization_finds_cross_corpus_head() -> None:
    a = (_pin("a", "producer", "A.lean"), """
theorem source (n : Nat) : FermatLastTheoremFor n := by trivial
""")
    b = (_pin("b", "consumer", "B.lean"), """
namespace Fermat
abbrev HoldsAt (n : Nat) : Prop := FermatLastTheoremFor n
theorem target (n : Nat) (h : HoldsAt n) : HoldsAt n := h
end Fermat
""")
    out = discover([a, b])
    hits = [
        x for x in out["equivalence_candidates"]
        if x["canonical_symbol"] == "FermatLastTheoremFor"
    ]
    assert hits
    assert hits[0]["corpora"] == ["a", "b"]


def test_structure_extension_proposes_implication_route() -> None:
    producer = (_pin("a", "producer", "A.lean"), """
theorem source {R : Type} (xs : List R) : RingTheory.Sequence.IsRegular R xs := by trivial
""")
    consumer = (_pin("b", "consumer", "B.lean"), """
def need {R : Type} (xs : List R) : Prop := Sequence.IsWeaklyRegular R xs
""")
    bridge = (_pin("mathlib", "bridge-library", "Bridge.lean"), """
namespace RingTheory.Sequence
structure IsWeaklyRegular (rs : List R) : Prop where
  x : True
structure IsRegular (rs : List R) : Prop extends IsWeaklyRegular R rs where
  y : True
end RingTheory.Sequence
""")
    out = discover([producer, consumer, bridge])
    hits = [
        x for x in out["implication_candidates"]
        if x["source_symbol"] == "IsRegular"
        and x["target_symbol"] == "IsWeaklyRegular"
    ]
    assert hits
    assert hits[0]["producer"]["corpus"] == "a"
    assert hits[0]["consumer"]["corpus"] == "b"


def test_unrelated_symbols_do_not_form_cross_corpus_candidate() -> None:
    a = (_pin("a", "producer", "A.lean"), "theorem x : StrongThing := by trivial\n")
    b = (_pin("b", "consumer", "B.lean"), "theorem y : DifferentThing := by trivial\n")
    out = discover([a, b])
    assert not out["equivalence_candidates"]
