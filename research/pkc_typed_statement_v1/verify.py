#!/usr/bin/env python3
"""Fail-closed qualification of an original-source PKC typed statement-to-type test."""
import hashlib
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
cases = {
    "typed_match": ("MATCH", "PKC:Edge(width,length)", "width_length"),
    "false_mismatch": ("MISMATCH", "False", "width_length"),
    "typed_mismatch": ("MISMATCH", "PKC:Edge(width,height)", "width_length"),
    "wrong_citation": ("MISMATCH", "PKC:Edge(width,length)", "height_length"),
    "unsupported": ("UNKNOWN_UNSUPPORTED", "The width is a length", "width_length"),
    "true_unsupported": ("UNKNOWN_UNSUPPORTED", "True", "width_length"),
    "no_statement": ("NO_ASSERTION", None, "width_length"),
}
status = {}
for line in (root / "native-status.tsv").read_text().splitlines():
    case, code = line.split("\t")
    assert case in cases and case not in status, f"invalid native status {case}"
    status[case] = int(code)
assert set(status) == set(cases), f"lost native cases: {status}"
assert all(v == 0 for v in status.values()), f"not universally accepted: {status}"

lean_text = (root / "independent-typed.log").read_text()
results = {}
pattern = re.compile(r"^PKC_V6_TYPED_RESULT case=(\w+) status=(\w+) decl=([^ ]+) statement=(.*)$")
for line in lean_text.splitlines():
    match = pattern.fullmatch(line)
    if not match:
        continue
    case, result, decl, representation = match.groups()
    assert case in cases and case not in results
    expected, statement, suffix = cases[case]
    assert result == expected, (case, result, expected)
    assert decl == f"PropertyKindCalculus.Iso80000.Part3.Edge.{suffix}"
    assert (statement is None) == (representation == "none")
    results[case] = result

assert results == {k: v[0] for k, v in cases.items()}, results
assert "PKC_V6_PINNED_TYPED_CORRESPONDENCE_MATRIX_PASS count=7" in lean_text
digests = {}
for case, (_, statement, suffix) in cases.items():
    contents = (root / f"{case}.sysml").read_text()
    generated = (root / f"{case}.Generated.lean").read_text()
    parsed = json.loads((root / f"{case}.api.json").read_text())
    assert isinstance(parsed, list)
    literals = [x.get("value") for x in parsed if x.get("@type") == "LiteralString"]
    assert f"PropertyKindCalculus.Iso80000.Part3.Edge.{suffix}" in literals
    if statement is not None:
        assert statement in literals
        assert contents.count(f'statement = "{statement}"') == 1
        assert f"-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.{suffix} — {statement}" in generated
    else:
        assert 'statement = ' not in contents
    assert not re.search(r"^\s*(?:theorem|example)\s*:\s*False\b", generated, re.M)
    digest = lambda b: hashlib.sha256(b).hexdigest()
    digests[case] = {
        "sysml": digest((root / f"{case}.sysml").read_bytes()),
        "api_json": digest((root / f"{case}.api.json").read_bytes()),
        "lean": digest((root / f"{case}.Generated.lean").read_bytes()),
        "kernel_log": digest((root / f"{case}.kernel.log").read_bytes()),
    }

receipt = {
    "status": "WARRANTED_BOUNDED_POSITIVE_NONEMPTY_TYPED_PKCSOURCE_STATEMENT_CORRESPONDENCE",
    "upstream": "nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824",
    "original_v5_harness": "metalogiclabs/mathgraph@4691ae2de91958d5a366f636b4a329a938b76116",
    "scope": "Source-authored tiny grammar PKC:Edge(K1,K2) where K in {width,length,height}, plus literal False; exact original Lean declaration types under pinned source; no arbitrary prose parsing.",
    "checked_cases": results,
    "original_importer_accepted": status,
    "source_native_sysml_to_api_to_kernel": True,
    "independent_comparison": "Lean.Meta.isDefEq of typed interpreted statement against kernel declaration's ci.type",
    "input_and_output_sha256": digests,
    "source_modified": False,
    "authoritative_semantics_of_JPL_optional_statement": "UNKNOWN",
    "unknowns": [
        "No general equivalence for natural-language or arbitrary Lean proposition strings",
        "JPL importer still accepts unsupported and mismatched nonempty statement strings",
        "This independent checker is not upstream and is not a declaration of JPL intent",
        "No automatic interpretation acquisition or third-source transfer"
    ],
}
out = root / "receipt.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print("PKC_V6_7_CASE_NATIVE_TYPE_CORRESPONDENCE_PASS")
print(json.dumps(results, sort_keys=True))
