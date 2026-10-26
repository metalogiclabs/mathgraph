#!/usr/bin/env python3
"""Independent synthetic tests of native receipt verifier: no held-out sources."""
from __future__ import annotations
import importlib.util
import itertools
import json
from pathlib import Path
import random
import sys
import xml.etree.ElementTree as ET

file = Path(__file__).with_name("native_receipt_v4.py")
spec = importlib.util.spec_from_file_location("native_receipt_v4", file)
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
SHA = "a" * 40
ARGV = ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def xml(ids, *, failures=0, errors=0, skips=0, declared=None, nested=False):
    suite = ET.Element("testsuite", tests=str(len(ids) if declared is None else declared),
                       failures=str(failures), errors=str(errors), skipped=str(skips))
    for i, ident in enumerate(ids):
        case = ET.SubElement(suite, "testcase", file=ident[0], classname=ident[1], name=ident[2])
        if i < failures:
            ET.SubElement(case, "failure", message="failed")
        elif i < failures + errors:
            ET.SubElement(case, "error", message="error")
        elif i < failures + errors + skips:
            ET.SubElement(case, "skipped", message="skipped")
    if nested:
        root = ET.Element("testsuites")
        root.append(suite)
    else:
        root = suite
    return ET.tostring(root)


def judge(raw, status="WARRANTED_BOUNDED_EXECUTED_CASE_IDS"):
    got = v.read_native_receipt(raw, original_sha=SHA, git_head=SHA, argv=ARGV,
                                exit_code=0, original_case_scope="SYNTHETIC_FIXTURE_ONLY")
    assert got["status"] == status, (got["status"], status)
    return got


def refuse(raw, error):
    try:
        v.exact_case_ids(raw)
    except v.EvidenceObstruction as e:
        assert str(e) == error, (str(e), error)
        return
    raise AssertionError(("incorrectly accepted", error))


def independent_minimal(alternatives, live):
    """Different oracle: exhaust all subsets of active tokens and compare relations."""
    from itertools import combinations
    alternatives = [set(a) for a in alternatives]
    viable = [x for x in alternatives if x <= live]
    result = []
    for a in viable:
        if not any(b < a for b in viable):
            if sorted(a) not in result:
                result.append(sorted(a))
    return sorted(result, key=lambda x: (len(x), x))


def main():
    ids = [("tests/test_scope.py", "tests.test_scope", "test_a"),
           ("tests/test_scope.py", "tests.test_scope", "test_b")]
    cases = {}
    record = judge(xml(ids, nested=True))
    assert len(record["evidence"]["case_ids"]) == 2
    cases["valid_nested_junit"] = "PASS"
    assert judge(xml(ids, failures=1), "UNKNOWN_NATIVE_FAILURE")
    cases["original_failed_test_refuses_success"] = "PASS"
    assert judge(xml(ids, skips=1), "UNKNOWN_PARTIAL_EXECUTED_SCOPE")
    cases["skipped_case_not_complete"] = "PASS"
    refuse(xml(ids, declared=3), "UNKNOWN_TEST_IDENTITY_OR_COUNT")
    cases["wrong_reported_count_refused"] = "PASS"
    refuse(xml(ids + [ids[0]]), "UNKNOWN_TEST_IDENTITY_OR_COUNT")
    cases["duplicate_case_refused"] = "PASS"
    refuse(b"not xml", "UNKNOWN_INVALID_JUNIT")
    cases["invalid_xml_refused"] = "PASS"
    refuse(xml([("x", "", "foo")]), "UNKNOWN_TEST_IDENTITY")
    cases["missing_case_identity_refused"] = "PASS"
    assert judge(xml(ids, nested=False))
    cases["plain_testsuite_supported"] = "PASS"
    try:
        v.read_native_receipt(xml(ids), original_sha=SHA, git_head="b" * 40,
                              argv=ARGV, exit_code=0,
                              original_case_scope="SYNTHETIC")
    except v.EvidenceObstruction as e:
        assert str(e) == "UNKNOWN_SOURCE_COMMIT_MISMATCH"
    else:
        raise AssertionError("source mismatch accepted")
    cases["source_mismatch_refused"] = "PASS"
    try:
        v.read_native_receipt(xml(ids), original_sha=SHA, git_head=SHA,
                              argv=["python", "-c", "print('hi')"], exit_code=0,
                              original_case_scope="SYNTHETIC")
    except v.EvidenceObstruction as e:
        assert str(e) == "UNKNOWN_UNSUPPORTED_NATIVE_COMMAND"
    else:
        raise AssertionError("arbitrary command accepted")
    cases["unsupported_command_refused"] = "PASS"
    r1, r2 = judge(xml(ids)), judge(xml(list(reversed(ids))))
    assert v.compare_equally_informed(r1, r2) == "TIE_EXACT_EXECUTED_CASE_IDENTITIES"
    r3 = judge(xml(ids[:1]))
    assert v.compare_equally_informed(r1, r3) == "DIFFERENT_SCOPE_NO_SUPERIORITY_PROOF"
    assert v.compare_equally_informed(r1, None) == "UNKNOWN_MISSING_COMPARATOR"
    cases["comparison_limits"] = "PASS"

    statements = {"shared": [["src", "runner", "doc1"], ["src", "runner", "doc2"]],
                  "only_doc1": [["src", "runner", "doc1"]],
                  "independent": [["independent"]]}
    before = v.claims_at_snapshot(statements, {"src", "runner", "doc1", "doc2", "independent"})
    after = v.claims_at_snapshot(statements, {"src", "runner", "doc2", "independent"})
    assert before["shared"]["active"] and after["shared"]["active"]
    assert before["only_doc1"]["active"] and not after["only_doc1"]["active"]
    assert after["independent"]["active"]
    assert statements["only_doc1"] == [["src", "runner", "doc1"]]
    cases["selective_withdrawal_alternatives_and_immutable_history"] = "PASS"
    rng = random.Random(20261026)
    for _ in range(512):
        tokens = ["t%d" % i for i in range(6)]
        live = set(x for x in tokens if rng.randrange(2))
        alternatives = [list(x for x in tokens if rng.randrange(2))
                        for j in range(8)]
        got = v.minimal_supports(alternatives, live)
        expected = independent_minimal(alternatives, live)
        assert got == expected, (got, expected)
    cases["independent_support_oracle"] = "PASS"
    print(json.dumps({
        "status": "PASS_F1_V4_NATIVE_RECEIPT_SOURCE_FREE",
        "named_tests": len(cases),
        "independent_support_oracle_trials": 512,
        "source_kind": "SYNTHETIC_ONLY",
        "previously_unseen_source_exposure": "NONE",
        "competent_human_baseline": "NOT_TESTED",
        "new_sensor_type": "UNKNOWN",
        "cases": cases,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
