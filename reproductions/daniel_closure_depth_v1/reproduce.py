#!/usr/bin/env python3
"""One-command deterministic reproduction for Closure-Relative Developmental Depth V1.

No third-party dependencies. The experiment regenerates RESULT.json, while an
independently frozen EXPECTED.json acts as the reproduction oracle. The wrapper
checks the committed result, regenerated result, and headline claim boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments" / "closure_relative_developmental_depth_v1"
RUN = EXP / "run.py"
RESULT = EXP / "RESULT.json"
EXPECTED = Path(__file__).resolve().with_name("EXPECTED.json")
SOURCE_RESULT_COMMIT = "df795a6446ec884b40d4760e230d7776a3032e39"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(RUN.is_file(), f"missing experiment runner: {RUN}")
    require(RESULT.is_file(), f"missing committed certificate: {RESULT}")
    require(EXPECTED.is_file(), f"missing independent reproduction oracle: {EXPECTED}")

    original_result_bytes = RESULT.read_bytes()
    committed = json.loads(original_result_bytes)
    expected_bytes = EXPECTED.read_bytes()
    expected = json.loads(expected_bytes)
    expected_norm = canonical(expected)

    # Before executing anything, require the published certificate and the
    # reproduction oracle to agree. This prevents the runner from silently
    # redefining what counts as success.
    require(
        canonical(committed) == expected_norm,
        "committed RESULT.json differs from independently frozen EXPECTED.json",
    )

    print("Closure-Relative Developmental Depth V1 — clean reproduction")
    print(f"python={sys.version.split()[0]}")
    print(f"source_result_commit={SOURCE_RESULT_COMMIT}")
    print(f"run_py_sha256={sha256(RUN)}")
    print(f"expected_oracle_sha256={hashlib.sha256(expected_bytes).hexdigest()}")
    print(f"committed_result_sha256={hashlib.sha256(original_result_bytes).hexdigest()}")
    print()

    try:
        proc = subprocess.run(
            [sys.executable, str(RUN)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(proc.stdout.rstrip())
        require(proc.returncode == 0, f"experiment exited {proc.returncode}")
        require(RESULT.is_file(), "experiment did not emit RESULT.json")

        actual = json.loads(RESULT.read_text())
        actual_norm = canonical(actual)

        # The independently frozen oracle, not the generated output path,
        # determines the expected certificate.
        require(
            actual_norm == expected_norm,
            "regenerated certificate differs from independently frozen EXPECTED.json",
        )

        gates = actual["gates"]
        require(len(gates) == 14, f"expected 14 gates, got {len(gates)}")
        require(all(gates.values()), "one or more core gates failed")
        require(actual["core_verdict"] == "PASS_DISCOVERABILITY_DEPTH", "core verdict changed")
        require(
            actual["verdict"] == "PARTIAL_STRICT_CONSTRUCTIBILITY_NOT_ESTABLISHED",
            "overall claim boundary changed",
        )

        g1 = actual["generation1"]
        g2 = actual["generation2"]
        inv = actual["invariance"]
        econ = actual["economics"]
        audit = actual["claim_audit"]

        require(g1["literal_intersection"] == 0, "literal-identity separator changed")
        require(g1["selected_class"] == {"src": "LT", "dst": "LE"}, "O1 changed")
        require(g1["heldout_quotient_transport_pass"] is True, "held-out quotient transfer failed")

        require(g2["cold_one_new_literal_candidates_tested"] == 28, "cold candidate count changed")
        require(g2["cold_survivors"] == 0, "cold survivor count changed")
        require(g2["O2_class"] == {"src": "AND", "dst": "OR"}, "O2 changed")
        require(g2["O2_outside_G1_closure"] is True, "O2 closure obstruction failed")
        require(g2["final_pass"] is True, "O1+O2 final capability failed")
        require(g2["O1_ablated_O2_present_pass"] is False, "O1 ablation unexpectedly passes")
        require(g2["O2_ablated_O1_present_pass"] is False, "O2 ablation unexpectedly passes")

        require(
            inv["token_renamings_passed"] == 24 and inv["token_renamings_total"] == 24,
            "presentation invariance changed",
        )
        require(econ["cold_exhaustive_two_rewrite_candidates"] == 784, "cold search count changed")
        require(econ["warm_full_one_rewrite_audit_calls"] == 28, "warm search count changed")
        require(econ["compression_ratio"] == 28.0, "search compression changed")
        require(actual["lifecycle"]["revoked"] is True, "counterevidence no longer revokes scope")

        require(
            audit["developmental_discoverability_depends_on_O1"] is True,
            "discoverability result changed",
        )
        require(
            audit["strict_O2_raw_meta_language_constructibility_depends_on_O1"] is False,
            "strict constructibility falsification changed",
        )

        print("\n=== REPRODUCTION VERIFIED ===")
        print("independent oracle: MATCH")
        print("14/14 core gates: PASS")
        print("O1: [LT -> LE]")
        print("cold O2 survivors: 0/28")
        print("after O1, O2: [AND -> OR]")
        print("O2 outside G1 semantic closure: PASS")
        print("both targeted ablations: FAIL as required")
        print("presentation invariance: 24/24")
        print("search compression: 784 -> 28 (28x)")
        print("later counterevidence: REVOKE")
        print("core verdict: PASS_DISCOVERABILITY_DEPTH")
        print("strict raw constructibility: NOT ESTABLISHED (intended falsification)")
        return 0
    finally:
        # Leave a fresh checkout byte-identical even if a failed experiment
        # emitted a partial or differently formatted RESULT.json.
        RESULT.write_bytes(original_result_bytes)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nREPRODUCTION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
