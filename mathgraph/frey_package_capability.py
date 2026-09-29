"""Compile warranted FreyPackage reconciliation into Crystal semantic memory."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import AdapterContract, SemanticObject, canonical_bytes


@dataclass(frozen=True)
class FreyPackageCapability:
    canonical_object: SemanticObject
    source_objects: tuple[SemanticObject, ...]
    adapters: tuple[AdapterContract, ...]
    interface_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema":"mathgraph.compiled-frey-package-capability.v1",
            "canonical_object_id":self.canonical_object.id,
            "source_object_ids":[x.id for x in self.source_objects],
            "adapter_contract_ids":[x.id for x in self.adapters],
            "interface_ids":list(self.interface_ids),
            "source_spaces":[x.source_space for x in self.adapters],
            "target_space":self.adapters[0].target_space if self.adapters else None,
            "source_count":len(self.source_objects),
        }


def compile_frey_package_capability(
    authority: Mapping[str, Any],
) -> FreyPackageCapability:
    if authority.get("status") != "WARRANTED_BOUNDED_RECONCILIATION":
        raise ValueError("warranted FreyPackage reconciliation required")

    auth=dict(authority["authority"])
    schema=dict(authority["schema_equivalence"])
    interfaces=(
        "lean.number-theory.frey-package.schema@1",
        "lean.number-theory.frey-package.nonempty@1",
        "lean.number-theory.frey-package.is-empty@1",
    )
    target_space="mathgraph.number-theory.frey-package@1"

    canonical=SemanticObject(
        "lean.canonical-project-local-object@1",
        1,
        canonical_bytes({
            "name":"FreyPackage",
            "semantic_digest":schema["semantic_digest"],
            "view":authority["canonical_view"],
            "provenance_note":authority["provenance_note"],
            "authority_run":auth["run_id"],
            "authority_head_sha":auth["head_sha"],
            "revocation_boundary":authority["revocation_boundary"],
        }),
        interfaces,
    )

    sources=[]
    adapters=[]
    for env in authority["environments"]:
        corpus=str(env["corpus"])
        blob=(schema["anthropic_blob_sha"] if corpus=="anthropic-flt"
              else schema["imperial_blob_sha"])
        source_space=(
            f"lean.corpus.{corpus}.mathlib-{env['mathlib_commit'][:12]}"
            f".toolchain-{str(env['lean_toolchain']).split(':')[-1]}@1"
        )
        sources.append(SemanticObject(
            "lean.versioned-project-local-object@1",
            1,
            canonical_bytes({
                "corpus":corpus,
                "source_blob_sha":blob,
                "mathlib_commit":env["mathlib_commit"],
                "lean_toolchain":env["lean_toolchain"],
                "semantic_digest":schema["semantic_digest"],
            }),
            interfaces,
        ))
        adapters.append(AdapterContract(
            f"frey-package:{corpus}-to-canonical",
            1,
            source_space,
            target_space,
            interfaces,
            assumption_refs=(
                f"semantic-digest:{schema['semantic_digest']}",
                f"source-blob:{blob}",
            ),
            evidence_refs=(
                f"github-run:{auth['run_id']}",
                f"git-head:{auth['head_sha']}",
                f"github-artifact:{auth['result_artifact_id']}:{auth['result_artifact_digest']}",
            ),
        ))

    return FreyPackageCapability(
        canonical_object=canonical,
        source_objects=tuple(sources),
        adapters=tuple(adapters),
        interface_ids=interfaces,
    )


def compile_authority_file(authority_path, out_path=None):
    authority=json.loads(Path(authority_path).read_text())
    capability=compile_frey_package_capability(authority)
    out=capability.to_dict()
    out["authority_status"]=authority["status"]
    out["semantic_digest"]=authority["schema_equivalence"]["semantic_digest"]
    out["provenance_note"]=authority["provenance_note"]
    out["unknowns"]=authority["unknowns"]
    if out_path:
        Path(out_path).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    return out
