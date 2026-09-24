from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from adapters.tla_peterson_refinement import (
    ADAPTER_CONTRACT,
    CONTROL_INTERFACE,
    PETERSON_INTERNAL_INTERFACE,
    REFINEMENT_INTERFACE,
    SOURCE_BLOB_SHA,
    SOURCE_COMMIT,
    SOURCE_PATH,
    SOURCE_REPOSITORY,
    LockState,
    PetersonState,
    lower_peterson_object,
    lower_state,
    peterson_state_object,
    qualification_report,
    reachable_peterson_states,
)
from mathgraph.crystal import SemanticObject, UnknownTranslation


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _fetch_source() -> str:
    url = (
        "https://raw.githubusercontent.com/"
        f"{SOURCE_REPOSITORY}/{SOURCE_COMMIT}/{SOURCE_PATH}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mathgraph-crystal-gate"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    assert _git_blob_sha(data) == SOURCE_BLOB_SHA
    return data.decode("utf-8")


def test_adapter_is_bound_to_exact_external_refinement_source():
    src = _fetch_source()
    assert 'pc_translation(label) ==' in src
    assert '(label \\in {"a1", "a2", "a3"}) -> "l1"' in src
    assert 'lock_translation == IF \\E p \\in ProcSet' in src
    assert "THEOREM Refinement == Spec => L!Spec" in src
    assert REFINEMENT_INTERFACE in ADAPTER_CONTRACT.preserves_interfaces


def test_exhaustive_reachable_refinement_has_no_violations():
    report = qualification_report()
    assert report["reachable_states"] == 42
    assert report["concrete_transitions"] > 0
    assert report["abstract_steps"] > 0
    assert report["abstract_stutters"] > 0
    assert report["violations"] == ()


def test_every_reachable_source_object_lowers_on_refinement_interface():
    for state in reachable_peterson_states():
        src_obj = peterson_state_object(state)
        result = lower_peterson_object(src_obj, REFINEMENT_INTERFACE)
        assert isinstance(result, SemanticObject)
        assert result.type_id == "tla.lock.state"
        assert result.contract_version == 1
        assert REFINEMENT_INTERFACE in result.interfaces
        assert result.id != src_obj.id


def test_control_interface_is_preserved_by_nonidentity_lowering():
    state = PetersonState("a2", "a0", True, False, 2)
    expected = lower_state(state)
    assert expected == LockState("l1", "l0", 1)

    result = lower_peterson_object(peterson_state_object(state), CONTROL_INTERFACE)
    assert isinstance(result, SemanticObject)
    payload = json.loads(result.payload.decode("utf-8"))
    assert payload == {
        "lock": 1,
        "pc": {"1": "l1", "2": "l0"},
    }


def test_peterson_only_internal_semantics_fail_closed_as_unknown():
    state = PetersonState("a2", "a0", True, False, 2)
    obj = peterson_state_object(state)
    before = obj.to_bytes()

    result = lower_peterson_object(obj, PETERSON_INTERNAL_INTERFACE)
    assert result == UnknownTranslation(
        object_id=obj.id,
        adapter_contract_id=ADAPTER_CONTRACT.id,
        requested_interface=PETERSON_INTERNAL_INTERFACE,
        reason="outside_preservation_contract",
    )
    assert obj.to_bytes() == before


def test_lowering_is_intentionally_many_to_one_only_inside_preserved_boundary():
    buckets = {}
    for state in reachable_peterson_states():
        buckets.setdefault(lower_state(state), []).append(state)

    merged = [states for states in buckets.values() if len(states) > 1]
    assert merged, "refinement should actually quotient concrete states"
    assert any(
        len({(s.c1, s.c2, s.turn) for s in states}) > 1
        for states in merged
    )


def test_adapter_contract_does_not_claim_peterson_internal_interface():
    assert PETERSON_INTERNAL_INTERFACE not in ADAPTER_CONTRACT.preserves_interfaces
    assert ADAPTER_CONTRACT.source_space.startswith("tla.peterson@")
    assert ADAPTER_CONTRACT.target_space.startswith("tla.lock@")
