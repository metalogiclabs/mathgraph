"""Replayable falsifier adapter evidence.

This module turns already-existing, machine-checkable negative tests into
content-addressed adapter evidence for the falsifier fabric. It does not infer
mathematics from prose and does not promote a test merely because its filename
looks relevant: an exact pytest node must replay successfully.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from mathgraph.crystal import AdapterContract, SemanticObject, content_id


FALSIFIER_REPLAY_INTERFACE = "falsifier.replayable.test@1"
PROVENANCE_INTERFACE = "evidence.provenance@1"


@dataclass(frozen=True)
class ReplayableFalsifierAnchor:
    source_path: str
    source_sha256: str
    node_id: str
    line: int
    assertion_text: str
    marker: str
    replay_command: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_path or not self.source_sha256 or not self.node_id:
            raise ValueError("source identity is required")
        if self.line <= 0 or not self.assertion_text or not self.marker:
            raise ValueError("anchored assertion is required")
        if not self.replay_command:
            raise ValueError("replay command is required")

    @property
    def id(self) -> str:
        return content_id(self, prefix="falsifier-anchor")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "source_path": self.source_path,
                "source_sha256": self.source_sha256,
                "node_id": self.node_id,
                "line": self.line,
                "assertion_text": self.assertion_text,
                "marker": self.marker,
                "replay_command": list(self.replay_command),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="falsifier.replayable.anchor@1",
            contract_version=1,
            payload=payload,
            interfaces=(FALSIFIER_REPLAY_INTERFACE, PROVENANCE_INTERFACE),
        )


def replayable_falsifier_contract(
    anchor: ReplayableFalsifierAnchor,
    *,
    family_space: str,
    evidence_refs: tuple[str, ...],
) -> AdapterContract:
    return AdapterContract(
        adapter_id=f"adapter:falsifier-replay:{anchor.id}",
        contract_version=1,
        source_space=family_space,
        target_space="falsifier.replayable.anchor@1",
        preserves_interfaces=(FALSIFIER_REPLAY_INTERFACE, PROVENANCE_INTERFACE),
        assumption_refs=(
            "assumption:exact-pytest-node-replays-successfully",
            "assumption:anchored-assertion-is-negative-evidence",
        ),
        evidence_refs=evidence_refs + (
            f"source-sha256:{anchor.source_sha256}",
            f"pytest-node:{anchor.node_id}",
        ),
    )
