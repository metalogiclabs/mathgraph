#!/usr/bin/env python3
"""Fast V71 exact-frontier diagnostic.

Uses the identical graph construction, retained-node budget, training policy,
and held-out source split machinery as V71, but does not invoke beam theorem
search. It reports whether the learned graph surgery increases the exact
replay-verified one-step consequence frontier. This is diagnostic only.
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "experiments" / "capability_graph_frontier_transfer_v71" / "run_calibration.py"
S = importlib.util.spec_from_file_location("v71_exact_diag_core", P)
if S is None or S.loader is None:
    raise RuntimeError("cannot load V71")
V71 = importlib.util.module_from_spec(S)
sys.modules[S.name] = V71
S.loader.exec_module(V71)

V71.TRAIN_SOURCE_COUNT = 6
V71.EVAL_SOURCE_COUNT = 6
V71.MAX_SOURCE_ATTEMPTS = 220

def evaluate_graph_exact(graph, developer):
    cf = V71.counterfactual_records(graph)
    candidates = cf["candidates"]
    if not candidates:
        return None

    cold_kept = cf["cold_kept"]
    cold_frontier = cf["cold_frontier"]
    dropped = cf["dropped"]
    base = cold_kept[:-1]

    oracle = max(
        candidates,
        key=lambda r: (r["utility"], r["gain_count"], -r["loss_count"], -r["seed_id"]),
    )
    learned = max(
        candidates,
        key=lambda r: (V71.score_candidate(r, developer), -r["seed_id"]),
    )

    learned_kept = tuple(base) + (learned["seed_id"],)
    learned_frontier = V71.reachable_children(graph, learned_kept)
    learned_gains = learned_frontier - cold_frontier
    learned_losses = cold_frontier - learned_frontier

    oracle_kept = tuple(base) + (oracle["seed_id"],)
    oracle_frontier = V71.reachable_children(graph, oracle_kept)

    cold_basis = V71.basis_for_round1(graph, cold_kept)
    meta_basis = V71.basis_for_round1(graph, learned_kept)
    direct = []
    for child_id in sorted(learned_gains)[:6]:
        direct_meta = V71.direct_child_certificate(graph, child_id, meta_basis)
        direct_cold = V71.direct_child_certificate(graph, child_id, cold_basis)
        direct.append({
            "child_id": child_id,
            "direct_meta_certificate": direct_meta,
            "direct_cold_certificate": direct_cold,
            "direct_causal_frontier": bool(direct_meta and not direct_cold),
            "causal_theorem_replay": False,
        })

    return {
        "source_key": graph["source_key"],
        "round1_nodes": len(graph["round1_ids"]),
        "round2_nodes": len(graph["round2_ids"]),
        "cold_frontier_size": len(cold_frontier),
        "dropped_seed_id": dropped,
        "oracle_seed_id": oracle["seed_id"],
        "oracle_utility": oracle["utility"],
        "oracle_gain_count": oracle["gain_count"],
        "oracle_frontier_size": len(oracle_frontier),
        "learned_seed_id": learned["seed_id"],
        "learned_score": V71.score_candidate(learned, developer),
        "learned_utility": len(learned_gains) - len(learned_losses),
        "learned_gain_count": len(learned_gains),
        "learned_loss_count": len(learned_losses),
        "learned_frontier_size": len(learned_frontier),
        "learned_matches_oracle_seed": learned["seed_id"] == oracle["seed_id"],
        "theorem_examples": direct,
    }

V71.evaluate_graph = evaluate_graph_exact

if __name__ == "__main__":
    V71.main()
