import json
from pathlib import Path

from mathgraph.lean_bridge_discovery import SourcePin
from mathgraph.lean_corpus_bridge_scout import build_scout_report


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_corpus_wide_scout_ranks_shared_interface_and_keeps_unknown(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    c = tmp_path / "c"

    _write(a, "Theorems/A.lean", "theorem a (n : Nat) : FermatLastTheoremFor n := by trivial\n")
    _write(b, "Fermat/B.lean", """
namespace Fermat
abbrev HoldsAt (n : Nat) : Prop := FermatLastTheoremFor n
theorem b (n : Nat) (h : HoldsAt n) : HoldsAt n := h
end Fermat
""")
    _write(c, "FLT/C.lean", "def B2 : Prop := ∀ p : Nat, FermatLastTheoremFor p\n")

    bridge_pin = SourcePin("mathlib", "bridge-library", "x/y", "0"*40, "Bridge.lean", "0"*40)
    bridge = """
namespace RingTheory.Sequence
structure IsWeaklyRegular (R : Type) (xs : List R) : Prop where
  ok : True
structure IsRegular (R : Type) (xs : List R) : Prop extends IsWeaklyRegular R xs where
  more : True
end RingTheory.Sequence
"""

    manifest = {
        "top_k": 10,
        "corpora": [
            {"corpus":"a","role":"producer","repository":"a/r","commit":"1"*40,"include_prefixes":["Theorems"]},
            {"corpus":"b","role":"consumer","repository":"b/r","commit":"2"*40,"include_prefixes":["Fermat"]},
            {"corpus":"c","role":"consumer","repository":"c/r","commit":"3"*40,"include_prefixes":["FLT"]},
        ],
    }

    report = build_scout_report(
        corpus_roots={"a":a,"b":b,"c":c},
        manifest=manifest,
        bridge_texts=[(bridge_pin, bridge)],
    )
    hits = [
        x for x in report["top_equivalence_candidates"]
        if x["canonical_symbol"] == "FermatLastTheoremFor"
    ]
    assert hits
    assert set(hits[0]["corpora"]) == {"a","b","c"}
    assert hits[0]["qualification_status"] == "UNKNOWN_UNQUALIFIED"
    assert report["default_disposition"] == "UNKNOWN_UNQUALIFIED"


def test_missing_corpus_root_fails_closed(tmp_path: Path) -> None:
    manifest = {
        "corpora": [
            {"corpus":"missing","role":"producer","repository":"x/y","commit":"0"*40,"include_prefixes":["Theorems"]}
        ]
    }
    try:
        build_scout_report(corpus_roots={}, manifest=manifest, bridge_texts=[])
    except KeyError as exc:
        assert "missing local corpus root" in str(exc)
    else:
        raise AssertionError("missing corpus root must fail closed")
