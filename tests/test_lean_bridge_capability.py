import json
from pathlib import Path

import pytest

from mathgraph.crystal import UnknownTranslation, translate_semantic_object
from mathgraph.lean_bridge_capability import (
    compile_authority_file,
    compile_warranted_bridge,
)


AUTHORITY = Path("evidence/crystal-auto-bridge-discovery-v1.json")


def test_warranted_bridge_compiles_to_content_addressed_crystal_capability() -> None:
    result = compile_authority_file(AUTHORITY)
    assert result["authority_status"] == "WARRANTED_BOUNDED_REUSABLE"
    assert result["interface_id"] == "lean.consequence.is-weakly-regular@1"
    assert result["semantic_object_id"].startswith("semantic:")
    assert result["adapter_contract_id"].startswith("adapter:")
    assert result["source_space"] == "lean.corpus.anthropic-flt@1"
    assert result["target_space"] == "lean.corpus.imperial-flt@1"


def test_compiled_capability_transports_only_inside_qualified_interface() -> None:
    authority = json.loads(AUTHORITY.read_text())
    compiled = compile_warranted_bridge(authority)
    ok = translate_semantic_object(
        compiled.semantic_object,
        compiled.adapter_contract,
        compiled.interface_id,
    )
    assert ok.id == compiled.semantic_object.id

    bad = translate_semantic_object(
        compiled.semantic_object,
        compiled.adapter_contract,
        "lean.consequence.is-regular@1",
    )
    assert isinstance(bad, UnknownTranslation)
    assert bad.reason == "outside_preservation_contract"


def test_unwarranted_bridge_cannot_be_compiled() -> None:
    authority = json.loads(AUTHORITY.read_text())
    authority["status"] = "CANDIDATE"
    with pytest.raises(ValueError):
        compile_warranted_bridge(authority)
