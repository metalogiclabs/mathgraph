#!/usr/bin/env python3
"""A decision-sufficient mode for the already qualified finite V1 experiment compiler.

No alteration of the original exact-quotient solver. An observation basis may
refine the goal partition: synthesize a downstream decoder so that g = decode ◦ O.
Effect/permission semantics and source tables are delegated unchanged to V1.
"""
from __future__ import annotations
from itertools import combinations
from typing import Any
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from consequence_experiment_compiler_v1.compiler import (
    parse_model, transformation_closure, compile_profiles, kernels,
)

MAX_REQUIRED_SEPARATIONS = 18  # Exhaustive DP cap: otherwise explicit UNKNOWN.


def preexisting_kernel(model) -> set[tuple[int,int]]:
    n = len(model.protected)
    eq = set(combinations(range(n), 2))
    readouts = {r.name: r for r in model.readouts}
    for name in model.base_readouts:
        eq &= kernels(readouts[name].values)
    return eq


def measured_decoder(model, selected: list[dict[str, Any]],
                     desired: tuple[int, ...]) -> list[dict[str, Any]]:
    named = {r.name: r for r in model.readouts}
    decoder: dict[tuple[int, ...], int] = {}
    for i in range(len(desired)):
        values = (tuple(named[name].values[i] for name in model.base_readouts) +
                  tuple(p["values"][i] for p in selected))
        if values in decoder and decoder[values] != desired[i]:
            raise AssertionError("DECODER_NOT_WELL_DEFINED")
        decoder[values] = desired[i]
    return [{"observed": list(values), "decision": decision}
            for values, decision in sorted(decoder.items())]


def solve(model, desired: tuple[int, ...], ignore_grants: bool = False) -> dict[str, Any]:
    if len(desired) != len(model.protected):
        raise ValueError("TARGET_DIMENSION_MISMATCH")
    before = preexisting_kernel(model)
    target = kernels(desired)
    needed = sorted(before-target)
    if len(needed) > MAX_REQUIRED_SEPARATIONS:
        return {"status": "UNKNOWN_EXACT_BASIS_RESOURCE_BOUND",
                "remaining_required_pair_count":len(needed),
                "diagnosis":"EXHAUSTIVE_SET_COVER_LIMIT"}
    closure, closure_stats = transformation_closure(model, ignore_grants=ignore_grants)
    profiles = compile_profiles(model, closure, ignore_grants=ignore_grants)
    options = []
    coverable = 0
    for p in profiles:  # Surplus distinctions ALLOWED.
        mask = sum(1<<j for j,(a,b) in enumerate(needed) if p["values"][a] != p["values"][b])
        if mask:
            options.append((mask,p))
            coverable |= mask
    required_mask = (1<<len(needed))-1
    if coverable != required_mask:
        return {
            "status":"UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR",
            "uncovered_pairs":[list(pair) for j,pair in enumerate(needed)
                               if not coverable & (1<<j)],
            "fully_examined_profiles":len(profiles),
            "closure":closure_stats,
            "basis":None,"basis_cost":None,"decoder":None,
        }
    dp = {0:(0,0,())}
    for mask, p in options:
        for seen, (cost, size, chosen) in list(dp.items()):
            newmask = seen | mask
            proposed = (cost+p["cost"],size+1,chosen+(tuple(p["program"]),))
            if newmask not in dp or proposed < dp[newmask]:
                dp[newmask] = proposed
    cost, size, ids = dp[required_mask]
    index = {tuple(p["program"]):p for _,p in options}
    selected=[index[name] for name in ids]
    decoder=measured_decoder(model,selected,desired)
    # This is the weaker but correct adequacy condition:
    # kernel(old + additional observation) <= kernel(goal).
    obs = {}
    for entry in decoder:
        k=tuple(entry["observed"])
        assert k not in obs or obs[k]==entry["decision"]
        obs[k]=entry["decision"]
    return {
        "status":"DECISION_SUFFICIENT_BASIS",
        "basis_cost":cost,"basis_size":size,
        "basis":[{"program":list(p["program"]),"values":list(p["values"]),"cost":p["cost"]}
                 for p in selected],
        "decoder":decoder,
        "required_pair_count":len(needed),
        "observable_pair_count":len(before),
        "goal_pair_count":len(target),
        "closure":closure_stats,
        "factored_condition":"g = decode ∘ (old_observations,new_observation_basis)",
        "surplus_readout_distinctions_admitted":True,
    }


def compile_decision_sufficient(obj: dict[str, Any]) -> dict[str, Any]:
    m = parse_model(obj)
    desired=tuple(obj["desired_labels"])
    answer=solve(m,desired)
    answer["model_name"]=obj["name"]
    answer["mode"]="decision_sufficient"
    answer["proof_boundary"]="fully declared finite deterministic source tables and grants; no physical assertion"
    if answer["status"] == "UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR":
        more=solve(m,desired,ignore_grants=True)
        if more["status"]=="DECISION_SUFFICIENT_BASIS":
            answer["diagnosis"]="MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR"
            answer["hypothetical_granted_cost"]=more["basis_cost"]
        elif more["status"]=="UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR":
            answer["diagnosis"]="NO_SOURCE_DECLARED_SAFE_OPERATOR_SUFFICIENT"
        else:
            answer["diagnosis"]="UNKNOWN_RESOURCE_BOUND"
    elif answer["status"]=="DECISION_SUFFICIENT_BASIS":
        answer["diagnosis"]="ADMITTED_SOURCE_DECLARED_COMPOSITION"
    return answer
