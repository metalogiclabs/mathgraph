from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import (
    SemanticObject,
    UnknownTranslation,
    compose_adapter_contracts,
    compose_lower_semantic_object,
    lower_semantic_object,
)
from mathgraph.prism_adapter import (
    PRISM_REACHABILITY_INTERFACE,
    adapt_prism_imdp,
    reachability_extrema,
)
from mathgraph.prism_quotient import (
    STATE_IDENTITY_INTERFACE,
    quotient_interval_mdp,
)


PINS = json.loads(
    Path("evidence/crystal-v1-source-pins.json").read_text(encoding="utf-8")
)["sources"]


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def _source():
    pin = PINS["prism_uncertain_robot"]
    url = (
        "https://raw.githubusercontent.com/"
        f"{pin['repository']}/{pin['commit']}/{pin['path']}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mathgraph-prism-quotient-gate"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    assert _git_blob_sha(data) == pin["blob_sha"]
    source_ref = (
        f"{pin['repository']}@{pin['commit']}:{pin['path']}"
        f"#gitblob={pin['blob_sha']}"
    )
    return data.decode("utf-8"), source_ref


def _adapt():
    source, source_ref = _source()
    return source, adapt_prism_imdp(
        source,
        delta="0.1",
        source_ref=source_ref,
    )


def _safe_map():
    return {
        "s0": "s0",
        "s1": "s1",
        "s2": "dead",
        "s3": "dead",
        "s4": "s4",
        "s5": "s5",
    }


def _bad_map():
    return {
        "s0": "s0",
        "s1": "s1",
        "s2": "dead",
        "s3": "dead",
        "s4": "dead",
        "s5": "s5",
    }


def test_safe_consequential_quotient_reduces_state_space():
    _, adapted = _adapt()
    quotient = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )

    assert len(adapted.model.states) == 6
    assert len(quotient.model.states) == 5
    assert quotient.model.states == ("dead", "s0", "s1", "s4", "s5")
    assert quotient.model.states_for_label("goal1") == ("s5",)
    assert quotient.model.states_for_label("goal2") == ("dead",)


def test_safe_quotient_preserves_protected_reachability_exactly():
    _, adapted = _adapt()
    quotient = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )

    original = reachability_extrema(adapted.model, target_label="goal1")
    reduced = reachability_extrema(quotient.model, target_label="goal1")

    assert abs(original[0] - Decimal("0.4")) < Decimal("1e-12")
    assert abs(original[1] - Decimal("0.6")) < Decimal("1e-12")
    assert reduced == original


def test_overquotient_is_rejected_by_protected_future_separator():
    _, adapted = _adapt()
    safe = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )
    bad = quotient_interval_mdp(
        adapted.model,
        _bad_map(),
        partition_id="bad-merge-s4-into-dead",
    )

    safe_result = reachability_extrema(safe.model, target_label="goal1")
    bad_result = reachability_extrema(bad.model, target_label="goal1")

    assert safe_result[0] > Decimal("0.39")
    assert safe_result[1] > Decimal("0.59")
    # The over-quotient unions s4's goal-reaching action into the merged
    # dead class, creating spurious max-resolver control power.
    assert bad_result == (Decimal(1), Decimal(1))
    assert bad_result != safe_result


def test_quotient_contract_discards_state_identity_as_unknown():
    _, adapted = _adapt()
    quotient = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )

    result = lower_semantic_object(
        adapted.semantic_object,
        quotient.contract,
        STATE_IDENTITY_INTERFACE,
        lambda _: quotient.semantic_object,
    )
    assert result == UnknownTranslation(
        object_id=adapted.semantic_object.id,
        adapter_contract_id=quotient.contract.id,
        requested_interface=STATE_IDENTITY_INTERFACE,
        reason="outside_preservation_contract",
    )


def test_real_prism_to_quotient_contract_composes_on_reachability_only():
    source, adapted = _adapt()
    quotient = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )
    composed = compose_adapter_contracts(adapted.contract, quotient.contract)

    assert composed.source_space == adapted.contract.source_space
    assert composed.target_space == quotient.contract.target_space
    assert composed.preserves_interfaces == (PRISM_REACHABILITY_INTERFACE,)

    source_obj = SemanticObject(
        type_id=adapted.contract.source_space,
        contract_version=1,
        payload=source.encode("utf-8"),
        interfaces=(PRISM_REACHABILITY_INTERFACE,),
    )

    def lower_prism(obj: SemanticObject) -> SemanticObject:
        assert obj.payload.decode("utf-8") == source
        return adapted.semantic_object

    def lower_quotient(obj: SemanticObject) -> SemanticObject:
        assert obj.id == adapted.semantic_object.id
        return quotient.semantic_object

    result = compose_lower_semantic_object(
        source_obj,
        adapted.contract,
        quotient.contract,
        PRISM_REACHABILITY_INTERFACE,
        lower_prism,
        lower_quotient,
    )
    assert isinstance(result, SemanticObject)
    assert result == quotient.semantic_object
    assert result.id != adapted.semantic_object.id


def test_composed_chain_keeps_discarded_identity_unknown():
    source, adapted = _adapt()
    quotient = quotient_interval_mdp(
        adapted.model,
        _safe_map(),
        partition_id="goal1-dead-s2-s3",
    )
    source_obj = SemanticObject(
        type_id=adapted.contract.source_space,
        contract_version=1,
        payload=source.encode("utf-8"),
        interfaces=(PRISM_REACHABILITY_INTERFACE,),
    )
    result = compose_lower_semantic_object(
        source_obj,
        adapted.contract,
        quotient.contract,
        STATE_IDENTITY_INTERFACE,
        lambda _: adapted.semantic_object,
        lambda _: quotient.semantic_object,
    )
    assert isinstance(result, UnknownTranslation)
    assert result.reason == "outside_preservation_contract"
