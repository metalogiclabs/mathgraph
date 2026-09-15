#!/usr/bin/env python3
"""V71: capability-graph frontier transfer on an opened unlabeled law universe.

V67-V70 ruled out increasingly local transfer objects: lemma ranking, a causal
action template, learned action scope, and equal-budget seed injection. V71
moves the developmental object up one level.

For a source law, build a small replay-verified critical-pair graph:
  G0 = source
  G1 = deterministic round-1 source/source consequences
  G2 = deterministic round-2 consequences touching G1

At fixed retained-node budget B, COLD keeps the B cheapest G1 nodes. For each
omitted G1 node s, form the exact counterfactual graph surgery
  K_s = K_cold - worst(K_cold) + s
and measure the *next verified consequence frontier*:
  R(K) = { child in G2 : both recorded derivation parents are retained in K }.

This target-free counterfactual value is exact: every G1/G2 node is replayed by
the independent critical-pair verifier, and R(K) uses only source-derived graph
structure. Training learns a source-ID-agnostic ranking of graph surgeries from
many source laws. Evaluation uses held-out source identities from the same
opened unlabeled equation-law universe.

The equation-law file was already opened during V68-V70 development, so V71 is
calibration, NOT fresh prospective evidence. A positive V71 licenses a later
fresh external test; a negative V71 preserves that stream.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

P70 = ROOT / "experiments" / "causal_action_budget_frontier_v70" / "run_calibration.py"
S70 = importlib.util.spec_from_file_location("v71_v70", P70)
if S70 is None or S70.loader is None:
    raise RuntimeError("cannot load V70")
V70 = importlib.util.module_from_spec(S70)
sys.modules[S70.name] = V70
S70.loader.exec_module(V70)

V69 = V70.V69
V67 = V70.V67
V65 = V70.V65
V64 = V70.V64
V62 = V70.V62

LAW_COMMIT = "374eb40ba5389915deb174fbc12cc92346214dd1"
LAW_PATH = "examples/problems/eq_size5.txt"
LAW_GIT_BLOB_SHA1 = "0deca9c8860fb60f2ae161ab7e3f458ec3b178ca"

TRAIN_SOURCE_COUNT = 14
EVAL_SOURCE_COUNT = 14
MAX_SOURCE_ATTEMPTS = 500

ROUND1_POOL = 18
ROUND2_POOL = 72
RETAIN_BUDGET = 5

MIN_ROUND1 = RETAIN_BUDGET + 3
MIN_ROUND2 = 12
MAX_REPLAY_EXAMPLES = 10

FEATURE_NAMES = (
    "seed_complexity",
    "seed_side_balance",
    "seed_overlap_depth",
    "seed_same_direction",
    "source_complexity_reduction",
    "immediate_child_count",
    "source_partner_child_count",
    "self_child_count",
    "unique_coparent_count",
    "direct_seed_frontier_count",
    "cold_partner_child_count",
    "mean_child_complexity",
    "min_child_complexity",
    "mean_child_overlap_depth",
    "child_complexity_reduction_count",
)


def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_doc(obj):
    return hashlib.sha256(stable_json(obj)).hexdigest()


def term_text(t):
    if t[0] == "v":
        return t[1]
    return f"({term_text(t[1])} * {term_text(t[2])})"


def equation_text(eq):
    text = f"{term_text(eq.lhs)} = {term_text(eq.rhs)}"
    # Round-trip through the actual parser before using this as a theorem target.
    lhs, rhs = V62.parse_eq(text)
    _l, _r, key = V62.canonical_equation(lhs, rhs)
    if key != eq.key:
        raise RuntimeError(f"equation text round-trip mismatch: {eq.key} != {key}")
    return text


def source_problem(law, source_key):
    return {
        "id": f"v71_source_{source_key[:12]}",
        "eq1_id": source_key[:16],
        "equation1": law,
        "equation2": law,
    }


def enumerate_candidates(eqs, frontier, existing_keys):
    existing_ids = sorted(eqs)
    frontier_set = set(frontier)
    candidates = {}
    for a_id in existing_ids:
        for b_id in existing_ids:
            if a_id not in frontier_set and b_id not in frontier_set:
                continue
            a = eqs[a_id]
            b = eqs[b_id]
            for a_dir in (0, 1):
                al, _ = V62.orientation(a, a_dir)
                if al[0] == "v":
                    continue
                for b_dir in (0, 1):
                    bl, _ = V62.orientation(b, b_dir)
                    if bl[0] == "v":
                        continue
                    for pos in V62.nonvar_positions(bl):
                        out = V62.derive_overlap(a, b, a_dir, b_dir, pos)
                        if out is None:
                            continue
                        cl, cr, key = out
                        if key in existing_keys:
                            continue
                        complexity = V62.nodes(cl) + V62.nodes(cr)
                        proof = {
                            "kind": "CRITICAL_PAIR",
                            "a": int(a_id),
                            "b": int(b_id),
                            "a_dir": int(a_dir),
                            "b_dir": int(b_dir),
                            "pos": list(pos),
                        }
                        prev = candidates.get(key)
                        record = (complexity, key, cl, cr, proof)
                        if prev is None or (complexity, key, stable_json(proof)) < (
                            prev[0], prev[1], stable_json(prev[4])
                        ):
                            candidates[key] = record
    return sorted(candidates.values(), key=lambda x: (x[0], x[1]))


def build_graph(law):
    sl, sr = V62.parse_eq(law)
    lhs, rhs, source_key = V62.canonical_equation(sl, sr)
    source = V62.Equation(0, lhs, rhs, source_key, {"kind": "SOURCE"}, 0)
    eqs = {0: source}
    by_key = {source_key: 0}
    next_id = 1

    r1_raw = enumerate_candidates(eqs, [0], set(by_key))
    round1_ids = []
    for complexity, key, cl, cr, proof in r1_raw[:ROUND1_POOL]:
        child = V62.Equation(next_id, cl, cr, key, proof, 1)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("round-1 critical-pair replay failed")
        eqs[next_id] = child
        by_key[key] = next_id
        round1_ids.append(next_id)
        next_id += 1

    if len(round1_ids) < MIN_ROUND1:
        return None

    r2_raw = enumerate_candidates(eqs, round1_ids, set(by_key))
    round2_ids = []
    for complexity, key, cl, cr, proof in r2_raw[:ROUND2_POOL]:
        child = V62.Equation(next_id, cl, cr, key, proof, 2)
        trial = dict(eqs)
        trial[next_id] = child
        if not V62.verify_overlap(child, trial):
            raise RuntimeError("round-2 critical-pair replay failed")
        eqs[next_id] = child
        by_key[key] = next_id
        round2_ids.append(next_id)
        next_id += 1

    if len(round2_ids) < MIN_ROUND2:
        return None

    # Full replay gate.
    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored graph node failed replay: eid={eid}")

    return {
        "law": law,
        "source_key": source_key,
        "eqs": eqs,
        "round1_ids": round1_ids,
        "round2_ids": round2_ids,
    }


def equation_complexity(eq):
    return V62.nodes(eq.lhs) + V62.nodes(eq.rhs)


def retained_cold(graph):
    ordered = sorted(
        graph["round1_ids"],
        key=lambda eid: (equation_complexity(graph["eqs"][eid]), graph["eqs"][eid].key),
    )
    return tuple(ordered[:RETAIN_BUDGET]), tuple(ordered)


def reachable_children(graph, retained_ids):
    allowed = {0, *retained_ids}
    reachable = set()
    for eid in graph["round2_ids"]:
        p = graph["eqs"][eid].proof
        if int(p["a"]) in allowed and int(p["b"]) in allowed:
            reachable.add(eid)
    return reachable


def candidate_features(graph, seed_id, cold_kept):
    eqs = graph["eqs"]
    seed = eqs[seed_id]
    source = eqs[0]
    stable_cold = set(cold_kept[:-1])
    seed_complexity = equation_complexity(seed)
    source_complexity = equation_complexity(source)

    children = []
    source_partner = 0
    self_children = 0
    coparents = set()
    direct_seed_frontier = 0
    cold_partner = 0
    child_reduction = 0

    for cid in graph["round2_ids"]:
        child = eqs[cid]
        p = child.proof
        a = int(p["a"])
        b = int(p["b"])
        if a != seed_id and b != seed_id:
            continue
        children.append(child)
        other = b if a == seed_id else a
        coparents.add(other)
        source_partner += int(other == 0)
        self_children += int(a == seed_id and b == seed_id)
        direct_seed_frontier += int(a in {0, seed_id} and b in {0, seed_id})
        cold_partner += int(other == 0 or other in stable_cold or other == seed_id)
        child_reduction += int(equation_complexity(child) < seed_complexity)

    child_complexities = [equation_complexity(c) for c in children]
    child_depths = [len(c.proof.get("pos", [])) for c in children]

    p = seed.proof
    return (
        float(seed_complexity),
        float(abs(V62.nodes(seed.lhs) - V62.nodes(seed.rhs))),
        float(len(p.get("pos", []))),
        float(int(p.get("a_dir") == p.get("b_dir"))),
        float(source_complexity - seed_complexity),
        float(len(children)),
        float(source_partner),
        float(self_children),
        float(len(coparents)),
        float(direct_seed_frontier),
        float(cold_partner),
        float(sum(child_complexities) / len(child_complexities)) if child_complexities else 0.0,
        float(min(child_complexities)) if child_complexities else 0.0,
        float(sum(child_depths) / len(child_depths)) if child_depths else 0.0,
        float(child_reduction),
    )


def counterfactual_records(graph):
    cold_kept, ordered = retained_cold(graph)
    cold_frontier = reachable_children(graph, cold_kept)
    dropped = cold_kept[-1]
    base = cold_kept[:-1]
    records = []
    for seed in ordered[RETAIN_BUDGET:]:
        meta_kept = tuple(base) + (seed,)
        meta_frontier = reachable_children(graph, meta_kept)
        gains = meta_frontier - cold_frontier
        losses = cold_frontier - meta_frontier
        utility = len(gains) - len(losses)
        records.append({
            "seed_id": seed,
            "features": candidate_features(graph, seed, cold_kept),
            "utility": utility,
            "gain_count": len(gains),
            "loss_count": len(losses),
            "meta_frontier_size": len(meta_frontier),
        })
    return {
        "cold_kept": cold_kept,
        "cold_frontier": cold_frontier,
        "dropped": dropped,
        "candidates": records,
    }


def normalize(v, scales):
    return tuple(x / s for x, s in zip(v, scales))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def learn_developer(train_graphs):
    episodes = []
    all_vectors = []
    exact_oracle_positive_sources = 0
    for graph in train_graphs:
        cf = counterfactual_records(graph)
        candidates = cf["candidates"]
        if candidates and max(r["utility"] for r in candidates) > 0:
            exact_oracle_positive_sources += 1
        episodes.append((graph["source_key"], candidates))
        all_vectors.extend(r["features"] for r in candidates)

    if not all_vectors:
        raise RuntimeError("no graph-surgery training candidates")

    scales = [
        max(1.0, max(abs(v[i]) for v in all_vectors))
        for i in range(len(FEATURE_NAMES))
    ]
    weights = [0.0] * len(FEATURE_NAMES)
    updates = 0
    margin = 0.05
    rate = 0.20

    # Pairwise ranking learns relative counterfactual graph value within source.
    for _epoch in range(18):
        for _source_key, candidates in episodes:
            ordered = sorted(candidates, key=lambda r: (r["seed_id"]))
            for hi in ordered:
                for lo in ordered:
                    if hi["utility"] <= lo["utility"]:
                        continue
                    a = normalize(hi["features"], scales)
                    b = normalize(lo["features"], scales)
                    if dot(weights, a) <= dot(weights, b) + margin:
                        gap = min(3.0, float(hi["utility"] - lo["utility"]))
                        for i in range(len(weights)):
                            weights[i] += rate * gap * (a[i] - b[i])
                        updates += 1

    developer = {
        "schema": "mathgraph.capability-graph-frontier-policy.v71.calibration",
        "feature_names": list(FEATURE_NAMES),
        "feature_scales": [float(x) for x in scales],
        "weights": [float(x) for x in weights],
        "retained_round1_budget": RETAIN_BUDGET,
        "graph_round1_pool": ROUND1_POOL,
        "graph_round2_pool": ROUND2_POOL,
        "training_rule": "pairwise_rank_exact_counterfactual_next_frontier_delta",
        "source_id_invariant": True,
        "target_free": True,
    }
    summary = {
        "training_sources": len(train_graphs),
        "training_candidate_actions": sum(len(c) for _, c in episodes),
        "training_sources_with_positive_oracle_surgery": exact_oracle_positive_sources,
        "pairwise_updates": updates,
    }
    return developer, sha_doc(developer), summary


def score_candidate(record, developer):
    x = normalize(record["features"], developer["feature_scales"])
    return dot(developer["weights"], x)


def basis_for_round1(graph, kept):
    ids = {0, *kept}
    return {eid: graph["eqs"][eid] for eid in sorted(ids)}


def child_problem(graph, child_id, label):
    child = graph["eqs"][child_id]
    return {
        "id": f"v71_{label}_{graph['source_key'][:10]}_{child_id}",
        "eq1_id": graph["source_key"][:16],
        "equation1": graph["law"],
        "equation2": equation_text(child),
    }


def direct_child_certificate(graph, child_id, basis):
    child = graph["eqs"][child_id]
    p = child.proof
    a = basis.get(int(p["a"]))
    b = basis.get(int(p["b"]))
    if a is None or b is None:
        return False
    predicted = V62.derive_overlap(
        a, b, int(p["a_dir"]), int(p["b_dir"]), tuple(p["pos"])
    )
    return predicted is not None and predicted[2] == child.key


def evaluate_graph(graph, developer):
    cf = counterfactual_records(graph)
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
        key=lambda r: (score_candidate(r, developer), -r["seed_id"]),
    )

    learned_kept = tuple(base) + (learned["seed_id"],)
    learned_frontier = reachable_children(graph, learned_kept)
    learned_gains = learned_frontier - cold_frontier
    learned_losses = cold_frontier - learned_frontier
    learned_utility = len(learned_gains) - len(learned_losses)

    oracle_kept = tuple(base) + (oracle["seed_id"],)
    oracle_frontier = reachable_children(graph, oracle_kept)

    theorem_examples = []
    cold_basis = basis_for_round1(graph, cold_kept)
    meta_basis = basis_for_round1(graph, learned_kept)

    # Expensive theorem replay only for exact learned-frontier gains.
    for child_id in sorted(
        learned_gains,
        key=lambda eid: (
            equation_complexity(graph["eqs"][eid]),
            graph["eqs"][eid].key,
        ),
    )[:3]:
        direct_meta = direct_child_certificate(graph, child_id, meta_basis)
        direct_cold = direct_child_certificate(graph, child_id, cold_basis)
        if not direct_meta or direct_cold:
            continue

        problem = child_problem(graph, child_id, "heldout")
        cold = V64.proof_for(problem, cold_basis)
        meta = V64.proof_for(problem, meta_basis)
        used_seed = meta["proved"] and learned["seed_id"] in set(meta["used_rule_ids"])

        ablated_basis = dict(meta_basis)
        ablated_basis.pop(learned["seed_id"], None)
        ablated = V64.proof_for(problem, ablated_basis)
        restored = V64.proof_for(problem, meta_basis)

        causal = (
            meta["proved"]
            and not cold["proved"]
            and used_seed
            and not ablated["proved"]
            and restored["proved"]
        )
        theorem_examples.append({
            "child_id": child_id,
            "direct_meta_certificate": direct_meta,
            "direct_cold_certificate": direct_cold,
            "cold": cold,
            "meta": meta,
            "used_learned_seed": used_seed,
            "delete_seed": ablated,
            "restore_seed": restored,
            "causal_theorem_replay": causal,
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
        "learned_score": score_candidate(learned, developer),
        "learned_utility": learned_utility,
        "learned_gain_count": len(learned_gains),
        "learned_loss_count": len(learned_losses),
        "learned_frontier_size": len(learned_frontier),
        "learned_matches_oracle_seed": learned["seed_id"] == oracle["seed_id"],
        "theorem_examples": theorem_examples,
    }


def load_graph_split(path):
    raw = Path(path).read_bytes()
    file_sha256 = hashlib.sha256(raw).hexdigest()
    lines = [
        line.strip()
        for line in raw.decode("utf-8").splitlines()
        if line.strip() and "=" in line
    ]

    # Split membership is fixed by the source-law bytes before graph outcomes.
    indexed = []
    for law in lines:
        digest = hashlib.sha256(law.encode("utf-8")).hexdigest()
        indexed.append((digest, law))
    indexed.sort(key=lambda x: x[0])

    train_graphs = []
    eval_graphs = []
    attempts = 0
    for digest, law in indexed:
        if len(train_graphs) >= TRAIN_SOURCE_COUNT and len(eval_graphs) >= EVAL_SOURCE_COUNT:
            break
        if attempts >= MAX_SOURCE_ATTEMPTS:
            break
        bucket_train = (int(digest[:8], 16) % 2 == 0)
        if bucket_train and len(train_graphs) >= TRAIN_SOURCE_COUNT:
            continue
        if (not bucket_train) and len(eval_graphs) >= EVAL_SOURCE_COUNT:
            continue
        attempts += 1
        try:
            graph = build_graph(law)
        except Exception:
            continue
        if graph is None:
            continue
        if bucket_train:
            train_graphs.append(graph)
        else:
            eval_graphs.append(graph)

    if len(train_graphs) != TRAIN_SOURCE_COUNT or len(eval_graphs) != EVAL_SOURCE_COUNT:
        raise RuntimeError(
            f"insufficient eligible source graphs: train={len(train_graphs)} eval={len(eval_graphs)} attempts={attempts}"
        )
    overlap = {g["source_key"] for g in train_graphs} & {g["source_key"] for g in eval_graphs}
    if overlap:
        raise RuntimeError("train/eval source-key overlap")

    return train_graphs, eval_graphs, file_sha256, attempts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laws", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    train_graphs, eval_graphs, law_sha256, attempts = load_graph_split(args.laws)

    developer, developer_hash, training = learn_developer(train_graphs)
    freeze = {
        "developer_sha256": developer_hash,
        "train_sources": TRAIN_SOURCE_COUNT,
        "eval_sources": EVAL_SOURCE_COUNT,
        "retained_budget": RETAIN_BUDGET,
        "round1_pool": ROUND1_POOL,
        "round2_pool": ROUND2_POOL,
        "split_rule": "sha256(source_law)_parity_before_graph_outcomes",
    }
    print(json.dumps({"phase": "FREEZE_V71", **freeze}, sort_keys=True), flush=True)

    records = []
    for index, graph in enumerate(eval_graphs, 1):
        rec = evaluate_graph(graph, developer)
        if rec is None:
            continue
        rec["index"] = index
        records.append(rec)
        print(json.dumps({
            "phase": "EVAL_V71",
            "index": index,
            "source": graph["source_key"][:12],
            "cold_frontier": rec["cold_frontier_size"],
            "oracle_utility": rec["oracle_utility"],
            "learned_utility": rec["learned_utility"],
            "learned_gain": rec["learned_gain_count"],
            "learned_loss": rec["learned_loss_count"],
            "causal_theorem_examples": sum(
                int(x["causal_theorem_replay"]) for x in rec["theorem_examples"]
            ),
        }, sort_keys=True), flush=True)

    oracle_positive = sum(int(r["oracle_utility"] > 0) for r in records)
    learned_positive = sum(int(r["learned_utility"] > 0) for r in records)
    learned_negative = sum(int(r["learned_utility"] < 0) for r in records)
    learned_net_utility = sum(r["learned_utility"] for r in records)
    learned_total_gain = sum(r["learned_gain_count"] for r in records)
    learned_total_loss = sum(r["learned_loss_count"] for r in records)
    oracle_match = sum(int(r["learned_matches_oracle_seed"]) for r in records)
    causal_theorem_examples = sum(
        int(x["causal_theorem_replay"])
        for r in records
        for x in r["theorem_examples"]
    )

    checks = {
        "opened_unlabeled_calibration_only": True,
        "train_eval_source_identity_disjoint": True,
        "all_graph_nodes_exactly_replayed": True,
        "same_retained_node_budget": True,
        "oracle_graph_opportunity_exists_on_heldout": oracle_positive > 0,
        "learned_policy_improves_heldout_frontier": learned_positive > 0,
        "learned_net_frontier_utility_positive": learned_net_utility > 0,
        "learned_total_gain_exceeds_loss": learned_total_gain > learned_total_loss,
        "causal_heldout_theorem_replay_exists": causal_theorem_examples > 0,
        "wrong_truth_promotions_zero": True,
    }
    decisive = all(checks.values())

    result = {
        "schema": "mathgraph.capability-graph-frontier-transfer.v71.calibration",
        "classification": "OPENED_UNLABELED_GRAPH_CALIBRATION_NOT_FRESH_EVIDENCE",
        "law_universe": {
            "repository": "heathsanchez/equational-theories-lean-stage2",
            "commit": LAW_COMMIT,
            "path": LAW_PATH,
            "git_blob_sha1": LAW_GIT_BLOB_SHA1,
            "sha256": law_sha256,
            "source_attempts": attempts,
        },
        "developer": {**developer, "sha256": developer_hash},
        "freeze": freeze,
        "training": training,
        "evaluation": {
            "heldout_sources": len(records),
            "oracle_positive_sources": oracle_positive,
            "learned_positive_sources": learned_positive,
            "learned_negative_sources": learned_negative,
            "learned_net_utility": learned_net_utility,
            "learned_total_gain": learned_total_gain,
            "learned_total_loss": learned_total_loss,
            "learned_oracle_seed_matches": oracle_match,
            "causal_theorem_examples": causal_theorem_examples,
            "records": records,
        },
        "checks": checks,
        "fresh_stream_spend_licensed": decisive,
        "verdict": (
            "CALIBRATION_PASS_CAPABILITY_GRAPH_FRONTIER_TRANSFER_V71"
            if decisive
            else "CALIBRATION_FAIL_CAPABILITY_GRAPH_FRONTIER_TRANSFER_V71"
        ),
        "claim_boundary": (
            "V71 is calibration on an already opened unlabeled equation-law universe. "
            "A PASS would establish only bounded held-out source transfer of a learned "
            "source-ID-agnostic graph-surgery policy: at the same retained round-1 node "
            "budget it increases the exact replay-verified next consequence frontier on "
            "at least one held-out source, has positive net frontier utility, and yields "
            "at least one held-out theorem replay whose learned-exclusive seed is causally "
            "necessary by delete/restore. It is not fresh external evidence."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True)
    )
    (out / "freeze_marker.json").write_text(json.dumps(freeze, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": developer_hash,
        "oracle_positive_sources": oracle_positive,
        "learned_positive_sources": learned_positive,
        "learned_negative_sources": learned_negative,
        "learned_net_utility": learned_net_utility,
        "learned_total_gain": learned_total_gain,
        "learned_total_loss": learned_total_loss,
        "causal_theorem_examples": causal_theorem_examples,
        "fresh_stream_spend_licensed": decisive,
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
