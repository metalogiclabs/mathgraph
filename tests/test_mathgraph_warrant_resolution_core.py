"""Fail-closed graph resolution over externally admitted evidence."""
from dataclasses import FrozenInstanceError, replace

import pytest

from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, QualifiedRelation, ResolutionSet,
    compare_snapshots, resolve_graph,
)


def test_conjunctive_premises_and_surviving_alternative_routes():
    claims = [Claim(x, "formal", "s") for x in "ABCD"]
    receipts = [Receipt(x, "formal", "s") for x in "rstuv"]
    routes = [Route("A", ("r",)), Route("A", ("s",)),
              Route("B", ("t",)), Route("C", ("u",), ("A", "B")),
              Route("D", ("v",))]
    before = resolve_graph(claims, routes, receipts)
    assert isinstance(before, ResolutionSet)
    assert dict(before.states) == dict.fromkeys("ABCD", "WARRANTED_BOUNDED")
    one = resolve_graph(claims, routes, receipts, withdrawn=frozenset({"r"}))
    assert one.states == before.states
    after = resolve_graph(claims, routes, receipts, withdrawn=frozenset({"r", "s"}))
    assert dict(after.states) == {"A": "UNKNOWN", "B": "WARRANTED_BOUNDED",
                                  "C": "UNKNOWN", "D": "WARRANTED_BOUNDED"}
    assert compare_snapshots(before.states, after.states)["C"]["after"] == "STALE"
    assert resolve_graph(claims, routes, receipts, withdrawn=frozenset({"t"})).states["C"] == "UNKNOWN"


def test_all_evidence_is_conjunctive_and_rootless_cycles_stay_unknown():
    claims = [Claim(x, "formal", "s") for x in "ABC"]
    receipts = [Receipt(x, "formal", "s") for x in "rs"]
    result = resolve_graph(claims, [Route("A", ("r",), ("B",)),
                                  Route("B", ("s",), ("A",)),
                                  Route("C", ("r", "s"))], receipts,
                           withdrawn=frozenset({"s"}))
    assert dict(result.states) == dict.fromkeys("ABC", "UNKNOWN")


@pytest.mark.parametrize("routes,withdrawn,error", [
    ([Route("missing", ("r",))], frozenset(), "INVALID_ROUTE"),
    ([Route("A", ())], frozenset(), "INVALID_ROUTE"),
    ([Route("A", ("missing",))], frozenset(), "UNKNOWN_ROUTE_RECEIPT"),
    ([Route("A", ("r",), ("missing",))], frozenset(), "UNKNOWN_ROUTE_PREMISE"),
    ([], frozenset({"missing"}), "UNKNOWN_WITHDRAWAL_TARGET"),
    ([Route("A", ("r",)), Route("A", ("r",))], frozenset(), "DUPLICATE_ROUTE"),
])
def test_unknown_references_and_duplicate_routes_reject(routes, withdrawn, error):
    with pytest.raises(ValueError, match=error):
        resolve_graph([Claim("A", "formal", "s")], routes,
                      [Receipt("r", "formal", "s")], withdrawn=withdrawn)


@pytest.mark.parametrize("duplicate", ["claim", "receipt", "relation"])
def test_duplicate_identities_reject(duplicate):
    claims = [Claim("A", "formal", "s")]
    receipts = [Receipt("r", "formal", "s")]
    relations = [QualifiedRelation("bridge", "formal", "s", "formal", "s", "r", ("r",))]
    {"claim": claims, "receipt": receipts, "relation": relations}[duplicate] *= 2
    with pytest.raises(ValueError, match="DUPLICATE"):
        resolve_graph(claims, [], receipts, relations=relations)


@pytest.mark.parametrize("kind,scope", [("documentary", "s"), ("formal", "elsewhere")])
def test_cross_kind_or_scope_receipts_reject_without_relation(kind, scope):
    with pytest.raises(ValueError, match="CROSS_BOUNDARY_EVIDENCE"):
        resolve_graph([Claim("A", "formal", "s")], [Route("A", ("r",))],
                      [Receipt("r", kind, scope)])


