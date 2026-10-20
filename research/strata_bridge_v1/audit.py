"""Independent documented consequence closure on two exact native Strata replay receipts.

No source-authentication function is smuggled into the existing MathGraph
resolver. Runs qualify the finite, documentary assertions below; neither
model-to-VC correctness nor universally sound translation is admitted.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph, compare_snapshots

root = Path(__file__).resolve().parents[2]
ev = root / "strata_bridge_collected"
read = lambda suffix, name: ev / ("strata-bridge-" + suffix) / name
for var, sha in (
 ("exposed_main","0bbe12d22650dc12dc4adc15249c965ba5ade8e3"),
 ("proposed_repair","4016549f846065b5cab405fc09cff9a35d13512f"),
):
    p = read(var, "run_report.json")
    rep=json.loads(p.read_text())
    assert rep["pinned_revision"] == sha == rep["actual_revision"]
    assert rep["control"] == "LEAN_CHECKED"
    assert rep["scientific_status"] == "EXPOSED_RETROSPECTIVE_ONLY"
    for path, digest in rep["evidence_hashes"].items():
        assert hashlib.sha256(read(var,path).read_bytes()).hexdigest() == digest
    control=read(var,"control.log").read_text()
    assert "MATHGRAPH_CONTROL_GREEN" in control and "sorryAx" not in control
    assert "plain_div_zero" in control and "smt_div_zero" in control
    bad=read(var,"bad_vc.log").read_text()
    if var=="exposed_main":
        assert rep["bad_vc"]=="ACCEPTED_WITH_BRIDGE"
        assert rep["bad_vc_exit_code"] == 0
        assert "_genSMTVCs_tcbBridge" in bad and "sorryAx" not in bad
        assert "MATHGRAPH_EXPOSED_FALSE_ACCEPTED" in bad
    else:
        assert rep["bad_vc"]=="REJECTED" and rep["bad_vc_exit_code"] != 0
        assert ("smtUDiv" in bad or "gen_smt_vcs" in bad or "udiv_zero" in bad)
        assert "error:" in bad or "error(" in bad
print("RAW_TWO_REVISION_ATTESTATIONS_PASS")
scope="documentary:Strata-VC-main-vs-open-fix-2026-10-20"
claim_names=(
 "strata.native_main.trusted_false",
 "strata.native_patch.refuses_false",
 "strata.control.main",
 "strata.control.patch",
 "strata.semantic_discrepancy.documented",
 "strata.unrelated_control",
 "strata.vc_translation_semantically_warranted",
 "cross_industry_universal_method",
)
claims=[Claim(id,"documentary",scope) for id in claim_names]
receipts=[Receipt(id,"documentary",scope) for id in (
 "main_acceptance","repair_refusal","main_control","repair_control","source_denotation")]
routes=[
 Route("strata.native_main.trusted_false",("main_acceptance",)),
 Route("strata.native_patch.refuses_false",("repair_refusal",)),
 Route("strata.control.main",("main_control",)),
 Route("strata.control.patch",("repair_control",)),
 Route("strata.semantic_discrepancy.documented",("main_acceptance","source_denotation")),
 Route("strata.unrelated_control",("main_control",)),
 Route("strata.unrelated_control",("repair_control",)),
]
before=dict(resolve_graph(claims,routes,receipts).states)
assert before["strata.vc_translation_semantically_warranted"]=="UNKNOWN"
assert before["cross_industry_universal_method"]=="UNKNOWN"
cases={
 "withdraw_main_proof":("main_acceptance",{"strata.native_main.trusted_false","strata.semantic_discrepancy.documented"}),
 "withdraw_repair_refusal":("repair_refusal",{"strata.native_patch.refuses_false"}),
 "withdraw_native_denotation":("source_denotation",{"strata.semantic_discrepancy.documented"}),
 "withdraw_main_control":("main_control",{"strata.control.main"}),
 "withdraw_repair_control":("repair_control",{"strata.control.patch"}),
}
states={}
for key,(withdrawn,expected) in cases.items():
    after=dict(resolve_graph(claims,routes,receipts,withdrawn=frozenset({withdrawn})).states)
    lost={i for i in before if before[i]!="UNKNOWN" and after[i]=="UNKNOWN"}
    assert lost==expected,(key,sorted(lost),sorted(expected))
    assert after["strata.unrelated_control"]=="SOURCE_DOCUMENTED"
    assert after["strata.vc_translation_semantically_warranted"]=="UNKNOWN"
    assert after["cross_industry_universal_method"]=="UNKNOWN"
    assert dict(resolve_graph(claims,routes,receipts).states)==before
    states[key]={"receipt":withdrawn,"lost_only":sorted(lost),"comparison":compare_snapshots(before,after),"restores":True}
report={
 "schema":"mathgraph.strata-smt.exposed-transfer-consequence.v1",
 "native_revision_qualifications":"EXPOSED_RETROSPECTIVE_NATIVE_REPLAY",
 "smt_translation_claim":"REJECTED_BOUNDED_FOR_BITVECTOR_DIVISION_BY_ZERO_ON_MAIN",
 "open_pr_correction":"WARRANTED_BOUNDED_ON_EXPOSED_REPRODUCER_IF_PATCH_REFUSES",
 "universal_method_claim":"UNKNOWN_NOT_PROSPECTIVE",
 "lean_kernel_unsound":"NOT_CLAIMED",
 "bridge_axiom_still_trusted":"YES_ON_CURRENT_REPAIR",
 "source_pins":{"main":"0bbe12d22650dc12dc4adc15249c965ba5ade8e3","fix":"4016549f846065b5cab405fc09cff9a35d13512f"},
 "native_runs":{v:json.loads(read(v,"run_report.json").read_text()) for v in ("exposed_main","proposed_repair")},
 "baseline":before,
 "withdrawals":states,
 "boundaries":[
  "No new source-unseen prospective transfer; Strata defect/fix already exposed.",
  "Source, compiler and trust bridge considered independent authorities. A Lean theorem using a trusted bridge is not an unqualified original-VC proof.",
  "Resolver only recomputes previously externally admitted documentary receipts; does not verify source authority or Lean proof.",
  "Withdrawals are logical receipt removals, not physical removal of upstream files.",
  "The changed upstream fix may block the exposed defect while additional unexamined translation/axiom mismatches remain."
 ],
}
out=ev/"RESULT.json"
out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"GREEN_EXPOSED_BOUNDED","native_main":"trusted axiom admits False","repair":"rejects bad VC","controls":"both pass","withdrawals_lost":{k:v["lost_only"] for k,v in states.items()}},indent=2))
