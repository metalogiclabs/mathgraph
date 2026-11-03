"""Source and obligation applicability are separate from verification success."""
from dataclasses import FrozenInstanceError, replace

import pytest

from mathgraph_check.warrant_resolution import Receipt, compare_snapshots


def fixture(kind="formal", suffix="l4", conclusion="SUPPORTED"):
    from mathgraph_check.boundary_warrant import (
        BoundaryWarrant, Conclusion, Obligation, Relation, Subject,
        Verification, required_dependencies,
    )
    subject = Subject("metalogiclabs/" + suffix, "a" * 40, "1" * 64)
    obligation = Obligation("consumer:" + suffix, "P", "PR_AUTHOR_DECLARED", "2" * 64)
    relation = Relation("logical_entailment" if kind == "formal" else "event_consistency",
                        "producer satisfies P" if kind == "formal" else "same physical event",
                        (("frame", "fixed"),))
    verification = Verification(kind, "verifier-v1", "3" * 64, ("propext",) if kind == "formal" else (),
                                "receipt:" + suffix)
    return BoundaryWarrant(
        subject, obligation, relation, verification,
        Conclusion(conclusion, ("bounded finite verification",)),
        required_dependencies(subject, obligation, relation, verification),
    )


def qualified_receipt(warrant):
    from mathgraph_check.boundary_warrant import scope_identity
    return Receipt(warrant.verification.receipt_id, warrant.verification.method,
                   scope_identity(warrant))


def test_carrier_scope_is_independent_of_success_labels_and_evidence_replay():
    from mathgraph_check.boundary_warrant import scope_identity
    w = fixture()
    assert len(scope_identity(w)) == 64
    assert scope_identity(w) == scope_identity(replace(w, conclusion=replace(
        w.conclusion, status="UNKNOWN")))
    assert scope_identity(w) != scope_identity(fixture(suffix="other"))
    with pytest.raises(FrozenInstanceError):
        w.obligation = replace(w.obligation, statement="True")
    assert isinstance(w.dependencies, tuple)


def test_changes_to_source_obligation_relation_or_policy_change_scope():
    from mathgraph_check.boundary_warrant import (
        BoundaryWarrant, required_dependencies, scope_identity,
    )
    w = fixture()
    for change in (
        {"subject": replace(w.subject, source_sha256="e" * 64)},
        {"obligation": replace(w.obligation, statement="P or True")},
        {"relation": replace(w.relation, statement="missing direction constraint")},
        {"verification": replace(w.verification, policy_sha256="f" * 64)},
    ):
        parts = {
            "subject": change.get("subject", w.subject),
            "obligation": change.get("obligation", w.obligation),
            "relation": change.get("relation", w.relation),
            "verification": change.get("verification", w.verification),
        }
        next_warrant = BoundaryWarrant(
            **parts, conclusion=w.conclusion,
            dependencies=required_dependencies(**parts),
        )
        assert scope_identity(w) != scope_identity(next_warrant)


def test_forged_or_incomplete_dependencies_fail_before_graph_closure():
    from mathgraph_check.boundary_warrant import BoundaryWarrant
    w = fixture()
    with pytest.raises(ValueError, match="DEPENDENCY_IDENTITY_MISMATCH"):
        replace(w, dependencies=(replace(w.dependencies[0], sha256="f" * 64),
                                 *w.dependencies[1:]))
    with pytest.raises(ValueError, match="MISSING_REQUIRED_DEPENDENCY"):
        replace(w, dependencies=w.dependencies[:-1])
    with pytest.raises(ValueError, match="DUPLICATE_DEPENDENCY"):
        replace(w, dependencies=w.dependencies + (w.dependencies[0],))
    with pytest.raises(ValueError, match="INVALID_STATUS"):
        replace(w, conclusion=replace(w.conclusion, status="WARRANTED"))


def test_unqualified_receipt_or_unsupported_conclusion_cannot_enter_a_route():
    from mathgraph_check.boundary_warrant import admitted_route
    w = fixture()
    with pytest.raises(ValueError, match="UNADMITTED_RECEIPT"):
        admitted_route(w, Receipt("self-hash", "formal", qualified_receipt(w).scope))
    with pytest.raises(ValueError, match="UNADMITTED_RECEIPT"):
        admitted_route(w, Receipt(w.verification.receipt_id, "formal", "wrong-scope"))
    with pytest.raises(ValueError, match="NO_SUPPORTING_CONCLUSION"):
        admitted_route(fixture(conclusion="UNKNOWN"), qualified_receipt(w))
    with pytest.raises(ValueError, match="NO_SUPPORTING_CONCLUSION"):
        admitted_route(fixture(conclusion="REJECTED"), qualified_receipt(w))


def test_native_and_formal_admissions_use_same_graph_interface_without_conflation():
    from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries
    formal, native = fixture(), fixture(kind="native", suffix="brahe")
    items = [(formal, qualified_receipt(formal)), (native, qualified_receipt(native))]
    observed = {dep.key: dep.sha256 for w, _ in items for dep in w.dependencies}
    result = resolve_boundaries(items, observed)
    assert result.states == {
        admitted_route(formal, qualified_receipt(formal))[0].id: "WARRANTED_BOUNDED",
        admitted_route(native, qualified_receipt(native))[0].id: "WARRANTED_BOUNDED_NATIVE",
    }


def test_changed_source_or_obligation_withdraws_only_its_dependent_warrant():
    from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries
    formal, native = fixture(), fixture(kind="native", suffix="brahe")
    items = [(formal, qualified_receipt(formal)), (native, qualified_receipt(native))]
    observed = {dep.key: dep.sha256 for w, _ in items for dep in w.dependencies}
    before = resolve_boundaries(items, observed)
    f_id = admitted_route(formal, qualified_receipt(formal))[0].id
    n_id = admitted_route(native, qualified_receipt(native))[0].id
    for role in ("source", "obligation"):
        changed = dict(observed)
        changed[next(dep.key for dep in formal.dependencies if dep.role == role)] = "f" * 64
        after = resolve_boundaries(items, changed)
        delta = compare_snapshots(before.states, after.states)
        assert delta[f_id] == {
            "before": "WARRANTED_BOUNDED", "after": "STALE", "changed": True,
        }
        assert delta[n_id]["changed"] is False
        assert resolve_boundaries(items, observed).states == before.states


def test_missing_authority_or_verifier_dependency_is_stale_not_false():
    from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries
    w = fixture()
    item = (w, qualified_receipt(w))
    observed = {dep.key: dep.sha256 for dep in w.dependencies}
    claim_id = admitted_route(*item)[0].id
    for role in ("obligation", "verifier"):
        remaining = {key: value for key, value in observed.items()
                     if key != next(dep.key for dep in w.dependencies if dep.role == role)}
        assert resolve_boundaries([item], remaining).states[claim_id] == "UNKNOWN"
