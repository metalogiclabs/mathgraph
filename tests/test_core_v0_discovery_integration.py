from mathgraph.core_v0 import (
    CoreGraph,
    EvidenceReceipt,
    Grammar,
    Relation,
    RelationKind,
    Status,
    Support,
    normalize,
    verify,
)
from mathgraph.discovery_candidate_sources import candidates_from_core_v0_graph
from mathgraph.discovery_scheduler import allocate_attention, make_policy


def _grammar() -> Grammar:
    return Grammar(
        "core-v0-discovery-integration",
        "1",
        "sha256:core-v0-discovery-integration-v1",
    )


def _admit(graph: CoreGraph, candidate, label: str, *, outcome: Status = Status.WARRANTED):
    support = Support(f"fixture:{label}", f"sha256:{label}")
    graph.add_support(support)
    receipt = EvidenceReceipt.for_candidate(
        candidate,
        verifier="fixture-verifier",
        support_ids=(support.id,),
        boundary="core-v0-discovery-integration-v1",
        payload={"label": label, "outcome": outcome.value},
        outcome=outcome,
    )
    graph.admit(verify(candidate, receipt))
    return support


def test_closed_warranted_consequence_disappears_from_future_attention() -> None:
    grammar = _grammar()
    a = normalize("A", grammar, lambda _: {"atom": "A"})
    b = normalize("B", grammar, lambda _: {"atom": "B"})
    residual = normalize("C", grammar, lambda _: {"atom": "C"})
    implication = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(
        grammars=[grammar],
        objects=[a, b, residual],
        relations=[implication],
    )
    _admit(graph, a, "A")
    _admit(graph, implication, "A-implies-B")

    # The source graph is deliberately not closed.
    assert graph.status_of(b.id) is Status.UNKNOWN

    candidates = candidates_from_core_v0_graph(graph)
    residual_ids = {candidate.residual_cluster for candidate in candidates}

    # The adapter closes a copy: B is derived as warranted and is not paid for again.
    assert a.id not in residual_ids
    assert implication.id not in residual_ids
    assert b.id not in residual_ids
    assert residual.id in residual_ids

    # Candidate extraction must not mutate durable state.
    assert graph.status_of(b.id) is Status.UNKNOWN


def test_unknown_grammar_residual_descends_to_representation_repair() -> None:
    grammar = _grammar()
    unknown = normalize("opaque surface", grammar, lambda _: None)
    graph = CoreGraph(grammars=[grammar], unknowns=[unknown])

    candidates = candidates_from_core_v0_graph(graph)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.residual_cluster == unknown.id
    assert candidate.descension_target == "representation_repair"
    assert candidate.candidate_type == "core_v0_unknown_grammar_candidate"
    assert candidate.advisory_only is True
    assert candidate.can_promote_truth is False
    assert "@sha256:" in candidate.source_ref


def test_unwarranted_relation_enters_existing_scheduler_without_truth_leakage() -> None:
    grammar = _grammar()
    a = normalize("A", grammar, lambda _: {"atom": "A"})
    b = normalize("B", grammar, lambda _: {"atom": "B"})
    implication = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(grammars=[grammar], objects=[a, b], relations=[implication])
    _admit(graph, a, "A")
    _admit(graph, b, "B")

    candidates = candidates_from_core_v0_graph(graph)
    relation_candidates = [
        candidate for candidate in candidates
        if candidate.residual_cluster == implication.id
    ]

    assert len(relation_candidates) == 1
    assert relation_candidates[0].descension_target == "verifier_contact"

    ranked, selected, invalid = allocate_attention(
        candidates,
        make_policy(mode="frontier", beta=1.0),
        top_k=10,
    )
    assert not invalid
    assert ranked
    assert selected
    assert all(candidate.advisory_only for candidate in ranked)
    assert all(not candidate.can_promote_truth for candidate in ranked)


def test_conflicted_subject_routes_to_trust_audit() -> None:
    grammar = _grammar()
    claim = normalize("claim", grammar, lambda _: {"atom": "claim"})
    graph = CoreGraph(grammars=[grammar], objects=[claim])
    _admit(graph, claim, "positive", outcome=Status.WARRANTED)
    _admit(graph, claim, "negative", outcome=Status.REJECTED)

    assert graph.status_of(claim.id) is Status.CONFLICTED

    candidates = candidates_from_core_v0_graph(graph)

    assert len(candidates) == 1
    assert candidates[0].descension_target == "trust_audit"
    assert candidates[0].candidate_type == "core_v0_conflict_candidate"


def test_core_v0_candidate_extraction_is_deterministic() -> None:
    grammar = _grammar()
    a = normalize("A", grammar, lambda _: {"atom": "A"})
    b = normalize("B", grammar, lambda _: {"atom": "B"})
    graph = CoreGraph(grammars=[grammar], objects=[a, b])

    first = [candidate.to_dict() for candidate in candidates_from_core_v0_graph(graph)]
    second = [candidate.to_dict() for candidate in candidates_from_core_v0_graph(graph)]

    assert first == second
