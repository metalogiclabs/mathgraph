"""Frozen contract for independently checked Crystal admission.

This suite is committed before the implementation. ATP statuses are untrusted.
"""
from dataclasses import replace
import importlib
import importlib.util

import pytest

from mathgraph.atp_tptp import ATPCandidateEvidence, FirstOrderResidual
from mathgraph.protected_future import ContinuationStatus as S, ProtectedContinuation as Edge, ProtectedContinuationMachine as Machine
from mathgraph.query_gateway import CrystalQuestion, query_crystal


def problem(goal="mortal(socrates)"):
    return FirstOrderResidual("socrates", (("rule", "! [X] : (human(X) => mortal(X))"), ("fact", "human(socrates)")), goal, boundary_ref="admission:horn-v1")


def candidate(p, status="Theorem"):
    return ATPCandidateEvidence("vampire", p.problem_id, p.id, p.tptp_sha256, status,
        "CANDIDATE_WARRANTED" if status == "Theorem" else "CANDIDATE_EXCLUDED",
        0, 0.0, ("unit-test-candidate",), (), "% SZS status " + status, "")


@pytest.fixture
def api():
    name = "mathgraph.crystal_admission"
    assert importlib.util.find_spec(name) is not None, "independent admission is not implemented"
    return importlib.import_module(name)


@pytest.fixture
def certs():
    name = "mathgraph.fol_horn_certificate"
    assert importlib.util.find_spec(name) is not None, "independent certificate checker is not implemented"
    return importlib.import_module(name)


def initial(api, p):
    q = api.bind_question(p)
    return Machine(p.boundary_ref, (q.source,), (Edge(q.source, q.continuation, q.outcome, S.UNKNOWN),)), q


def test_independent_proof_and_same_question_replay(api, certs):
    p = problem(); m, q = initial(api, p)
    certificate = certs.build_certificate(p)
    assert certs.check_certificate(p, certificate) == "WARRANTED"
    assert query_crystal(m, q).status is S.UNKNOWN
    result = api.admit_candidate(m, q, p, candidate(p), certificate)
    assert result.accepted and result.receipt["terminal_form"] == "VERIFIED_PROOF"
    assert query_crystal(result.machine, q).status is S.WARRANTED
    assert query_crystal(m, q).status is S.UNKNOWN  # immutable previous state
    assert result.receipt["checker_id"] != "vampire"


def test_independent_countermodel_excludes_entailment(api, certs):
    p = problem("wise(socrates)"); m, q = initial(api, p)
    certificate = certs.build_certificate(p)
    assert certs.check_certificate(p, certificate) == "EXCLUDED"
    result = api.admit_candidate(m, q, p, candidate(p, "CounterSatisfiable"), certificate)
    assert result.accepted and result.receipt["terminal_form"] == "FINITE_COUNTERMODEL"
    assert query_crystal(result.machine, q).status is S.EXCLUDED


def test_cached_question_never_calls_engine_or_checker_again(api):
    p = problem(); m, q = initial(api, p); calls = []
    def engine(residual):
        calls.append(residual.id)
        return candidate(residual)
    first = api.resolve_question(m, q, p, engine=engine)
    assert first.answer.status is S.WARRANTED and len(calls) == 1
    def forbidden(*args, **kwargs):
        raise AssertionError("warm query must not search or check again")
    second = api.resolve_question(first.machine, q, p, engine=forbidden, certificate_builder=forbidden)
    assert second.answer.status is S.WARRANTED
    assert second.answer.to_dict() == first.answer.to_dict()
    assert not second.engine_called and not second.checker_called


def test_wrong_problem_candidate_is_rejected(api, certs):
    p = problem(); m, q = initial(api, p)
    other = replace(p, conjecture="wise(socrates)")
    r = api.admit_candidate(m, q, p, candidate(other), certs.build_certificate(p))
    assert not r.accepted and r.machine == m


