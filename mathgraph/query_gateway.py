"""Crystal-first query gateway.

Answers only from the protected-continuation Crystal.  If the Crystal does not
have enough live authority for the exact question, the result is UNKNOWN and
contains the smallest residual needed to ask an external discovery system.

The gateway never upgrades candidate external evidence by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mathgraph.crystal import content_id
from mathgraph.protected_future import (
    ContinuationStatus,
    ProtectedContinuation,
    ProtectedContinuationMachine,
)


@dataclass(frozen=True)
class CrystalQuestion:
    source: str
    continuation: str
    outcome: tuple[str, ...] | None = None
    interface_id: str | None = None
    live_supports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source or not self.continuation:
            raise ValueError("source and continuation must be non-empty")
        object.__setattr__(self, "live_supports", tuple(sorted(set(self.live_supports))))

    @property
    def id(self) -> str:
        return content_id(self, prefix="crystal-question")


@dataclass(frozen=True)
class CrystalResidual:
    boundary_ref: str
    source: str
    continuation: str
    requested_outcome: tuple[str, ...] | None
    interface_id: str | None
    reason: str
    missing_supports: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    route_hint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "missing_supports", tuple(sorted(set(self.missing_supports))))
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))

    @property
    def id(self) -> str:
        return content_id(self, prefix="residual")

    def to_dict(self) -> dict[str, Any]:
        return {
            "residual_id": self.id,
            "boundary_ref": self.boundary_ref,
            "source": self.source,
            "continuation": self.continuation,
            "requested_outcome": list(self.requested_outcome) if self.requested_outcome is not None else None,
            "interface_id": self.interface_id,
            "reason": self.reason,
            "missing_supports": list(self.missing_supports),
            "evidence_refs": list(self.evidence_refs),
            "route_hint": self.route_hint,
        }


@dataclass(frozen=True)
class CrystalAnswer:
    question_id: str
    status: ContinuationStatus
    boundary_ref: str
    source: str
    continuation: str
    outcomes: tuple[tuple[str, ...], ...] = ()
    targets: tuple[str | None, ...] = ()
    provenance: tuple[str, ...] = ()
    support_refs: tuple[str, ...] = ()
    continuation_ids: tuple[str, ...] = ()
    residual: CrystalResidual | None = None

    @property
    def id(self) -> str:
        return content_id(self, prefix="crystal-answer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_id": self.id,
            "question_id": self.question_id,
            "status": self.status.value,
            "boundary_ref": self.boundary_ref,
            "source": self.source,
            "continuation": self.continuation,
            "outcomes": [list(x) for x in self.outcomes],
            "targets": list(self.targets),
            "provenance": list(self.provenance),
            "support_refs": list(self.support_refs),
            "continuation_ids": list(self.continuation_ids),
            "residual": self.residual.to_dict() if self.residual else None,
        }


def _route_hint(question: CrystalQuestion) -> str | None:
    if question.interface_id == "logic.first-order.entailment@1":
        return "atp:tptp"
    return None


def _residual(
    machine: ProtectedContinuationMachine,
    question: CrystalQuestion,
    reason: str,
    edges: tuple[ProtectedContinuation, ...] = (),
    *,
    missing_supports: tuple[str, ...] = (),
) -> CrystalResidual:
    return CrystalResidual(
        boundary_ref=machine.boundary_ref,
        source=question.source,
        continuation=question.continuation,
        requested_outcome=question.outcome,
        interface_id=question.interface_id,
        reason=reason,
        missing_supports=missing_supports,
        evidence_refs=tuple(ref for edge in edges for ref in edge.evidence_refs),
        route_hint=_route_hint(question),
    )


def query_crystal(
    machine: ProtectedContinuationMachine,
    question: CrystalQuestion,
) -> CrystalAnswer:
    """Answer conservatively from current Crystal authority only."""

    if question.source not in machine.states:
        residual = _residual(machine, question, "unknown_state")
        return CrystalAnswer(
            question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
            question.source, question.continuation, residual=residual,
        )

    by_continuation = tuple(
        edge for edge in machine.edges_from(question.source)
        if edge.continuation == question.continuation
    )
    if not by_continuation:
        residual = _residual(machine, question, "missing_continuation")
        return CrystalAnswer(
            question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
            question.source, question.continuation, residual=residual,
        )

    relevant = by_continuation
    if question.outcome is not None:
        relevant = tuple(edge for edge in by_continuation if edge.outcome == question.outcome)
        if not relevant:
            residual = _residual(machine, question, "outcome_not_covered", by_continuation)
            return CrystalAnswer(
                question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
                question.source, question.continuation, residual=residual,
            )

    live_supports = set(question.live_supports)
    live_warranted = tuple(
        edge for edge in relevant
        if edge.status is ContinuationStatus.WARRANTED and edge.is_live(live_supports)
    )
    blocked_warranted = tuple(
        edge for edge in relevant
        if edge.status is ContinuationStatus.WARRANTED and not edge.is_live(live_supports)
    )
    excluded = tuple(edge for edge in relevant if edge.status is ContinuationStatus.EXCLUDED)
    unresolved = tuple(edge for edge in relevant if edge.status is ContinuationStatus.UNKNOWN)

    all_refs = tuple(sorted({ref for edge in relevant for ref in edge.evidence_refs}))
    all_supports = tuple(sorted({ref for edge in relevant for ref in edge.support_refs}))
    ids = tuple(edge.id for edge in relevant)

    # Exact contradiction at the same requested outcome is a residual, never an
    # arbitrary precedence choice.
    if live_warranted and excluded:
        residual = _residual(machine, question, "conflicting_authority", relevant)
        return CrystalAnswer(
            question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
            question.source, question.continuation,
            provenance=all_refs, support_refs=all_supports,
            continuation_ids=ids, residual=residual,
        )

    if question.outcome is None and (
        unresolved or blocked_warranted or
        (live_warranted and excluded)
    ):
        missing = tuple(sorted({
            support
            for edge in blocked_warranted
            for support in edge.support_refs
            if support not in live_supports
        }))
        reason = "mixed_or_partial_knowledge"
        if blocked_warranted and not unresolved and not live_warranted and not excluded:
            reason = "missing_live_support"
        residual = _residual(machine, question, reason, relevant, missing_supports=missing)
        return CrystalAnswer(
            question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
            question.source, question.continuation,
            provenance=all_refs, support_refs=all_supports,
            continuation_ids=ids, residual=residual,
        )

    if live_warranted:
        return CrystalAnswer(
            question.id, ContinuationStatus.WARRANTED, machine.boundary_ref,
            question.source, question.continuation,
            outcomes=tuple(edge.outcome for edge in live_warranted),
            targets=tuple(edge.target for edge in live_warranted),
            provenance=tuple(sorted({ref for edge in live_warranted for ref in edge.evidence_refs})),
            support_refs=tuple(sorted({ref for edge in live_warranted for ref in edge.support_refs})),
            continuation_ids=tuple(edge.id for edge in live_warranted),
        )

    if excluded and not unresolved and not blocked_warranted:
        return CrystalAnswer(
            question.id, ContinuationStatus.EXCLUDED, machine.boundary_ref,
            question.source, question.continuation,
            outcomes=tuple(edge.outcome for edge in excluded),
            targets=tuple(edge.target for edge in excluded),
            provenance=tuple(sorted({ref for edge in excluded for ref in edge.evidence_refs})),
            support_refs=tuple(sorted({ref for edge in excluded for ref in edge.support_refs})),
            continuation_ids=tuple(edge.id for edge in excluded),
        )

    missing = tuple(sorted({
        support
        for edge in blocked_warranted
        for support in edge.support_refs
        if support not in live_supports
    }))
    if blocked_warranted:
        reason = "missing_live_support"
    elif unresolved:
        reason = "unresolved_continuation"
    else:
        reason = "insufficient_authority"
    residual = _residual(machine, question, reason, relevant, missing_supports=missing)
    return CrystalAnswer(
        question.id, ContinuationStatus.UNKNOWN, machine.boundary_ref,
        question.source, question.continuation,
        provenance=all_refs, support_refs=all_supports,
        continuation_ids=ids, residual=residual,
    )


def machine_to_dict(machine: ProtectedContinuationMachine) -> dict[str, Any]:
    return {
        "schema": "mathgraph.future.protected.partial@1",
        "boundary_ref": machine.boundary_ref,
        "states": list(machine.states),
        "continuations": [
            {
                "source": edge.source,
                "continuation": edge.continuation,
                "outcome": list(edge.outcome),
                "status": edge.status.value,
                "target": edge.target,
                "support_refs": list(edge.support_refs),
                "evidence_refs": list(edge.evidence_refs),
            }
            for edge in machine.continuations
        ],
    }


def machine_from_dict(data: Mapping[str, Any]) -> ProtectedContinuationMachine:
    edges = tuple(
        ProtectedContinuation(
            source=str(row["source"]),
            continuation=str(row["continuation"]),
            outcome=tuple(str(x) for x in row["outcome"]),
            status=ContinuationStatus(str(row["status"])),
            target=None if row.get("target") is None else str(row["target"]),
            support_refs=tuple(str(x) for x in row.get("support_refs", ())),
            evidence_refs=tuple(str(x) for x in row.get("evidence_refs", ())),
        )
        for row in data.get("continuations", ())
    )
    return ProtectedContinuationMachine(
        boundary_ref=str(data["boundary_ref"]),
        states=tuple(str(x) for x in data["states"]),
        continuations=edges,
    )


def question_from_dict(data: Mapping[str, Any]) -> CrystalQuestion:
    outcome = data.get("outcome")
    return CrystalQuestion(
        source=str(data["source"]),
        continuation=str(data["continuation"]),
        outcome=None if outcome is None else tuple(str(x) for x in outcome),
        interface_id=None if data.get("interface_id") is None else str(data["interface_id"]),
        live_supports=tuple(str(x) for x in data.get("live_supports", ())),
    )
