"""Compile a warranted Lean bridge promotion into Crystal semantic memory."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import AdapterContract, SemanticObject, canonical_bytes


@dataclass(frozen=True)
class CompiledLeanBridgeCapability:
    semantic_object: SemanticObject
    adapter_contract: AdapterContract
    interface_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mathgraph.compiled-lean-bridge-capability.v1",
            "semantic_object_id": self.semantic_object.id,
            "adapter_contract_id": self.adapter_contract.id,
            "interface_id": self.interface_id,
            "type_id": self.semantic_object.type_id,
            "contract_version": self.semantic_object.contract_version,
            "source_space": self.adapter_contract.source_space,
            "target_space": self.adapter_contract.target_space,
            "assumption_refs": list(self.adapter_contract.assumption_refs),
            "evidence_refs": list(self.adapter_contract.evidence_refs),
        }


def _slug(value: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "-", value).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def compile_warranted_bridge(
    authority: Mapping[str, Any],
) -> CompiledLeanBridgeCapability:
    if authority.get("status") != "WARRANTED_BOUNDED_REUSABLE":
        raise ValueError("bridge capability requires warranted bounded authority")

    route = dict(authority["selected_route"])
    producer = dict(route["producer"])
    consumer = dict(route["consumer"])
    qual = dict(authority["qualification"])
    auth = dict(authority["authority"])

    source_symbol = str(route["source_symbol"])
    target_symbol = str(route["target_symbol"])
    interface = f"lean.consequence.{_slug(target_symbol)}@1"

    payload = canonical_bytes({
        "source_symbol": source_symbol,
        "target_symbol": target_symbol,
        "producer": producer,
        "consumer": consumer,
        "protected_consequence": qual["protected_consequence"],
        "qualified_consumer": qual["qualified_consumer"],
        "source_proof_reformalized_loc": qual["source_proof_reformalized_loc"],
        "authority_run": auth["workflow_run"],
        "authority_head_sha": auth["head_sha"],
        "artifact_digest": auth["artifact_digest"],
        "revocation_boundary": list(authority.get("revocation_boundary", ())),
    })
    obj = SemanticObject(
        type_id="lean.verified-bridge-capability@1",
        contract_version=1,
        payload=payload,
        interfaces=(interface,),
    )

    contract = AdapterContract(
        adapter_id=f"qualified-lean-bridge:{_slug(source_symbol)}-to-{_slug(target_symbol)}",
        contract_version=1,
        source_space=f"lean.corpus.{producer['corpus']}@1",
        target_space=f"lean.corpus.{consumer['corpus']}@1",
        preserves_interfaces=(interface,),
        assumption_refs=(str(route["bridge_evidence"]),),
        evidence_refs=(
            f"github-run:{auth['workflow_run']}",
            f"github-artifact:{auth['artifact_id']}:{auth['artifact_digest']}",
            f"git-head:{auth['head_sha']}",
        ),
    )
    return CompiledLeanBridgeCapability(obj, contract, interface)


def compile_authority_file(
    authority_path: str | Path,
    *,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    authority = json.loads(Path(authority_path).read_text(encoding="utf-8"))
    compiled = compile_warranted_bridge(authority)
    result = compiled.to_dict()
    result["authority_status"] = authority["status"]
    result["protected_consequence"] = authority["qualification"]["protected_consequence"]
    result["unknowns"] = list(authority.get("unknowns", ()))
    if out_path is not None:
        Path(out_path).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result
