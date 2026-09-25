"""Semantic replay anchors for negative evidence not expressed as direct asserts."""
from __future__ import annotations

from dataclasses import dataclass
import json

from mathgraph.crystal import AdapterContract, SemanticObject, content_id
from mathgraph.falsifier_adapter import FALSIFIER_REPLAY_INTERFACE, PROVENANCE_INTERFACE


@dataclass(frozen=True)
class ReplayableSemanticNegativeAnchor:
    source_path: str
    source_sha256: str
    node_id: str
    line: int
    anchor_kind: str
    anchor_text: str
    marker: str
    replay_command: tuple[str, ...]

    def __post_init__(self) -> None:
        if not all((self.source_path, self.source_sha256, self.node_id, self.anchor_kind, self.anchor_text, self.marker)):
            raise ValueError("semantic negative anchor fields must be non-empty")
        if self.line <= 0 or not self.replay_command:
            raise ValueError("semantic anchor line and replay command are required")

    @property
    def id(self) -> str:
        return content_id(self, prefix="falsifier-semantic-anchor")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "source_path": self.source_path,
                "source_sha256": self.source_sha256,
                "node_id": self.node_id,
                "line": self.line,
                "anchor_kind": self.anchor_kind,
                "anchor_text": self.anchor_text,
                "marker": self.marker,
                "replay_command": list(self.replay_command),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="falsifier.replayable.semantic-anchor@1",
            contract_version=1,
            payload=payload,
            interfaces=(FALSIFIER_REPLAY_INTERFACE, PROVENANCE_INTERFACE),
        )


def semantic_negative_contract(
    anchor: ReplayableSemanticNegativeAnchor,
    *,
    family_space: str,
    evidence_refs: tuple[str, ...],
) -> AdapterContract:
    return AdapterContract(
        adapter_id=f"adapter:falsifier-semantic-replay:{anchor.id}",
        contract_version=1,
        source_space=family_space,
        target_space="falsifier.replayable.semantic-anchor@1",
        preserves_interfaces=(FALSIFIER_REPLAY_INTERFACE, PROVENANCE_INTERFACE),
        assumption_refs=(
            "assumption:exact-pytest-node-replays-successfully",
            "assumption:semantic-anchor-explicitly-encodes-negative-evidence",
        ),
        evidence_refs=evidence_refs + (
            f"source-sha256:{anchor.source_sha256}",
            f"pytest-node:{anchor.node_id}",
        ),
    )
