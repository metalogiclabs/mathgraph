import json
from pathlib import Path

from mathgraph.crystal import SemanticObject, UnknownTranslation, lower_semantic_object
from mathgraph.frey_package_semantic_bundle import compile_frey_package_bundle

SCHEMA=Path("evidence/crystal-frey-package-reconciliation-v1.json")
OPS=Path("evidence/crystal-frey-curve-operation-v1.json")


def test_object_and_operations_share_one_canonical_semantic_waist():
    bundle=compile_frey_package_bundle(
        json.loads(SCHEMA.read_text()),json.loads(OPS.read_text())
    )
    assert len(bundle.interface_ids)==5
    assert len(bundle.source_objects)==2
    for interface in bundle.interface_ids:
        ids=[]
        for source,adapter in zip(bundle.source_objects,bundle.adapters):
            lowered=lower_semantic_object(
                source,adapter,interface,lambda _:bundle.canonical_object
            )
            assert isinstance(lowered,SemanticObject)
            ids.append(lowered.id)
        assert ids==[bundle.canonical_object.id]*2


def test_unqualified_downstream_lemma_remains_unknown():
    bundle=compile_frey_package_bundle(
        json.loads(SCHEMA.read_text()),json.loads(OPS.read_text())
    )
    out=lower_semantic_object(
        bundle.source_objects[0],bundle.adapters[0],
        "lean.number-theory.frey-package.j-invariant-lemma@1",
        lambda _:bundle.canonical_object,
    )
    assert isinstance(out,UnknownTranslation)
    assert out.reason=="outside_preservation_contract"
