#!/usr/bin/env python3
"""Source-independent obligation receipt -> frozen MathGraph V1 warrant adapter.

This is a post-result, read-only evidence transport. It does not execute source
implementations, infer an unprovided semantic relation or modify the frozen core.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ORIGINAL_CORE_BLOB="2b50c382407cd3da07c95b4863b74947fb489920"
ORIGINAL_CORE_REV="e38e73287e82006795d629acbfb13bf7e1895d03"
METHOD_REV="0f5bf46ba92723f294fbdfcff42a4cc6fe7ad9b9"


def digest(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()


def payload(root:Path):
    meta=json.loads((root/"research/semantic_obligation_induction_v2/SELECTED_SOURCE.json").read_text())
    result=json.loads((root/"native-evidence/qualified-claims.json").read_text())
    assert meta["method_freeze_commit"]==METHOD_REV
    assert meta["source_sha"]==result["source_sha"]
    assert result["status"]=="PROSPECTIVE_EXECUTED_BOUNDED"
    assert result["native"]["passed"] is True
    assert result["native"]["errors"]==result["native"]["failures"]==0
    assert result["comparison"]["advantage"]==0
    assert result["candidate"]["obligations"]==result["expert"]["obligations"]
    actual={
        "metadata":meta,"qualified":result,
        "junit_digest":digest((root/"native-evidence/native-junit.xml").read_bytes()),
        "proposal_digest":digest((root/"native-evidence/candidate.json").read_bytes()),
    }
    assert actual["junit_digest"]==result["native_junit_sha256"]
    assert actual["proposal_digest"]==result["candidate_proposal_file_sha256"]
    return actual


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",required=True,type=Path)
    a.add_argument("--second",required=True,type=Path)
    a.add_argument("--qualified",required=True,type=Path)
    a.add_argument("--core",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    x=a.parse_args()

    core=x.core.resolve()
    assert subprocess.check_output(["git","hash-object",str(core)],text=True).strip()==ORIGINAL_CORE_BLOB
    assert subprocess.check_output(["git","-C",str(core.parents[2]),"rev-parse","HEAD"],text=True).strip()==ORIGINAL_CORE_REV
    sys.path.insert(0,str(core.parent))
    from protocol import Obligation,assess,judge

    qualified=json.loads(x.qualified.read_text())
    assert qualified["status"]=="WARRANTED_BOUNDED_PROSPECTIVE_SECOND_SOURCE_API_OBLIGATION_REUSE"
    actual={"tomliw":payload(x.first),"tomlkit":payload(x.second)}
    wanted={
        "tomliw":("hukkin/tomli-w","1210bb6f5708a4dc084cc3deb4a3a3e3939f4d6d"),
        "tomlkit":("python-poetry/tomlkit","eddd27e43a62fe58707c311bfad2f52e72493f53"),
    }
    expected_ids={
        "tomliw":["external-semantics"],
        "tomlkit":["external-semantics","native-roundtrip"],
    }
    required={
        "method":METHOD_REV,
        "fixtures":"V1_3_TYPED_MAPPING_FIXTURES@e70ca1625c5e0dc1b9ff7f31deee024e35f5ad0d",
        "external_oracle":"Python3.12:tomllib.loads:TOML",
    }
    items=[]
    for tag,data in actual.items():
        md=data["metadata"]
        out=data["qualified"]
        assert (md["repository"],md["source_sha"])==wanted[tag]
        assert out["source_sha"]==qualified["two_distinct_sources"][tag]["sha"]
        required[f"source:{tag}"]=md["source_sha"]
        required[f"native:{tag}"]=data["junit_digest"]
        required[f"proposal:{tag}"]=data["proposal_digest"]
        if tag=="tomlkit":
            required["native_reader:tomlkit"]="tomlkit.loads@"+md["source_sha"]
        observations=out["candidate"]["obligations"]
        assert [o["id"] for o in observations]==expected_ids[tag]
        for obs in observations:
            assert obs["verdict"] in ("WARRANTED_BOUNDED_INDEPENDENT",
                                     "WARRANTED_BOUNDED_NATIVE_CONSISTENCY")
            assert len(obs["observations"])==3
            assert all(o["same_typed_meaning"] is True
                       and o["false_claim_rejected"] is True for o in obs["observations"])
            claim=f"{tag}/{obs['id']}"
            dependencies=["method","fixtures",f"source:{tag}",f"native:{tag}",
                          f"proposal:{tag}"]
            if obs["id"]=="external-semantics":
                dependencies.append("external_oracle")
            else:
                dependencies.append(f"native_reader:{tag}")
            items.append(Obligation(
                name=claim,
                source=md["repository"]+"@"+md["source_sha"],
                relation="MATCH",authority="ASSERTED",
                dependencies=tuple(dependencies),
                qualifier="Only fixed three original typed mapping fixtures, explicitly supplied external/native relation",
            ))
    cases=tuple(items)
    baseline=assess(cases,required,required)
    assert baseline=={
        "tomliw/external-semantics":"SCOPED_AGREEMENT",
        "tomlkit/external-semantics":"SCOPED_AGREEMENT",
        "tomlkit/native-roundtrip":"SCOPED_AGREEMENT",
    }
    scenarios={
        "withdraw_source_tomliw":(["source:tomliw"],["tomliw/external-semantics"]),
        "withdraw_source_tomlkit":(["source:tomlkit"],
                                    ["tomlkit/external-semantics","tomlkit/native-roundtrip"]),
        "withdraw_native_tomlkit":(["native:tomlkit"],
                                    ["tomlkit/external-semantics","tomlkit/native-roundtrip"]),
        "withdraw_external_oracle":(["external_oracle"],
                                    ["tomliw/external-semantics","tomlkit/external-semantics"]),
        "withdraw_native_reader":(["native_reader:tomlkit"],["tomlkit/native-roundtrip"]),
        "withdraw_method":(["method"],sorted(baseline)),
        "withdraw_fixtures":(["fixtures"],sorted(baseline)),
    }
    outcomes={}
    for case,(withdraw,expected) in scenarios.items():
        new=dict(required)
        for key in withdraw:
            new[key]="WITHDRAWN"
        observed=assess(cases,new,required)
        changed=sorted(k for k,v in observed.items() if v!=baseline[k])
        assert changed==sorted(expected),(case,changed,expected)
        assert all(observed[k]=="UNKNOWN_WITHDRAWN_OR_CHANGED" for k in changed)
        assert all(observed[k]==baseline[k] for k in baseline if k not in changed)
        outcomes[case]={"withdrawn":withdraw,"dependent_warrants_lost":changed,"verdicts":observed}
    # An unidentified relationship is never promoted solely because prior
    # original source tests/receipt metadata happened to be green.
    unknown=Obligation(name="unsupported_future_obligation",
        source=wanted["tomliw"][0]+"@"+wanted["tomliw"][1],
        relation="UNSUPPORTED",authority="ASSERTED",dependencies=("method",),
        qualifier="No independently declared interpretation for this additional relation")
    assert judge(unknown,required,required)=="UNKNOWN_INTERPRETATION"
    assert assess(cases,required,required)==baseline  # genuine evidence replay, not label restoration
    evidence={
        "status":"WARRANTED_BOUNDED_SOURCE_INDEPENDENT_OBLIGATION_TO_WARRANT_TRANSPORT",
        "method":METHOD_REV,
        "unaltered_warrant_core_git_blob":ORIGINAL_CORE_BLOB,
        "post_result_authority_graph":True,
        "authentic_native_receipt_sources":[wanted["tomliw"][0],wanted["tomlkit"][0]],
        "original_verified_verdicts":baseline,
        "selective_withdrawal_tests":outcomes,
        "restored_only_by_previously_authenticated_source_native_receipts":True,
        "unsupported_relation":"UNKNOWN_INTERPRETATION",
        "scope":"Three finite TOML semantic claims, two sources, declared expert-authored dependency graph",
        "unproven":["physical source mutation in these libraries",
                    "autonomous dependency discovery","universal correspondence or semantics",
                    "human reviewer/agent advantage"],
    }
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("AUTO_PROPOSED_OBLIGATIONS_IN_UNCHANGED_WARRANT_CORE_PASS")
    print("TARGETED_AUTHORITY_WITHDRAWAL_SCENARIOS_PASS",len(scenarios))
    print(json.dumps({k:v["dependent_warrants_lost"] for k,v in outcomes.items()},sort_keys=True))


if __name__=="__main__":
    main()
