from __future__ import annotations

from adapters.tla_peterson_refinement import (
    COMPOSED_OCCUPANCY_CONTRACT,
    CONTROL_INTERFACE,
    LOCK_TO_OCCUPANCY_CONTRACT,
    OCCUPANCY_INTERFACE,
    PETERSON_INIT,
    PETERSON_TO_LOCK_OCCUPANCY_CONTRACT,
    composition_qualification_report,
    lower_peterson_to_occupancy,
    peterson_state_object_v2,
)
from mathgraph.crystal import (
    SemanticObject,
    UnknownTranslation,
    compose_adapter_contracts,
)


def test_composed_contract_is_mechanical_interface_intersection():
    composed = compose_adapter_contracts(
        PETERSON_TO_LOCK_OCCUPANCY_CONTRACT,
        LOCK_TO_OCCUPANCY_CONTRACT,
        adapter_id="tla.peterson-to-critical-occupancy",
    )
    assert composed == COMPOSED_OCCUPANCY_CONTRACT
    assert composed.preserves_interfaces == (OCCUPANCY_INTERFACE,)
    assert CONTROL_INTERFACE not in composed.preserves_interfaces
    assert f"adapter-contract:{PETERSON_TO_LOCK_OCCUPANCY_CONTRACT.id}" in composed.evidence_refs
    assert f"adapter-contract:{LOCK_TO_OCCUPANCY_CONTRACT.id}" in composed.evidence_refs


def test_composed_lowering_matches_direct_observation_on_all_reachable_states():
    report = composition_qualification_report()
    assert report["reachable_states"] == 42
    assert report["direct_mismatches"] == ()
    assert report["staged_mismatches"] == ()
    assert report["composed_interfaces"] == (OCCUPANCY_INTERFACE,)


def test_missing_interface_in_second_leg_becomes_unknown_in_composite():
    source = peterson_state_object_v2(PETERSON_INIT)
    result = lower_peterson_to_occupancy(source, CONTROL_INTERFACE)
    assert result == UnknownTranslation(
        object_id=source.id,
        adapter_contract_id=COMPOSED_OCCUPANCY_CONTRACT.id,
        requested_interface=CONTROL_INTERFACE,
        reason="outside_preservation_contract",
    )


def test_composed_occupancy_lowering_is_nonidentity():
    source = peterson_state_object_v2(PETERSON_INIT)
    result = lower_peterson_to_occupancy(source, OCCUPANCY_INTERFACE)
    assert isinstance(result, SemanticObject)
    assert result.type_id == "tla.critical-occupancy"
    assert result.id != source.id
    assert result.interfaces == (OCCUPANCY_INTERFACE,)
