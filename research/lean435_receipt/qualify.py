#!/usr/bin/env python3
"""Run pinned Lean 4.35.0 native check/comparator with explicit controls.

Never convert a failed checker or infrastructure failure into a theorem receipt.
Published website status remains untouched until the exact CI result is audited.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)
STEPS = []
EXPECTED = ["leanchecker-paranoid", "lean4lean", "nanoda", "con-leche", "con-ron"]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def exec_step(name, args, required_code):
    t = time.monotonic()
    p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, errors="replace", check=False)
    seconds = round(time.monotonic() - t, 3)
    (EVIDENCE / (name + ".log")).write_text(
        "$ " + " ".join(args) + "\n" + p.stdout, encoding="utf-8")
    observed = {"name": name, "command": args, "returncode": p.returncode,
                "expected_exit_code": required_code, "duration_seconds": seconds,
                "log_sha256": digest(EVIDENCE / (name + ".log"))}
    STEPS.append(observed)
    print(json.dumps(observed), flush=True)
    if p.returncode != required_code:
        raise RuntimeError(f"{name}: expected exit {required_code}, got {p.returncode}; "
                           f"inspect evidence/{name}.log")
    return p.stdout

def get_source_sha():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        head = (event.get("pull_request") or {}).get("head") or {}
        if head.get("sha"):
            return head["sha"]
    return os.environ.get("GITHUB_SHA", "LOCAL_UNQUALIFIED")

def run():
    status = "UNKNOWN"
    problem = None
    try:
        version = exec_step("lean_version", ["lean", "--version"], 0)
        if "4.35.0" not in version:
            raise RuntimeError("Wrong Lean version, fail closed")
        exec_step("lake_update", ["lake", "update"], 0)
        if not (ROOT / "lake-manifest.json").exists():
            raise RuntimeError("lake-manifest.json not produced; sandbox precondition missing")
        exec_step("lake_build_solution", ["lake", "build", "Solution"], 0)
        exec_step("lake_check_paranoid", ["lake", "check", "--paranoid"], 0)
        exec_step("lake_comparator_paranoid", ["lake", "comparator", "--paranoid"], 0)

        canonical = json.loads((ROOT / "comparator.json").read_text())
        mutated = {**canonical, "challenge_module": "ChallengeMutated"}
        (ROOT / "comparator-mutated.json").write_text(json.dumps(mutated, indent=2)+"\n")
        forbidden = {**canonical, "solution_module": "SolutionAxiom"}
        (ROOT / "comparator-forbidden.json").write_text(json.dumps(forbidden, indent=2)+"\n")
        exec_step("negative_statement_mutation",
                  ["lake", "comparator", "--config", "comparator-mutated.json", "--paranoid"], 1)
        exec_step("negative_forbidden_axiom",
                  ["lake", "comparator", "--config", "comparator-forbidden.json", "--paranoid"], 1)
        status = "WARRANTED_BOUNDED_NATIVE_REPLAY"
    except Exception as exc:
        problem = str(exc)
        print("QUALIFICATION FAILED CLOSED:", problem, file=sys.stderr, flush=True)
    finally:
        report = {
            "schema": "mathgraph.lean435-receipt-candidate.v1",
            "status": status,
            "qualification_problem": problem,
            "source_repo": "metalogiclabs/mathgraph",
            "source_commit": get_source_sha(),
            "upstream": {
                "repository": "leanprover/lean4",
                "toolchain": "leanprover/lean4:v4.35.0",
                "source_file": "src/Init/Data/Nat/Gcd.lean",
                "git_blob_sha": "6b3ac409cc1ed8775644c5c6a00a1a59f96fac2b",
                "original_declaration": "Nat.gcd_comm"
            },
            "formal_statement": "forall m n : Nat, Nat.gcd m n = Nat.gcd n m",
            "local_declaration": "MathGraphReceipt.upstream_gcd_comm",
            "permitted_axioms": [],
            "requested_checker_mode": "paranoid",
            "bundled_external_checkers_expected_by_release": EXPECTED,
            "covered_by_receipt": [
                "exact statement comparison", "Lean kernel replay",
                "Lean v4.35 paranoid bundled external recheck",
                "rejection of altered challenge", "rejection of new axiom"
            ] if status.startswith("WARRANTED") else [],
            "not_covered": [
                "new theorem discovery", "independent reconstruction of original proof",
                "natural-language fidelity", "whole Mathlib",
                "Nucleus or JPL port", "production action authority"
            ],
            "input_sha256": {path: digest(ROOT / path) for path in [
                "lean-toolchain", "lakefile.toml", "Challenge.lean",
                "Solution.lean", "ChallengeMutated.lean",
                "SolutionAxiom.lean", "comparator.json", "qualify.py"]},
            "steps": STEPS,
        }
        (EVIDENCE / "receipt.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("RECEIPT:", json.dumps({"status": status, "source_commit": report["source_commit"],
                                    "failure": problem}), flush=True)
    return 0 if status.startswith("WARRANTED") else 1

if __name__ == "__main__":
    sys.exit(run())
