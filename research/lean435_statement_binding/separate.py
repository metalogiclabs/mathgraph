#!/usr/bin/env python3
"""One decisive distinction: correct proof vs. correct source statement.

This is a bounded, native Lean experiment. It does not extend original proof
receipt authority or infer natural-language fidelity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "lean435_receipt"
OUT = HERE / "evidence"
OUT.mkdir(parents=True, exist_ok=True)
UPSTREAM_COMMIT = "eb6cafb7290e8bd5f2937522d8d804f58f02bafc"
UPSTREAM_BLOB = "6b3ac409cc1ed8775644c5c6a00a1a59f96fac2b"
ORIGINAL_RECEIPT_SOURCE_COMMIT = "d009cbe2a0094c0df460e892557150847639372f"
STEPS: list[dict] = []

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def github_git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def step(label: str, command: list[str], expected_exit: int, must_contain: str | None = None) -> None:
    start = time.monotonic()
    p = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, encoding="utf8",
                       errors="replace", check=False)
    contents = "$ " + " ".join(command) + "\n" + p.stdout
    raw = contents.encode("utf8")
    (OUT / (label + ".log")).write_bytes(raw)
    result = {
        "label": label, "exit_code": p.returncode, "expected_exit": expected_exit,
        "log_sha256": sha256(raw), "seconds": round(time.monotonic() - start, 3),
        "expected_diagnostic": must_contain,
        "diagnostic_present": must_contain in p.stdout if must_contain else None,
    }
    STEPS.append(result)
    print(json.dumps(result), flush=True)
    if p.returncode != expected_exit:
        raise RuntimeError(label + ": wrong exit code; read recorded log")
    if must_contain and must_contain not in p.stdout:
        raise RuntimeError(label + ": missing specific diagnostic; read recorded log")

def source_preflight() -> dict:
    url = (f"https://raw.githubusercontent.com/leanprover/lean4/"
           f"{UPSTREAM_COMMIT}/src/Init/Data/Nat/Gcd.lean")
    req = Request(url, headers={"User-Agent": "mathgraph-source-identity-separator"})
    with urlopen(req, timeout=40) as response:
        raw = response.read()
    actual_blob = github_git_blob_sha(raw)
    if actual_blob != UPSTREAM_BLOB:
        raise RuntimeError("UPSTREAM_SOURCE_BLOB_MISMATCH")
    if b"theorem gcd_comm (m n : Nat) : gcd m n = gcd n m :=" not in raw:
        raise RuntimeError("UPSTREAM_THEOREM_SURFACE_MISSING")
    changed = raw.replace(b"theorem gcd_comm (m n : Nat)", b"theorem gcd_comm_weaker (m n : Nat)", 1)
    if changed == raw or github_git_blob_sha(changed) == UPSTREAM_BLOB:
        raise RuntimeError("SOURCE_MUTATION_CONTROL_DID_NOT_DISTINGUISH")
    return {"url": url, "sha256": sha256(raw), "git_blob": actual_blob,
            "mutation_sha_differs": True, "decl_surface_found": True}

def run() -> int:
    result = {"schema": "mathgraph.lean435.source-identity-separator.v1",
              "status": "UNKNOWN", "source_preflight": None,
              "original_receipt_commit": ORIGINAL_RECEIPT_SOURCE_COMMIT,
              "upstream_revision": UPSTREAM_COMMIT, "upstream_git_blob": UPSTREAM_BLOB,
              "qualified_claim": None, "steps": STEPS, "failure": None}
    try:
        step("version", ["lean", "--version"], 0, "4.35.0")
        result["source_preflight"] = source_preflight()
        step("lake_manifest", ["lake", "update"], 0)
        step("build_both_pairs", ["lake", "build", "Solution", "ForgedChallenge", "ForgedSolution"], 0)
        # Source-authority anchor compares imported Lean declaration types using Meta.isDefEq.
        step("genuine_statement_anchor", ["lake", "env", "lean", "SourceAnchorHonest.lean"],
             0, "SOURCE_STATEMENT_MATCH")
        # Important: this is deliberately a PASS: the comparator is doing its job.
        comparator = {"challenge_module": "ForgedChallenge",
                      "solution_module": "ForgedSolution",
                      "theorem_names": ["MathGraphReceipt.upstream_gcd_comm"],
                      "permitted_axioms": ["propext", "Quot.sound", "Classical.choice"]}
        config = ROOT / "comparator-weak-pair.json"
        config.write_text(json.dumps(comparator, sort_keys=True, indent=2) + "\n")
        step("paired_weak_statement_comparator",
             ["lake", "comparator", "--config", config.name, "--paranoid"],
             0, "Your solution is okay!")
        step("weak_statement_source_anchor",
             ["lake", "env", "lean", "SourceAnchorForged.lean"], 1,
             "SOURCE_STATEMENT_MISMATCH")
        result["qualified_claim"] = (
            "The unchanged Lean 4.35 comparator accepts a valid, jointly weakened "
            "challenge/solution; an independently anchored type comparison to "
            "upstream Nat.gcd_comm rejects misattribution while accepting the "
            "genuine theorem. This only addresses formal-source statement identity."
        )
        result["status"] = "WARRANTED_BOUNDED_FORMAL_SOURCE_IDENTITY"
    except Exception as e:
        result["failure"] = str(e)
    finally:
        result["branch_head_sha"] = (os.environ.get("GITHUB_HEAD_SHA")
                                      or os.environ.get("GITHUB_SHA") or "LOCAL")
        report = OUT / "report.json"
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("FINAL", json.dumps({"status": result["status"], "failure": result["failure"]}),
              flush=True)
    return 0 if result["status"] == "WARRANTED_BOUNDED_FORMAL_SOURCE_IDENTITY" else 1

if __name__ == "__main__":
    sys.exit(run())
