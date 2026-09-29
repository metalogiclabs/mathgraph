import json
from pathlib import Path

import pytest

from mathgraph.crystal import SemanticObject, UnknownTranslation, lower_semantic_object
from mathgraph.lean_transparent_wrapper_bridge import compile_transparent_wrapper_bridge

AUTH=Path("evidence/crystal-transparent-wrapper-bridge-v1.json")


def test_different_name_bridge_composes_source_to_consumer():
    authority=json.loads(AUTH.read_text())
    cap=compile_transparent_wrapper_bridge(authority)
    assert cap.composed.source_space=="lean.corpus.teorth-pfr.finite-range@1"
    assert cap.composed.target_space=="lean.corpus.anthropic-flt.finite-range-consumer@1"
    assert cap.composed.preserves_interfaces==(cap.interface_id,)

    lowered=lower_semantic_object(
        cap.source_object,
        cap.composed,
        cap.interface_id,
        lambda _: cap.canonical_object,
    )
    assert isinstance(lowered,SemanticObject)
    assert lowered.id==cap.canonical_object.id


def test_bridge_fails_closed_outside_finite_range_interface():
    authority=json.loads(AUTH.read_text())
    cap=compile_transparent_wrapper_bridge(authority)
    bad=lower_semantic_object(
        cap.source_object,
        cap.composed,
        "function.compact-range@1",
        lambda _: cap.canonical_object,
    )
    assert isinstance(bad,UnknownTranslation)
    assert bad.reason=="outside_preservation_contract"


def test_candidate_cannot_enter_memory_without_warrant():
    authority=json.loads(AUTH.read_text())
    authority["status"]="CANDIDATE"
    with pytest.raises(ValueError):
        compile_transparent_wrapper_bridge(authority)
