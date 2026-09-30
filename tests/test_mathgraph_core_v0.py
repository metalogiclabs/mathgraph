import json
from pathlib import Path

from mathgraph.core_v0 import (
    CoreGraph,
    EvidenceReceipt,
    Grammar,
    Relation,
    RelationKind,
    Status,
    Support,
    Unknown,
    normalize,
    verify,
)
from mathgraph.core_v0_family_adapter import replay_family
from mathgraph.cross_prover_family_discovery import discover_family


def grammar():
    return Grammar(
        grammar_id="test.formula-ast",
        version="1",
        definition_digest="sha256:grammar-definition-v1",
    )


def receipt(candidate, *, verifier, support_ids, payload, outcome=Status.WARRANTED):
    return EvidenceReceipt.for_candidate(
        candidate,
        verifier=verifier,
        support_ids=support_ids,
        boundary="fixture-v1",
        payload=payload,
        outcome=outcome,
    )


def add_evidenced(graph, candidate, support, *, verifier, payload, outcome=Status.WARRANTED):
    graph.add_support(support)
    graph.add_candidate(candidate)
    warrant = verify(
        candidate,
        receipt(
            candidate,
            verifier=verifier,
            support_ids=(support.id,),
            payload=payload,
            outcome=outcome,
        ),
    )
    graph.admit(warrant)
    return warrant


def test_normalization_identity_uses_meaning_and_grammar_not_surface_or_theorem_name():
    g = grammar()
    canonical_formula = {
        "binders": [{"sort": "real"}, {"sort": "real"}],
        "relation": "ge",
        "lhs": ["add", ["pow", "x", 2], ["pow", "y", 2]],
        "rhs": ["mul", 2, "x", "y"],
    }
    pvs = normalize(
        "d_amgm: LEMMA ...",
        g,
        lambda _surface: canonical_formula,
    )
    lean = normalize(
        "theorem amgm2_real ...",
        g,
        lambda _surface: canonical_formula,
    )
    changed = normalize(
        "theorem amgm3_real ...",
        g,
        lambda _surface: {**canonical_formula, "rhs": ["mul", 3, "x", "y"]},
    )
    other_grammar = normalize(
        "d_amgm: LEMMA ...",
        Grammar("test.formula-ast", "2", "sha256:grammar-definition-v2"),
        lambda _surface: canonical_formula,
    )

    assert pvs.id == lean.id
    assert changed.id != lean.id
    assert other_grammar.id != lean.id


def test_normalized_object_does_not_mutate_after_its_content_id_is_observed():
    g = grammar()
    input_term = {"operation": "eq", "args": ["x", "x"]}
    obj = normalize("x=x", g, lambda _: input_term)
    identity = obj.id
    input_term["args"].append("changed")

    assert obj.id == identity
    assert obj.normal_form["args"] == ("x", "x")


def test_unsupported_normalization_is_typed_unknown_without_creating_an_object():
    result = normalize("opaque PVS formula", grammar(), lambda _surface: None)

    assert isinstance(result, Unknown)
    assert result.status is Status.UNKNOWN
    assert result.reason == "UNKNOWN_UNSUPPORTED_GRAMMAR"


def test_external_verifier_can_reject_a_typed_unknown_surface_without_normalizing_it():
    g = grammar()
    unknown = normalize("false but unsupported claim", g, lambda _: None)
    support = Support("source:false-claim", "sha256:false-claim")
    graph = CoreGraph(grammars=[g], unknowns=[unknown], supports=[support])
    warrant = verify(
        unknown,
        EvidenceReceipt.for_candidate(
            unknown,
            verifier="pvs-cad-counterexample",
            support_ids=(support.id,),
            boundary="pinned-pvs-source-v1",
            payload={"counterexample": "verified"},
            outcome=Status.REJECTED,
        ),
    )

    graph.admit(warrant)

    assert graph.status_of(unknown.id) is Status.REJECTED
    assert CoreGraph.from_mg(graph.to_mg()).status_of(unknown.id) is Status.REJECTED


def test_conflicting_active_warrants_are_not_silently_resolved_as_positive():
    g = grammar()
    candidate = normalize("claim", g, lambda _: {"atom": "claim"})
    graph = CoreGraph(grammars=[g], objects=[candidate])
    add_evidenced(
        graph, candidate, Support("source:positive", "sha256:positive"),
        verifier="lean", payload={"result": "proved"},
    )
    add_evidenced(
        graph, candidate, Support("source:negative", "sha256:negative"),
        verifier="countermodel", payload={"result": "refuted"},
        outcome=Status.REJECTED,
    )

    assert graph.status_of(candidate.id) is Status.CONFLICTED


