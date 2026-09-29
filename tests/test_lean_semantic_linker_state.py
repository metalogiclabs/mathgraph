import json
from pathlib import Path

import pytest

from mathgraph.crystal import UnknownSemantics, interpret_semantic_object
from mathgraph.lean_semantic_linker_state import compile_linker_state

AUTH=Path("evidence/crystal-origin-first-linker-v1.json")


def test_zero_actionable_linker_state_compiles_to_crystal_memory():
    authority=json.loads(AUTH.read_text())
    obj=compile_linker_state(authority)
    assert obj.id.startswith("semantic:")
    assert authority["combined_state"]=={
        "candidate_count":82,
        "qualified_reusable_count":9,
        "discharged_non_bridge_count":64,
        "rejected_false_candidate_count":9,
        "unknown_actionable_count":0,
    }


def test_linker_state_is_fail_closed_outside_advertised_interfaces():
    authority=json.loads(AUTH.read_text())
    obj=compile_linker_state(authority)
    result=interpret_semantic_object(
        obj,
        "lean.corpus-linker.universal-equivalence@1",
        {},
    )
    assert isinstance(result,UnknownSemantics)


def test_nonwarranted_or_nonzero_residual_cannot_compile_as_closed_state():
    authority=json.loads(AUTH.read_text())
    authority["status"]="CANDIDATE"
    with pytest.raises(ValueError):
        compile_linker_state(authority)

    authority=json.loads(AUTH.read_text())
    authority["combined_state"]["unknown_actionable_count"]=1
    with pytest.raises(ValueError):
        compile_linker_state(authority)
