#!/usr/bin/env python3
"""Pinned source-provenance audit; this is NOT a Lean proof checker."""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

REPO = "openai/math"
PIN = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
BASE = f"https://raw.githubusercontent.com/{REPO}/{PIN}/"
PREFIX = "preprints/"
WITHDRAWALS = {
    "weil": (PREFIX + "Algebraicity-of-Weil-classes-on-split-abelian-eightfolds-September-18-2026/README.md", "c7c9b6abcde71135b68582a318a23111b996494b"),
    "kuga_satake": (PREFIX + "Algebraicity-of-Kuga-Satake-Correspondences-for-K3-Surfaces-October-3-2026/README.md", "f5c9294c6447ba3dd0477007704c039c73aec71e"),
    "hodge_k3": (PREFIX + "The-rational-Hodge-conjecture-for-products-of-K3-surfaces-October-4-2026/README.md", "7d0be5e083c7dd0cb8fa330498cb40c9ce059e27"),
}
LOGSPACE = {
    "challenge": ("lean/ComparatorChallenges/LogspaceEquality.lean", "692a4bdc0de7de093d83abdcb7a2bb1ccb7d476b"),
    "comparator": ("lean/ComparatorChallenges/LogspaceEquality.json", "06ca6c6af3ecbe3b426f36b54c7ec9b4e319d117"),
    "solution": ("lean/OAI/Computability/Logspace/Equality.lean", "5397fc4cc54b4aefd0898108746b1f301c5c2ce7"),
}
FILES = dict(WITHDRAWALS, **LOGSPACE)
THEOREM = "OAI.ExactDerandomization.exact_logarithmic_space_derandomization"

def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def remote_loader(path):
    with urllib.request.urlopen(BASE + path, timeout=45) as res:
        return res.read()

def audit(loader=remote_loader, *, check_hashes=True):
    texts = {}
    sources = {}
    for key, (path, expected) in FILES.items():
        raw = loader(path)
        actual = git_blob_sha(raw)
        if check_hashes and actual != expected:
            raise ValueError(f"PIN_MISMATCH {key}: {actual} != {expected}")
        texts[key] = raw.decode("utf-8")
        sources[key] = {"path": path, "blob_sha": actual, "url": BASE + path}

    for key in WITHDRAWALS:
        if "Withdrawn on October 6, 2026" not in texts[key]:
            raise ValueError(f"WITHDRAWAL_NOTICE_MISSING {key}")
        if "does not assert that the mathematical statement is false" not in texts[key]:
            raise ValueError(f"PROOF_VS_THEOREM_DISTINCTION_MISSING {key}")
    root = texts["weil"]
    for token in ("sign error", "I_{\\mathrm{new}}", "-2m", "Eliashberg-Murphy", "zero signed double-point count"):
        if token not in root:
            raise ValueError(f"ROOT_WITNESS_MISSING {token}")
    for key in ("kuga_satake", "hodge_k3"):
        if "flawed stabilization-trace construction" not in texts[key]:
            raise ValueError(f"DECLARED_DEPENDENCY_MISSING {key}")

    challenge = texts["challenge"]
    solution = texts["solution"]
    comparator = json.loads(texts["comparator"])
    name = THEOREM.rsplit(".", 1)[1]
    if not re.search(r"theorem\s+" + re.escape(name) + r"\s*:\s*L\s*=\s*RL\s*∧\s*RL\s*=\s*BPL", challenge):
        raise ValueError("CHALLENGE_STATEMENT_CHANGED")
    if not re.search(r"theorem\s+" + re.escape(name) + r"\s*:\s*L\s*=\s*RL\s*∧\s*RL\s*=\s*BPL", solution):
        raise ValueError("SOLUTION_STATEMENT_CHANGED")
    if not re.search(r"theorem\s+" + re.escape(name) + r"[\s\S]*?:=\s*by\s+sorry", challenge):
        raise ValueError("EXPECTED_CHALLENGE_HOLE_MISSING")
    if re.search(r"\bsorry\b|\bunsafe\b|\badmit\b", solution):
        raise ValueError("SOLUTION_FILE_CONTAINS_UNVERIFIED_SYNTAX")
    if comparator.get("solution_module") != "OAI.Computability.Logspace.Equality":
        raise ValueError("COMPARATOR_SOLUTION_MAPPING_CHANGED")
    if THEOREM not in comparator.get("theorem_names", []):
        raise ValueError("COMPARATOR_THEOREM_MAPPING_CHANGED")
    if set(comparator.get("permitted_axioms", [])) != {"propext", "Quot.sound", "Classical.choice"}:
        raise ValueError("AXIOM_POLICY_CHANGED")
    return {
        "upstream": {"repository": REPO, "commit": PIN},
        "audit_boundary": "Pinned source and declared withdrawal dependency; no Lean/kernel, PDF-to-formal-statement or independent mathematics replay",
        "withdrawals": {
            "weil": {"status": "SOURCE_REPORTED_WITHDRAWN_PROOF", "reason": "signed stabilization-trace count -2m != 0 for positive m", "source": sources["weil"]},
            "kuga_satake": {"status": "SOURCE_REPORTED_WITHDRAWN_DEPENDENT_PROOF", "depends_on": "weil", "source": sources["kuga_satake"]},
            "hodge_k3": {"status": "SOURCE_REPORTED_WITHDRAWN_DEPENDENT_PROOF", "depends_on": "weil", "source": sources["hodge_k3"]},
        },
        "logspace": {"theorem": THEOREM, "status": "UNKNOWN_INDEPENDENT_LEAN_REPLAY", "challenge_contains_hole": True,
                     "solution_source_present": True, "axiom_policy": comparator["permitted_axioms"],
                     "scope": "L=RL and RL=BPL as defined by Comparator challenge, not independently compared to paper",
                     "sources": {key: sources[key] for key in LOGSPACE}},
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", help="Write machine-readable report here")
    args = ap.parse_args()
    result = audit()
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(encoded)

if __name__ == "__main__":
    main()