def test_relation_kinds_preserve_implication_asymmetry_and_rejection_evidence():
    g = grammar()
    a = normalize("A", g, lambda _: {"atom": "A"})
    b = normalize("B", g, lambda _: {"atom": "B"})
    assert a.id != b.id
    implies = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(grammars=[g], objects=[a, b])
    add_evidenced(
        graph,
        implies,
        Support("lean:A-to-B", "sha256:a-to-b"),
        verifier="lean-kernel",
        payload={"checked": "A -> B"},
    )
    assert graph.status_of(a.id) is Status.UNKNOWN
    assert graph.status_of(implies.id) is Status.WARRANTED
    assert Relation(RelationKind.SAME_MEANING, (a.id,), (b.id,)).id != implies.id

    false_claim = Relation(RelationKind.IMPLIES, (b.id,), (a.id,))
    add_evidenced(
        graph,
        false_claim,
        Support("finite-countermodel:B-not-A", "sha256:countermodel"),
        verifier="finite-model-checker",
        payload={"countermodel": [0, 1]},
        outcome=Status.REJECTED,
    )
    assert graph.status_of(false_claim.id) is Status.REJECTED


def test_warranted_implication_transports_a_warrant_to_its_consequence():
    g = grammar()
    a, b = [normalize(n, g, lambda _: {"atom": n}) for n in "AB"]
    implication = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(grammars=[g], objects=[a, b])
    add_evidenced(
        graph, a, Support("source:A", "sha256:A"),
        verifier="lean", payload={"proof": "A"}
    )
    add_evidenced(
        graph, implication, Support("source:A-implies-B", "sha256:AtoB"),
        verifier="lean", payload={"proof": "A -> B"}
    )

    graph.close()

    assert graph.status_of(b.id) is Status.WARRANTED


def test_warranted_implications_close_and_support_revocation_recloses_only_dependents():
    g = grammar()
    a, b, c = [normalize(n, g, lambda _: {"atom": n}) for n in "ABC"]
    ab = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    bc = Relation(RelationKind.IMPLIES, (b.id,), (c.id,))
    graph = CoreGraph(grammars=[g], objects=[a, b, c])
    support_ab = Support("source:A-B", "sha256:ab")
    wa = add_evidenced(
        graph, ab, support_ab,
        verifier="lean", payload={"proof": "A implies B"}
    )
    add_evidenced(
        graph, bc, Support("source:B-C", "sha256:bc"),
        verifier="lean", payload={"proof": "B implies C"}
    )

    graph.close()
    ac = Relation(RelationKind.IMPLIES, (a.id,), (c.id,))
    assert graph.status_of(ac.id) is Status.WARRANTED
    assert ac.id in {edge.id for edge in graph.query(a.id).relations}

    delta = graph.revoke(support_ab.id)
    assert wa.id in delta.invalidated_warrants
    assert graph.status_of(ab.id) is Status.REVOKED
    assert graph.status_of(ac.id) is Status.REVOKED
    assert graph.status_of(bc.id) is Status.WARRANTED


def test_relation_closure_terminates_on_cycles_without_adding_reflexive_edges():
    g = grammar()
    a, b, c = [normalize(n, g, lambda _: {"atom": n}) for n in "ABC"]
    graph = CoreGraph(grammars=[g], objects=[a, b, c])
    cycle = [
        Relation(RelationKind.IMPLIES, (a.id,), (b.id,)),
        Relation(RelationKind.IMPLIES, (b.id,), (c.id,)),
        Relation(RelationKind.IMPLIES, (c.id,), (a.id,)),
    ]
    for index, edge in enumerate(cycle):
        add_evidenced(
            graph, edge, Support(f"source:{index}", f"sha256:{index}"),
            verifier="lean", payload={"edge": index}
        )

    graph.close()

    assert all(
        edge.sources != edge.targets
        for edge in graph.relations.values()
        if edge.kind is RelationKind.IMPLIES
    )
    assert len(graph.warrants) < 20


def test_same_meaning_substitutes_across_an_implication_edge():
    g = grammar()
    a, alias, b = [normalize(n, g, lambda _: {"atom": n}) for n in "AXB"]
    equivalent = Relation(RelationKind.SAME_MEANING, (a.id,), (alias.id,))
    implication = Relation(RelationKind.IMPLIES, (alias.id,), (b.id,))
    graph = CoreGraph(grammars=[g], objects=[a, alias, b])
    add_evidenced(
        graph, equivalent, Support("source:A=X", "sha256:ax"),
        verifier="lean", payload={"equivalence": "A=X"}
    )
    add_evidenced(
        graph, implication, Support("source:X=>B", "sha256:xb"),
        verifier="lean", payload={"implication": "X=>B"}
    )

    graph.close()

    consequence = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    assert graph.status_of(consequence.id) is Status.WARRANTED


