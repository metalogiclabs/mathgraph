"""Compile the qualified FreyPackage object plus Frey-curve operations into one Crystal waist."""

from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import AdapterContract, SemanticObject, canonical_bytes


@dataclass(frozen=True)
class FreyPackageSemanticBundle:
    canonical_object: SemanticObject
    source_objects: tuple[SemanticObject, ...]
    adapters: tuple[AdapterContract, ...]
    interface_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema":"mathgraph.compiled-frey-package-semantic-bundle.v1",
            "canonical_object_id":self.canonical_object.id,
            "source_object_ids":[x.id for x in self.source_objects],
            "adapter_contract_ids":[x.id for x in self.adapters],
            "interface_ids":list(self.interface_ids),
            "source_count":len(self.source_objects),
        }


def compile_frey_package_bundle(
    schema_authority: Mapping[str, Any],
    operation_authority: Mapping[str, Any],
) -> FreyPackageSemanticBundle:
    if schema_authority.get("status")!="WARRANTED_BOUNDED_RECONCILIATION":
        raise ValueError("warranted FreyPackage schema authority required")
    if operation_authority.get("status")!="WARRANTED_BOUNDED_OPERATION_RECONCILIATION":
        raise ValueError("warranted Frey operation authority required")
    if operation_authority.get("parent_candidate")!="equiv:FreyPackage":
        raise ValueError("operation authority does not refine FreyPackage candidate")

    s_auth=dict(schema_authority["authority"])
    o_auth=dict(operation_authority["authority"])
    schema=dict(schema_authority["schema_equivalence"])
    operations=dict(operation_authority["operation_schema"])

    interfaces=(
        "lean.number-theory.frey-package.schema@1",
        "lean.number-theory.frey-package.nonempty@1",
        "lean.number-theory.frey-package.is-empty@1",
        "lean.number-theory.frey-package.frey-curve-int@1",
        "lean.number-theory.frey-package.frey-curve@1",
    )

    canonical=SemanticObject(
        "lean.canonical-project-local-semantic-bundle@1",
        1,
        canonical_bytes({
            "name":"FreyPackage",
            "schema_digest":schema["semantic_digest"],
            "operation_digest":operations["semantic_digest"],
            "canonical_view":schema_authority["canonical_view"],
            "operations":operations["operations"],
            "provenance_note":schema_authority["provenance_note"],
            "schema_authority_run":s_auth["run_id"],
            "operation_authority_run":o_auth["run_id"],
            "revocation_boundary":[
                *schema_authority["revocation_boundary"],
                *operation_authority["revocation_boundary"],
            ],
        }),
        interfaces,
    )

    env_by={x["corpus"]:x for x in schema_authority["environments"]}
    source_blobs={
        "anthropic-flt":{
            "schema":schema["anthropic_blob_sha"],
            "operations":operations["anthropic_source_blob"],
        },
        "imperial-flt":{
            "schema":schema["imperial_blob_sha"],
            "operations":operations["imperial_source_blob"],
        },
    }
    sources=[]; adapters=[]
    for corpus in ("anthropic-flt","imperial-flt"):
        env=env_by[corpus]
        source_space=(
            f"lean.corpus.{corpus}.mathlib-{env['mathlib_commit'][:12]}"
            f".toolchain-{str(env['lean_toolchain']).split(':')[-1]}@1"
        )
        blobs=source_blobs[corpus]
        sources.append(SemanticObject(
            "lean.versioned-project-local-semantic-bundle@1",
            1,
            canonical_bytes({
                "corpus":corpus,
                "schema_blob":blobs["schema"],
                "operation_blob":blobs["operations"],
                "schema_digest":schema["semantic_digest"],
                "operation_digest":operations["semantic_digest"],
                "mathlib_commit":env["mathlib_commit"],
                "lean_toolchain":env["lean_toolchain"],
            }),
            interfaces,
        ))
        adapters.append(AdapterContract(
            f"frey-package-bundle:{corpus}-to-canonical",
            1,
            source_space,
            "mathgraph.number-theory.frey-package@1",
            interfaces,
            assumption_refs=(
                f"schema-digest:{schema['semantic_digest']}",
                f"operation-digest:{operations['semantic_digest']}",
            ),
            evidence_refs=(
                f"github-run:{s_auth['run_id']}",
                f"github-run:{o_auth['run_id']}",
                f"schema-artifact:{s_auth['result_artifact_id']}:{s_auth['result_artifact_digest']}",
                f"operation-artifact:{o_auth['result_artifact_id']}:{o_auth['result_artifact_digest']}",
            ),
        ))

    return FreyPackageSemanticBundle(
        canonical_object=canonical,
        source_objects=tuple(sources),
        adapters=tuple(adapters),
        interface_ids=interfaces,
    )


def compile_files(schema_path, operation_path, out_path=None):
    schema=json.loads(Path(schema_path).read_text())
    operations=json.loads(Path(operation_path).read_text())
    bundle=compile_frey_package_bundle(schema,operations)
    out=bundle.to_dict()
    out["schema_digest"]=schema["schema_equivalence"]["semantic_digest"]
    out["operation_digest"]=operations["operation_schema"]["semantic_digest"]
    out["status"]="REUSABLE"
    if out_path:
        Path(out_path).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    return out
