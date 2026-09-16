"""First-class artifacts for verifier-gated developmental intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_artifact_hash(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _require_text(name: str, value: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{name} must be nonempty")


def _require_provenance(provenance: tuple[str, ...]) -> None:
    if not provenance or any(not str(item).strip() for item in provenance):
        raise ValueError("provenance must contain at least one nonempty entry")


@dataclass(frozen=True)
class VerifiedCapabilityBlock:
    capability_id: str
    applicability: dict[str, Any]
    action: dict[str, Any]
    verifier_boundary: str
    certificate_refs: tuple[str, ...]
    provenance: tuple[str, ...]
    dependencies: tuple[str, ...]
    scope: dict[str, Any]
    causal_evidence: tuple[str, ...]
    persistence_hash: str

    def __post_init__(self) -> None:
        _require_text("capability_id", self.capability_id)
        _require_text("verifier_boundary", self.verifier_boundary)
        _require_text("persistence_hash", self.persistence_hash)
        _require_provenance(self.provenance)
        if not self.certificate_refs:
            raise ValueError("certificate_refs must be nonempty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def stable_hash(self) -> str:
        return stable_artifact_hash(self.to_dict())


@dataclass(frozen=True)
class VerifiedObstruction:
    obstruction_id: str
    prior_state: tuple[int, ...]
    prior_scope: dict[str, Any]
    extended_scope: dict[str, Any]
    exact_global_old: int
    persistent_value_new: int
    exact_global_new: int
    residual: int
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text("obstruction_id", self.obstruction_id)
        _require_provenance(self.provenance)
        if self.residual <= 0:
            raise ValueError("residual must be positive for a verified obstruction")
        expected = self.exact_global_new - self.persistent_value_new
        if expected != self.residual:
            raise ValueError("residual must equal exact_global_new - persistent_value_new")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def stable_hash(self) -> str:
        return stable_artifact_hash(self.to_dict())


@dataclass(frozen=True)
class VerifiedDevelopmentTransition:
    transition_id: str
    from_state: tuple[int, ...]
    proposal: dict[str, Any]
    verifier: str
    delta: int
    admitted: bool
    to_state: tuple[int, ...]
    causal_witnesses: tuple[str, ...]
    exact_optimality_status: str

    def __post_init__(self) -> None:
        _require_text("transition_id", self.transition_id)
        _require_text("verifier", self.verifier)
        _require_text("exact_optimality_status", self.exact_optimality_status)
        if self.admitted and self.delta <= 0:
            raise ValueError("admitted development requires positive verifier delta")
        if not self.admitted and self.to_state != self.from_state:
            raise ValueError("rejected transition cannot change persistent state")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def stable_hash(self) -> str:
        return stable_artifact_hash(self.to_dict())


def validate_capability_block(block: VerifiedCapabilityBlock) -> None:
    block.__post_init__()


def validate_obstruction(obstruction: VerifiedObstruction) -> None:
    obstruction.__post_init__()


def validate_transition(transition: VerifiedDevelopmentTransition) -> None:
    transition.__post_init__()
