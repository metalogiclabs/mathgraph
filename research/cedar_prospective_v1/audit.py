"""Prospective Cedar V1: fail-closed source-author original integration receipt audit.

The independent meaning authority is a previously unopened, author-maintained
fixture; original Rust and Lean FFI test harnesses separately consume it.
This module does not manufacture semantic requirements or prove all equivalence.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph, compare_snapshots

E = Path(sys.argv[1]).resolve()
def read(name):
    return (E / name).read_text()
def digest(name):
    return hashlib.sha256((E / name).read_bytes()).hexdigest()
def require(p,why):
    if not p:
        raise AssertionError(why)

pins=json.loads(read("pins.json"))
require(pins["cedar_spec"]=="7893e685a91a6a391d609fd9940a1c13dcdf2472", "SPEC_PIN_MISMATCH")
require(pins["cedar_rust"]=="34db4c67641172b98e876ce79ef41277e29af433", "RUST_PIN_MISMATCH")
require(pins["author_corpus"]=="b157547fb8856911b293b7214768922c731878de","CORPUS_PIN_MISMATCH")
case=json.loads(read("first_fixture.json"))
require(case["relative_path"]=="tests/decimal/1.json","NOT_FIRST_REGISTERED_FIXTURE")
require(case["expected_decisions"]==["allow","deny"],"UNEXPECTED_EXPECTED_DECISIONS")
require(case["count"]==2,"NOT_TWO_PREDECLARED_REQUESTS")
require(case["fixture_sha256"]==read("fixture.sha256").split()[0],"CORPUS_FIXTURE_DIGEST_MISMATCH")
require("leanprover/lean4:v4.34.1" in read("lean_version.txt"),"LEAN_TOOLCHAIN_NOT_PINNED")

for name,label in (("rust_first.log","RUST"),("lean_integration.log","LEAN")):
    log=read(name)
    require("test result: ok." in log, label+"_NATIVE_TEST_NOT_GREEN")
    require("tests/decimal/1.json" in log, label+"_FIRST_FIXTURE_NOT_EXECUTED")
require("test result: ok." in read("rust_unrelated.log"),"RUST_UNRELATED_CONTROL_NOT_GREEN")

# This experiment records original-author test acceptance against two signed
# expected decisions, but does not get raw per-request native traces or independently
# reexecute the author's test assertion logic. The receipt authenticity boundary
# is the checked-out pinned source + original native test process.
scope="cedar-prospective-author-fixture-decimal1-two-requests-v1"
names=(
 "cedar.source_author_expected_allow_deny",
 "cedar.rust_original_fixture_test_passes",
 "cedar.lean_original_fixture_test_passes",
 "cedar.both_match_declared_outcomes",
 "cedar.unrelated_rust_test_passes",
 "cedar.universal_rust_lean_equivalence",
)
claims=[Claim(n,"documentary",scope) for n in names]
receipts=[Receipt(x,"documentary",scope) for x in (
    "fixture_authority","rust_native_suite","lean_native_suite","shared_case_verification","unrelated_rust_test",
)]
routes=[
    Route("cedar.source_author_expected_allow_deny",("fixture_authority",)),
    Route("cedar.rust_original_fixture_test_passes",("rust_native_suite",)),
    Route("cedar.lean_original_fixture_test_passes",("lean_native_suite",)),
    Route("cedar.both_match_declared_outcomes",("shared_case_verification",),
          ("cedar.source_author_expected_allow_deny",
           "cedar.rust_original_fixture_test_passes",
           "cedar.lean_original_fixture_test_passes")),
    Route("cedar.unrelated_rust_test_passes",("unrelated_rust_test",)),
]
def reclose(withdrawn=frozenset()):
    return dict(resolve_graph(claims,routes,receipts,withdrawn=withdrawn).states)
before=reclose()
require(before["cedar.both_match_declared_outcomes"]=="SOURCE_DOCUMENTED","NOT_NATIVE_ADMITTED")
require(before["cedar.universal_rust_lean_equivalence"]=="UNKNOWN","ILLICIT_UNIVERSAL_PROMOTION")
interventions={}
for title,receipt,lost_expected in (
    ("withdraw_author_fixture","fixture_authority",
     {"cedar.source_author_expected_allow_deny","cedar.both_match_declared_outcomes"}),
    ("withdraw_rust_test","rust_native_suite",
     {"cedar.rust_original_fixture_test_passes","cedar.both_match_declared_outcomes"}),
    ("withdraw_lean_test","lean_native_suite",
     {"cedar.lean_original_fixture_test_passes","cedar.both_match_declared_outcomes"}),
    ("withdraw_shared_comparison","shared_case_verification",
     {"cedar.both_match_declared_outcomes"}),
):
    after=reclose(frozenset([receipt]))
    lost={k for k in before if before[k]!="UNKNOWN" and after[k]=="UNKNOWN"}
    require(lost==lost_expected,"WRONG_DEPENDENT_LOSS_"+title)
    require(after["cedar.unrelated_rust_test_passes"]=="SOURCE_DOCUMENTED","UNRELATED_CONTROL_LOST")
    require(after["cedar.universal_rust_lean_equivalence"]=="UNKNOWN","ILLICIT_WARRANT_"+title)
    require(reclose()==before,"FAILED_TO_RESTORE_"+title)
    interventions[title]={"receipt":receipt,"lost_only":sorted(lost),
                           "restored":True,"comparison":compare_snapshots(before,after)}

baseline={
 "input":case["expected_decisions"],
 "comparator":"independent explicit author-decision equality rule on same two receipts",
 "result":"TIE_BY_TEST_SUITE_ASSERTIONS",
 "is_human_expert":False,
 "method_superiority":"UNKNOWN_NOT_DEMONSTRATED",
}
report={
 "schema":"mathgraph.cedar-prospective-author-corpus.v1",
 "status":"WARRANTED_BOUNDED_NATIVE_SOURCE_DISTINCT_AUTHOR_CORPUS",
 "source":pins,
 "fixture":case,
 "native_rust": "EXACT_ORIGINAL_AUTHOR_TESTS_PASS",
 "native_lean": "EXACT_ORIGINAL_AUTHOR_FFI_TESTS_PASS",
 "case_correspondence":"TWO_EXPECTED_AUTHORIZATION_DECISIONS_SHARED_SOURCE_TESTS",
 "raw_native_request_outputs":"NOT_EMITTED_BY_ORIGINAL_HARNESS",
 "universal_fidelity":"UNKNOWN",
 "method_discovery":"UNKNOWN_HUMAN_FROZEN",
 "human_comparator_advantage":"UNKNOWN_NO_HUMAN_TESTED",
 "baseline":baseline,
 "claims":before,
 "withdrawal":interventions,
 "sha256":{n:digest(n) for n in
    ("first_fixture.json","rust_first.log","rust_unrelated.log","lean_integration.log",
     "fixture.sha256","pins.json","lean_version.txt")},
 "boundaries":[
    "Third code source had no source inspection before method freeze",
    "Author test suite validates each implementation against common predeclared expectations",
    "FFI uses Rust parser/serialization; independent parsers not certified",
    "No independent human author-intent measurement",
    "No universal semantic-preservation claim from two fixture requests",
    "No new autonomous observer invention",
    "Withdrawal removes typed logical receipts, not upstream source bytes",
    "MathGraph resolver trusts externally admitted artifact references",
 ],
}
(E/"RESULT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":report["status"],"fixture":case["relative_path"],
"expected":case["expected_decisions"],"native_rust":"PASS",
"native_lean":"PASS","withdrawals":{k:v["lost_only"] for k,v in interventions.items()},
"universal":"UNKNOWN","baseline":"SAME_INPUT_PROXY_TIE"},indent=2,sort_keys=True))
