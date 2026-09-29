"""Compile a warranted cross-version Lean interface into Crystal memory.

The source objects remain version-specific and provenance-bearing. Qualification
allows each pinned version to lower to one canonical semantic interface. This
does not claim that compiled proof objects or implementation-specific APIs can
be transported between Lean versions.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import (
    AdapterContract,
    SemanticObject,
    canonical_bytes,
)


@dataclass(frozen=True)
class CrossVersionInterfaceCapability:
    canonical_object: SemanticObject
    source_objects: tuple[SemanticObject, ...]
    adapters: tuple[AdapterContract, ...]
    interface_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mathgraph.compiled-cross-version-lean-interface.v1",
            "interface_id": self.interface_id,
            "canonical_object_id": self.canonical_object.id,
            "source_object_ids": [x.id for x in self.source_objects],
            "adapter_contract_ids": [x.id for x in self.adapters],
            "source_spaces": [x.source_space for x in self.adapters],
            "target_space": self.adapters[0].target_space if self.adapters else None,
            "version_count": len(self.source_objects),
        }


def compile_cross_version_interface(
    authority: Mapping[str, Any],
) -> CrossVersionInterfaceCapability:
    if authority.get("status") != "WARRANTED_BOUNDED_CROSS_VERSION_INTERFACE":
        raise ValueError("cross-version interface requires warranted authority")

    semantic = dict(authority["semantic_surface"])
    qualifications = list(authority["qualifications"])
    auth = dict(authority["authority"])

    interface_id = "lean.number-theory.fermat-last-theorem-for@1"
    target_space = "mathgraph.number-theory.flt@1"

    canonical_object = SemanticObject(
        "lean.canonical-semantic-interface@1",
        1,
        canonical_bytes({
            "canonical_symbol": authority["candidate_lineage"]["canonical_symbol"],
            "semantic_digest": semantic["digest"],
            "definitions": list(semantic["definitions"]),
            "protected_claim": authority["bounded_claim"],
            "authority_run": auth["run_id"],
            "authority_head_sha": auth["head_sha"],
            "revocation_boundary": list(authority.get("revocation_boundary", ())),
        }),
        (interface_id,),
    )

    source_objects = []
    adapters = []
    for item in qualifications:
        corpus = str(item["corpus"])
        source_space = (
            f"lean.corpus.{corpus}.mathlib-{item['mathlib_commit'][:12]}"
            f".toolchain-{str(item['lean_toolchain']).split(':')[-1]}@1"
        )
        source_objects.append(SemanticObject(
            "lean.versioned-theorem-interface@1",
            1,
            canonical_bytes({
                "corpus": corpus,
                "mathlib_commit": item["mathlib_commit"],
                "lean_toolchain": item["lean_toolchain"],
                "basic_blob_sha": item["basic_blob_sha"],
                "semantic_digest": semantic["digest"],
                "qualification_artifact_id": item["artifact_id"],
                "qualification_artifact_digest": item["artifact_digest"],
            }),
            (interface_id,),
        ))
        adapters.append(AdapterContract(
            f"flt-cross-version:{corpus}-to-canonical",
            1,
            source_space,
            target_space,
            (interface_id,),
            assumption_refs=(
                f"semantic-digest:{semantic['digest']}",
                f"source-blob:{item['basic_blob_sha']}",
            ),
            evidence_refs=(
                f"github-run:{auth['run_id']}",
                f"github-artifact:{item['artifact_id']}:{item['artifact_digest']}",
                f"git-head:{auth['head_sha']}",
            ),
        ))

    return CrossVersionInterfaceCapability(
        canonical_object=canonical_object,
        source_objects=tuple(source_objects),
        adapters=tuple(adapters),
        interface_id=interface_id,
    )


def compile_authority_file(
    authority_path: str | Path,
    *,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    authority = json.loads(Path(authority_path).read_text(encoding="utf-8"))
    capability = compile_cross_version_interface(authority)
    result = capability.to_dict()
    result["authority_status"] = authority["status"]
    result["semantic_digest"] = authority["semantic_surface"]["digest"]
    result["corpora"] = [x["corpus"] for x in authority["qualifications"]]
    result["unknowns"] = list(authority.get("unknowns", ()))
    if out_path is not None:
        Path(out_path).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result
