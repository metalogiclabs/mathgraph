from mathgraph.lean_bridge_discovery import SourcePin, discover, extract_declarations


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
theorem need {R : Type} (xs : List R)
    (h : Sequence.IsWeaklyRegular R xs) : True := by trivial
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
        if x["source_symbol"] == "RingTheory.Sequence.IsRegular"
        and x["target_symbol"] == "RingTheory.Sequence.IsWeaklyRegular"
    ]
    assert hits
    assert hits[0]["producer"]["corpus"] == "a"
    assert hits[0]["consumer"]["corpus"] == "b"


def test_unrelated_symbols_do_not_form_cross_corpus_candidate() -> None:
    a = (_pin("a", "producer", "A.lean"), "theorem x : StrongThing := by trivial\n")
    b = (_pin("b", "consumer", "B.lean"), "theorem y : DifferentThing := by trivial\n")
    out = discover([a, b])
    assert not out["equivalence_candidates"]


def test_ambient_typeclasses_do_not_dominate_consequence_matching() -> None:
    a = (_pin("a", "producer", "A.lean"), """
theorem a {R : Type} [AddCommGroup R] (n : Nat) :
    FermatLastTheoremFor n := by trivial
""")
    b = (_pin("b", "consumer", "B.lean"), """
theorem b {R : Type} [AddCommGroup R] (n : Nat) :
    FermatLastTheoremFor n := by trivial
""")
    out = discover([a, b])
    symbols = {x["canonical_symbol"] for x in out["equivalence_candidates"]}
    assert "FermatLastTheoremFor" in symbols
    assert "AddCommGroup" not in symbols


def test_namespace_collision_does_not_create_false_implication() -> None:
    producer = (_pin("a", "producer", "A.lean"), """
theorem source {R : Type} (x : R) : Foo.IsRegular x := by trivial
""")
    consumer = (_pin("b", "consumer", "B.lean"), """
theorem need {R : Type} (xs : List R)
    (h : Sequence.IsWeaklyRegular R xs) : True := by trivial
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
    assert not out["implication_candidates"]


def test_named_section_end_does_not_erase_enclosing_namespace() -> None:
    pin = _pin("a", "producer", "A.lean")
    out = extract_declarations(pin, """
namespace Outer
section Inner
theorem inside : StrongThing := by trivial
end Inner
theorem after : StrongThing := by trivial
end Outer
""")
    names=[x.full_name for x in out]
    assert names==["Outer.inside","Outer.after"]
