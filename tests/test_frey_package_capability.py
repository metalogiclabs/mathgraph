import json
from pathlib import Path

import pytest

from mathgraph.crystal import SemanticObject, UnknownTranslation, lower_semantic_object
from mathgraph.frey_package_capability import compile_frey_package_capability

AUTH=Path("evidence/crystal-frey-package-reconciliation-v1.json")


def test_two_versioned_frey_packages_lower_to_one_canonical_object():
    authority=json.loads(AUTH.read_text())
    cap=compile_frey_package_capability(authority)
    assert len(cap.source_objects)==2
    assert len({x.id for x in cap.source_objects})==2
    for interface in cap.interface_ids:
        lowered=[]
        for source,adapter in zip(cap.source_objects,cap.adapters):
            result=lower_semantic_object(
                source,adapter,interface,lambda _:cap.canonical_object
            )
            assert isinstance(result,SemanticObject)
            lowered.append(result.id)
        assert lowered==[cap.canonical_object.id]*2


def test_frey_package_capability_fails_closed_outside_warrant():
    authority=json.loads(AUTH.read_text())
    cap=compile_frey_package_capability(authority)
    bad=lower_semantic_object(
        cap.source_objects[0],
        cap.adapters[0],
        "lean.number-theory.frey-package.downstream-api@1",
        lambda _:cap.canonical_object,
    )
    assert isinstance(bad,UnknownTranslation)
    assert bad.reason=="outside_preservation_contract"


def test_unwarranted_reconciliation_cannot_enter_crystal_memory():
    authority=json.loads(AUTH.read_text())
    authority["status"]="CANDIDATE"
    with pytest.raises(ValueError):
        compile_frey_package_capability(authority)
