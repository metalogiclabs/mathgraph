from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import (
    SemanticObject,
    UnknownTranslation,
    translate_semantic_object,
)
from mathgraph.prism_adapter import (
    PRISM_REACHABILITY_INTERFACE,
    PRISM_REWARD_INTERFACE,
    adapt_prism_imdp,
    reachability_extrema,
)


PINS = json.loads(
    Path("evidence/crystal-v1-source-pins.json").read_text(encoding="utf-8")
)["sources"]


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def _fetch_pin(name: str) -> tuple[str, dict]:
    pin = PINS[name]
    url = (
        "https://raw.githubusercontent.com/"
        f"{pin['repository']}/{pin['commit']}/{pin['path']}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mathgraph-prism-adapter-gate"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    assert _git_blob_sha(data) == pin["blob_sha"]
    return data.decode("utf-8"), pin


def _adapt():
    source, pin = _fetch_pin("prism_uncertain_robot")
    source_ref = (
        f"{pin['repository']}@{pin['commit']}:{pin['path']}"
        f"#gitblob={pin['blob_sha']}"
    )
    return adapt_prism_imdp(
        source,
        delta="0.1",
        source_ref=source_ref,
    )


def test_source_pinned_prism_model_lowers_to_generic_typed_interval_effects():
    adapted = _adapt()
    model = adapted.model

    assert model.states == ("s0", "s1", "s2", "s3", "s4", "s5")
    assert model.states_for_label("goal1") == ("s5",)

    s1 = model.actions_from("s1")
    assert len(s1) == 2
    east = next(action for action in s1 if action.action == "east")
    south = next(action for action in s1 if action.action == "south")

    assert tuple(
        (outcome.target, outcome.lower, outcome.upper)
        for outcome in east.effect.outcomes
    ) == (
        ("s2", "0.8", "0.9"),
        ("s1", "0.1", "0.2"),
    )
    assert tuple(
        (outcome.target, outcome.lower, outcome.upper)
        for outcome in south.effect.outcomes
    ) == (
        ("s4", "0.4", "0.6"),
        ("s2", "0.4", "0.6"),
    )

    obj = adapted.semantic_object
    assert isinstance(obj, SemanticObject)
    assert obj.type_id == "mathgraph.interval-mdp"
    assert obj.interfaces == (PRISM_REACHABILITY_INTERFACE,)


def test_mathgraph_independent_reachability_matches_prism_quantitative_boundary():
    adapted = _adapt()
    worst, best = reachability_extrema(
        adapted.model,
        target_label="goal1",
    )

    assert abs(worst - Decimal("0.4")) < Decimal("1e-12")
    assert abs(best - Decimal("0.6")) < Decimal("1e-12")
    assert best - worst > Decimal("0.19")


def test_adapter_contract_preserves_reachability_interface_byte_for_byte():
    adapted = _adapt()
    obj = adapted.semantic_object
    before = obj.to_bytes()

    translated = translate_semantic_object(
        obj,
        adapted.contract,
        PRISM_REACHABILITY_INTERFACE,
    )
    assert isinstance(translated, SemanticObject)
    assert translated.id == obj.id
    assert translated.to_bytes() == before


def test_reward_semantics_is_deliberately_outside_adapter_contract():
    adapted = _adapt()
    obj = adapted.semantic_object

    result = translate_semantic_object(
        obj,
        adapted.contract,
        PRISM_REWARD_INTERFACE,
    )
    assert result == UnknownTranslation(
        object_id=obj.id,
        adapter_contract_id=adapted.contract.id,
        requested_interface=PRISM_REWARD_INTERFACE,
        reason="outside_preservation_contract",
    )


def test_transition_change_changes_adapted_semantic_identity():
    source, pin = _fetch_pin("prism_uncertain_robot")
    source_ref = (
        f"{pin['repository']}@{pin['commit']}:{pin['path']}"
        f"#gitblob={pin['blob_sha']}"
    )
    base = adapt_prism_imdp(
        source,
        delta="0.1",
        source_ref=source_ref,
    )
    mutated_source = source.replace(
        "0.6:(s'=1) + 0.4:(s'=0)",
        "0.7:(s'=1) + 0.3:(s'=0)",
        1,
    )
    mutated = adapt_prism_imdp(
        mutated_source,
        delta="0.1",
        source_ref=source_ref + ":derived-transition-mutation",
    )

    assert base.semantic_object.id != mutated.semantic_object.id
