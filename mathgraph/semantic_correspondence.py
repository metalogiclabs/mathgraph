"""Conservative, typed source-to-formal contract comparison.

This is NOT a natural-language semantic oracle or a truth promotion gate.
Protected dimensions must come from an independently reviewed source contract.
Differences are structural separators between *these two contracts*.
Agreement does not certify that either contract faithfully represents its source.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, TypeAlias

Value: TypeAlias = str | int | bool | tuple[str, ...]


class ContractStatus(str, Enum):
    DIVERGENT = "DIVERGENT_PROTECTED_CONTRACT"
    UNKNOWN = "UNKNOWN_INCOMPLETE_CONTRACT"
    AGREES = "SCOPED_AGREEMENT_SEMANTICS_UNKNOWN"


class ArgumentStatus(str, Enum):
    DIFFERENT = "DIFFERENT_DECLARED_ARGUMENT"
    UNKNOWN = "ARGUMENT_FIDELITY_UNKNOWN"


@dataclass(frozen=True)
class ClaimContract:
    anchor: str
    dimensions: Mapping[str, Value]
    argument_route: str = ""


@dataclass(frozen=True)
class ContractAudit:
    status: ContractStatus
    argument_status: ArgumentStatus
    mismatches: tuple[str, ...]
    missing_dimensions: tuple[str, ...]
    source_anchor: str
    formal_anchor: str
    can_promote_truth: bool = False


def compare_protected_contracts(
    source: ClaimContract,
    formal: ClaimContract,
    protected_dimensions: tuple[str, ...],
) -> ContractAudit:
    """Detect explicit separators; never return an automatic semantic warrant.

    Missing values are UNKNOWN, not an equality assertion. Source contract
    extraction and the fidelity of this protected dimension set are external
    obligations. The checker cannot assert implications between differing
    mathematical bounds and never equates proof-goal agreement with argument
    preservation.
    """
    keys = tuple(dict.fromkeys(protected_dimensions))
    if not keys or any(not key for key in keys):
        raise ValueError("A nonempty, explicitly named protected scope is required")
    if not source.anchor or not formal.anchor:
        raise ValueError("Both pinned source and formal anchors are required")
    missing = tuple(
        key for key in keys
        if key not in source.dimensions or key not in formal.dimensions
    )
    mismatches = tuple(
        key for key in keys
        if key not in missing and source.dimensions[key] != formal.dimensions[key]
    )
    if mismatches:
        status = ContractStatus.DIVERGENT
    elif missing:
        status = ContractStatus.UNKNOWN
    else:
        status = ContractStatus.AGREES
    argument_status = (
        ArgumentStatus.DIFFERENT
        if source.argument_route and formal.argument_route
        and source.argument_route != formal.argument_route
        else ArgumentStatus.UNKNOWN
    )
    return ContractAudit(
        status=status,
        argument_status=argument_status,
        mismatches=mismatches,
        missing_dimensions=missing,
        source_anchor=source.anchor,
        formal_anchor=formal.anchor,
    )
