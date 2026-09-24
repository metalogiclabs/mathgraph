from __future__ import annotations

from mathgraph.crystal import (
    AdapterContract,
    SemanticObject,
    UnknownTranslation,
    translate_semantic_object,
)


def _future_object() -> SemanticObject:
    return SemanticObject(
        type_id="effect.weird.future.physics",
        contract_version=1,
        payload=b"future-payload\\x00\\xff",
        interfaces=("effect.compose@2", "future.physics@1"),
    )


def _adapter_v1() -> AdapterContract:
    return AdapterContract(
        adapter_id="example.source-to-mathgraph",
        contract_version=1,
        source_space="source.example@9",
        target_space="mathgraph.semantic-envelope@1",
        preserves_interfaces=("effect.compose@2",),
        assumption_refs=("assumption:source-valid",),
        evidence_refs=("evidence:qualified-run-1",),
    )


def test_unknown_concrete_type_transports_under_known_preserved_interface():
    obj = _future_object()
    before = obj.to_bytes()
    before_id = obj.id
    contract = _adapter_v1()

    result = translate_semantic_object(obj, contract, "effect.compose@2")
    assert isinstance(result, SemanticObject)
    assert result.to_bytes() == before
    assert result.payload == obj.payload
    assert result.interfaces == obj.interfaces
    assert result.id == before_id


def test_adapter_returns_unknown_outside_declared_preservation_boundary():
    obj = _future_object()
    contract = _adapter_v1()
    before = obj.to_bytes()

    result = translate_semantic_object(obj, contract, "future.physics@1")
    assert result == UnknownTranslation(
        object_id=obj.id,
        adapter_contract_id=contract.id,
        requested_interface="future.physics@1",
        reason="outside_preservation_contract",
    )
    assert obj.to_bytes() == before


def test_adapter_cannot_claim_interface_object_does_not_implement():
    obj = SemanticObject(
        "effect.old",
        1,
        b"opaque",
        ("effect.compose@2",),
    )
    contract = AdapterContract(
        "adapter.future-aware",
        2,
        "source",
        "target",
        ("future.physics@1",),
    )
    result = translate_semantic_object(obj, contract, "future.physics@1")
    assert result == UnknownTranslation(
        object_id=obj.id,
        adapter_contract_id=contract.id,
        requested_interface="future.physics@1",
        reason="object_missing_interface",
    )


def test_adapter_contract_identity_is_canonical():
    a = AdapterContract(
        "adapter.x",
        3,
        "source",
        "target",
        ("z@1", "a@1", "z@1"),
        ("assumption:b", "assumption:a"),
        ("evidence:2", "evidence:1"),
    )
    b = AdapterContract(
        "adapter.x",
        3,
        "source",
        "target",
        ("a@1", "z@1"),
        ("assumption:a", "assumption:b"),
        ("evidence:1", "evidence:2"),
    )
    assert a == b
    assert a.id == b.id


def test_new_adapter_contract_adds_preservation_without_changing_old_object():
    obj = _future_object()
    before = obj.to_bytes()
    before_id = obj.id
    old = _adapter_v1()
    new = AdapterContract(
        adapter_id=old.adapter_id,
        contract_version=2,
        source_space=old.source_space,
        target_space=old.target_space,
        preserves_interfaces=("effect.compose@2", "future.physics@1"),
        assumption_refs=old.assumption_refs,
        evidence_refs=("evidence:qualified-run-2",),
    )

    old_result = translate_semantic_object(obj, old, "future.physics@1")
    new_result = translate_semantic_object(obj, new, "future.physics@1")

    assert isinstance(old_result, UnknownTranslation)
    assert isinstance(new_result, SemanticObject)
    assert new_result.to_bytes() == before
    assert new_result.id == before_id
    assert obj.to_bytes() == before
    assert obj.id == before_id
    assert old.id != new.id


def test_adapter_evidence_changes_contract_not_semantic_object_identity():
    obj = _future_object()
    a = AdapterContract(
        "adapter.x", 1, "source", "target", ("effect.compose@2",),
        evidence_refs=("evidence:A",),
    )
    b = AdapterContract(
        "adapter.x", 1, "source", "target", ("effect.compose@2",),
        evidence_refs=("evidence:B",),
    )
    assert a.id != b.id
    assert obj.id == _future_object().id
