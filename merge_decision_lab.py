"""Source-native, evidence-seeking three-way merge review.

OFFLINE: Source-pinned native test replay on constructed mutants. It neither
calls Nebius nor merges code, and grants no general software correctness.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from upstream_encoding_transfer import (
    ENCODING_PATH, EXPANDED_COMMAND, NATIVE_COMMAND, MUTANTS, UPSTREAM_COMMIT,
    acquired_tests, call_native_code, copy_package, digest, domain, execute,
    independent_minimum_bound, minimum_separator, mutate, oracle, pinned_source,
    qualify,
)

CASES = (
    ("defective_green_tests", "standard_alphabet", (1,2,3)),
    ("correct_but_initially_unknown", "reference", (1,2,3)),
    ("correct_but_observation_forbidden", "reference", (3,)),
)

def _truth_table(checkout: Path, root: Path, source: bytes):
    inputs=domain()
    observations={}
    for name in ("reference",)+tuple(sorted(MUTANTS)):
        folder=root/("model_"+name)
        folder.mkdir()
        candidate=source if name=="reference" else mutate(source,name)
        copy_package(checkout,folder,candidate)
        observations[name]=call_native_code(folder,inputs)
    if observations["reference"] != [oracle(x) for x in inputs]:
        raise AssertionError("PINNED_REFERENCE_ORACLE_DISAGREEMENT")
    return inputs,observations

def _select(inputs, observations, lengths):
    positions=[i for i,value in enumerate(inputs) if len(value) in lengths]
    selected=tuple(inputs[i] for i in positions)
    projected={name:[values[i] for i in positions]
               for name,values in observations.items()}
    basis=minimum_separator(selected,projected)
    checked=independent_minimum_bound(basis["cover_records"])
    if basis["status"]=="MINIMUM_BASIS":
        if checked != basis["total_synthetic_cost"]:
            raise AssertionError("MINIMUM_NOT_INDEPENDENTLY_CHECKED")
    elif basis["status"]=="OBSTRUCTION":
        if checked is not None:
            raise AssertionError("FALSE_OBSTRUCTION")
    else:
        raise AssertionError("INVALID_FINITE_VERDICT")
    return {"status":basis["status"],"permitted_lengths":list(lengths),
            "eligible_input_count":len(selected),
            "tests_hex":basis["tests_hex"],
            "synthetic_cost":basis["total_synthetic_cost"],
            "independent_minimum_cost":checked,
            "unsplittable":basis["unsplittable"]}

def _candidate(checkout: Path, root: Path, source: bytes, original_sha: str,
               case_id: str, candidate_name: str, plan: dict):
    work=root/("review_"+case_id)
    work.mkdir()
    candidate=source if candidate_name=="reference" else mutate(source,candidate_name)
    copy_package(checkout,work,candidate)
    receipt0=execute(work,original_sha,NATIVE_COMMAND)
    native, _=qualify(work,receipt0,original_sha,NATIVE_COMMAND)
    if native!="WARRANTED":
        raise AssertionError("NATIVE_BASELINE_NOT_GREEN:"+case_id)
    steps=[
        {"step":"original_native_tests","state":"WARRANTED_BOUNDED",
         "scope":"ONLY original test suite","receipt":asdict(receipt0)},
        {"step":"protected_target_not_yet_distinguished","state":"UNKNOWN",
         "reason":"Existing passing tests admit competing semantics"},
    ]
    result={"scenario":case_id,
            "candidate_origin":"PINNED_REFERENCE" if candidate_name=="reference"
                else "DELIBERATE_INJECTED_FAULT",
            "candidate_sha256":digest(candidate),
            "fixed_suite_baseline":"WARRANTED_ONLY_FOR_EXISTING_TESTS",
            "target_initially":"UNKNOWN","selector":plan}
    if plan["status"]=="OBSTRUCTION":
        if not plan["unsplittable"]:
            raise AssertionError("UNNAMED_OBSTRUCTION")
        steps.append({"step":"permitted_observation_obstruction",
                      "state":"UNKNOWN",
                      "reason":"Cannot distinguish "+", ".join(plan["unsplittable"])
                               +" with permitted probes"})
        result.update({"final_state":"UNKNOWN","release_permission":"NONE",
                       "claim_scope":"target unidentifiable within admitted probe grammar",
                       "transitions":steps})
        return result

    witnesses=tuple(bytes.fromhex(x) for x in plan["tests_hex"])
    (work/"test_mathgraph_acquired.py").write_bytes(acquired_tests(witnesses))
    stale0, _=qualify(work,receipt0,original_sha,NATIVE_COMMAND)
    if stale0!="REJECTED":
        raise AssertionError("STALE_OLD_TEST_RECEIPT_ACCEPTED")
    steps.append({"step":"new_tests_withdraw_prior_receipt","state":"REJECTED"})
    receipt=execute(work,original_sha,EXPANDED_COMMAND)
    verdict,why=qualify(work,receipt,original_sha,EXPANDED_COMMAND)
    if verdict not in ("WARRANTED","REJECTED"):
        raise AssertionError("INCOMPLETE_NATIVE_REPLAY")
    final="WARRANTED_BOUNDED" if verdict=="WARRANTED" else "REJECTED"
    result.update({"final_state":final,
                   "release_permission":"REVIEW_ONLY_BOUNDED" if verdict=="WARRANTED" else "NONE",
                   "claim_scope":"only exact current source and declared original+acquired native tests",
                   "expanded_receipt":asdict(receipt)})
    steps.append({"step":"acquired_tests_executed","state":final,
                  "reason":why,"receipt":asdict(receipt)})

    code=work/"src"/"itsdangerous"/"encoding.py"
    saved=code.read_bytes()
    code.write_bytes(saved+b"\n# post-test edit\n")
    invalid, _=qualify(work,receipt,original_sha,EXPANDED_COMMAND)
    if invalid!="REJECTED":
        raise AssertionError("SOURCE_CHANGE_RETAINED_AUTHORITY")
    steps.append({"step":"source_changed_after_testing","state":"REJECTED",
                  "reason":"Previously passing receipt no longer applies"})
    code.write_bytes(saved)
    fresh=execute(work,original_sha,EXPANDED_COMMAND)
    again, _=qualify(work,fresh,original_sha,EXPANDED_COMMAND)
    if again!=verdict:
        raise AssertionError("REACQUISITION_VERDICT_CHANGED")
    steps.append({"step":"fresh_native_receipt_acquired","state":final,
                  "receipt":asdict(fresh)})
    result.update({"final_receipt":asdict(fresh),"transitions":steps})
    return result

def experiment(checkout: Path) -> dict:
    pins=pinned_source(checkout)
    source=(checkout/ENCODING_PATH).read_bytes()
    source_hash=digest(source)
    with TemporaryDirectory(prefix="mathgraph-three-way-review-") as tmp:
        work=Path(tmp)
        inputs,observations=_truth_table(checkout,work,source)
        outcomes={}
        for case_id,choice,lengths in CASES:
            planned=_select(inputs,observations,lengths)
            outcomes[case_id]=_candidate(checkout,work,source,source_hash,
                                         case_id,choice,planned)
    expected={"defective_green_tests":"REJECTED",
              "correct_but_initially_unknown":"WARRANTED_BOUNDED",
              "correct_but_observation_forbidden":"UNKNOWN"}
    if {k:v["final_state"] for k,v in outcomes.items()}!=expected:
        raise AssertionError("THREE_WAY_TEST_FAILED")
    if outcomes["correct_but_observation_forbidden"]["selector"]["unsplittable"]!=["unstripped_padding"]:
        raise AssertionError("OBSTRUCTION_IS_NOT_NAMED")
    return {"schema":"mathgraph.evidence-seeking-merge-review.v1",
            "scope":"constructed encoding mutations with independently replayed native tests",
            "source":{"repository":"pallets/itsdangerous",
                      "commit":UPSTREAM_COMMIT,"encoding_sha256":source_hash,
                      "file_evidence":pins},
            "model_provenance":"OFFLINE_SCRIPTED_DECISIONS_NO_NEW_NEBIUS_CALL",
            "actions_performed":"READ_ONLY_SIMULATED_MERGE_REVIEW_NO_UPSTREAM_CHANGES",
            "hypotheses":["reference"]+sorted(MUTANTS),
            "domain_size":len(domain()),
            "cost":"synthetic unit = 1 + byte length",
            "cases":outcomes}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--report",type=Path,default=Path("merge-decision-report.json"))
    args=p.parse_args()
    report=experiment(args.upstream_checkout.resolve())
    args.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({name:{"outcome":v["final_state"],
                             "permission":v["release_permission"],
                             "price":v["selector"]["synthetic_cost"],
                             "obstruction":v["selector"]["unsplittable"]}
                      for name,v in report["cases"].items()},indent=2))

if __name__=="__main__":
    main()
