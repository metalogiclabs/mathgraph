#!/usr/bin/env python3
"""Input-only, frozen derivation of new SysML statement cases from V5 source fixture."""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
base_dir = pathlib.Path(sys.argv[2])
base = (base_dir / "false_statement.sysml").read_text()
blank = (base_dir / "no_statement.sysml").read_text()
source_decl = "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"
wrong_decl = "PropertyKindCalculus.Iso80000.Part3.Edge.height_length"
assert base.count('statement = "False"') == 1
assert base.count(source_decl) == 1
assert 'statement = ' not in blank
assert blank.count(source_decl) == 1

values = {
    "typed_match": "PKC:Edge(width,length)",
    "false_mismatch": "False",
    "typed_mismatch": "PKC:Edge(width,height)",
    "wrong_citation": "PKC:Edge(width,length)",
    "unsupported": "The width is a length",
    "true_unsupported": "True",
}
root.mkdir(parents=True, exist_ok=True)
for label, value in values.items():
    modified = base.replace('statement = "False"', f'statement = "{value}"')
    if label == "wrong_citation":
        modified = modified.replace(source_decl, wrong_decl)
    assert modified.count(f'statement = "{value}"') == 1
    assert modified.count(wrong_decl if label == "wrong_citation" else source_decl) == 1
    (root / (label + ".sysml")).write_text(modified)
    print(f"PKC_V6_FROZEN_INPUT case={label} sha256={hashlib.sha256(modified.encode()).hexdigest()}")
(root / "no_statement.sysml").write_text(blank)
print(f"PKC_V6_FROZEN_INPUT case=no_statement sha256={hashlib.sha256(blank.encode()).hexdigest()}")
