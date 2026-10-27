#!/usr/bin/env python3
"""MathGraph Claim Assurance V1 -- independent bounded PKC SysML receipt adjudicator.

Read-only, source-identity-locked checker. It does not patch PKC, parse arbitrary
scientific English, or infer that kernel-checking a citation checks an adjacent
SysML text field. Native input production and ingest are done by the separately
pinned V4/V5 protocols, not by this checker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

SOURCE = "nasa-jpl/PropertyKindCalculus"
PIN = "e0deb453e05ffa63297d9704ceb47d0855193824"
DECL = "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"
TOOLCHAIN = "leanprover/lean4:v4.34.0"

EXPECTED_V5 = {
    ("original", "no_statement"): True,
    ("original", "false_statement"): True,
    ("strict", "no_statement"): True,
    ("strict", "false_statement"): False,
    ("withdrawn", "false_statement"): True,
}
EXPECTED_V4 = {
    ("original", "no_statement"): True,
    ("original", "false_statement"): True,
    ("original", "true_statement"): True,
    ("original", "missing_declaration"): False,
    ("original", "data_citation"): False,
    ("original", "axiom_citation"): False,
    ("strict", "no_statement"): True,
    ("strict", "false_statement"): False,
    ("strict", "true_statement"): False,
    ("strict", "missing_declaration"): False,
    ("strict", "data_citation"): False,
    ("strict", "axiom_citation"): False,
    ("withdrawn", "false_statement"): True,
}

class Unavailable(Exception):
    """Authority cannot be recovered (withdrawal, not a proof of falsehood)."""

class Corrupt(Exception):
    """Available evidence contradicts the predeclared native expectations."""

def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise Unavailable(f"MISSING_EVIDENCE:{path.name}")
    return path.read_text(encoding="utf-8")

def check(ok: bool, message: str) -> None:
    if not ok:
        raise Corrupt(message)

def digest(path: pathlib.Path) -> str:
    if not path.is_file():
        raise Unavailable(f"MISSING_EVIDENCE:{path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def table(folder: pathlib.Path, expected: dict[tuple[str, str], bool], version: str
          ) -> dict[str, str]:
    rows: dict[tuple[str, str], bool] = {}
    for line in read(folder / "native-results.tsv").splitlines():
        cols = line.split("\t")
        check(len(cols) == 3, f"{version}:BAD_TSV_ROW")
        lane, case, status = cols
        check(re.fullmatch(r"[0-9]+", status) is not None, f"{version}:BAD_EXIT")
        key = (lane, case)
        check(key not in rows, f"{version}:DUPLICATE_CASE:{key}")
        rows[key] = int(status) == 0
    check(rows == expected, f"{version}:NATIVE_VECTOR_CHANGED:{rows}")
    for (lane, case), successful in expected.items():
        log = read(folder / f"{lane}-{case}.log")
        check(bool(log.strip()), f"{version}:EMPTY_NATIVE_LOG:{lane}:{case}")
        if successful:
            check("0 unverified citation(s)" in log and "unverified citations in" not in log,
                  f"{version}:UNJUSTIFIED_ACCEPT:{lane}:{case}")
        else:
            check("unverified citations in" in log,
                  f"{version}:APPARATUS_ERROR_NOT_CITATION_REJECTION:{lane}:{case}")
            if lane == "strict" and case.endswith("_statement"):
                check("@Checked.statement is unchecked free text" in log,
                      f"{version}:WRONG_TEXT_POLICY_REASON:{lane}:{case}")
            elif case == "missing_declaration":
                check("is not a declaration" in log, f"{version}:WRONG_MISSING_REASON")
            elif case == "data_citation":
                check("not evidence" in log or "is data" in log, f"{version}:WRONG_DATA_REASON")
            elif case == "axiom_citation":
                check("is an axiom" in log or "theorem" in log, f"{version}:WRONG_AXIOM_REASON")
    return {f"{lane}/{case}": "ACCEPT" if success else "REJECT"
            for (lane, case), success in sorted(rows.items())}

def literals(folder: pathlib.Path, case: str) -> list[str]:
    try:
        arr = json.loads(read(folder / f"convert-{case}-api.json"))
    except json.JSONDecodeError as ex:
        raise Corrupt(f"INVALID_AUTHENTIC_API_JSON:{case}") from ex
    check(isinstance(arr, list), f"NOT_API_ELEMENT_ARRAY:{case}")
    check(all(isinstance(x, dict) for x in arr), f"NOT_API_ELEMENT_OBJECTS:{case}")
    return [x.get("value") for x in arr if x.get("@type") == "LiteralString"]

def assess(v4: pathlib.Path, v5: pathlib.Path, source_revision: str,
           *, require_full: bool = True) -> dict[str, Any]:
    """Return no-authority when a source or evidence dependency is missing.

    Six predeclared control classes; the bad-declaration class has three
    authentic negative subcases. Policy restoration is an extra causal check.
    The separate CLI is fail-closed if the *baseline* is withdrawn.
    """
    if source_revision != PIN:
        return {"authorization": "WITHDRAWN", "reason": "STALE_SOURCE_REVISION",
                "expected_revision": PIN, "observed_revision": source_revision}
    try:
        v5native = table(v5, EXPECTED_V5, "V5")
        v4native = table(v4, EXPECTED_V4, "V4")
        false_sysml = read(v5 / "false_statement.sysml")
        clean_sysml = read(v5 / "no_statement.sysml")
        checked_lean = read(v5 / "OriginalFalseGenerated.lean")
        v5receipt = json.loads(read(v5 / "PINNED_RESULT.json"))
        v4receipt = json.loads(read(v4 / "PINNED_RESULT.json"))
        release = read(v5 / "opensysml-version.txt")
        patch_v5 = json.loads(read(v5 / "policy-patch.json"))
        patch_v4 = json.loads(read(v4 / "strict-patch-receipt.json"))
    except Unavailable as ex:
        return {"authorization": "WITHDRAWN", "reason": str(ex)}
    except json.JSONDecodeError as ex:
        raise Corrupt("MALFORMED_ORIGINAL_RECEIPT") from ex

    check(v5receipt.get("upstream") == f"{SOURCE}@{PIN}", "V5_UPSTREAM_NOT_PINNED")
    check(v4receipt.get("source_sha") == PIN, "V4_UPSTREAM_NOT_PINNED")
    check("0.9.1" in release, "WRONG_EXTERNAL_CONVERTER")
    check(patch_v4.get("changed_files") ==
          ["interchange/PropertyKindCalculus/Interchange/Harvest.lean"],
          "UNTRUSTED_PATCH_SCOPE")
    check(patch_v5.get("old_sha256") ==
          "28bb3c84b7cf86813e60967eb88d680e274f9a8f5d59d8e4432f411dfe75263c",
          "CHANGED_JPL_HARVEST_SOURCE")
    check(patch_v5.get("new_sha256") ==
          "ff1e12beb4dccd58cc1a9ba3da022cb8f018c229b11e9705c45544974e25cf98",
          "CHANGED_STRICT_POLICY")

    clean_literals = literals(v5, "no_statement")
    false_literals = literals(v5, "false_statement")
    check(DECL in clean_literals and DECL in false_literals,
          "CITATION_NOT_IN_AUTHENTIC_CONVERTER_OUTPUT")
    check("False" in false_literals and "False" not in clean_literals,
          "TEXT_IDENTITY_NOT_PRESERVED")
    check('statement = "False"' in false_sysml, "FALSE_TEXT_NOT_IN_REAL_SYSML")
    check('statement = "False"' not in clean_sysml, "GOOD_SOURCE_CONTAMINATED")
    check(f"-- checked: {DECL} — False" in checked_lean,
          "UNCHECKED_TEXT_NOT_VISIBLE_AS_LEAN_COMMENT")
    check("example : False" not in checked_lean and "theorem False" not in checked_lean,
          "CLAIM_WRONGFULLY_DESCRIBED_AS_PROOF")
    read(v5 / "original-Lean-kernel.log")
    check(v5native["original/false_statement"] == "ACCEPT" and
          v5native["strict/false_statement"] == "REJECT" and
          v5native["withdrawn/false_statement"] == "ACCEPT",
          "CAUSAL_WITHDRAWAL_MISSING")

    # Each outcome states the authority of a scoped claim, NOT generic YAML,
    # SysML semantics or the truth of a physical observation.
    controls = [
        {"id": "C1", "name": "valid_declaration_without_statement",
         "verdict": "WARRANTED_CITATION_ONLY",
         "reason": "native proof citation admitted; no arbitrary text proposition authorized"},
        {"id": "C2", "name": "False_text_on_unrelated_valid_proof",
         "verdict": "REJECTED_UNCHECKED_STATEMENT",
         "reason": "real SysML and API JSON retain False, original Lean only comments it"},
        {"id": "C3", "name": "missing_data_axiom_citations",
         "verdict": "REJECTED_INVALID_EVIDENCE",
         "subcases": ["missing_declaration", "data_citation", "axiom_citation"],
         "reason": "native PKC importer rejects absent, computational and axiom citations"},
        {"id": "C4", "name": "alternate_True_text",
         "verdict": "REJECTED_UNCHECKED_STATEMENT",
         "reason": "plausible text is not promoted merely because the cited theorem is valid"},
        {"id": "C5", "name": "stale_revision",
         "verdict": "WITHDRAWN",
         "reason": "pin mismatch prevents inherited authority"},
        {"id": "C6", "name": "evidence_withdrawal",
         "verdict": "WITHDRAWN",
         "reason": "missing source-linked receipt prevents promotion"},
    ]
    # Preserve meaningful provenance. These bytes are real outputs, not model guesses.
    files = [
        (v5, "false_statement.sysml"), (v5, "no_statement.sysml"),
        (v5, "convert-false_statement-api.json"),
        (v5, "convert-no_statement-api.json"), (v5, "OriginalFalseGenerated.lean"),
        (v5, "native-results.tsv"), (v5, "PINNED_RESULT.json"),
        (v5, "policy-patch.json"), (v4, "native-results.tsv"),
        (v4, "PINNED_RESULT.json"), (v4, "strict-patch-receipt.json"),
    ]
    artifacts = {f"{'V5' if folder == v5 else 'V4'}/{filename}":
                 digest(folder / filename) for folder, filename in files}
    result = {
        "protocol": "MATHGRAPH_CLAIM_ASSURANCE_V1_PKC_SYSML",
        "authority": "WARRANTED_BOUNDED_SELECTED_CITATION",
        "upstream": f"{SOURCE}@{PIN}",
        "toolchain": TOOLCHAIN,
        "external_converter": release.strip(),
        "identity": {"declaration": DECL,
                     "unverified_free_text": "False",
                     "verified_proposition_is_False": False,
                     "claim_text_semantics": "UNDETERMINED_BY_CURRENT_SYSML_CONTRACT"},
        "primary_controls": controls,
        "causal_ablation": {
            "original_false_citation": "ACCEPT",
            "strict_false_citation": "REJECT",
            "withdrawn_policy_false_citation": "ACCEPT",
            "independent_claim_authority_after_policy_withdrawal": "REJECTED_UNCHECKED_STATEMENT",
        },
        "actual_native_v4": v4native,
        "actual_native_v5": v5native,
        "observed_bytes_sha256": artifacts,
        "limitations": [
            "Original JPL importer accepts citation; it does not prove the optional statement.",
            "Statement field authoritative-versus-commentary contract awaits JPL decision.",
            "No general natural-language claim alignment or whole-PKC correctness established.",
            "No NASA/JPL source changed upstream, no endorsement or publication authorization.",
            "All verdicts conditional on pinned source and complete independent receipts.",
        ],
    }
    if require_full:
        check(len(result["primary_controls"]) == 6, "SIX_CONTROL_CENSUS_LOST")
        check(len(v4native) == 13 and len(v5native) == 5,
              "NATIVE_CONTROL_CENSUS_CHANGED")
    return result

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4", type=pathlib.Path, required=True)
    ap.add_argument("--v5", type=pathlib.Path, required=True)
    ap.add_argument("--source-checkout", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    a = ap.parse_args()
    # Git HEAD is measured, never derived from a document label.
    actual = subprocess.check_output(
        ["git", "-C", str(a.source_checkout), "rev-parse", "HEAD"], text=True).strip()
    out = assess(a.v4, a.v5, actual)
    check(out.get("authority") == "WARRANTED_BOUNDED_SELECTED_CITATION",
          "BASELINE_WITHDRAWN:" + str(out))
    check(read(a.source_checkout / "lean-toolchain").strip() == TOOLCHAIN,
          "SOURCE_TOOLCHAIN_DRIFT")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("MATHGRAPH_CLAIM_ASSURANCE_V1_WARRANTED_BOUNDED",
          json.dumps({"primary_controls": len(out["primary_controls"]),
                      "v4_native_replays": len(out["actual_native_v4"]),
                      "v5_fulltext_replays": len(out["actual_native_v5"]),
                      "source": out["upstream"]}))

if __name__ == "__main__":
    main()
