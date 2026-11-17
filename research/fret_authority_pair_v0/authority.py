"""Bounded three-way authority decision for the FRET/R2U2 pilot."""

from dataclasses import dataclass
from typing import Mapping
import string


@dataclass(frozen=True)
class Decision:
    status: str
    scope: str
    reason: str
    question: str | None = None


@dataclass(frozen=True)
class OwnerChoice:
    candidate: str
    source_digest: str
    verified: bool
    revoked: bool = False


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(c in string.hexdigits for c in value)


def check_signal_binding(expected: tuple[str, ...], observed: tuple[str, ...],
                         source_digest: str, current_digest: str,
                         strict_policy_active: bool,
                         policy_revoked: bool = False) -> Decision:
    scope = "bound_monitor_replay"
    if not _valid_digest(source_digest) or not _valid_digest(current_digest):
        return Decision("ABSTAIN", scope, "source_pin_unverified")
    if source_digest != current_digest:
        return Decision("ABSTAIN", scope, "source_pin_changed")
    if not strict_policy_active or policy_revoked:
        return Decision("ABSTAIN", scope, "strict_name_binding_not_authorized")
    if (not expected or not observed or
            len(set(expected)) != len(expected) or
            len(set(observed)) != len(observed) or
            any(not name.strip() for name in expected + observed)):
        return Decision("REFUSE", scope, "invalid_signal_identity")
    if expected != observed:
        return Decision("REFUSE", scope, "signal_order_mismatch")
    return Decision("ALLOW", scope, "declared_binding_matches")


def choose_requirement(native_verdicts: Mapping[str, bool],
                       oracle_verdicts: Mapping[str, bool],
                       source_digest: str, current_digest: str,
                       owner_choices: tuple[OwnerChoice, ...],
                       question: str) -> Decision:
    scope = "requirement_selection"
    if not _valid_digest(source_digest) or source_digest != current_digest:
        return Decision("ABSTAIN", scope, "source_pin_changed", question)
    if (len(native_verdicts) != 2 or
            set(native_verdicts) != set(oracle_verdicts) or
            any(type(v) is not bool for v in native_verdicts.values()) or
            any(type(v) is not bool for v in oracle_verdicts.values())):
        return Decision("ABSTAIN", scope, "incomplete_or_invalid_verdicts", question)
    if native_verdicts != oracle_verdicts:
        return Decision("ABSTAIN", scope, "independent_oracle_conflict", question)
    if len(set(native_verdicts.values())) < 2:
        return Decision("ABSTAIN", scope, "no_distinguishing_witness", question)
    if not owner_choices:
        return Decision("ABSTAIN", scope, "owner_intent_missing", question)
    if len(owner_choices) != 1:
        return Decision("ABSTAIN", scope, "conflicting_owner_choices", question)
    choice = owner_choices[0]
    if not choice.verified or choice.revoked or choice.source_digest != source_digest:
        return Decision("ABSTAIN", scope, "owner_authority_not_live", question)
    if choice.candidate not in native_verdicts:
        return Decision("ABSTAIN", scope, "owner_selected_unknown_candidate", question)
    return Decision("ALLOW", "candidate_selection_only", "owner_selected_candidate_not_approved_deployment")
