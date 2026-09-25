"""Semantic compiler registry for residual-first swarm routing.

A registry entry names a reusable semantic operation and its current provider.
It does not make universal preservation claims. Family-specific adapters remain
separate evidence-bearing objects.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from mathgraph.crystal import AdapterContract, SemanticObject, content_id


@dataclass(frozen=True)
class CompilerSpec:
    compiler_id: str
    motif: str
    provider_modules: tuple[str, ...]
    interfaces: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    scope_note: str

    @property
    def id(self) -> str:
        return content_id(self, prefix="compiler")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "compiler_id": self.compiler_id,
                "motif": self.motif,
                "provider_modules": list(self.provider_modules),
                "interfaces": list(self.interfaces),
                "evidence_refs": list(self.evidence_refs),
                "scope_note": self.scope_note,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="swarm.semantic-compiler@1",
            contract_version=1,
            payload=payload,
            interfaces=("swarm.compiler.registry@1",),
        )


@dataclass(frozen=True)
class ReplayableOperationAnchor:
    source_path: str
    source_sha256: str
    node_id: str
    line: int
    motif: str
    anchor_text: str
    replay_command: tuple[str, ...]

    def __post_init__(self) -> None:
        if not all((self.source_path, self.source_sha256, self.node_id, self.motif, self.anchor_text)):
            raise ValueError("operation anchor fields must be non-empty")
        if self.line <= 0 or not self.replay_command:
            raise ValueError("operation anchor line and replay command are required")

    @property
    def id(self) -> str:
        return content_id(self, prefix="operation-anchor")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "source_path": self.source_path,
                "source_sha256": self.source_sha256,
                "node_id": self.node_id,
                "line": self.line,
                "motif": self.motif,
                "anchor_text": self.anchor_text,
                "replay_command": list(self.replay_command),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="swarm.replayable-operation-anchor@1",
            contract_version=1,
            payload=payload,
            interfaces=("swarm.operation.replay@1", "evidence.provenance@1"),
        )


def operation_adapter_contract(
    anchor: ReplayableOperationAnchor,
    compiler: CompilerSpec,
    *,
    evidence_refs: tuple[str, ...],
) -> AdapterContract:
    return AdapterContract(
        adapter_id=f"adapter:swarm-operation:{compiler.compiler_id}:{anchor.id}",
        contract_version=1,
        source_space=f"repo-test-family:{anchor.source_path}",
        target_space=compiler.compiler_id,
        preserves_interfaces=("swarm.operation.replay@1", "evidence.provenance@1"),
        assumption_refs=(
            "assumption:exact-pytest-node-replays-successfully",
            "assumption:anchor-exercises-declared-semantic-operation",
        ),
        evidence_refs=evidence_refs + (
            f"source-sha256:{anchor.source_sha256}",
            f"pytest-node:{anchor.node_id}",
            f"compiler:{compiler.id}",
        ),
    )


def default_registry() -> tuple[CompilerSpec, ...]:
    return (
        CompilerSpec(
            "compiler:evidence-manifest@1",
            "provenance_lineage",
            ("mathgraph.evidence_manifest", "mathgraph.certificates"),
            ("evidence.provenance@1", "evidence.replay@1", "certificate.terminal@1"),
            ("gate:swarm-runtime-v4:evidence-manifest",),
            "Replayable evidence/provenance carrier; family semantics require adapters.",
        ),
        CompilerSpec(
            "compiler:certificate-evidence@1",
            "certificate_witness",
            ("mathgraph.certificates", "mathgraph.evidence_manifest"),
            ("certificate.terminal@1", "certificate.witness@1", "evidence.replay@1"),
            ("gate:swarm-runtime-v5:certificate-evidence",),
            "Terminal certificate/witness carrier plus replayable evidence manifest; family semantics require adapters.",
        ),
        CompilerSpec(
            "compiler:lawbook-acceptance@1",
            "admission_promotion",
            ("mathgraph.lawbook_acceptance",),
            ("promotion.admission@1", "evidence.replay@1"),
            ("gate:swarm-runtime-v4:lawbook-acceptance",),
            "Promotion only after acceptance contract and replay boundary.",
        ),
        CompilerSpec(
            "compiler:crystal-reclosure@1",
            "residual_reclosure",
            ("mathgraph.crystal",),
            ("residual.reclose@1", "viability.kernel@1"),
            ("gate:swarm-runtime-v4:crystal-reclosure",),
            "Finite protected-boundary reclosure/viability reference semantics.",
        ),
        CompilerSpec(
            "compiler:adapter-contract@1",
            "adapter_transport",
            ("mathgraph.crystal",),
            ("translation.preservation@1",),
            ("gate:swarm-runtime-v4:adapter-contract",),
            "Explicit preservation contracts; missing interfaces fail closed.",
        ),
        CompilerSpec(
            "compiler:discovery-scheduler@1",
            "scheduler_value",
            ("mathgraph.discovery_scheduler",),
            ("scheduler.value@1",),
            ("gate:swarm-runtime-v4:discovery-scheduler",),
            "Advisory scheduling only; cannot promote truth.",
        ),
        CompilerSpec(
            "compiler:source-grounding@1",
            "source_grounding",
            ("mathgraph.evidence_manifest", "mathgraph.semantic_validation"),
            ("source.grounding@1", "evidence.provenance@1"),
            ("gate:swarm-runtime-v4:source-grounding",),
            "Pinned provenance / semantic-validation metadata, not source-intent oracle.",
        ),
        CompilerSpec(
            "compiler:crystal-viability@1",
            "transition_viability",
            ("mathgraph.crystal",),
            ("transition.viability@1", "viability.kernel@1"),
            ("gate:swarm-runtime-v4:crystal-viability",),
            "Finite greatest viability reference semantics.",
        ),
        CompilerSpec(
            "compiler:compounding-engine@1",
            "capability_compounding",
            ("mathgraph.compounding_engine",),
            ("capability.compounding@1",),
            ("gate:swarm-runtime-v4:compounding",),
            "Existing bounded compounding machinery; no universal learning claim.",
        ),
        CompilerSpec(
            "compiler:finite-relation@1",
            "relation_compiler",
            ("mathgraph.finite_relation",),
            ("relation.equivalence@1", "relation.implication@1", "relation.separator@1"),
            ("exact-head:3f323e5b713acd5b5c47d68fe13d485027aa676c",),
            "Qualified finite relation compiler.",
        ),
        CompilerSpec(
            "compiler:finite-falsifier@1",
            "countermodel_falsifier",
            ("mathgraph.finite_falsifier", "mathgraph.falsifier_adapter", "mathgraph.falsifier_semantic_adapter"),
            ("falsifier.finite.witness@1", "falsifier.replayable.test@1"),
            ("exact-head:2dd1a4410e4d0c02fb354fe7a60bcfc947ae469c",),
            "56/56 replayable falsifier adapter coverage on mined frontier.",
        ),
    )
