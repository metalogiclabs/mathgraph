#!/usr/bin/env python3
"""Independent, fail-closed claim/evidence audit on one immutable L4YAML revision.

This audit identifies a *documented scope mismatch*, not a Lean kernel error
or a newly discovered false theorem. It never reinterprets a passing build
as evidence of complete YAML 1.2.2 acceptance equivalence.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

PIN = "bca37392fdcb80481342a186a37ab37a5ede6e46"
CLAIM = "YAML 1.2.2 acceptance/conformance is established by mathematical proof"
SEPARATOR = "current README documents that the converse remains unproved"

def classify(headline, residual, local_proof):
    """Only an explicit contradiction in documented warrant yields a finding."""
    if headline and residual:
        return "NOT_ESTABLISHED_BY_DOCUMENTED_PROOF"
    if headline and not residual:
        return "UNKNOWN_REQUIRE_FURTHER_AUTHORITY"
    if local_proof:
        return "BOUNDED_PROOF_NOT_REFUTED"
    return "NO_CLAIM"

def check_source(root):
    actual = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != PIN:
        raise RuntimeError(f"FAIL_CLOSED_SOURCE_REVISION: expected={PIN}, got={actual}")
    return actual

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("jpl-claim-audit.json"))
    args = ap.parse_args()
    root = args.upstream
    sha = check_source(root)
    files = {
        "README.md": root / "README.md",
        "L4YAML/Proofs/Serialization/README.md":
            root / "L4YAML/Proofs/Serialization/README.md",
        "L4YAML/Proofs/Serialization/ExecutableBoundary.lean":
            root / "L4YAML/Proofs/Serialization/ExecutableBoundary.lean",
    }
    text = {k: v.read_text(encoding="utf-8") for k, v in files.items()}
    readme = text["README.md"]
    package = text["L4YAML/Proofs/Serialization/README.md"]
    lean = text["L4YAML/Proofs/Serialization/ExecutableBoundary.lean"]

    headline = bool(re.search(
        r"Conformance to the \\[YAML 1\\.2\\.2 specification\\]"
        r"[\\s\\S]{0,260}?established\\s+by mathematical proof", readme
    ))
    residual = all([
        "**Work in progress.** One converse theorem remains open" in readme,
        "-- NOT the target: this statement is false." in readme,
        "the converse is false as stated" in readme,
        "The complete independent input-to-event-trace correspondence" in package,
        "theorem are not proved here" in package,
    ])
    bounded = all([
        "lemma parse_iff_executable_language (input : String)" in lean,
        "the executable factorization" in package.lower(),
    ])
    if not headline or not residual or not bounded:
        raise RuntimeError("FAIL_CLOSED_MISSING_PINNED_CLAIM_OR_WARRANT")
    verdict = classify(headline, residual, bounded)
    assert verdict == "NOT_ESTABLISHED_BY_DOCUMENTED_PROOF"

    tests = {
        "positive_documented_headline_mismatch":
            verdict == "NOT_ESTABLISHED_BY_DOCUMENTED_PROOF",
        "negative_no_headline":
            classify(False, residual, False) == "NO_CLAIM",
        "negative_no_residual_no_false_accusation":
            classify(True, False, False) == "UNKNOWN_REQUIRE_FURTHER_AUTHORITY",
        "positive_bounded_local_theorem_preserved":
            classify(False, False, True) == "BOUNDED_PROOF_NOT_REFUTED",
        "negative_unproven_global_claim_not_promoted":
            verdict != "REFUTED_THEOREM",
    }
    if not all(tests.values()):
        raise RuntimeError("FAIL_CLOSED_AUDIT_CONTROL")

    receipt = {
        "protocol": "JPL_REFUTE_FIRST_CLAIM_SCOPE_V1",
        "upstream": "nasa-jpl/L4YAML",
        "upstream_sha": sha,
        "claim": CLAIM,
        "finding": verdict,
        "scope": "README marketing/header claim vs documented current theorem coverage",
        "not_claimed": [
            "The current Lean kernel accepted a false theorem",
            "The YAML acceptance biconditional was freshly refuted by this audit",
            "Universal YAML specification compliance is disproved by a new witness",
            "This automated check establishes the authors' scientific intent",
        ],
        "warrant": [
            "README begins with unqualified proof-based conformance statement",
            "README later explicitly marks grammar converse false/unproved",
            "Serialization package README says independent input-to-event bridge is not proved",
            "ExecutableBoundary contains a narrower checked factorization lemma",
        ],
        "file_sha256": {
            name: hashlib.sha256(file.read_bytes()).hexdigest()
            for name, file in files.items()
        },
        "controls": tests,
        "source_kind": "public exact SHA; README declarations are author-stated, not external normative YAML proof",
        "fresh_semantic_counterexample": "NOT_TESTED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "sha": sha, "controls_pass": sum(tests.values())}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