def test_transitive_consequence_remains_live_through_an_alternative_parent_warrant():
    g = grammar()
    a, b, c = [normalize(n, g, lambda _: {"atom": n}) for n in "ABC"]
    ab = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    bc = Relation(RelationKind.IMPLIES, (b.id,), (c.id,))
    first_support = Support("source:A-B-1", "sha256:ab1")
    graph = CoreGraph(grammars=[g], objects=[a, b, c])
    add_evidenced(
        graph, ab, first_support, verifier="lean-1", payload={"proof": "A->B-1"}
    )
    add_evidenced(
        graph, ab, Support("source:A-B-2", "sha256:ab2"),
        verifier="lean-2", payload={"proof": "A->B-2"}
    )
    add_evidenced(
        graph, bc, Support("source:B-C", "sha256:bc"),
        verifier="lean", payload={"proof": "B->C"}
    )
    graph.close()
    ac = Relation(RelationKind.IMPLIES, (a.id,), (c.id,))

    graph.revoke(first_support.id)

    assert graph.status_of(ac.id) is Status.WARRANTED


def test_alternative_independent_support_keeps_a_relation_warranted_after_one_revocation():
    g = grammar()
    a = normalize("A", g, lambda _: {"atom": "A"})
    b = normalize("B", g, lambda _: {"atom": "B"})
    edge = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(grammars=[g], objects=[a, b])
    first_support = Support("support:one", "sha256:one")
    add_evidenced(
        graph, edge, first_support,
        verifier="lean-A", payload={"proof": "route one"}
    )
    add_evidenced(
        graph, edge, Support("support:two", "sha256:two"),
        verifier="lean-B", payload={"proof": "route two"}
    )

    graph.revoke(first_support.id)

    assert graph.status_of(edge.id) is Status.WARRANTED


def test_mg_encoding_is_canonical_and_round_trips_the_graph():
    g = grammar()
    a = normalize("A", g, lambda _: {"atom": "A"})
    b = normalize("B", g, lambda _: {"atom": "B"})
    ab = Relation(RelationKind.IMPLIES, (a.id,), (b.id,))
    graph = CoreGraph(grammars=[g], objects=[a, b])
    add_evidenced(
        graph, ab, Support("source:A-B", "sha256:evidence"),
        verifier="lean", payload={"checked": True}
    )

    encoded = graph.to_mg()
    decoded = CoreGraph.from_mg(encoded)

    assert encoded.startswith(b'{"format":"mathgraph-core-v0"')
    assert decoded.to_mg() == encoded
    assert decoded.status_of(ab.id) is Status.WARRANTED
    assert json.loads(encoded)["format"] == "mathgraph-core-v0"


