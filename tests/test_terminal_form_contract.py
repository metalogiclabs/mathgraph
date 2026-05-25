from mathgraph.invariants import check_terminal_form_contract
from mathgraph.terminal_form_contract import (
    TerminalForm,
    audit_terminal_rows,
    boundary_preserved,
    can_promote_false,
    can_promote_true,
    decision_as_dict,
    decide_terminal_form,
)


def test_accepted_claim_requires_exactly_one_terminal_form():
    assert check_terminal_form_contract({"status": "ACCEPTED", "terminal_form": "FINITE_COUNTERMODEL"}).ok
    assert not check_terminal_form_contract({"status": "ACCEPTED"}).ok
    assert not check_terminal_form_contract({"status": "ACCEPTED", "terminal_forms": ["VERIFIED_PROOF", "FINITE_COUNTERMODEL"]}).ok


def test_invalid_terminal_form_rejected():
    report = check_terminal_form_contract({"status": "ACCEPTED", "terminal_form": "TRUE"})
    assert not report.ok
    assert report.violations[0].code == "invalid_terminal_form"


def test_finite_countermodel_can_promote_false_terminal():
    decision = decide_terminal_form({"status": "finite_countermodel_found", "eq1_holds": True, "eq2_violated": True})
    assert decision.accepted
    assert decision.terminal_form == TerminalForm.FINITE_COUNTERMODEL
    assert decision.can_promote_truth


def test_finite_countermodel_requires_checker_backed_validity():
    assert not can_promote_false({"status": "finite_countermodel_found"})
    assert not decide_terminal_form({"status": "finite_countermodel_found"}).accepted
    assert can_promote_false({"certificate_status": "finite_countermodel_verified", "finite_checker_valid": True})


def test_failed_search_is_residual_not_true():
    decision = decide_terminal_form({"status": "failed_search", "finite_search_miss": True})
    assert not decision.accepted
    assert decision.terminal_form == TerminalForm.NONE
    assert not decision.can_promote_truth


def test_proof_verified_evidence_promotes_true():
    assert can_promote_true({"proof_verified": True})
    decision = decide_terminal_form({"proof_verified": True})
    assert decision.accepted
    assert decision.terminal_form == TerminalForm.VERIFIED_PROOF
    assert not decision.advisory_only


def test_boundary_preserved_for_advisory_rows():
    assert boundary_preserved([{"status": "named_obstruction_advisory", "obstruction_name": "x"}, {"status": "failed_search"}])


def test_named_obstruction_is_advisory_and_bad_advisory_truth_is_rejected():
    decision = decide_terminal_form({"status": "named_obstruction_advisory", "obstruction_name": "x"})
    assert decision.terminal_form == TerminalForm.NAMED_OBSTRUCTION
    assert decision.advisory_only
    assert not decision.can_promote_truth
    assert not boundary_preserved([{"advisory_only": True, "can_promote_truth": True, "terminal_form": "VERIFIED_PROOF"}])


def test_decision_dict_and_audit_helpers():
    row = {"lean_verified": True}
    assert decision_as_dict(row)["terminal_form"] == "VERIFIED_PROOF"
    assert audit_terminal_rows([row])[0]["accepted"] is True
