"""Build two equal-information reviewer packets for EXPOSED calibration only."""
from pathlib import Path
import json
R=Path("research/mathgraph_check_decision_value_20261021")
D=Path("public/mathgraph-check/reviewer-calibration")
COMMON={
 "subject":"goccy/go-yaml PR #958",
 "base":"edee2f91616c6d73112a13e7c0dbde72ce938877",
 "head":"a34b94ecb553bb5a693296c30232a89026db79ca",
 "sources":[
  "https://github.com/goccy/go-yaml/pull/958",
  "https://github.com/goccy/go-yaml/issues/872",
  "https://github.com/heathsanchez/test/actions/runs/38559572638",
  "https://github.com/heathsanchez/test/actions/runs/38560167831",
  "https://github.com/heathsanchez/test/actions/runs/38560825707",
  "https://github.com/heathsanchez/test/blob/20864090c084efc0511cffcf47aae556b4003fea/research/mathgraph_pr958_one_finding_20261015/ONE_FINDING_REPORT.json"
 ],
 "task":"Classify evidence about PR-introduced regressions versus inherited issues, state what can and cannot be concluded, and select merge/block/defer/request-evidence action. Evidence may be insufficient for global merge approval.",
 "questions":[
  "Which evidence belongs to the PR base/head and which to inherited issue #872?",
  "What is justified about introduced regressions under the declared native case matrix?",
  "What stays UNKNOWN and what additional evidence would change your decision?",
  "What happens if the primary native PR receipt is withdrawn but separate issue evidence remains?"
 ]
}
def build():
 D.mkdir(parents=True,exist_ok=True)
 a={**COMMON,"arm":"A","presentation":"Conventional flat source ledger; review the links and assemble the evidence dependencies yourself."}
 b={**COMMON,"arm":"B","presentation":"MathGraph scoped-evidence navigation; same raw source links, with typed prompts for source identity, verification boundary, evidence dependence, and withdrawal.","workflow":["Identify exact claims and scope","Match each claim to source-pinned native receipts","Separate inherited issue from introduced regressions","Apply dependency-local withdrawal","Retain UNKNOWN rather than infer merge approval"]}
 for name,obj in [("A.json",a),("B.json",b)]:
  (D/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
 truth={"calibration_only":True,"not_for_participants":True,
  "reference":{"repairs":69,"introduced_regressions_in_matrix":0,"inherited_failures":20,"prior_issue":872,
  "action":"Do not block solely for inherited #872; no universal safe-to-merge claim",
  "withdrawal":"Loss of native PR receipt makes PR-specific behavioral assurance UNKNOWN; independent issue receipt survives"},
  "warnings":["Historical answer was already exposed","No independent reviewer measurements","Do not put answer key in A/B presentation"]}
 (R/"REVIEWER_CALIBRATION_KEY.json").write_text(json.dumps(truth,indent=2,sort_keys=True)+"\n")
 assert a["sources"]==b["sources"] and a["task"]==b["task"] and a["questions"]==b["questions"]
 for p in (D/"A.json",D/"B.json"):
  t=p.read_text()
  for forbidden in ['"repairs": 69','"inherited_failures": 20','"introduced_regressions_in_matrix": 0']:
   assert forbidden not in t
 print("CALIBRATION_PACKETS_EQUAL_INFORMATION_AND_NO_KEY_LEAK: PASS")
if __name__=="__main__":build()