def test_existing_cross_prover_claim_surfaces_normalize_to_one_object_without_importing_prover_identity():
    from mathgraph.cross_prover_semantic_surface import (
        load_manifest,
        render_lean_expression,
        render_pvs_claim,
        verify_pvs_source_surface,
    )

    manifest_path = Path("experiments/crystal_cross_prover_cad_v1/manifest.json")
    manifest = load_manifest(manifest_path)
    pvs_surface = render_pvs_claim(manifest)
    lean_surface = render_lean_expression(manifest)
    source = (
        "cad_demo: THEORY\nBEGIN\n"
        "d_amgm: LEMMA " + pvs_surface + "\nEND cad_demo\n"
    )
    assert verify_pvs_source_surface(manifest, source)["status"] == "EXACT_CANONICAL_SURFACE_MATCH"

    claim = manifest["canonical_claim"]
    names = {binder["name"]: index for index, binder in enumerate(claim["binders"])}

    def alpha_normalize(value):
        if isinstance(value, dict):
            if set(value) == {"var"}:
                return {"bound": names[value["var"]]}
            return {key: alpha_normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [alpha_normalize(item) for item in value]
        return value

    normalized_claim = {
        "binders": [binder["sort"] for binder in claim["binders"]],
        "proposition": alpha_normalize(claim["proposition"]),
    }

    def pvs_normalizer(_surface):
        return normalized_claim

    def lean_normalizer(_surface):
        return normalized_claim

    g = Grammar("math.claim-ast", "1", "sha256:claim-ast-v1")
    pvs = normalize(pvs_surface, g, pvs_normalizer)
    lean = normalize(lean_surface, g, lean_normalizer)
    assert pvs.id == lean.id


def test_verifier_receipt_is_bound_to_candidate_and_evidence_digest():
    from dataclasses import replace
    import pytest

    g = grammar()
    claim = normalize("A", g, lambda _: {"atom": "A"})
    support = Support("source:A", "sha256:source-A")
    valid = receipt(
        claim,
        verifier="lean-kernel",
        support_ids=(support.id,),
        payload={"result": "checked"},
    )
    assert verify(claim, valid).status is Status.WARRANTED

    with pytest.raises(ValueError, match="evidence digest"):
        verify(claim, replace(valid, payload={"result": "different"}))
    with pytest.raises(ValueError, match="subject"):
        verify(
            normalize("B", g, lambda _: {"atom": "B"}),
            valid,
        )


def test_cross_prover_family_adapter_preserves_quotient_unknown_and_refutation():
    sources = {
        "cad_demo": """
T: THEORY
BEGIN
d_amgm: LEMMA FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 2 * x * y
s_pos: LEMMA FORALL (x: real): FORALL (y: real): x > 0 AND y > 0 IMPLIES x * y > 0
d_false: LEMMA FORALL (x: real): x^3 = -1
opaque: LEMMA FORALL (x: real): mysterious(x)
END T
"""
    }
    proofs = {
        "cad_demo": "(|T|\n (|d_amgm| 0 (|d_amgm-0| proof))\n (|d_false| 0 (|d_false-0| proof))\n)"
    }
    discovery = discover_family(sources, proofs)
    # Simulate the pinned family’s unverified duplicate occurrence.
    pos = next(x for x in discovery["supported_occurrences"] if x["formula"] == "s_pos")
    pos["source_proof_status"] = "NO_PINNED_PROOF"
    replay = replay_family(
        discovery,
        grammar=grammar(),
        source_digests={"cad_demo": "gitblob:cad_demo"},
        verified_claim_authorities={"real.amgm2@1": ["run:lean", "run:pvs"]},
        refuted_source_authorities={"cad_demo.d_false": ["run:refutation"]},
        implication_authorities={
            "cad_demo.opaque": {
                "source_claim_id": "real.amgm2@1",
                "target_claim_id": "real.amgm2@1",
                "authority_refs": ["fixture:projection-verifier"],
            }
        },
        repository="j-tanner-slagel/pvs_cad",
        commit="pinned-test-commit",
    )

    assert replay.partition["source_occurrences"] == 4
    assert replay.partition["warranted_exact_occurrences"] == 1
    assert replay.partition["unknown_supported_occurrences"] == 1
    assert replay.graph.status_of(replay.object_by_claim["real.amgm2@1"].id) is Status.WARRANTED
    assert replay.graph.status_of(replay.unknown_by_source["cad_demo.s_pos"].id) is Status.UNKNOWN
    assert replay.graph.status_of(replay.unknown_by_source["cad_demo.d_false"].id) is Status.REJECTED
    assert replay.graph.status_of(replay.unknown_by_source["cad_demo.opaque"].id) is Status.UNKNOWN
    amgm_id = replay.object_by_claim["real.amgm2@1"].id
    projected = Relation(RelationKind.IMPLIES, (amgm_id,), (amgm_id,))
    assert replay.graph.status_of(projected.id) is Status.WARRANTED


def test_pinned_six_projection_vectors_replay_as_warranted_directed_edges():
    manifest = json.loads(
        Path(
            "experiments/crystal_cross_prover_bounded_closure_v1/"
            "core_v0_projection_map.json"
        ).read_text()
    )
    rows = manifest["relations"]
    assert len(rows) == 6
    discovery = {
        "source_lemma_count": 6,
        "unsupported_occurrences": [
            {
                "theory": "cad_star_ex",
                "formula": row["source_occurrence"].split(".", 1)[1],
                "normalized_surface": f"unsupported {row['source_occurrence']}",
            }
            for row in rows
        ],
    }
    replay = replay_family(
        discovery,
        grammar=grammar(),
        source_digests={"cad_star_ex": "gitblob:cad_star_ex"},
        verified_claim_authorities={},
        implication_authorities={row["source_occurrence"]: row for row in rows},
        repository="j-tanner-slagel/pvs_cad",
        commit=manifest["source_commit"],
    )

    assert replay.partition["warranted_implication_occurrences"] == 6
    warranted_implications = [
        relation for relation in replay.graph.relations.values()
        if relation.kind is RelationKind.IMPLIES
        and replay.graph.status_of(relation.id) is Status.WARRANTED
    ]
    assert len(warranted_implications) == 6
    assert len({edge.sources[0] for edge in warranted_implications}) == 6
    assert len({edge.targets[0] for edge in warranted_implications}) == 6
    assert all(source != target for edge in warranted_implications for source in edge.sources for target in edge.targets)
    restored = CoreGraph.from_mg(replay.graph.to_mg())
    assert sum(
        1 for relation in restored.relations.values()
        if relation.kind is RelationKind.IMPLIES
        and restored.status_of(relation.id) is Status.WARRANTED
    ) == 6