def test_cross_boundary_premise_rejects_without_relation():
    with pytest.raises(ValueError, match="CROSS_BOUNDARY_PREMISE"):
        resolve_graph([Claim("A", "documentary", "s"), Claim("B", "formal", "s")],
                      [Route("B", ("r",), ("A",))], [Receipt("r", "formal", "s")])


def bridge_graph():
    claims = [Claim("source", "documentary", "source-scope"), Claim("target", "formal", "target-scope")]
    receipts = [Receipt("notice", "documentary", "source-scope"),
                Receipt("verifier", "formal", "target-scope"), Receipt("checked", "formal", "target-scope")]
    relation = QualifiedRelation("bridge", "documentary", "source-scope", "formal", "target-scope",
                                 "verifier", ("checked",))
    routes = [Route("source", ("notice",)), Route("target", ("notice",), ("source",), relation="bridge")]
    return claims, routes, receipts, relation


def test_qualified_relation_requires_live_verifier_and_evidence():
    claims, routes, receipts, relation = bridge_graph()
    result = resolve_graph(claims, routes, receipts, relations=[relation])
    assert dict(result.states) == {"source": "SOURCE_DOCUMENTED", "target": "WARRANTED_BOUNDED"}
    for withdrawn in ("verifier", "checked", "notice"):
        after = resolve_graph(claims, routes, receipts, relations=[relation], withdrawn=frozenset({withdrawn}))
        assert after.states["target"] == "UNKNOWN"


@pytest.mark.parametrize("change,error", [
    ({"verifier": "missing"}, "UNKNOWN_RELATION_VERIFIER"),
    ({"evidence": ("missing",)}, "UNKNOWN_RELATION_RECEIPT"),
    ({"evidence": ()}, "INVALID_RELATION"),
    ({"kind": "self_hash"}, "UNSUPPORTED_RELATION"),
    ({"source_scope": "wrong"}, "CROSS_BOUNDARY_EVIDENCE"),
    ({"target_scope": "wrong"}, "RELATION_TARGET"),
    ({"verifier": "notice"}, "UNQUALIFIED_RELATION_VERIFIER"),
    ({"evidence": ("notice",)}, "UNQUALIFIED_RELATION_EVIDENCE"),
])
def test_relation_cannot_assert_its_own_qualification(change, error):
    claims, routes, receipts, relation = bridge_graph()
    with pytest.raises(ValueError, match=error):
        resolve_graph(claims, routes, receipts, relations=[replace(relation, **change)])


def test_unknown_relation_rejects():
    claims, routes, receipts, _ = bridge_graph()
    with pytest.raises(ValueError, match="UNKNOWN_ROUTE_RELATION"):
        resolve_graph(claims, routes, receipts)


def test_documentary_withdrawal_never_implies_refutation():
    claims = [Claim("paper", "documentary", "s"), Claim("theorem", "formal", "s")]
    receipts = [Receipt("notice", "documentary", "s")]
    routes = [Route("paper", ("notice",))]
    before = resolve_graph(claims, routes, receipts)
    after = resolve_graph(claims, routes, receipts, withdrawn=frozenset({"notice"}))
    assert compare_snapshots(before.states, after.states) == {
        "paper": {"before": "SOURCE_DOCUMENTED", "after": "STALE", "changed": True},
        "theorem": {"before": "UNKNOWN", "after": "UNKNOWN", "changed": False},
    }


def test_resolution_is_immutable_and_independent_of_input_order():
    claims, routes, receipts, relation = bridge_graph()
    result = resolve_graph(claims, routes, receipts, relations=[relation])
    assert result == resolve_graph(claims[::-1], routes[::-1], receipts[::-1], relations=[relation])
    with pytest.raises(TypeError):
        result.states["target"] = "REFUTED"
    with pytest.raises(FrozenInstanceError):
        result.active_routes = ()
