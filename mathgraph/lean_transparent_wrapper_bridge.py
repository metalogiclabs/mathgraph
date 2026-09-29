"""Compile the qualified PFR→canonical→Anthropic finite-range bridge."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import (
    AdapterContract,
    SemanticObject,
    canonical_bytes,
    compose_adapter_contracts,
)


@dataclass(frozen=True)
class TransparentWrapperBridgeCapability:
    source_object: SemanticObject
    canonical_object: SemanticObject
    source_to_canonical: AdapterContract
    canonical_to_consumer: AdapterContract
    composed: AdapterContract
    interface_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema":"mathgraph.compiled-transparent-wrapper-bridge.v1",
            "interface_id":self.interface_id,
            "source_object_id":self.source_object.id,
            "canonical_object_id":self.canonical_object.id,
            "source_to_canonical_adapter_id":self.source_to_canonical.id,
            "canonical_to_consumer_adapter_id":self.canonical_to_consumer.id,
            "composed_adapter_id":self.composed.id,
            "source_space":self.composed.source_space,
            "target_space":self.composed.target_space,
        }


def compile_transparent_wrapper_bridge(
    authority: Mapping[str, Any],
) -> TransparentWrapperBridgeCapability:
    if authority.get("status") != "WARRANTED_BOUNDED_REUSABLE":
        raise ValueError("transparent-wrapper bridge requires warranted authority")

    interface_id=str(authority["canonical_interface"]["interface_id"])
    run=int(authority["authority"]["run_id"])
    artifact_id=int(authority["authority"]["artifact_id"])
    artifact_digest=str(authority["authority"]["artifact_digest"])
    head=str(authority["authority"]["head_sha"])

    source=authority["source"]
    consumer=authority["consumer"]

    source_space="lean.corpus.teorth-pfr.finite-range@1"
    canonical_space="mathgraph.function-finite-range@1"
    consumer_space="lean.corpus.anthropic-flt.finite-range-consumer@1"

    source_object=SemanticObject(
        "lean.project-local-transparent-wrapper@1",
        1,
        canonical_bytes({
            "corpus":source["corpus"],
            "commit":source["commit"],
            "path":source["path"],
            "blob_sha":source["blob_sha"],
            "source_interface":source["source_interface"],
            "qualified_equivalence":authority["canonical_interface"]["law"],
        }),
        (interface_id,),
    )

    canonical_object=SemanticObject(
        "lean.canonical-proposition-interface@1",
        1,
        canonical_bytes({
            "canonical_proposition":authority["canonical_interface"]["proposition"],
            "consumer_corpus":consumer["corpus"],
            "consumer_declaration":consumer["declaration"],
            "consumer_blob_sha":consumer["blob_sha"],
        }),
        (interface_id,),
    )

    evidence=(
        f"github-run:{run}",
        f"github-artifact:{artifact_id}:{artifact_digest}",
        f"git-head:{head}",
    )

    source_to_canonical=AdapterContract(
        "pfr-finite-range-to-canonical-set-range-finite",
        1,
        source_space,
        canonical_space,
        (interface_id,),
        assumption_refs=(f"lean-law:{authority['canonical_interface']['law']}",),
        evidence_refs=evidence,
    )

    canonical_to_consumer=AdapterContract(
        "canonical-set-range-finite-to-anthropic-finite-range-integral",
        1,
        canonical_space,
        consumer_space,
        (interface_id,),
        assumption_refs=(f"consumer:{consumer['declaration']}",),
        evidence_refs=evidence,
    )

    composed=compose_adapter_contracts(source_to_canonical,canonical_to_consumer)

    return TransparentWrapperBridgeCapability(
        source_object=source_object,
        canonical_object=canonical_object,
        source_to_canonical=source_to_canonical,
        canonical_to_consumer=canonical_to_consumer,
        composed=composed,
        interface_id=interface_id,
    )


def compile_authority_file(path: str | Path, out_path: str | Path | None=None) -> dict[str,Any]:
    authority=json.loads(Path(path).read_text(encoding="utf-8"))
    cap=compile_transparent_wrapper_bridge(authority)
    out=cap.to_dict()
    out["status"]="REUSABLE"
    out["bridge_kind"]=authority["qualification"]["qualified_laws"]
    out["next_residual"]=authority["next_residual"]
    if out_path is not None:
        Path(out_path).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return out
