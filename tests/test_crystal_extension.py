from __future__ import annotations

from mathgraph.crystal import (
    Hyperedge,
    SemanticObject,
    UnknownSemantics,
    interpret_semantic_object,
)


def _future_object() -> SemanticObject:
    return SemanticObject(
        type_id="effect.weird.future.physics",
        contract_version=1,
        payload=b"\\x00\\xffFUTURE\\x00\\x10\\x80opaque-payload\\x00",
        interfaces=(
            "future.physics@1",
            "effect.compose@2",
            "future.physics@1",
        ),
    )


def test_unknown_future_type_round_trips_losslessly():
    future = _future_object()
    wire = future.to_bytes()
    received = SemanticObject.from_bytes(wire)

    assert received.type_id == "effect.weird.future.physics"
    assert received.contract_version == 1
    assert received.payload == future.payload
    assert received.interfaces == ("effect.compose@2", "future.physics@1")
    assert received.to_bytes() == wire
    assert received.id == future.id


def test_unknown_future_type_can_be_stored_referenced_and_retransmitted():
    future = _future_object()
    wire = future.to_bytes()

    # Old runtime storage is opaque: identity points to exact envelope bytes.
    store = {future.id: wire}
    restored = SemanticObject.from_bytes(store[future.id])
    assert restored.id == future.id
    assert restored.to_bytes() == wire

    # Existing Crystal objects may carry the future semantic object in
    # provenance/evidence without claiming authority for its interpretation.
    edge = Hyperedge(
        "q0",
        "q1",
        "future-effect-reference",
        evidence_refs=(future.id,),
    )
    assert edge.evidence_refs == (future.id,)


def test_missing_future_interface_returns_typed_unknown_without_mutation():
    future = _future_object()
    before_wire = future.to_bytes()
    before_id = future.id

    result = interpret_semantic_object(
        future,
        "future.physics@1",
        interpreters={},
    )
    assert result == UnknownSemantics(
        object_id=before_id,
        requested_interface="future.physics@1",
    )
    assert future.to_bytes() == before_wire
    assert future.id == before_id


def test_future_runtime_can_add_interpretation_without_changing_old_meaning_bytes():
    future = _future_object()
    before_wire = future.to_bytes()
    before_id = future.id

    result = interpret_semantic_object(
        future,
        "future.physics@1",
        interpreters={
            "future.physics@1": lambda obj: (
                "interpreted-via-interface",
                obj.payload.hex(),
            )
        },
    )
    assert result == ("interpreted-via-interface", future.payload.hex())
    assert future.to_bytes() == before_wire
    assert future.id == before_id


def test_interface_order_does_not_change_canonical_identity():
    a = SemanticObject(
        "effect.example",
        7,
        b"same",
        ("z@1", "a@1", "z@1"),
    )
    b = SemanticObject(
        "effect.example",
        7,
        b"same",
        ("a@1", "z@1"),
    )
    assert a.interfaces == b.interfaces == ("a@1", "z@1")
    assert a.to_bytes() == b.to_bytes()
    assert a.id == b.id


def test_noncanonical_transport_is_rejected_not_silently_rewritten():
    canonical = SemanticObject(
        "effect.example",
        1,
        b"payload",
        ("a@1", "z@1"),
    ).to_bytes()

    # Rebuild the same semantic fields with interface order z,a. The decoder
    # must reject this transport rather than normalize it behind the caller.
    magic = canonical[:6]
    type_bytes = b"effect.example"
    payload = b"payload"
    noncanonical = (
        magic
        + len(type_bytes).to_bytes(4, "big")
        + type_bytes
        + (1).to_bytes(4, "big")
        + (2).to_bytes(4, "big")
        + (3).to_bytes(4, "big") + b"z@1"
        + (3).to_bytes(4, "big") + b"a@1"
        + len(payload).to_bytes(8, "big")
        + payload
    )
    assert noncanonical != canonical
    try:
        SemanticObject.from_bytes(noncanonical)
    except ValueError as exc:
        assert "non-canonical" in str(exc)
    else:
        raise AssertionError("non-canonical transport must be rejected")

def test_known_interface_can_dispatch_on_unknown_concrete_type():
    future = _future_object()
    before_wire = future.to_bytes()
    before_id = future.id

    result = interpret_semantic_object(
        future,
        "effect.compose@2",
        interpreters={
            "effect.compose@2": lambda obj: (
                "generic-interface-dispatch",
                obj.type_id,
                obj.id,
            )
        },
    )
    assert result == (
        "generic-interface-dispatch",
        "effect.weird.future.physics",
        before_id,
    )
    assert future.to_bytes() == before_wire
    assert future.id == before_id
