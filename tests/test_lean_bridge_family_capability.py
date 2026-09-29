import json
from pathlib import Path

import pytest

from mathgraph.crystal import UnknownTranslation, translate_semantic_object
from mathgraph.lean_bridge_family_capability import compile_bridge_family

AUTH=Path("evidence/crystal-directional-bridge-batch-v2.json")


def test_six_producers_share_one_qualified_interface_without_collapsing_identity() -> None:
    authority=json.loads(AUTH.read_text())
    family=compile_bridge_family(authority)
    assert len(family.producer_objects)==6
    assert len({x.id for x in family.producer_objects})==6
    assert all(x.interfaces==(family.interface_id,) for x in family.producer_objects)


def test_one_adapter_transports_all_six_and_fails_closed_outside_interface() -> None:
    authority=json.loads(AUTH.read_text())
    family=compile_bridge_family(authority)
    for obj in family.producer_objects:
        moved=translate_semantic_object(obj,family.adapter_contract,family.interface_id)
        assert moved.id==obj.id

    bad=translate_semantic_object(
        family.producer_objects[0],
        family.adapter_contract,
        "lean.consequence.ring-theory.sequence.is-regular@1",
    )
    assert isinstance(bad,UnknownTranslation)
    assert bad.reason=="outside_preservation_contract"


def test_unwarranted_family_cannot_enter_crystal_memory() -> None:
    authority=json.loads(AUTH.read_text())
    authority["status"]="CANDIDATE"
    with pytest.raises(ValueError):
        compile_bridge_family(authority)
