#!/usr/bin/env python3
"""Route qualified three-lane physical source experiment through unchanged V1 warrant core.

A SOURCE REVISION CHANGE invalidates all old source-bound claims pending replay.
A granular TYPE-premise withdrawal only affects that declaration's dependent claims.
Only actually re-executed native lanes receive new source-bound verdicts.
"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cross_domain_correspondence_v1"))
from protocol import Obligation, assess, judge

orig = json.loads((root/"BASE-qualified.json").read_text())
mut = json.loads((root/"MUTANT-qualified.json").read_text())
again = json.loads((root/"RESTORED-qualified.json").read_text())
final = json.loads((root/"v7-final-evidence.json").read_text())
assert final["status"] == "WARRANTED_BOUNDED_PHYSICAL_DECLARATION_TYPE_REVERSAL_AND_REQUALIFICATION"
assert final["only_semantic_verdicts_changed"] == ["typed_match", "typed_mismatch"]
assert orig["observed"] == again["observed"] and orig["observed"] != mut["observed"]
assert orig["source_sha256"] == again["source_sha256"]
assert orig["source_sha256"] != mut["source_sha256"]

TRANSLATE = {
    "MATCH": "MATCH",
    "MISMATCH": "MISMATCH",
    "UNKNOWN_UNSUPPORTED": "UNSUPPORTED",
    "NO_ASSERTION": "NO_ASSERTION",
}
DEPENDENT = {"typed_match", "false_mismatch", "typed_mismatch"}
OTHER_DECL = {"wrong_citation"}

def make(lane):
    status = lane["observed"]
    source_hash = lane["source_sha256"]
    native_log = (root / f'{lane["lane"]}-typed.log').read_bytes()
    required={
        "source_revision": source_hash,
        "native_lane": hashlib.sha256(native_log).hexdigest(),
        "interpretation":"V6_EXACT_FROZEN_INTERPRETER_88914d5c6cd38dc55ffe555d11320f15aeb88bfe",
        "width_length_type":"Edge_width_height" if lane["lane"]=="MUTANT" else "Edge_width_length",
        "height_length_type":"Edge_height_length",
    }
    cases=[]
    for name, verdict in status.items():
        deps=("source_revision", "native_lane", "interpretation")
        if name in DEPENDENT:
            deps+=("width_length_type",)
        elif name in OTHER_DECL:
            deps+=("height_length_type",)
        cases.append(Obligation(name=name,
            source="nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824"
                   + "#local-source-sha256:" + source_hash,
            relation=TRANSLATE[verdict], authority="ASSERTED",
            dependencies=deps,
            qualifier="Conditional on source-authored typed grammar and authoritative optional statement"))
    return tuple(cases),required,assess(tuple(cases),required,required)

cases_base, req_base, verdicts_base=make(orig)
cases_mut, req_mut, verdicts_mut=make(mut)
cases_rest, req_rest, verdicts_rest=make(again)
expected_base={
    "typed_match":"SCOPED_AGREEMENT",
    "false_mismatch":"DIVERGENT_BOUNDED",
    "typed_mismatch":"DIVERGENT_BOUNDED",
    "wrong_citation":"DIVERGENT_BOUNDED",
    "unsupported":"UNKNOWN_INTERPRETATION",
    "true_unsupported":"UNKNOWN_INTERPRETATION",
    "no_statement":"NO_SEMANTIC_ASSERTION",
}
expected_mut={**expected_base,
              "typed_match":"DIVERGENT_BOUNDED",
              "typed_mismatch":"SCOPED_AGREEMENT"}
assert verdicts_base==verdicts_rest==expected_base
assert verdicts_mut==expected_mut
assert {k for k in expected_base if expected_base[k]!=expected_mut[k]}=={
    "typed_match","typed_mismatch"
}
# All OLD source-wide certificates become unknown under the changed source pin.
old_under_mutant=assess(cases_base,req_mut,req_base)
assert set(old_under_mutant.values())=={"UNKNOWN_WITHDRAWN_OR_CHANGED"}
# Isolated type-premise withdrawal must NOT invalidate an independently pinned
# height_length claim; its actual lane requalification is still required for a
# changed whole source revision.
targeted=dict(req_base,width_length_type="WITHDRAWN")
after_targeted=assess(cases_base,targeted,req_base)
assert all(after_targeted[name]=="UNKNOWN_WITHDRAWN_OR_CHANGED" for name in DEPENDENT)
assert all(after_targeted[name]==verdicts_base[name]
           for name in expected_base if name not in DEPENDENT)
# Distinguish author's optional field intent from the *conditional* typed result.
positive=next(x for x in cases_base if x.name=="typed_match")
assert judge(Obligation(**{**vars(positive),"authority":"UNRESOLVED"}),
             req_base,req_base)=="UNKNOWN_CONTRACT"
assert judge(Obligation(**{**vars(positive),"authority":"ANNOTATION"}),
             req_base,req_base)=="NO_SEMANTIC_ASSERTION"
# Reversion is not merely label reinstatement: recorded RESTORED lane compiled,
# checked the source-native statement types, and has the original file digest.
assert (root/"RESTORED-typed.log").exists()
assert (root/"RESTORED-build.log").exists()

result={
 "status":"WARRANTED_BOUNDED_V7_PHYSICAL_SOURCE_REQUALIFICATION_UNCHANGED_V1_CORE",
 "frozen_core":"cross_domain_correspondence_v1/protocol.py",
 "conditional_on_field_being_asserted":True,
 "original_verdicts":verdicts_base,
 "mutated_verdicts_after_source_native_replay":verdicts_mut,
 "restored_verdicts_after_source_native_replay":verdicts_rest,
 "old_source_certificates_under_changed_source":old_under_mutant,
 "targeted_type_withdrawal":after_targeted,
 "actual_type_changes":["typed_match","typed_mismatch"],
 "source_digests":{"base":orig["source_sha256"],"mutant":mut["source_sha256"],
                   "restored":again["source_sha256"]},
 "author_intent":"UNKNOWN_CONTRACT",
 "no_automatic_semantic_interpretation_discovery":True,
}
(root/"v7-v1-warrant-replay.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print("PKC_V7_UNCHANGED_V1_WARRANT_ENGINE_PHYSICAL_SOURCE_REPLAY_PASS")
print(json.dumps(result["mutated_verdicts_after_source_native_replay"],sort_keys=True))
