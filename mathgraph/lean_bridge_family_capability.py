"""Compile a verified directional Lean bridge family into Crystal memory.

One verified consequence law is shared by every qualified producer theorem.
Producer objects remain distinct; only their consumer-facing semantic interface
is shared. This avoids collapsing theorem-specific hypotheses or provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import AdapterContract, SemanticObject, canonical_bytes


@dataclass(frozen=True)
class CompiledBridgeFamily:
    law_object: SemanticObject
    producer_objects: tuple[SemanticObject, ...]
    adapter_contract: AdapterContract
    interface_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema":"mathgraph.compiled-lean-bridge-family.v1",
            "interface_id":self.interface_id,
            "law_object_id":self.law_object.id,
            "adapter_contract_id":self.adapter_contract.id,
            "producer_count":len(self.producer_objects),
            "producer_object_ids":[x.id for x in self.producer_objects],
            "source_space":self.adapter_contract.source_space,
            "target_space":self.adapter_contract.target_space,
            "evidence_refs":list(self.adapter_contract.evidence_refs),
        }


def compile_bridge_family(authority: Mapping[str, Any]) -> CompiledBridgeFamily:
    if authority.get("status") != "WARRANTED_BOUNDED_REUSABLE":
        raise ValueError("bridge family requires warranted bounded authority")

    auth=dict(authority["authority"])
    law=dict(authority["bridge_law"])
    qual=dict(authority["qualification"])
    promoted=list(authority["promoted"])

    interface_id="lean.consequence.ring-theory.sequence.is-weakly-regular@1"

    law_object=SemanticObject(
        "lean.verified-consequence-law@1",
        1,
        canonical_bytes({
            "source_interface":law["source_interface"],
            "target_interface":law["target_interface"],
            "witness":law["witness"],
            "authority_run":auth["run_id"],
            "authority_head_sha":auth["head_sha"],
            "artifact_digest":auth["artifact_digest"],
            "revocation_boundary":list(authority.get("revocation_boundary",())),
        }),
        (interface_id,),
    )

    producer_objects=[]
    for item in promoted:
        producer_objects.append(SemanticObject(
            "lean.qualified-producer-capability@1",
            1,
            canonical_bytes({
                "rank":item["rank"],
                "producer":item["producer"],
                "source_blob_sha":item["blob_sha"],
                "qualified_wrapper":item["wrapper"],
                "bridge_law_object":law_object.id,
                "source_environment":qual["source_environment"],
                "consumer_surface":qual["consumer_surface"],
            }),
            (interface_id,),
        ))

    adapter=AdapterContract(
        "lean.regular-to-weak-regular-family",
        1,
        "lean.corpus.anthropic-flt@1",
        "mathgraph.consequence-bank@1",
        (interface_id,),
        assumption_refs=(f"lean-law:{law['witness']}",),
        evidence_refs=(
            f"github-run:{auth['run_id']}",
            f"github-artifact:{auth['artifact_id']}:{auth['artifact_digest']}",
            f"git-head:{auth['head_sha']}",
            f"law-object:{law_object.id}",
        ),
    )

    return CompiledBridgeFamily(
        law_object=law_object,
        producer_objects=tuple(producer_objects),
        adapter_contract=adapter,
        interface_id=interface_id,
    )


def compile_authority_file(
    authority_path: str | Path,
    *,
    out_path: str | Path | None=None,
) -> dict[str, Any]:
    authority=json.loads(Path(authority_path).read_text(encoding="utf-8"))
    compiled=compile_bridge_family(authority)
    result=compiled.to_dict()
    result["authority_status"]=authority["status"]
    result["bridge_law"]=authority["bridge_law"]
    result["producer_names"]=[x["producer"] for x in authority["promoted"]]
    result["unknowns"]=list(authority.get("unknowns",()))
    if out_path is not None:
        Path(out_path).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result