def test_changed_query_binding_is_rejected(api, certs):
    p = problem(); m, q = initial(api, p)
    q = replace(q, source="another-claim")
    r = api.admit_candidate(m, q, p, candidate(p), certs.build_certificate(p))
    assert not r.accepted and r.machine == m


def test_changed_boundary_is_rejected(api, certs):
    p = problem(); m, q = initial(api, p)
    m = replace(m, boundary_ref="different-foundation")
    r = api.admit_candidate(m, q, p, candidate(p), certs.build_certificate(p))
    assert not r.accepted and r.machine == m


def test_forged_szs_theorem_cannot_admit_false_entailment(api, certs):
    p = problem("wise(socrates)"); m, q = initial(api, p)
    r = api.admit_candidate(m, q, p, candidate(p, "Theorem"), certs.build_certificate(p))
    assert not r.accepted and r.reason == "solver_checker_disagreement" and r.machine == m


def test_mutated_certificate_is_not_authority(api, certs):
    p = problem(); m, q = initial(api, p)
    certificate = certs.build_certificate(p)
    certificate["problem_digest"] = "0" * 64
    r = api.admit_candidate(m, q, p, candidate(p), certificate)
    assert not r.accepted and r.machine == m


def test_proof_step_tampering_is_rejected(certs):
    p = problem(); certificate = certs.build_certificate(p)
    certificate["steps"][-1]["substitution"] = {"X": "plato"}
    with pytest.raises(certs.CertificateError):
        certs.check_certificate(p, certificate)


def test_model_violating_axiom_is_rejected(certs):
    p = problem("wise(socrates)"); certificate = certs.build_certificate(p)
    certificate["true_atoms"] = []
    with pytest.raises(certs.CertificateError):
        certs.check_certificate(p, certificate)


@pytest.mark.parametrize("formula", ["? [X] : human(X)", "human(X)", "p(a) | q(a)", "a = a", "p(f(a))", "! [X] : p(X) => q(X)", "! [X] : (p(X) => q(Y))"])
def test_unsupported_or_unbound_formula_stays_unknown(api, formula):
    p = replace(problem(), axioms=(("unsupported", formula),))
    m, q = initial(api, p)
    r = api.resolve_question(m, q, p, engine=lambda r: candidate(r))
    assert r.answer.status is S.UNKNOWN and r.machine == m


def test_recursive_rule_does_not_invent_a_proof(certs):
    p = FirstOrderResidual("cycle", (("cycle", "! [X] : (p(X) => p(X))"),), "p(a)")
    certificate = certs.build_certificate(p)
    assert certs.check_certificate(p, certificate) == "EXCLUDED"


def test_multivariable_conjunction_rule(certs):
    p = FirstOrderResidual("transitive", (("ab", "r(a,b)"), ("bc", "r(b,c)"),
        ("trans", "! [X,Y,Z] : ((r(X,Y) & r(Y,Z)) => r(X,Z))")), "r(a,c)")
    assert certs.check_certificate(p, certs.build_certificate(p)) == "WARRANTED"


def test_resource_limit_never_becomes_a_proof(certs):
    with pytest.raises(certs.UnsupportedFragment):
        certs.build_certificate(problem(), max_ground_instances=0)


def test_revoked_exclusion_is_unknown_not_sticky():
    m = Machine("b", ("q",), (Edge("q", "claim", ("holds",), S.EXCLUDED,
        support_refs=("model-checker",), evidence_refs=("checked:model",)),))
    q = CrystalQuestion("q", "claim", ("holds",))
    assert query_crystal(m, q).status is S.UNKNOWN
    assert query_crystal(m, replace(q, live_supports=("model-checker",))).status is S.EXCLUDED


def test_admission_is_idempotent(api, certs):
    p = problem(); m, q = initial(api, p); c = certs.build_certificate(p); e = candidate(p)
    a = api.admit_candidate(m, q, p, e, c)
    b = api.admit_candidate(a.machine, q, p, e, c)
    assert a.accepted and b.accepted and a.machine == b.machine
    assert a.receipt["receipt_id"] == b.receipt["receipt_id"]
