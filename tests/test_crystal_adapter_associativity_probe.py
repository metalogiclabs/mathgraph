from __future__ import annotations

from mathgraph.crystal import (
    AdapterContract,
    SemanticObject,
    compose_adapter_contracts,
    compose_lower_semantic_object,
    identity_adapter_contract,
    lower_semantic_object,
)


I = "interface.i@1"
J = "interface.j@1"
K = "interface.k@1"


def _a() -> AdapterContract:
    return AdapterContract(
        "A", 1, "S", "M", (I, J),
        assumption_refs=("assumption:A",),
        evidence_refs=("evidence:A",),
    )


def _b() -> AdapterContract:
    return AdapterContract(
        "B", 1, "M", "N", (I, K),
        assumption_refs=("assumption:B",),
        evidence_refs=("evidence:B",),
    )


def _c() -> AdapterContract:
    return AdapterContract(
        "C", 1, "N", "T", (I, J, K),
        assumption_refs=("assumption:C",),
        evidence_refs=("evidence:C",),
    )


def test_preservation_meaning_is_associative():
    left = compose_adapter_contracts(
        compose_adapter_contracts(_a(), _b(), adapter_id="AB"),
        _c(),
        adapter_id="ABC",
    )
    right = compose_adapter_contracts(
        _a(),
        compose_adapter_contracts(_b(), _c(), adapter_id="BC"),
        adapter_id="ABC",
    )
    assert left.source_space == right.source_space == "S"
    assert left.target_space == right.target_space == "T"
    assert left.preserves_interfaces == right.preserves_interfaces == (I,)
    assert left.assumption_refs == right.assumption_refs


def test_strict_contract_identity_is_associative():
    left = compose_adapter_contracts(
        compose_adapter_contracts(_a(), _b(), adapter_id="AB"),
        _c(),
        adapter_id="ABC",
    )
    right = compose_adapter_contracts(
        _a(),
        compose_adapter_contracts(_b(), _c(), adapter_id="BC"),
        adapter_id="ABC",
    )
    assert left == right
    assert left.id == right.id


def test_automatic_composition_identity_is_associative():
    left = compose_adapter_contracts(
        compose_adapter_contracts(_a(), _b()),
        _c(),
    )
    right = compose_adapter_contracts(
        _a(),
        compose_adapter_contracts(_b(), _c()),
    )
    assert left == right
    assert left.id == right.id


def test_identity_contract_is_neutral_on_both_sides():
    a = _a()
    left_identity = identity_adapter_contract("S", (I, J, K))
    right_identity = identity_adapter_contract("M", (I, J, K))
    assert compose_adapter_contracts(left_identity, a) == a
    assert compose_adapter_contracts(a, right_identity) == a


def _obj(space: str, marker: str) -> SemanticObject:
    return SemanticObject(space, 1, marker.encode("utf-8"), (I,))


def _la(obj: SemanticObject) -> SemanticObject:
    return _obj("M", obj.payload.decode("utf-8") + "A")


def _lb(obj: SemanticObject) -> SemanticObject:
    return _obj("N", obj.payload.decode("utf-8") + "B")


def _lc(obj: SemanticObject) -> SemanticObject:
    return _obj("T", obj.payload.decode("utf-8") + "C")


def _identity_lowerer(obj: SemanticObject) -> SemanticObject:
    return SemanticObject.from_bytes(obj.to_bytes())


def test_lowering_outputs_are_associative():
    source = _obj("S", "x")
    ab_contract = compose_adapter_contracts(_a(), _b())
    bc_contract = compose_adapter_contracts(_b(), _c())

    def lower_ab(obj: SemanticObject) -> SemanticObject:
        mid = lower_semantic_object(obj, _a(), I, _la)
        assert isinstance(mid, SemanticObject)
        out = lower_semantic_object(mid, _b(), I, _lb)
        assert isinstance(out, SemanticObject)
        return out

    def lower_bc(obj: SemanticObject) -> SemanticObject:
        mid = lower_semantic_object(obj, _b(), I, _lb)
        assert isinstance(mid, SemanticObject)
        out = lower_semantic_object(mid, _c(), I, _lc)
        assert isinstance(out, SemanticObject)
        return out

    left = compose_lower_semantic_object(
        source, ab_contract, _c(), I, lower_ab, _lc
    )
    right = compose_lower_semantic_object(
        source, _a(), bc_contract, I, _la, lower_bc
    )
    assert isinstance(left, SemanticObject)
    assert isinstance(right, SemanticObject)
    assert left == right
    assert left.payload == b"xABC"


def test_identity_lowering_is_neutral():
    source = _obj("S", "x")
    identity = identity_adapter_contract("S", (I,))
    result = lower_semantic_object(source, identity, I, _identity_lowerer)
    assert isinstance(result, SemanticObject)
    assert result == source
    assert result.id == source.id
    assert result.to_bytes() == source.to_bytes()
