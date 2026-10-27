#!/usr/bin/env python3
"""Independent source-pinned PKC tutorial claim audit. No JPL imports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PIN="023ff7e730e86260871c1adb7411dee12848d006"
REPO="nasa-jpl/PropertyKindCalculus"
TOOLCHAIN="leanprover/lean4:v4.35.0"
PINS={
 "HCP/L4_OutOfTheLine.lean":"27d8b00f69d585f33b5f1e2d175f27ac9dcfe4c8",
 "HCP/L5_Damping.lean":"8f846e1da5db32b1eb9efd22b92fb2bd1eb3d9b2",
 "HCP/L6_Requirements.lean":"b8287671b90cd80ec49e28dff2ccbe20d1d0f4e5",
 "HCP/Worksheets/L4_OutOfTheLine.lean":"9070fbc17bf2f82989314d915bc461f2227e3296",
 "HCP/Worksheets/L5_Damping.lean":"c2c71d91da82a9605b1562e2e5b2ce553e6531ad",
 "HCP/Worksheets/L6_Requirements.lean":"c318589d857303e1f3d24680c49c92e769ac688f",
 "blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L4_OutOfTheLine.lean":"0a52b6f45d86851afa03a151b7e33c01c93a92b7",
 "blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L5_Damping.lean":"cc750911701186acbe43ed8b985705c5262cb263",
 "blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L6_Requirements.lean":"ed43dade121c2cba57a31fbc4e113ae97ffac450",
 "HCP/README.md":"7a0c1209e158a063b01ab5e43be11b6970e8efc8",
 "HCP.lean":"af90682226ef90ed1c62fb77301d01a33c07911f",
 "HCP/check-hcp.py":"76c00ac97c1595f62a9bce9aead3a7480c749984",
}
LESSONS={
 "L4_OutOfTheLine":("pair_state_and_bearers","points_vectors_and_distances","whose_distance","distance_is_length","bare_frames","kinded_frames","observer_motion","adoption_ladder"),
 "L5_Damping":("damped_rig_and_parts","energy_dissipation","kinds_and_decay_rate","same_dimension_different_kinds","underdamped_regime","same_oscillator_states"),
 "L6_Requirements":("pair_context","pair_mass_model","r1_pair_mass","r2_no_aggregation","r3_empirical","invalid_scopes","requirement_census","scope_gap"),
}
CLAIM="L6_P_SCOPED_R3_HAS_GATE_REFERENT_AND_BOUNDARY_COVERAGE"
SCOPE="DECLARED_P_ONLY_GATE_TWO_SAMPLES_NOT_UNIVERSAL_TRUTH"
class Reject(Exception):pass
class Missing(Exception):pass
def check(x,msg):
 if not x:raise Reject(msg)
def read(p):
 if not p.is_file():raise Missing("MISSING:"+str(p))
 return p.read_text(encoding="utf-8")
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def git(root,*args):
 return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
def anchor_blocks(s):
 return {m[0]:m[1].strip("\n") for m in re.findall(
   r"(?ms)^-- ANCHOR: ([A-Za-z0-9_-]+)[ \t]*\n(.*?)^-- ANCHOR_END: \1[ \t]*$",s)}
def normalize_blank_lines(s):
 return re.sub(r"\n[ \t]*\n", "\n", s.strip("\n"))
def doc_blocks(s):
 # SubVerso syntax: three backticks followed by 'anchor', then exact source.
 return {m[0]:m[1].strip("\n") for m in re.findall(
   r"(?ms)^[\x60]{3}anchor ([A-Za-z0-9_-]+)[ \t]*\n(.*?)^[\x60]{3}[ \t]*$",s)}
def audit_chapter_sources(root,change=None):
 change=change or {}
 summaries={}
 for short,want in LESSONS.items():
  srcp="HCP/"+short+".lean"
  bp="blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/"+short+".lean"
  wp="HCP/Worksheets/"+short+".lean"
  source=change.get(srcp,read(root/srcp))
  blueprint=change.get(bp,read(root/bp))
  worksheet=change.get(wp,read(root/wp))
  ac=anchor_blocks(source)
  dc=doc_blocks(blueprint)
  check(tuple(ac)==want,"SOURCE_ANCHOR_ORDER_CHANGED:"+short+":"+str(list(ac)))
  check(tuple(dc)==want,"DOC_ANCHOR_ORDER_CHANGED:"+short+":"+str(list(dc)))
  work=tuple(re.findall(r"(?m)^-- EXERCISE: ([A-Za-z0-9_-]+)[ \t]*$",worksheet))
  check(work==want,"WORKSHEET_EXERCISE_ORDER_CHANGED:"+short)
  for anchor in want:
   check(normalize_blank_lines(ac[anchor])==normalize_blank_lines(dc[anchor]),
         "BLUEPRINT_QUOTE_CHANGED:"+short+":"+anchor)
   check("-- EXERCISE_END: "+anchor in worksheet,"MISSING_WORKSHEET_END:"+anchor)
  check("#guard_msgs" not in worksheet,"WORKSHEET_CONTAINS_PRODUCTION_GUARD:"+short)
  check("import HCP."+short in read(root/"HCP.lean"),"LESSON_NOT_IN_HCP_IMPORT:"+short)
  summaries[short]={"anchor_count":len(ac),"source_sha256":h(source),
      "blueprint_sha256":h(blueprint),"worksheet_sha256":h(worksheet),
      "anchor_names":list(ac)}
 return summaries
def segment(source,name):
 k="-- ANCHOR: "+name
 e="-- ANCHOR_END: "+name
 check(source.count(k)==1 and source.count(e)==1,"DUPLICATE_OR_MISSING_ANCHOR:"+name)
 return source.split(k,1)[1].split(e,1)[0]
def semantic(source,blueprint):
 r1=segment(source,"r1_pair_mass")
 r2=segment(source,"r2_no_aggregation")
 r3=segment(source,"r3_empirical")
 census=segment(source,"requirement_census")
 gap=segment(source,"scope_gap")
 expected={
 "R1":(r1,["name := \"R1\"","kind := .provable","scope := .sort "+chr(96)*2+"pairS","witness := "+chr(96)*2+"pairMass_assembled","spotChecks := ["+chr(96)*2+"r1Spot]"]),
 "R2":(r2,["name := \"R2\"","kind := .provable","scope := .sort "+chr(96)*2+"pairS","absent := "+chr(96)*2+"pairNormalModeLicense"]),
 "R3":(r3,["name := \"R3\"","kind := .empirical","scope := .objects ["+chr(96)*2+"PairId.P]","referents := ["+chr(96)*2+"couplingSpringRatedExtension]","gate := "+chr(96)*2+"withinRatedRange","spotChecks := ["+chr(96)*2+"pairP_earlierWithinRatedRange, "+chr(96)*2+"pairP_laterWithinRatedRange]","withinRatedRange (s : PairState .P)"]),
 "census":(census,["2 provable, 1 empirical, 0 attested","3 row(s) over 3 model boundary(ies): 3 governed — clean","#kind_requirement_clean HCP.L6_Requirements"]),
 "scope_gap":(gap,["couplingExtensionOfAny {π : PairId}","UNGOVERNED","PairId.Q","1 governed, 1 UNGOVERNED","HCP.L6_ScopeGap"]),
 }
 for label,(section,required) in expected.items():
  for needle in required:
   check(needle in section,"MISSING_SEMANTIC_PREMISE:"+label+":"+needle)
 check("leaves Q ungoverned" in blueprint,"DOC_OMITTED_NEGATIVE_Q_CASE")
 check("P-scoped requirement governs" in blueprint,"DOC_SCOPE_RULE_CHANGED")
 return {
  "R1":"sort-scoped theorem witness and finite sample, not merely a passing sample",
  "R2":"absence of instance checked at pinned environment, not future logical impossibility",
  "R3":"P-only declared empirical referent, Boolean gate, two positive samples; no proof all observations satisfy it",
  "coverage":"3/3 explicitly governed result ports; not a proof physical validity",
  "negative":"generic P/Q boundary reports Q UNGOVERNED; explicitly presented as author negative"
 }
def qualify(root,logs,change=None):
 if git(root,"rev-parse","HEAD")!=PIN:
  return {"status":"WITHDRAWN","reason":"SOURCE_HEAD_CHANGED"}
 for p,pin in PINS.items():
  if git(root,"rev-parse","HEAD:"+p)!=pin:
   return {"status":"WITHDRAWN","reason":"SOURCE_BLOB_CHANGED:"+p}
 if read(root/"lean-toolchain").strip()!=TOOLCHAIN:
  return {"status":"WITHDRAWN","reason":"LEAN_TOOLCHAIN_CHANGED"}
 try:
  anchors=audit_chapter_sources(root,change)
  l6=(change or {}).get("HCP/L6_Requirements.lean",read(root/"HCP/L6_Requirements.lean"))
  p="blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L6_Requirements.lean"
  l6doc=(change or {}).get(p,read(root/p))
  meanings=semantic(l6,l6doc)
  validated=read(logs/"hcp-validator.log")
  compiled=read(logs/"native-lean.log")
  check("7 HCPs checked, 0 errors" in validated,"NATIVE_HCP_CHECKER_NOT_GREEN")
  check("Build completed successfully" in compiled,"LEAN_NATIVE_COMPILATION_NOT_GREEN")
  counterexample=read(logs/"native-r3-counterexample.log")
  check("MATHGRAPH_R3_P_POSITIVE_AND_NEGATIVE_LEAN_PROOF_CHECKED" in counterexample,
        "LEAN_P_EMPIRICAL_COUNTEREXAMPLE_NOT_KERNEL_CHECKED")
  check("out_of_range_record_refused" in counterexample,
        "LEAN_COUNTEREXAMPLE_AXIOM_PROFILE_NOT_OBSERVED")
 except Missing as exc:return {"status":"WITHDRAWN","reason":str(exc)}
 except Reject as exc:return {"status":"REJECTED_EVIDENCE","reason":str(exc)}
 return {"status":"WARRANTED_BOUNDED_SOURCE_FIDELITY",
         "upstream":REPO+"@"+PIN,"lean":TOOLCHAIN,
         "anchors":anchors,"semantics":meanings,
         "native_hcp_log_sha256":h(validated),
         "native_lean_log_sha256":h(compiled),
         "native_r3_counterexample_sha256":h(counterexample),
         "explicit_finite_counterexample":"type-correct PairState P with extension 7 exceeds model limit 6; Lean checks false gate",
         "worksheet_sorrys":"intentional exercises; not cited as solution proof",
         "historical_scope":"HCP currently L0-L6; requested chapters 6-8 not a literal L6-L8 path"}
def verdict(record,claim):
 if record is None:return {"verdict":"WITHDRAWN","reason":"NO_NATIVE_RECEIPT"}
 if claim["source"]!=REPO+"@"+PIN:return {"verdict":"WITHDRAWN","reason":"SOURCE_REVISION_DRIFT"}
 if record.get("status")!="WARRANTED_BOUNDED_SOURCE_FIDELITY":
  return {"verdict":"WITHDRAWN","reason":"UNQUALIFIED_EVIDENCE"}
 if claim["witness"]!="r3CouplingSpringRange":
  return {"verdict":"MISMATCH","reason":"WRONG_REQUIREMENT_WITNESS"}
 if claim["claim_id"]!=CLAIM:return {"verdict":"UNKNOWN","reason":"UNBOUND_REQUIREMENT"}
 if claim["scope"]=="ALL_PAIRS":
  return {"verdict":"MISMATCH","reason":"Q_EXPLICITLY_UNGOVERNED"}
 if claim["scope"]=="ALL_P_STATES_EMPIRICALLY_TRUE":
  return {"verdict":"UNKNOWN","reason":"TWO_SAMPLES_AND_GATE_NOT_UNIVERSAL_EMPIRICAL_TRUTH"}
 if claim["scope"]!=SCOPE:return {"verdict":"UNKNOWN","reason":"UNSUPPORTED_SCOPE"}
 if claim["anchor"]!="HCP.L6_Requirements#r3_empirical":
  return {"verdict":"MISMATCH","reason":"WRONG_SOURCE_ANCHOR"}
 return {"verdict":"WARRANTED_BOUNDED",
         "reason":"P_SCOPED_REQUIREMENT_RECORDED_AND_GATED_NOT_ALL_STATES_PROVED"}
def main():
 ap=argparse.ArgumentParser()
 for k in ("source","logs","output"):ap.add_argument("--"+k,type=Path,required=True)
 a=ap.parse_args()
 root=a.source.resolve();logs=a.logs.resolve()
 record=qualify(root,logs)
 check(record["status"]=="WARRANTED_BOUNDED_SOURCE_FIDELITY",
       "BASELINE_NOT_QUALIFIED:"+str(record))
 good={"source":REPO+"@"+PIN,"claim_id":CLAIM,"scope":SCOPE,
       "witness":"r3CouplingSpringRange","anchor":"HCP.L6_Requirements#r3_empirical"}
 positive=verdict(record,good)
 check(positive["verdict"]=="WARRANTED_BOUNDED","GOOD_CLAIM_FAILED")
 controls=[]
 cases=[
 ("P_warrant_misattributed_to_Q",{"scope":"ALL_PAIRS"},"MISMATCH"),
 ("two_empirical_samples_claim_all_P_states",{"scope":"ALL_P_STATES_EMPIRICALLY_TRUE"},"UNKNOWN"),
 ("R1_theorem_misbound_to_R3",{"witness":"r1PairMass"},"MISMATCH"),
 ("wrong_document_anchor",{"anchor":"HCP.L6_Requirements#r1_pair_mass"},"MISMATCH"),
 ("other_claim_id",{"claim_id":"HCP_L6_HARDWARE_SAFETY"},"UNKNOWN"),
 ("stale_upstream_pin",{"source":REPO+"@"+"0"*40},"WITHDRAWN"),
 ]
 for name,change,want in cases:
  got=verdict(record,{**good,**change})
  check(got["verdict"]==want,"ADMITTED_BAD_CLAIM:"+name)
  controls.append({"id":name,**got})
 got=verdict(None,good)
 check(got["verdict"]=="WITHDRAWN","MISSING_RECEIPT_ACCEPTED")
 controls.append({"id":"evidence_withdrawn",**got})
 docname="blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L6_Requirements.lean"
 doc=read(root/docname)
 bad=doc.replace("scope: objects HCP.L6_Requirements.PairId.P",
                 "scope: objects HCP.L6_Requirements.PairId.Q",1)
 check(bad!=doc,"NO_DOC_TARGET")
 mutated=qualify(root,logs,{docname:bad})
 check(mutated["status"]=="REJECTED_EVIDENCE","FORGED_DOC_ACCEPTED")
 controls.append({"id":"source_blueprint_mismatch",**mutated})
 pathname="HCP/L6_Requirements.lean"
 original=read(root/pathname)
 bad=original.replace("gate := "+chr(96)*2+"withinRatedRange",
                      "gate := "+chr(96)*2+"r1Spot",1)
 check(bad!=original,"NO_GATE_TARGET")
 mutated=qualify(root,logs,{pathname:bad})
 check(mutated["status"]=="REJECTED_EVIDENCE","FORGED_GATE_ACCEPTED")
 controls.append({"id":"R3_gate_identity_mutated",**mutated})
 result={"protocol":"MATHGRAPH_PKC_HCP_INDEPENDENT_ASSURANCE_V1",
         "upstream":REPO+"@"+PIN,"positive":positive,
         "current_lesson_scope":"L4, L5, L6; HCP L7/L8 do not exist",
         "native_source_fidelity":record,
         "negative_controls":controls,"negative_count":len(controls),
         "bounds":["R3 declared scope is P; Q remains ungoverned on generic pair",
                   "R3 two true examples do not prove every P state passes",
                   "R1 theorem is scoped; R2 is current-env license absence",
                   "HCP worksheets contain intentional sorry holes",
                   "not complete literal chapters 6-8 of historical outline",
                   "not a safety certification or independent science measurement",
                   "no direct FGM replay or CPU/GPU equivalence established"],
         "contacted_Nicolas":False,"upstream_modified":False,
         "release_authorized":False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("MATHGRAPH_PKC_HCP_AUDIT_WARRANTED_BOUNDED",
       json.dumps({"lessons":len(LESSONS),"anchors":sum(map(len,LESSONS.values())),
                   "negative_controls":len(controls),"pin":PIN},sort_keys=True))
if __name__=="__main__":main()
