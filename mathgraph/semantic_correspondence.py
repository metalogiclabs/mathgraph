"""Compatibility path for the independently qualified contract comparator.

The implementation now lives in the dependency-free mathgraph_check package.
Its logic and status meanings are unchanged.
"""
from mathgraph_check.contracts import (
    Value, ContractStatus, ArgumentStatus, ClaimContract, ContractAudit,
    compare_protected_contracts,
)

__all__ = (
    "Value", "ContractStatus", "ArgumentStatus", "ClaimContract",
    "ContractAudit", "compare_protected_contracts",
)
