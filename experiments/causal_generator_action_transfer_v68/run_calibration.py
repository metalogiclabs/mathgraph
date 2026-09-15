#!/usr/bin/env python3
"""V68 calibration: causal generator-action transfer on an already-opened stream.

This is deliberately NOT fresh evidence. It uses V67's spent Stage2 normal stream
only to test whether the abstraction suggested by V66's causal ablations is
better than V67's failed lemma-ranking abstraction.

Training: recover exact causally necessary generator roots from the old V66
source histories (3501, 3892) by proof-lineage deletion/restoration.

Learned object: the intersection of source-ID-agnostic action descriptors across
independent causal roots. Absolute left/right positions are never retained.

Evaluation: same budget as cold development. META prioritizes matching generator
actions in round 1 and then recursively prioritizes descendants of those seeds.
All retained equations and accepted proofs are exactly replayed.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "experiments" / "cross_source_developmental_transfer_v67" / "run.py"
S = importlib.util.spec_from_file_location("v68_v67", P)
if S is None or S.loader is None:
    raise RuntimeError("cannot load V67")
V67 = importlib.util.module_from_spec(S)
sys.modules[S.name] = V67
S.loader.exec_module(V67)

V65, V64, V62, V58 = V67.V65, V67.V64, V67.V62, V67.V58
QUOTAS = V67.COLD_QUOTAS
TOTAL_BUDGET = sum(QUOTAS)
SOURCE_LIMIT = 100
TARGETS_PER_SOURCE = 2
PROBE_CAP = 36

def stable_hash(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def descriptor(eq):
    p = eq.proof
    if p.get("kind") != "CRITICAL_PAIR":
        return None
    return {
        "a_is_source": int(p["a"]) == 0,
        "b_is_source": int(p["b"]) == 0,
        "same_parent": int(p["a"]) == int(p["b"]),
        "a_dir": int(p["a_dir"]),
        "b_dir": int(p["b_dir"]),
        "overlap_depth": len(p["pos"]),
        "proper_overlap": len(p["pos"]) > 0,
    }

def learn_operator(training_rows):
    groups = V67.training_groups(training_rows)
    causal = {}
    episodes = 0
    for source, group in groups:
        basis = V64.compile_source(group[0])
        if basis["verified_count"] != len(basis["eqs"]):
            raise RuntimeError("training basis replay failure")
        found_source_root = False
        for problem in group[:V67.TRAIN_TARGETS_PER_SOURCE]:
            route = V65.route(problem)
            if not route["proof_candidate"]:
                continue
            cold = V64.proof_for(problem, V64.source_only_basis(problem))
            warm = V64.proof_for(problem, basis["eqs"])
            if cold["proved"] or not warm["proved"]:
                continue
            used = sorted({int(e) for e in warm["used_rule_ids"] if int(e) != 0})
            for eid in used:
                ablated, removed = V65.ablate_lineage(basis["eqs"], eid)
                lost = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, basis["eqs"])
                if (not lost["proved"]) and restored["proved"]:
                    episodes += 1
                    causal[(source, eid)] = {
                        "descriptor": descriptor(basis["eqs"][eid]),
                        "removed_count": len(removed),
                    }
                    found_source_root = True
                    break
            if found_source_root:
                break
    by_source = defaultdict(list)
    for (source, eid), rec in causal.items():
        by_source[source].append((eid, rec))
    if len(by_source) < 2:
        raise RuntimeError(f"need causal roots from >=2 independent sources, got {sorted(by_source)}")

    descs = [rec["descriptor"] for rec in causal.values() if rec["descriptor"] is not None]
    fields = tuple(descs[0])
    common = {}
    for f in fields:
        vals = {d[f] for d in descs}
        if len(vals) == 1:
            common[f] = vals.pop()
    if "pos" in common:
        raise RuntimeError("absolute overlap path leaked into developer")
    if not common.get("proper_overlap", False):
        raise RuntimeError("causal roots did not generalize to proper overlaps")

    removed_counts = [r["removed_count"] for r in causal.values()]
    operator = {
        "schema": "mathgraph.causal-generator-action.v68.calibration",
        "action_constraints": common,
        "recursive_descendant_priority": min(removed_counts) > 1,
        "round_quotas": list(QUOTAS),
        "total_derived_budget": TOTAL_BUDGET,
        "training_rule": "intersection_of_independent_exact_causal_ablation_roots",
        "position_invariant": True,
        "target_independent": True,
    }
    summary = {
        "causal_episode_count": episodes,
        "distinct_causal_roots": len(causal),
        "independent_sources": len(by_source),
        "roots_per_source": {s: [eid for eid, _ in rows] for s, rows in sorted(by_source.items())},
        "removed_lineage_counts": removed_counts,
        "learned_action_constraints": common,
    }
    return operator, stable_hash(operator), summary

def action_matches(proof, op):
    if proof.get("kind") != "CRITICAL_PAIR":
        return False
    d = {
        "a_is_source": int(proof["a"]) == 0,
        "b_is_source": int(proof["b"]) == 0,
        "same_parent": int(proof["a"]) == int(proof["b"]),
        "a_dir": int(proof["a_dir"]),
        "b_dir": int(proof["b_dir"]),
        "overlap_depth": len(proof["pos"]),
        "proper_overlap": len(proof["pos"]) > 0,
    }
    return all(d.get(k) == v for k, v in op["action_constraints"].items())

def compile_budgeted(problem, mode, op):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    eqs = {0: V62.Equation(0, lhs, rhs, key, {"kind": "SOURCE"}, 0)}
    by_key, next_id, frontier = {key: 0}, 1, [0]
    lineage = set()
    seed_ids = []
    rounds = []

    for round_no, quota in enumerate(QUOTAS, start=1):
        existing = sorted(eqs)
        front = set(frontier)
        candidates = {}
        for a_id in existing:
            for b_id in existing:
                if a_id not in front and b_id not in front:
                    continue
                a, b = eqs[a_id], eqs[b_id]
                for ad in (0, 1):
                    al, _ = V62.orientation(a, ad)
                    if al[0] == "v":
                        continue
                    for bd in (0, 1):
                        bl, _ = V62.orientation(b, bd)
                        if bl[0] == "v":
                            continue
                        for pos in V62.nonvar_positions(bl):
                            out = V62.derive_overlap(a, b, ad, bd, pos)
                            if out is None:
                                continue
                            cl, cr, ck = out
                            if ck in by_key:
                                continue
                            proof = {"kind":"CRITICAL_PAIR","a":a_id,"b":b_id,
                                     "a_dir":ad,"b_dir":bd,"pos":list(pos)}
                            complexity = V62.nodes(cl) + V62.nodes(cr)
                            candidates.setdefault(ck, (complexity, cl, cr, proof))

        ranked = []
        for ck, (complexity, cl, cr, proof) in candidates.items():
            if mode == "cold":
                priority = (0, 0)
            else:
                is_seed = round_no == 1 and action_matches(proof, op)
                is_desc = round_no > 1 and (
                    int(proof["a"]) in lineage or int(proof["b"]) in lineage
                )
                priority = (int(is_seed), int(is_desc))
            ranked.append((priority, complexity, ck, cl, cr, proof))
        if mode == "cold":
            ranked.sort(key=lambda x: (x[1], x[2]))
        else:
            ranked.sort(key=lambda x: (-x[0][0], -x[0][1], x[1], x[2]))

        added = []
        matched = 0
        lineage_added = 0
        for priority, complexity, ck, cl, cr, proof in ranked[:quota]:
            child = V62.Equation(next_id, cl, cr, ck, proof, round_no)
            trial = dict(eqs); trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError("critical-pair replay failure")
            eqs[next_id] = child; by_key[ck] = next_id; added.append(next_id)
            if mode == "meta" and round_no == 1 and action_matches(proof, op):
                lineage.add(next_id); seed_ids.append(next_id); matched += 1
            elif mode == "meta" and round_no > 1 and (
                int(proof["a"]) in lineage or int(proof["b"]) in lineage
            ):
                lineage.add(next_id); lineage_added += 1
            next_id += 1
        rounds.append({"round":round_no,"candidates":len(candidates),"added":len(added),
                       "matched_seeds_added":matched,"lineage_descendants_added":lineage_added})
        frontier = added
        if not frontier:
            break

    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored replay failure {eid}")
    return {"eqs":eqs,"rounds":rounds,"seed_ids":seed_ids,"lineage_ids":sorted(lineage)}

def evaluate(rows, training_ids, op):
    sources, selected, rejected = V67.select_unseen_sources(
        rows, training_ids, SOURCE_LIMIT, TARGETS_PER_SOURCE
    )
    stats = defaultdict(int)
    records, examples = [], []
    for i, problem in enumerate(selected, 1):
        route = V65.route(problem)
        rec = {"index":i,"problem_id":problem["id"],"source_id":V67.sid(problem),"route":route}
        if not route["proof_candidate"]:
            records.append(rec); continue
        stats["proof_candidates"] += 1
        base = V64.proof_for(problem, V64.source_only_basis(problem))
        if base["proved"]:
            stats["source_only_proved"] += 1; records.append(rec); continue
        if stats["development_probes"] >= PROBE_CAP:
            records.append(rec); continue
        stats["development_probes"] += 1
        cold_basis = compile_budgeted(problem, "cold", op)
        meta_basis = compile_budgeted(problem, "meta", op)
        cold = V64.proof_for(problem, cold_basis["eqs"])
        meta = V64.proof_for(problem, meta_basis["eqs"])
        stats["cold_proved"] += int(cold["proved"])
        stats["meta_proved"] += int(meta["proved"])
        is_meta_only = meta["proved"] and not cold["proved"]
        stats["meta_only"] += int(is_meta_only)
        stats["cold_only"] += int(cold["proved"] and not meta["proved"])

        cold_keys = {e.key for e in cold_basis["eqs"].values()}
        meta_used = [int(e) for e in meta["used_rule_ids"] if int(e) != 0] if meta["proved"] else []
        exclusive = [eid for eid in meta_used if meta_basis["eqs"][eid].key not in cold_keys]
        stats["meta_exclusive_used"] += int(bool(exclusive))
        if meta_basis["seed_ids"]:
            stats["sources_with_matching_seed"] += 1
        causal = False
        if is_meta_only and exclusive:
            for eid in exclusive:
                ablated, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                gone = V64.proof_for(problem, ablated)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if not gone["proved"] and restored["proved"]:
                    causal = True
                    stats["causal_lineages"] += 1
                    stats["operator_sandwiches"] += int(not cold["proved"])
                    if len(examples) < 10:
                        examples.append({"problem_id":problem["id"],"source_id":V67.sid(problem),
                                         "eid":eid,"removed":len(removed),
                                         "seed_ids":meta_basis["seed_ids"],
                                         "lineage_ids":meta_basis["lineage_ids"]})
                    break
        rec.update({"cold":cold,"meta":meta,"meta_only":is_meta_only,
                    "meta_exclusive_used_ids":exclusive,"causal":causal,
                    "meta_seed_ids":meta_basis["seed_ids"],
                    "meta_lineage_ids":meta_basis["lineage_ids"],
                    "cold_rounds":cold_basis["rounds"],"meta_rounds":meta_basis["rounds"]})
        records.append(rec)
        print(json.dumps({"phase":"CALIBRATION","id":problem["id"],"source":V67.sid(problem),
                          "cold":cold["proved"],"meta":meta["proved"],"meta_only":is_meta_only,
                          "exclusive":len(exclusive),"causal":causal}, sort_keys=True), flush=True)
    return {"selected_sources":len(sources),"selected_rows":len(selected),
            "training_overlap":len(set(sources)&training_ids),"rejected_training_rows":rejected,
            **dict(stats),"causal_examples":examples,"records":records}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--stage2", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    l3000, s3000 = V67.read_frozen_lines(Path(a.book3000), V58.EXPECTED_3000_SHA256)
    l3500, s3500 = V67.read_frozen_lines(Path(a.book3500), V58.EXPECTED_3500_SHA256)
    train = V67.parse_slice(l3000, V67.TRAIN_START, V67.TRAIN_END_3000) + \
            V67.parse_slice(l3500, V67.TRAIN_START, V67.TRAIN_END_3500)
    training_ids = {V67.sid(r) for r in train}
    op, op_hash, training = learn_operator(train)
    print(json.dumps({"phase":"FREEZE_CALIBRATION_OPERATOR","operator_sha256":op_hash,
                      "operator":op}, sort_keys=True), flush=True)

    rows, stage_sha = V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev = evaluate(rows, training_ids, op)
    signal = (
        ev.get("meta_only",0) > 0 or
        ev.get("meta_exclusive_used",0) > 0 or
        ev.get("meta_proved",0) > ev.get("cold_proved",0)
    )
    result = {
        "schema":"mathgraph.causal-generator-action.v68.calibration",
        "classification":"OPENED_DATA_CALIBRATION_NOT_FRESH_EVIDENCE",
        "operator":{**op,"sha256":op_hash},
        "training":training,
        "evaluation":ev,
        "integrity":{
            "training_hashes_exact": s3000 == V58.EXPECTED_3000_SHA256 and s3500 == V58.EXPECTED_3500_SHA256,
            "same_total_budget": sum(QUOTAS) == TOTAL_BUDGET,
            "zero_training_eval_source_overlap": ev["training_overlap"] == 0,
            "operator_target_independent": op["target_independent"],
            "operator_position_invariant": op["position_invariant"],
            "all_retained_equations_exactly_replayed": True,
            "all_accepted_proofs_exactly_replayed": True,
        },
        "stage2_sha256":stage_sha,
        "signal":signal,
        "verdict":"CALIBRATION_ACTION_OPERATOR_SIGNAL_V68" if signal else "CALIBRATION_NO_ACTION_OPERATOR_SIGNAL_V68",
        "claim_boundary":"Calibration only. The Stage2 stream was opened by V67 and cannot support a fresh transfer claim."
    }
    out=Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    (out/"operator.json").write_text(json.dumps({**op,"sha256":op_hash},indent=2,sort_keys=True))
    print(json.dumps({"verdict":result["verdict"],"operator_sha256":op_hash,
                      "cold":ev.get("cold_proved",0),"meta":ev.get("meta_proved",0),
                      "meta_only":ev.get("meta_only",0),"exclusive_used":ev.get("meta_exclusive_used",0),
                      "causal":ev.get("causal_lineages",0)}, indent=2, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
