#!/usr/bin/env python3
"""Synthetic independent authority-boundary control (no held-out source access).

A hash-equal document can support a *textual* proposed test command without
establishing either normative author intention or complete verification scope.
A forged proposal must also be checked against the frozen source-blind scanner.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("observer_v2", BASE / "construct.py")
candidate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = candidate
spec.loader.exec_module(candidate)

def digest(b):
    return hashlib.sha256(b).hexdigest()

def manufactured_selected(root):
    p = root / "test" / "README.md"
    raw = p.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    k = next(i for i, line in enumerate(lines) if "python test.py" in line)
    return {
        "kind": "AUTHOR_DRIVER",
        "argv": ["python", "test.py"],
        "cwd": "test",
        "parser": "author_test_py",
        "supports": [{
            "path": "test/README.md",
            "sha256": digest(raw),
            "line": k + 1,
            "line_sha256": digest(lines[k].encode())
        }]
    }

def old_lexical_auditor(root, selected):
    """Faithful minimal false-positive mechanism of prior local F1 auditor."""
    support = selected["supports"][0]
    p = root / support["path"]
    raw = p.read_bytes()
    if digest(raw) != support["sha256"]:
        return False
    lines = raw.decode("utf-8").splitlines()
    k = support["line"] - 1
    if digest(lines[k].encode()) != support["line_sha256"]:
        return False
    text = " ".join(lines[max(0, k - 4):k + 1]).lower()
    return ("test" in text
            and not any(t in text for t in ("do not run", "never run",
                                            "unsafe example", "example only"))
            and "test.py" in lines[k].lower())

def source_consistent_but_not_author_certified(root, selected):
    """Cross-check source-bound V2 candidate; never promote human author intent."""
    real = candidate.propose(root)
    chosen = real.get("selected")
    if selected != chosen:
        return "REJECTED_FORGED_OR_STALE_PROPOSAL"
    if chosen is None:
        return "UNKNOWN_NO_SOURCE_DECLARED_OBSERVATION"
    if chosen["kind"] == "AUTHOR_DRIVER":
        return "CANDIDATE_DOCUMENT_SUPPORTED_AUTHOR_INTENT_UNKNOWN"
    return "CANDIDATE_CONFIG_SUPPORTED_SCOPE_UNKNOWN"

def evaluate():
    findings = []
    fixtures = [
        ("positive_explicit_command", "To run the full test suite:\npython test.py\n", "CANDIDATE_DOCUMENT_SUPPORTED_AUTHOR_INTENT_UNKNOWN", True),
        ("dont_run", "Don't run the test suite:\npython test.py\n", "REJECTED_FORGED_OR_STALE_PROPOSAL", True),
        ("do_not_execute", "Do not execute these tests:\npython test.py\n", "REJECTED_FORGED_OR_STALE_PROPOSAL", True),
        ("never_use", "Never use this test runner:\npython test.py\n", "REJECTED_FORGED_OR_STALE_PROPOSAL", True),
        ("incidental_text", "Testing only; not author instructions:\npython test.py\n", "REJECTED_FORGED_OR_STALE_PROPOSAL", True),
        ("example_only", "Example only: to run tests:\npython test.py\n", "REJECTED_FORGED_OR_STALE_PROPOSAL", False)
    ]
    for name, doc, expected, lexical_expected in fixtures:
        with TemporaryDirectory(prefix="mg-authority-v2-") as td:
            root = Path(td)
            (root / "test").mkdir()
            (root / "test" / "test.py").write_text("print('source fixture only')\n")
            (root / "test" / "README.md").write_text(doc)
            selected = manufactured_selected(root)
            old_accepts = old_lexical_auditor(root, selected)
            observed = source_consistent_but_not_author_certified(root, selected)
            assert old_accepts == lexical_expected, (name, old_accepts)
            assert observed == expected, (name, observed, expected)
            # Source bytes can be authentic but no longer support the claim.
            (root / "test" / "README.md").write_text("No runnable suite declared here.\n")
            withdrawn = source_consistent_but_not_author_certified(root, selected)
            assert withdrawn == "REJECTED_FORGED_OR_STALE_PROPOSAL", (name, withdrawn)
            findings.append({"case": name, "old_lexical_accepts": old_accepts,
                             "cross_checked_verdict": observed,
                             "after_document_withdrawal": withdrawn})
    assert sum(x["old_lexical_accepts"] for x in findings) == 5
    assert all(x["cross_checked_verdict"] != "WARRANTED" for x in findings)
    return {
        "status": "PASS_EXPOSED_AUTHORITY_NEGATIVE_GATE",
        "controls": len(findings),
        "original_independent_auditor_false_authority_positives": 4,
        "source_contents_accessed": "SYNTHETIC_ONLY",
        "scope": "forged proposal rejection, not author meaning certification",
        "findings": findings,
        "forbidden_promotions": ["full source-author suite", "new operator grammar",
                                 "original native held-out evidence", "competent human advantage"]
    }

if __name__ == "__main__":
    r = evaluate()
    if len(sys.argv) == 3 and sys.argv[1] == "--out":
        out = Path(sys.argv[2])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, sort_keys=True, indent=2) + "\n")
    print(json.dumps(r, sort_keys=True))
