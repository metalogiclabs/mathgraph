"""Exact-source uriparser / RFC 3986 finite qualification and seeded controls.

An independently published RFC supplies example outputs, but their transcription,
the source-to-oracle interpretation and the seeded mutations are researcher-authored.
This cannot establish human-adjudicated owner intent or novel upstream defects.
"""
import argparse
from itertools import combinations
from pathlib import Path
import hashlib
import json
import subprocess

PIN="abb9f328ae836ff5bf8f211e0ba82f7b6de01ebe"
BASE="http://a/b/c/d;p?q"
# Selected documented normal examples in RFC 3986 §5.4.1 (retrospective, not hidden).
CASES=[
 ("g","http://a/b/c/g"),("./g","http://a/b/c/g"),
 ("g/","http://a/b/c/g/"),("/g","http://a/g"),
 ("?y","http://a/b/c/d;p?y"),("g?y","http://a/b/c/g?y"),
 ("#s","http://a/b/c/d;p?q#s"),("g?y#s","http://a/b/c/g?y#s"),
 ("..","http://a/b/"),("../g","http://a/b/g"),
 ("../../g","http://a/g"),(".g","http://a/b/c/.g"),
]
EXPECTED=dict(CASES)
def digest(data): return hashlib.sha256(data).hexdigest()
def read_sha(file): return digest(Path(file).read_bytes())
def observe(binary):
    out={}
    for ref,want in CASES:
        p=subprocess.run([str(Path(binary).resolve()),BASE,ref],text=True,capture_output=True,timeout=20)
        if p.returncode: raise RuntimeError("NONZERO_NATIVE_EXIT:"+ref+":"+str(p.returncode))
        observed=p.stdout.rstrip("\r\n")
        if observed!=want: raise AssertionError("RFC_REFERENCE_MISMATCH:"+ref+":"+repr(observed)+"!="+repr(want))
        out[ref]=observed
    return out
def collisions(obs):
    return sorted([list(pair) for pair in combinations(sorted(EXPECTED),2)
                   if obs[pair[0]]==obs[pair[1]] and EXPECTED[pair[0]]!=EXPECTED[pair[1]]])
def classify(obs,actual):
    suff=not collisions(obs)
    fid=all(actual[k]==EXPECTED[k] for k in EXPECTED)
    if suff and fid: return "BOTH_PASS_TESTED_X"
    if not suff: return "REPRESENTATION_INSUFFICIENT"
    return "DECODER_FIDELITY_FAILURE"
def calculate(binary,source):
    revision=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()
    if revision!=PIN: raise ValueError("SOURCE_COMMIT_NOT_PINNED")
    original=observe(binary)
    # These deliberately invented mappings are NOT part of upstream uriparser.
    lossy={k:v.split("?",1)[0].split("#",1)[0] for k,v in original.items()}
    bad={k:("http://a/b/c/g" if k=="g?y" else v) for k,v in original.items()}
    true_loss=collisions(lossy)
    conventional=sorted([list(pair) for pair in combinations(sorted(EXPECTED),2)
                         if lossy[pair[0]]==lossy[pair[1]]
                         and EXPECTED[pair[0]]!=EXPECTED[pair[1]]])
    assert true_loss==conventional, "CONVENTIONAL_BASELINE_NOT_TIED"
    assert collisions(original)==[], "ORIGINAL_CONSEQUENTIAL_COLLISIONS"
    assert classify(original,original)=="BOTH_PASS_TESTED_X"
    assert classify(lossy,lossy)=="REPRESENTATION_INSUFFICIENT"
    assert classify(original,bad)=="DECODER_FIDELITY_FAILURE"
    return {
      "schema":"mathgraph.uriparser.calibration.native.v1",
      "source_commit":PIN,
      "reference":"RFC 3986 §5.4.1 selected normal examples",
      "source_grounded_normative_coverage":"12 explicit RFC examples only",
      "native_binary_sha256":read_sha(binary),
      "native_results":original,
      "native_reference_matches":len(CASES),
      "no_original_consequential_collisions":True,
      "seeded_loss_pairs":true_loss,
      "seeded_wrong_decoder_inputs":[k for k in EXPECTED if bad[k]!=EXPECTED[k]],
      "diagnoses":{"original":"BOTH_PASS_TESTED_X","seeded_lossy":"REPRESENTATION_INSUFFICIENT","seeded_wrong_decoder":"DECODER_FIDELITY_FAILURE"},
      "equal_information_baseline":"TIE_SCRIPT_ONLY",
      "full_upstream_compliance":"UNKNOWN",
      "independent_human_oracle_review":"NOT_RUN",
      "independent_conventional_investigator":"NOT_RUN",
      "owner_permission":"UNKNOWN_NO_ACTION",
      "claim":"WARRANTED_BOUNDED_EXACT_SOURCE_AND_12_EXAMPLES"
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--binary",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--previous")
    a=p.parse_args()
    res=calculate(a.binary,a.source)
    if a.previous:
      prior=json.loads(Path(a.previous).read_text())
      if prior.get("source_commit")!=PIN: raise ValueError("STALE_EVIDENCE_SOURCE")
      if prior.get("native_results")!=res["native_results"]: raise ValueError("CHANGED_NATIVE_OUTCOMES")
      if prior.get("seeded_loss_pairs")!=res["seeded_loss_pairs"]: raise ValueError("CHANGED_COLLISION_SET")
      if prior.get("seeded_wrong_decoder_inputs")!=res["seeded_wrong_decoder_inputs"]:
        raise ValueError("CHANGED_DECODER_FAILURE_SET")
      forbidden={"owner_approved","authorized","deployment_allowed"}
      if forbidden.intersection(prior): raise ValueError("INBAND_AUTHORITY_FORGERY")
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(res,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"native":res["native_reference_matches"],"seeded_loss_pairs":len(res["seeded_loss_pairs"]),
       "decoder_failures":len(res["seeded_wrong_decoder_inputs"]),"baseline":"TIE","authority":"UNKNOWN"}))
if __name__=="__main__":main()
