"""Separately coded explicit eight-bit rule comparator on the exact same observations.

This is an equally informed *rule proxy* and not a human expert trial.
"""
from __future__ import annotations

def expert_rule_proxy(bit_width: int, observed_lean: int, observed_smt: int) -> dict:
    if bit_width != 8:
        raise ValueError("UNREGISTERED_BITWIDTH")
    if observed_lean != 0 or observed_smt != (1 << bit_width) - 1:
        raise ValueError("OBSERVATION_DISAGREES_WITH_REGISTERED_REFERENCE_RULE")
    return {
        "bit_width": bit_width,
        "lean_native_div_zero": observed_lean,
        "smt_bvudiv_zero": observed_smt,
        "relation": "DIFFERENT",
        "status": "EQUAL_INPUT_EXPLICIT_RULE_PROXY_NOT_HUMAN",
    }
