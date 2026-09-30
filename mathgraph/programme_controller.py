"""Fail-closed programme-level Crystal controller.

The controller does not prove claims or execute experiments.  It selects the
cheapest consequentially useful *admitted* experiment only after a campaign has
named a protected objective and an unresolved typed residual.

Verification remains external authority.  UNKNOWN is a first-class result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class EpistemicState(str, Enum):
    INTERESTING = "INTERESTING"
    CANDIDATE = "CANDIDATE"
    WARRANTED = "WARRANTED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    REUSABLE = "REUSABLE"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class Residual:
    campaign: str
    protected_objective: str
    residual_id: str
    residual_kind: str
    evidence_refs: tuple[str, ...]
    state: EpistemicState = EpistemicState.UNKNOWN


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    campaign: str
    residual_id: str
    experiment_kind: str
    expected_contraction: float
    cost: float
    evidence_refs: tuple[str, ...] = ()
    preserves_prior_warrant: bool = True
    independently_verifiable: bool = True
    requires_unearned_distinction: bool = False
    repeats_superseded_route: bool = False
    executable: bool = True

    @property
    def utility(self) -> float:
        if self.cost <= 0:
            return self.expected_contraction if self.expected_contraction > 0 else 0.0
        return self.expected_contraction / self.cost


@dataclass(frozen=True)
class Decision:
    route: str
    residual: Residual | None
    experiment: Experiment | None
    reason: str


def admitted(exp: Experiment, residual: Residual) -> bool:
    """Hard admission boundary before ranking.

    Ranking can never make an inadmissible experiment lawful.
    """
    return (
        exp.campaign == residual.campaign
        and exp.residual_id == residual.residual_id
        and exp.preserves_prior_warrant
        and exp.independently_verifiable
        and not exp.requires_unearned_distinction
        and not exp.repeats_superseded_route
        and exp.executable
        and exp.expected_contraction > 0
        and exp.cost >= 0
    )


def select_experiment(
    residuals: Iterable[Residual],
    experiments: Iterable[Experiment],
) -> Decision:
    """Select one programme action, or fail closed.

    Residuals without a protected objective/evidence are not actionable.
    If several experiments are admissible, maximize verified-residual
    contraction per declared unit cost, then prefer lower absolute cost and a
    stable lexical id.  This is a policy over declared candidates, not a claim
    that the declarations are true.
    """
    residual_list = [
        r for r in residuals
        if r.protected_objective.strip()
        and r.residual_id.strip()
        and r.residual_kind.strip()
        and r.evidence_refs
        and r.state not in {
            EpistemicState.WARRANTED,
            EpistemicState.REJECTED,
            EpistemicState.REUSABLE,
            EpistemicState.SUPERSEDED,
        }
    ]
    if not residual_list:
        return Decision("DO_NOTHING", None, None, "no_actionable_typed_residual")

    candidates: list[tuple[Residual, Experiment]] = []
    experiment_list = list(experiments)
    for residual in residual_list:
        for exp in experiment_list:
            if admitted(exp, residual):
                candidates.append((residual, exp))

    if not candidates:
        # An unresolved residual exists, but the current experiment language
        # cannot lawfully act on it.  This mirrors VDN EXTEND_QUESTIONS.
        first = sorted(residual_list, key=lambda r: (r.campaign, r.residual_id))[0]
        return Decision(
            "EXTEND_EXPERIMENT_LANGUAGE",
            first,
            None,
            "no_admitted_experiment_for_typed_residual",
        )

    residual, exp = sorted(
        candidates,
        key=lambda pair: (
            -pair[1].utility,
            pair[1].cost,
            pair[0].campaign,
            pair[1].experiment_id,
        ),
    )[0]
    return Decision("EXPERIMENT", residual, exp, "max_declared_residual_contraction_per_cost")
