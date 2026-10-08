#!/usr/bin/env python3
"""OpenAI math pinned-source evidence audit.

This is intentionally NOT a Lean kernel proof replay or a mathematical
validation of an informal manuscript. It checks source provenance,
declared formalization interfaces, and withdrawal dependency notices.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

REV = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
ARCHIVE_REV = "adc7f1241b42e322a6451854ab7e4b4c146bf78a"
UPSTREAM = "https://github.com/openai/math"
PAPER = "preprints/Exact-Derandomization-of-Logarithmic-Space-L-equals-RL-equals-BPL-September-23-2026"
WEIL = "preprints/Algebraicity-of-Weil-classes-on-split-abelian-eightfolds-September-18-2026"
KUGA = "preprints/Algebraicity-of-Kuga-Satake-Correspondences-for-K3-Surfaces-October-3-2026"
HODGE = "preprints/The-rational-Hodge-conjecture-for-products-of-K3-surfaces-October-4-2026"

# Blob hashes independently obtainable from GitHub's pinned Git tree.
# This fixes bytes, not just mutable path names.
SOURCES = {
    "README.md": "50feb63d396138f30dc1ff1e0af121d0263bf5a3",
    "history.md": "693874f398905b1bc59e01b898b223ae9956bfc2",
    f"{WEIL}/README.md": "c7c9b6abcde71135b68582a318a23111b996494b",
    f"{KUGA}/README.md": "f5c9294c6447ba3dd0477007704c039c73aec71e",
    f"{HODGE}/README.md": "7d0be5e083c7dd0cb8fa330498cb40c9ce059e27",
    f"{PAPER}/README.md": "a0d9a904fafc640a781cdb943375cec991cb9c46",
    f"{PAPER}/build/sections/introduction.tex": "46ca8910d9f4ea7e80485281b8be31e3cfea81b3",
    f"{PAPER}/build/sections/model.tex": "1b74a91334ca9690802c0287bca110afda9e1937",
    f"{PAPER}/build/sections/conclusion.tex": "cba0ac20874b5892a6468df7c0c40f4c5ce92e87",
    "lean/formalization.yaml": "275eee8cfab7ce49d3a5e88f02cbb8f28fe6fee6",
    "lean/ComparatorChallenges/LogspaceEquality.json": "06ca6c6af3ecbe3b426f36b54c7ec9b4e319d117",
    "lean/ComparatorChallenges/LogspaceEquality.lean": "692a4bdc0de7de093d83abdcb7a2bb1ccb7d476b",
    "lean/OAI/Computability/Logspace/Equality.lean": "5397fc4cc54b4aefd0898108746b1f301c5c2ce7",
}


def git_blob_sha(blob: bytes) -> str:
    header = f"blob {len(blob)}\0".encode("ascii")
    return hashlib.sha1(header + blob).hexdigest()


def get_bytes(path: str, from_dir: pathlib.Path | None) -> bytes:
    if from_dir is not None:
        return (from_dir / path).read_bytes()
    url = f"https://raw.githubusercontent.com/openai/math/{REV}/{path}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "MathGraph-Pinned-Evidence-Audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def run_audit(from_dir: pathlib.Path | None) -> tuple[dict, bool]:
    records = []
    failures = []
    source_bytes = {}
    for path, expected in SOURCES.items():
        url = f"{UPSTREAM}/blob/{REV}/{path}"
        try:
            payload = get_bytes(path, from_dir)
            actual = git_blob_sha(payload)
            good = actual == expected
            if not good:
                failures.append(f"blob mismatch: {path}: expected {expected}, got {actual}")
            else:
                source_bytes[path] = payload.decode("utf-8")
            records.append({"path": path, "url": url,
                            "expected_git_blob": expected,
                            "actual_git_blob": actual,
                            "integrity": "PASS" if good else "FAIL"})
        except (OSError, UnicodeDecodeError, TimeoutError) as error:
            failures.append(f"unreadable source: {path}: {error}")
            records.append({"path": path, "url": url, "integrity": "ERROR",
                            "error": str(error)})

    checks = []

    def check(name: str, passed: bool, explanation: str) -> None:
        checks.append({"name": name, "result": "PASS" if passed else "FAIL",
                       "explanation": explanation})
        if not passed:
            failures.append(f"{name}: {explanation}")

    if len(source_bytes) != len(SOURCES):
        check("all_pinned_bytes", False, "Some source blobs could not be authenticated")
    else:
        check("all_pinned_bytes", True, "All 13 source blobs matched their exact Git SHA-1")

        readme = source_bytes["README.md"]
        history = source_bytes["history.md"]
        base = source_bytes[f"{WEIL}/README.md"]
        children = [source_bytes[f"{KUGA}/README.md"],
                    source_bytes[f"{HODGE}/README.md"]]

        check("catalogue_scope",
              all(s in readme for s in ("719 manuscripts", "372 families", "~42%")),
              "Current catalogue/version statement is present")
        check("withdrawal_origin",
              all(s in base for s in (
                  "Withdrawn on October 6, 2026",
                  "sign error", "negative double points",
                  "-2m", "not establish its claimed algebraicity theorem",
                  ARCHIVE_REV)),
              "Weil-classes notice supplies exact sign/cancellation failure and archive")
        check("withdrawal_children",
              all("Withdrawn on October 6, 2026" in item and
                  "Weil classes" in item and
                  "flawed stabilization-trace" in item and
                  ARCHIVE_REV in item for item in children),
              "Both K3-family notices explicitly cite the flawed upstream construction")
        check("withdrawal_not_disproof",
              all("does not assert that the mathematical statement is false" in item
                  for item in [base, *children]),
              "Withdrawal invalidates published proof, not necessarily the conjecture")
        check("history_crosscheck",
              all(s in history for s in ("October 7, 2026",
                   "three manuscripts", "14 other manuscripts",
                   "6 formalizations", "300 / 719")),
              "Release history reports the withdrawals, repairs, and formalization count")

        manifest = source_bytes["lean/formalization.yaml"]
        config = json.loads(source_bytes["lean/ComparatorChallenges/LogspaceEquality.json"])
        challenge = source_bytes["lean/ComparatorChallenges/LogspaceEquality.lean"]
        solution = source_bytes["lean/OAI/Computability/Logspace/Equality.lean"]
        intro = source_bytes[f"{PAPER}/build/sections/introduction.tex"]
        model = source_bytes[f"{PAPER}/build/sections/model.tex"]
        conclusion = source_bytes[f"{PAPER}/build/sections/conclusion.tex"]

        mapping = re.search(
            r"comparator_config:\s*ComparatorChallenges/LogspaceEquality\.json"
            r"\s+declaration:\s*OAI\.ExactDerandomization\.exact_logarithmic_space_derandomization"
            r"\s+file:\s*OAI/Computability/Logspace/Equality\.lean",
            manifest)
        check("manifest_to_solution", mapping is not None,
              "Manifest explicitly maps the result to the theorem and source module")
        check("comparator_config",
              config.get("solution_module") == "OAI.Computability.Logspace.Equality" and
              "OAI.ExactDerandomization.exact_logarithmic_space_derandomization"
              in config.get("theorem_names", []) and
              set(config.get("permitted_axioms", [])) ==
              {"propext", "Quot.sound", "Classical.choice"},
              "Comparator names the theorem and its permitted-axiom policy")
        check("challenge_is_placeholder",
              "theorem exact_logarithmic_space_derandomization" in challenge and
              "sorry" in challenge,
              "The challenge contains a sorry; it is not the solution proof")
        theorem = re.search(
            r"theorem exact_logarithmic_space_derandomization\s*:\s*"
            r"L\s*=\s*RL\s*∧\s*RL\s*=\s*BPL\s*:=\s*by\b(.+?)\n\nend",
            solution, re.S)
        check("actual_solution_theorem",
              theorem is not None and "sorry" not in theorem.group(1) if theorem else False,
              "A separately submitted Lean solution theorem has no literal sorry in its body; "
              "imports and kernel acceptance are NOT checked")
        check("paper_headline_alignment",
              r"\Lclass=\RL=\BPL" in intro and
              r"\begin{theorem}[Exact logarithmic-space derandomization]" in intro and
              "BPL" in conclusion and "RL" in conclusion,
              "The source paper states the same headline equality; this is NOT full semantic equivalence")
        check("paper_model_documented",
              "polynomial-time randomized machine" in model and
              "work space" in model and
              "randomized machine" in intro,
              "Paper includes a concrete time/space machine model; faithful Lean mapping remains UNKNOWN")

    clean = not failures
    report = {
        "schema": "metalogic.openai_math_evidence_audit.v1",
        "upstream_repository": UPSTREAM,
        "upstream_commit": REV,
        "archive_commit": ARCHIVE_REV,
        "audit_scope": "pinned source bytes, declared interfaces, and withdrawal notices",
        "run_result": "PASS" if clean else "FAIL",
        "source_files": records,
        "checks": checks,
        "dependency_edges": [
            {"from": f"{WEIL}/README.md", "to": f"{KUGA}/README.md",
             "relation": "cited_flawed_construction"},
            {"from": f"{WEIL}/README.md", "to": f"{HODGE}/README.md",
             "relation": "cited_flawed_construction"},
        ],
        "epistemic_state": {
            "source_byte_integrity": "WARRANTED_BOUNDED" if clean else "UNKNOWN",
            "withdrawal_notices_and_declared_lineage":
                "WARRANTED_SOURCE_ATTESTATION" if clean else "UNKNOWN",
            "declared_main_theorem_comparator_mapping":
                "WARRANTED_SOURCE_ATTESTATION" if clean else "UNKNOWN",
            "source_headline_correspondence":
                "CANDIDATE" if clean else "UNKNOWN",
            "independent_lean_comparator_replay": "UNKNOWN_NOT_RUN",
            "import_dependency_axiom_audit": "UNKNOWN_NOT_RUN",
            "full_paper_to_formal_statement_semantic_alignment": "UNKNOWN_NOT_DONE",
            "independent_sign_error_mathematical_derivation": "UNKNOWN_NOT_DONE",
            "withdrawn_proofs": "REJECTED_BY_SOURCE_WITHDRAWAL",
        },
        "failures": failures,
    }
    return report, clean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-dir", type=pathlib.Path,
                        help="Offline mirror of pinned openai/math checkout")
    parser.add_argument("--output", type=pathlib.Path,
                        default=pathlib.Path("openai-math-audit-report.json"))
    args = parser.parse_args()
    report, clean = run_audit(args.from_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Audit {'PASS' if clean else 'FAIL'}; "
          f"{len(report['source_files'])} files; "
          f"{sum(x['result'] == 'PASS' for x in report['checks'])}/"
          f"{len(report['checks'])} checks")
    print(f"Report: {args.output}")
    for failure in report["failures"]:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
