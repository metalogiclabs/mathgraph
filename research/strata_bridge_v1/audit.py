"""Replay exact-source and verification outputs, then use unchanged MathGraph closure.

Documentary receipts are accepted from an explicitly trusted caller. This is
not an independent formal transport proof, nor an evidence authentication
engine; source comparisons are exactly the exposed 8-bit closed case.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph, compare_snapshots
from research.strata_bridge_v1.baseline import expert_rule_proxy

E = pathlib.Path(sys.argv[1]).resolve()
def read(name):
    return (E / name).read_text()
def digest(name):
    return hashlib.sha256((E / name).read_bytes()).hexdigest()
def check(condition, error):
    if not condition:
        raise AssertionError(error)

pins = json.loads(read("pins.json"))
check(pins["original"] == "0bbe12d22650dc12dc4adc15249c965ba5ade8e3",
      "ORIGINAL_SOURCE_PIN_CHANGED")
check(pins["patched"] == "4016549f846065b5cab405fc09cff9a35d13512f",
      "PATCH_SOURCE_PIN_CHANGED")
for name in ("original_oracle.log", "patched_oracle.log"):
    source = read(name)
    check("MATHGRAPH_LEAN_DIV0=0" in source, "MISSING_LEAN_ZERO_" + name)
    check("MATHGRAPH_SMT_DIV0=255" in source, "MISSING_SMT_ONES_" + name)
    check("MATHGRAPH_STRATA_DENOTATION_ORACLE_PASSED" in source,
          "MISSING_ORACLE_PROOF_" + name)
    check("sorryAx" not in source, "NON_KERNEL_ORACLE_" + name)

original = read("original_bridge.log")
patched = read("patched_bridge.log")
check("MATHGRAPH_STRATA_FALSE_VIA_BRIDGE_COMPILED" in original,
      "NO_ORIGINAL_CONTRADICTION_THEOREM")
check("_genSMTVCs_tcbBridge" in original, "AXIOM_DEPENDENCY_NOT_EXPOSED")
check("sorryAx" not in original, "UNEXPECTED_SORRY_AXIOM_IN_ORIGINAL")
check(read("patched_bridge.exit").strip() not in ("", "0"),
      "PATCH_ACCEPTED_OR_NO_EXIT")
check("error:" in patched or "error(" in patched,
      "PATCH_FAILURE_NOT_A_LEAN_DIAGNOSTIC")
check("MATHGRAPH_STRATA_FALSE_VIA_BRIDGE_COMPILED" in patched,
      "PATCH_PROBE_DID_NOT_REACH_END")
check("BitVec.smtUDiv" in read("patched_translate_excerpt.txt"),
      "PATCH_TRANSLATOR_NOT_SMTUDIV")
check("mkBitVecDiv" in read("original_translate_excerpt.txt"),
      "ORIGINAL_TRANSLATOR_NOT_HDIV")

# A source-independent pairwise disagreement observer can distinguish a
# specified model and source on the finite input once BOTH outputs are admitted.
# It does not autonomously identify the correct interpretation of unfamiliar syntax.
observer = "DIFFERENT" if 0 != 255 else "SAME"
baseline = expert_rule_proxy(8, 0, 255)
check(observer == baseline["relation"], "EQUAL_INFORMATION_BASELINE_DISAGREES")

scope = "strata-main-vs-pr1490-bitvec8-divzero-exposed-20261020"
keys = (
    "source.smt_denotation_255",
    "checker.translated_goal_0",
    "original.bridge_assisted_false_theorem",
    "source.semantic_mismatch_observed",
    "patch.refuses_known_false_proof",
    "unrelated.oracle_control",
    "source_to_verifier.full_semantic_preservation",
)
claims = [Claim(key, "documentary", scope) for key in keys]
receipts = [Receipt(key, "documentary", scope) for key in (
    "smt_oracle", "translated_goal", "bridge_proof",
    "disagreement_admission", "patch_rejection", "unrelated_oracle",
)]
routes = [
    Route("source.smt_denotation_255", ("smt_oracle",)),
    Route("checker.translated_goal_0", ("translated_goal",)),
    Route("original.bridge_assisted_false_theorem", ("bridge_proof",)),
    Route("source.semantic_mismatch_observed", ("disagreement_admission",),
          ("source.smt_denotation_255", "checker.translated_goal_0")),
    Route("patch.refuses_known_false_proof", ("patch_rejection",)),
    Route("unrelated.oracle_control", ("unrelated_oracle",)),
]
def resolve(withdrawn=frozenset()):
    return dict(resolve_graph(claims, routes, receipts, withdrawn=withdrawn).states)
before = resolve()
check(before["source.semantic_mismatch_observed"] == "SOURCE_DOCUMENTED",
      "MISMATCH_NOT_ADMITTED_AS_SOURCE_DOCUMENTARY")
check(before["source_to_verifier.full_semantic_preservation"] == "UNKNOWN",
      "ILLEGITIMATE_GLOBAL_PRESERVATION_WARRANT")
withdrawals = {}
for label, removed, wanted in (
    ("withdraw_smt_oracle", "smt_oracle",
     {"source.smt_denotation_255", "source.semantic_mismatch_observed"}),
    ("withdraw_translated_goal", "translated_goal",
     {"checker.translated_goal_0", "source.semantic_mismatch_observed"}),
    ("withdraw_bridge_proof", "bridge_proof",
     {"original.bridge_assisted_false_theorem"}),
    ("withdraw_patch_rejection", "patch_rejection",
     {"patch.refuses_known_false_proof"}),
):
    after = resolve(frozenset((removed,)))
    lost = {n for n in before if before[n] != "UNKNOWN" and after[n] == "UNKNOWN"}
    check(lost == wanted, "NONSELECTIVE_WITHDRAWAL_" + label)
    check(after["source_to_verifier.full_semantic_preservation"] == "UNKNOWN",
          "POST_WITHDRAWAL_FALSE_WARRANT")
    check(after["unrelated.oracle_control"] == "SOURCE_DOCUMENTED",
          "UNRELATED_CONTROL_LOST")
    check(resolve() == before, "RESTORATION_FAILURE")
    withdrawals[label] = {
        "receipt": removed,
        "lost_only": sorted(lost),
        "restoration_identical": True,
        "comparison": compare_snapshots(before, after),
    }

report = {
    "schema": "mathgraph.strata-smt-meaning-withdrawal.v1",
    "status": "WARRANTED_BOUNDED_RETROSPECTIVE_CROSS_FAMILY_REPLAY",
    "pins": pins,
    "source_denotation": 255,
    "translated_lean_division": 0,
    "semantic_preservation": "REJECTED_BOUNDED_ONE_8BIT_ZERO_DIVISION",
    "bridge_false_theorem": "PROVED_WITH_EXTRA_TCB_AXIOM_NOT_KERNEL_UNSOUNDNESS",
    "patch_original_proof": "REJECTED_AT_PROPOSED_PATCH_PIN",
    "observer": observer,
    "comparison": baseline,
    "method_superiority": "NOT_DEMONSTRATED_EQUAL_INPUT_PROXY_TIE",
    "native_prospective_transfer": "UNKNOWN_PRE_EXPOSED_SOURCE",
    "autonomous_observation_family": "UNKNOWN_NOT_TESTED",
    "receipt_kind": "DOCUMENTARY_EXTERNAL_TRUSTED_ADMISSION",
    "claims_before": before,
    "withdrawals": withdrawals,
    "hashes": {n: digest(n) for n in (
        "original_oracle.log", "patched_oracle.log", "original_bridge.log",
        "patched_bridge.log", "original_translate_excerpt.txt",
        "patched_translate_excerpt.txt",
    )},
    "limits": [
        "Known public upstream issue; cannot claim prospective discovery",
        "Contradiction relies on an explicit added bridge axiom",
        "Original vs proposed patch cannot establish globally sound Strata",
        "No physical revocation, only typed logical withdrawal",
        "Receipt construction and authentication trusted to external runner",
        "No source-independent autonomous obligation generation or human advantage",
    ],
}
(E / "RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "result": report["status"],
    "original_bridge_false_theorem": True,
    "patch_rejects_unchanged_proof": True,
    "original_semantic_values": {"lean": 0, "smt": 255},
    "selective_withdrawals": {k: v["lost_only"] for k, v in withdrawals.items()},
    "baseline": baseline["relation"],
}, indent=2, sort_keys=True))
