from mathgraph.crystal import (
    ConsequentialState,
    Hyperedge,
    action_quotient,
    content_id,
    find_quotient_falsifiers,
    greatest_viability_kernel,
    quotient_states,
    uncovered_failures,
)


def test_content_ids_are_canonical_and_content_addressed():
    assert content_id({"b": 2, "a": 1}) == content_id({"a": 1, "b": 2})
    assert content_id({"a": 1}) != content_id({"a": 2})


def test_future_signature_quotient_erases_raw_difference():
    states = [
        ConsequentialState("proof_body_a", ("opaque",), ("syntax-A",)),
        ConsequentialState("proof_body_b", ("opaque",), ("syntax-B",)),
        ConsequentialState("definition", ("reducible",), ("syntax-C",)),
    ]
    classes = quotient_states(states)
    assert classes[("opaque",)] == ("proof_body_a", "proof_body_b")
    assert classes[("reducible",)] == ("definition",)


def test_same_representation_different_target_is_a_separator():
    representation = {"x": ("coarse",), "y": ("coarse",), "z": ("other",)}
    target = {"x": ("accept",), "y": ("reject",), "z": ("accept",)}
    witnesses = find_quotient_falsifiers(representation, target)
    assert len(witnesses) == 1
    assert {witnesses[0].left, witnesses[0].right} == {"x", "y"}


def test_hyperedges_encode_alternatives_and_conjunctive_support():
    edges = [
        Hyperedge("q", "q", "f0", frozenset({"w0"})),
        Hyperedge("q", "q", "f0", frozenset({"w1"})),
        Hyperedge("q", "q", "f1", frozenset({"w1", "w2"})),
        Hyperedge("q", "q", "f1", frozenset({"w3"})),
    ]
    assert uncovered_failures("q", ["f0", "f1"], edges, {"w0", "w2"})[0].failure_class == "f1"
    assert uncovered_failures("q", ["f0", "f1"], edges, {"w0", "w3"}) == ()


def test_revocation_reclosure_exposes_only_affected_residual():
    edges = [
        Hyperedge("q", "q", "f0", frozenset({"w0"})),
        Hyperedge("q", "q", "f1", frozenset({"w1"})),
    ]
    assert uncovered_failures("q", ["f0", "f1"], edges, {"w0", "w1"}) == ()
    residuals = uncovered_failures("q", ["f0", "f1"], edges, {"w0"})
    assert [(r.state, r.failure_class) for r in residuals] == [("q", "f1")]


def test_stateful_viability_separates_static_cover_from_sustainable_cover():
    # A one-shot repair is statically available at ready, but sends the system
    # to spent, where the next identical disturbance has no repair. Greatest
    # robust viability is therefore empty.
    one_shot = [Hyperedge("ready", "spent", "fail", frozenset({"repair"}))]
    assert uncovered_failures("ready", ["fail"], one_shot, {"repair"}) == ()
    assert greatest_viability_kernel(
        {"ready", "spent"}, ["fail"], one_shot, {"repair"}
    ) == frozenset()

    # Immediate replenishment changes the consequential transition, preserving
    # exactly the ready state as the viable kernel.
    replenished = [Hyperedge("ready", "ready", "fail", frozenset({"repair"}))]
    assert greatest_viability_kernel(
        {"ready", "spent"}, ["fail"], replenished, {"repair"}
    ) == frozenset({"ready"})


def test_actions_quotient_by_induced_protected_transition():
    actions = ["A", "B", "C", "D", "E"]
    sources = ["s0", "s1", "s2"]
    induced = {}
    for source in sources:
        for action in ("A", "C", "E"):
            induced[(source, action)] = f"{source}:mark"
        for action in ("B", "D"):
            induced[(source, action)] = f"{source}:transform"

    classes = set(action_quotient(actions, sources, induced).values())
    assert classes == {("A", "C", "E"), ("B", "D")}
