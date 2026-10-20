#!/usr/bin/env python3
"""Source-free controls: ensure typed metadata selection and no invented semantic warrant."""
import ast, pathlib, json, re, sys
r=pathlib.Path(__file__).resolve().parent
for f in ("selection.py","candidate.py","baseline.py","assay.py"):
    ast.parse((r/f).read_text(),filename=str(r/f))
sys.path.insert(0,str(r))
import candidate,baseline,selection
assert selection.POOL[0]=="Verified-zkEVM/ArkLib"
assert len(selection.POOL)==len(set(selection.POOL))
assert "physical real-world equivalence" not in (r/"PROTOCOL.md").read_text()
assert not any(p in (r/"candidate.py").read_text() for p in ["Aeneas","Strata","sparkle","ArkLib"])
assert not any(p in (r/"baseline.py").read_text() for p in ["Aeneas","Strata","sparkle","ArkLib"])
# Both observers must abstain on source without declarations.
import tempfile
with tempfile.TemporaryDirectory() as temp:
    root=pathlib.Path(temp)
    (root/"Example.lean").write_text("def f : Nat := 3\n")
    assert candidate.propose(root)==[]
    assert baseline.propose(root)==[]
    (root/"Example.lean").write_text("namespace Trial\ntheorem certified_correct : 1 = 1 := by rfl\nend Trial\n")
    a=candidate.propose(root);b=baseline.propose(root)
    assert a[0]["name"]=="Trial.certified_correct" and b[0]["name"]=="Trial.certified_correct"
    assert a[0]["source_sha256"]==b[0]["source_sha256"]
print("FROZEN_V2_NATIVE_MODULE_SOURCE_BLIND_CONTROLS_PASS")
