from __future__ import annotations

from mathgraph.crystal import AdapterContract, compose_adapter_contracts


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
