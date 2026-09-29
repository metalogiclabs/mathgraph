import json
from pathlib import Path

import pytest

from mathgraph.crystal import (
    SemanticObject,
    UnknownTranslation,
    lower_semantic_object,
)
from mathgraph.lean_cross_version_interface_capability import (
    compile_cross_version_interface,
)

AUTH = Path("evidence/crystal-cross-version-flt-interface-v1.json")


def test_three_version_sources_lower_to_one_canonical_semantic_object() -> None:
    authority = json.loads(AUTH.read_text())
    capability = compile_cross_version_interface(authority)
    assert len(capability.source_objects) == 3
    assert len(capability.adapters) == 3
    assert len({x.id for x in capability.source_objects}) == 3

    lowered = []
    for source, adapter in zip(capability.source_objects, capability.adapters):
        result = lower_semantic_object(
            source,
            adapter,
            capability.interface_id,
            lambda _: capability.canonical_object,
        )
        assert isinstance(result, SemanticObject)
        lowered.append(result.id)

    assert lowered == [capability.canonical_object.id] * 3


def test_cross_version_interface_fails_closed_outside_qualified_surface() -> None:
    authority = json.loads(AUTH.read_text())
    capability = compile_cross_version_interface(authority)
    bad = lower_semantic_object(
        capability.source_objects[0],
        capability.adapters[0],
        "lean.number-theory.fermat-last-theorem-with-int@1",
        lambda _: capability.canonical_object,
    )
    assert isinstance(bad, UnknownTranslation)
    assert bad.reason == "outside_preservation_contract"


def test_unwarranted_cross_version_candidate_cannot_enter_memory() -> None:
    authority = json.loads(AUTH.read_text())
    authority["status"] = "CANDIDATE"
    with pytest.raises(ValueError):
        compile_cross_version_interface(authority)
