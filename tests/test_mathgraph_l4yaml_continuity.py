"""Behavioral source continuity is distinct from proof, documentary identity and permission."""

from copy import deepcopy

import pytest

from mathgraph_check.l4yaml_continuity import (
    CONTROL_CASES, CYCLE_CASES, DEFECT_CASES, REFUSAL_CASES,
    EMPTY_SHA256, project_qualified_receipt,
)


PIN = "82cdb78e8909f25d9079d9bb05ed7c6f508ee95c"
NEW = "f" * 40


def receipt(*, defects=5, commit=PIN):
    # A qualified fixture models a prior external verifier invocation; direct
    # invocation of this projection is NOT an authentication mechanism.
    category = ("BOUNDED_DEFECT_REPRODUCED" if defects == 5
                else "BOUNDED_FIX_OBSERVED" if defects == 0
                else "BOUNDED_PARTIAL_DEFECT")
    return {
        "status": category,
        "errors": [],
        "source": {
            "repository": "https://github.com/nasa-jpl/L4YAML",
            "commit": commit,
            "tracked_checkout_clean": True,
            "toolchain": "leanprover/lean4:v4.35.0",
            "lean_version": "Lean (version 4.35.0, x86_64-unknown-linux-gnu)",
            "source_files": {"L4YAML/Spec/Types.lean": {"sha256": "a" * 64, "git_blob": "b" * 40}},
        },
        "counts": {
            "native_rows": 13,
            "acyclic_cases": 10,
            "defects_reproduced_both_pipelines": defects,
            "acyclic_controls_passed_both_pipelines": 5,
            "cycle_policy_observations": 2,
            "undefined_alias_controls_refused": 1,
        },
        "artifact_sha256": {
            "Probe.lean": "c" * 64, "analyze.py": "d" * 64,
            "oracle_results.json": "e" * 64,
            "native_latest.jsonl": "1" * 64, "native_latest.stderr": EMPTY_SHA256,
        },
        "defect_cases": sorted(DEFECT_CASES)[:defects],
        "control_cases": sorted(CONTROL_CASES),
        "cases": ([
            {"case": name, "agrees": i >= defects, "category": "defect"}
            for i, name in enumerate(sorted(DEFECT_CASES))
        ] + [
            {"case": name, "agrees": True, "category": "control"}
            for name in sorted(CONTROL_CASES)
        ] + [
            {"case": name, "category": "cycle_policy"} for name in sorted(CYCLE_CASES)
        ] + [
            {"case": name, "category": "refusal"} for name in sorted(REFUSAL_CASES)
        ]),
    }


def test_current_source_reports_bounded_nonconformance_not_proof_or_permission():
    result = project_qualified_receipt(receipt(), expected_head=PIN, current_head=PIN)
    assert result["status"] == "BOUNDED_NONCONFORMANCE_OBSERVED"
    assert result["claims"] == {
        "source_identity": "SOURCE_DOCUMENTED",
        "native_controls": "WARRANTED_BOUNDED",
        "bounded_nonconformance": "WARRANTED_BOUNDED",
        "bounded_repair": "UNKNOWN",
    }
    assert result["mathematical_terminal_form"] is None
    assert result["decision_authority"] == "NOT_AUTHORIZED"
    assert result["source"]["commit"] == PIN
    assert result["evidence"]["raw_native_sha256"] == "1" * 64


def test_oracle_withdrawal_selectively_disables_interpretation():
    after = project_qualified_receipt(receipt(), expected_head=PIN, current_head=PIN,
                                      withdrawn=frozenset({"oracle"}))
    assert after["claims"]["bounded_nonconformance"] == "UNKNOWN"
    assert after["claims"]["native_controls"] == "WARRANTED_BOUNDED"
    assert after["claims"]["source_identity"] == "SOURCE_DOCUMENTED"
    assert after["status"] == "UNKNOWN"
    assert after["changes"]["bounded_nonconformance"]["after"] == "STALE"


@pytest.mark.parametrize("removed", ["native", "verifier", "source"])
def test_withdrawal_of_required_native_authority_is_fail_closed(removed):
    after = project_qualified_receipt(receipt(), expected_head=PIN, current_head=PIN,
                                      withdrawn=frozenset({removed}))
    assert after["status"] == "UNKNOWN"
    assert after["claims"]["bounded_nonconformance"] == "UNKNOWN"
    if removed == "source":
        assert after["claims"]["source_identity"] == "UNKNOWN"


def test_source_update_forces_replay_even_if_old_cases_were_successful():
    after = project_qualified_receipt(receipt(), expected_head=PIN, current_head=NEW)
    assert after["status"] == "UNKNOWN"
    assert all(value == "UNKNOWN" for value in after["claims"].values())
    assert after["changes"]["bounded_nonconformance"]["after"] == "STALE"
    assert after["source"]["commit"] == PIN
    assert after["source"]["current_head"] == NEW


def test_repair_on_new_pin_must_have_new_qualified_native_receipt():
    repaired = project_qualified_receipt(receipt(defects=0, commit=NEW), expected_head=NEW,
                                         current_head=NEW)
    assert repaired["status"] == "BOUNDED_REPAIR_OBSERVED"
    assert repaired["claims"]["bounded_repair"] == "WARRANTED_BOUNDED"
    assert repaired["claims"]["bounded_nonconformance"] == "UNKNOWN"
    assert repaired["decision_authority"] == "NOT_AUTHORIZED"
    assert project_qualified_receipt(receipt(), expected_head=PIN,
                                     current_head=NEW)["status"] == "UNKNOWN"


@pytest.mark.parametrize("mutate", [
    lambda x: x.update(status="BOUNDED_FIX_OBSERVED"),
    lambda x: x.update(errors=["native process failed"]),
    lambda x: x["counts"].update(native_rows=12),
    lambda x: x["counts"].update(cycle_policy_observations=0),
    lambda x: x["artifact_sha256"].update({"native_latest.jsonl": "junk"}),
    lambda x: x["source"].update(tracked_checkout_clean=False),
    lambda x: x["source"].update(toolchain="leanprover/lean4:v4.34.0"),
    lambda x: x["source"].update(repository="untrusted-source"),
])
def test_malformed_or_contradictory_qualification_rejected(mutate):
    bad = deepcopy(receipt())
    mutate(bad)
    with pytest.raises(ValueError):
        project_qualified_receipt(bad, expected_head=PIN, current_head=PIN)


def test_pin_mismatch_refuses_a_forged_authority_scope():
    with pytest.raises(ValueError, match="RECEIPT_SOURCE_MISMATCH"):
        project_qualified_receipt(receipt(commit=NEW), expected_head=PIN, current_head=PIN)


def test_arbitrary_or_unknown_withdrawal_rejected():
    with pytest.raises(ValueError, match="UNKNOWN_WITHDRAWAL_TARGET"):
        project_qualified_receipt(receipt(), expected_head=PIN, current_head=PIN,
                                  withdrawn=frozenset({"outside"}))
