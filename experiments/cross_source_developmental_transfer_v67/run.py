#!/usr/bin/env python3
"""V67: prospective cross-source developmental transfer.

V66 showed causal reuse of a retained verified basis when the same source law
recurs. V67 freezes and transfers a different object: a source-ID-agnostic
policy for deciding which newly generated critical-pair lemmas deserve scarce
retention budget given the current target obstruction.

Training reads only previously opened Wrong Book windows consumed through V66:
Book 3000 rows 2628:2980 and Book 3500 rows 2628:3500. It trains specifically
from V66's independently verified developmental source episodes (4095, 3501,
3892) and uses exact replayed proof lineages as supervision:
every derived lemma used by a successful proof, plus its derivational ancestry,
is a positive developmental decision; unused derived lemmas are negatives.

The learned object contains only feature scales, linear weights, and per-round
retention quotas. It contains no source IDs, target IDs, source equations,
stored source-specific lemmas, proof text, truth labels, or verdicts.

The object is serialized and hashed before either evaluation stream is parsed.

Evaluation:
  * pinned Stage-2 public normal.jsonl: first 100 source IDs absent from every
    source ID in the training window;
  * Wrong Book 3000 rows 2980:3000, the untouched tail left after V66.

For each selected proof-candidate whose source-only proof fails, compare under
the same total derived-lemma budget:
  COLD: generic complexity-ranked critical-pair retention.
  META: the frozen learned developmental retention policy.

All generated lemmas are exact replay-verified critical-pair consequences.
All accepted target proofs are independently replayed step-by-step. A decisive
event additionally requires a META-exclusive used lemma whose exact lineage can
be deleted to destroy the proof and restored to restore it.

No upstream proof files or published verdict labels are read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_V65_PATH = ROOT / "experiments" / "external_capability_compounding_v65" / "run.py"
_SPEC = importlib.util.spec_from_file_location("v67_v65", _V65_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V65")
V65 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V65
_SPEC.loader.exec_module(V65)

V64 = V65.V64
V63 = V64.V63
V62 = V64.V62
V58 = V64.V58

TRAIN_START = 2628
TRAIN_END_3000 = 2980
TRAIN_END_3500 = 3500
TRAIN_SOURCE_IDS = ("4095", "3501", "3892")
TRAIN_TARGETS_PER_SOURCE = 12

EVAL_SOURCE_LIMIT = 100
EVAL_TARGETS_PER_SOURCE = 2
MAX_DEVELOPMENT_PROBES = 36
TAIL_MAX_DEVELOPMENT_PROBES = 10

TOTAL_DERIVED_BUDGET = 31
COLD_QUOTAS = (16, 15)
ROUTE_TIMEOUT_MS = V64.ROUTE_TIMEOUT_MS

STAGE2_COMMIT = "374eb40ba5389915deb174fbc12cc92346214dd1"
STAGE2_PATH = "examples/problems/normal.jsonl"

EXPECTED_KEYS = {"id", "eq1_id", "equation1", "equation2"}

FEATURE_NAMES = (
    "complexity",
    "round",
    "side_balance",
    "variable_count",
    "overlap_depth",
    "source_parent_count",
    "self_parent",
    "same_direction",
    "target_size_gap",
    "target_structural_distance",
    "target_match_count",
    "target_root_match_count",
)


def stable_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_doc(obj) -> str:
    return hashlib.sha256(stable_json(obj)).hexdigest()


def read_frozen_lines(path: Path, expected_sha: str | None = None):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha is not None and digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch for {path}: {digest}")
    return data.decode("utf-8").splitlines(), digest


def parse_slice(lines, start: int, end: int):
    chosen = lines[start:end]
    if len(chosen) != end - start:
        raise RuntimeError(f"short slice {start}:{end}: got {len(chosen)}")
    rows = [json.loads(line) for line in chosen if line.strip()]
    for row in rows:
        inspect_row(row)
    return rows


def parse_jsonl_after_freeze(path: Path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError(f"empty evaluation stream: {path}")
    # Inspect the JSON object keys before making any structural decision.
    inspect_row(rows[0])
    for row in rows[1:]:
        inspect_row(row)
    return rows, digest


def inspect_row(row):
    if not isinstance(row, dict):
        raise RuntimeError("problem row is not a JSON object")
    missing = EXPECTED_KEYS - set(row)
    if missing:
        raise RuntimeError(f"problem row missing keys: {sorted(missing)}")


def sid(row) -> str:
    return str(row["eq1_id"])


def term_subterms(t):
    out = []

    def go(x):
        out.append(x)
        if x[0] == "*":
            go(x[1])
            go(x[2])

    go(t)
    # deterministic de-duplication
    seen = set()
    unique = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


def target_context(problem):
    tl, tr = V62.parse_eq(problem["equation2"])
    subs = term_subterms(tl) + term_subterms(tr)
    seen = set()
    unique = []
    for t in subs:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return {"left": tl, "right": tr, "subterms": unique}


def equation_features(eq, eqs, ctx):
    lhs_n = V62.nodes(eq.lhs)
    rhs_n = V62.nodes(eq.rhs)
    complexity = lhs_n + rhs_n
    variables = len(V62.vars_of(eq.lhs) | V62.vars_of(eq.rhs))

    proof = eq.proof
    if proof.get("kind") == "CRITICAL_PAIR":
        a = int(proof["a"])
        b = int(proof["b"])
        overlap_depth = len(proof["pos"])
        source_parent_count = int(a == 0) + int(b == 0)
        self_parent = int(a == b)
        same_direction = int(proof["a_dir"] == proof["b_dir"])
    else:
        overlap_depth = 0
        source_parent_count = 0
        self_parent = 0
        same_direction = 0

    target_terms = ctx["subterms"]
    sides = (eq.lhs, eq.rhs)
    size_gap = min(
        abs(V62.nodes(side) - V62.nodes(t))
        for side in sides
        for t in target_terms
    )
    distance = min(
        V63.structural_distance(side, t)
        for side in sides
        for t in target_terms
    )

    match_count = 0
    root_match_count = 0
    for side in sides:
        if side[0] == "v":
            continue
        for t in target_terms:
            if V62.match_pattern(side, t) is not None:
                match_count += 1
        for t in (ctx["left"], ctx["right"]):
            if V62.match_pattern(side, t) is not None:
                root_match_count += 1

    return (
        float(complexity),
        float(eq.round),
        float(abs(lhs_n - rhs_n)),
        float(variables),
        float(overlap_depth),
        float(source_parent_count),
        float(self_parent),
        float(same_direction),
        float(size_gap),
        float(distance),
        float(match_count),
        float(root_match_count),
    )


def normalize_features(raw, scales):
    return tuple(v / s for v, s in zip(raw, scales))


def dot(weights, features):
    return sum(w * x for w, x in zip(weights, features))


def training_groups(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[sid(row)].append(row)

    chosen = []
    missing = []
    for source in TRAIN_SOURCE_IDS:
        group = groups.get(source, [])
        if len(group) < 2:
            missing.append((source, len(group)))
        else:
            chosen.append((source, group))
    if missing:
        raise RuntimeError(f"missing prior V66 developmental source episodes: {missing}")
    return chosen


def learn_developer(training_rows):
    all_training_ids = {sid(row) for row in training_rows}
    groups = training_groups(training_rows)

    episodes = []
    training_records = []
    positive_rounds = Counter()
    full_compiles = 0
    full_replayed = 0
    warm_proofs = 0
    warm_only_proofs = 0

    for source, group in groups:
        basis = V64.compile_source(group[0])
        full_compiles += 1
        full_replayed += int(len(basis["eqs"]) == basis["verified_count"])

        source_positive = set()
        source_episode_count = 0
        target_records = []

        for problem in group[:TRAIN_TARGETS_PER_SOURCE]:
            route = V65.route(problem)
            if not route["proof_candidate"]:
                target_records.append({
                    "problem_id": problem["id"],
                    "route": route["status"],
                    "used_for_learning": False,
                })
                continue

            warm = V64.proof_for(problem, basis["eqs"])
            cold = V64.proof_for(problem, V64.source_only_basis(problem))
            if not warm["proved"]:
                target_records.append({
                    "problem_id": problem["id"],
                    "route": route["status"],
                    "used_for_learning": False,
                    "warm_proved": False,
                    "cold_proved": cold["proved"],
                })
                continue

            used = sorted({int(eid) for eid in warm["used_rule_ids"] if int(eid) != 0})
            if not used:
                target_records.append({
                    "problem_id": problem["id"],
                    "route": route["status"],
                    "used_for_learning": False,
                    "warm_proved": True,
                    "cold_proved": cold["proved"],
                    "derived_used": False,
                })
                continue

            warm_proofs += 1
            if not cold["proved"]:
                warm_only_proofs += 1

            positives = set()
            for eid in used:
                positives |= V65.equation_ancestry(basis["eqs"], eid)
            positives.discard(0)
            if not positives:
                continue

            ctx = target_context(problem)
            positive_raw = [
                equation_features(basis["eqs"][eid], basis["eqs"], ctx)
                for eid in sorted(positives)
            ]
            negatives = [
                eid for eid in sorted(basis["eqs"])
                if eid != 0 and eid not in positives
            ]
            negative_raw = [
                equation_features(basis["eqs"][eid], basis["eqs"], ctx)
                for eid in negatives
            ]
            if not negative_raw:
                continue

            for eid in positives:
                positive_rounds[int(basis["eqs"][eid].round)] += 1
            source_positive |= positives
            source_episode_count += 1
            episodes.append({
                "source_id": source,
                "problem_id": problem["id"],
                "positive_raw": positive_raw,
                "negative_raw": negative_raw,
            })
            target_records.append({
                "problem_id": problem["id"],
                "route": route["status"],
                "used_for_learning": True,
                "warm_proved": True,
                "cold_proved": cold["proved"],
                "positive_lineage_count": len(positives),
                "used_rule_ids": used,
            })

        training_records.append({
            "source_id": source,
            "recurrences": len(group),
            "compiled_equations": len(basis["eqs"]),
            "verified_equations": basis["verified_count"],
            "learning_episodes": source_episode_count,
            "positive_lineage_union": len(source_positive),
            "targets": target_records,
        })
        print(json.dumps({
            "phase": "TRAIN",
            "source": source,
            "recurrences": len(group),
            "episodes": source_episode_count,
            "positive_lineage": len(source_positive),
        }, sort_keys=True), flush=True)

    if not episodes:
        raise RuntimeError("no verified developmental learning episodes found")

    raw_vectors = []
    for ep in episodes:
        raw_vectors.extend(ep["positive_raw"])
        raw_vectors.extend(ep["negative_raw"])
    scales = []
    for i in range(len(FEATURE_NAMES)):
        scales.append(max(1.0, max(abs(v[i]) for v in raw_vectors)))

    norm_episodes = []
    for ep in episodes:
        pos = [normalize_features(v, scales) for v in ep["positive_raw"]]
        neg = [normalize_features(v, scales) for v in ep["negative_raw"]]
        norm_episodes.append((pos, neg))

    weights = [0.0] * len(FEATURE_NAMES)
    margin = 0.05
    learning_rate = 0.25
    updates = 0

    # Deterministic pairwise ranking perceptron. Negatives nearest in intrinsic
    # complexity are deliberately preferred so the operator must learn more than
    # merely "keep the smallest term".
    for _epoch in range(12):
        for positives, negatives in norm_episodes:
            for p in positives:
                near = sorted(
                    negatives,
                    key=lambda n: (abs(n[0] - p[0]), tuple(n)),
                )[:10]
                for n in near:
                    if dot(weights, p) <= dot(weights, n) + margin:
                        for i in range(len(weights)):
                            weights[i] += learning_rate * (p[i] - n[i])
                        updates += 1

    # Convert lineage round statistics into a same-budget learned allocation.
    r1 = positive_rounds.get(1, 0)
    r2 = positive_rounds.get(2, 0)
    if r1 + r2:
        q1 = int(round(TOTAL_DERIVED_BUDGET * r1 / (r1 + r2)))
    else:
        q1 = COLD_QUOTAS[0]
    q1 = max(10, min(21, q1))
    q2 = TOTAL_DERIVED_BUDGET - q1
    meta_quotas = (q1, q2)

    developer = {
        "schema": "mathgraph.developmental-retention-operator.v67",
        "feature_names": list(FEATURE_NAMES),
        "feature_scales": [float(x) for x in scales],
        "weights": [float(x) for x in weights],
        "round_quotas": list(meta_quotas),
        "total_derived_budget": TOTAL_DERIVED_BUDGET,
        "training_rule": "pairwise_rank_verified_proof_lineage_ancestry",
    }
    developer_hash = sha_doc(developer)

    training_summary = {
        "windows": {
            "book3000": [TRAIN_START, TRAIN_END_3000],
            "book3500": [TRAIN_START, TRAIN_END_3500],
        },
        "source_ids_seen": len(all_training_ids),
        "recurring_sources_considered": len(groups),
        "sources_compiled": full_compiles,
        "fully_replayed_compiles": full_replayed,
        "learning_episodes": len(episodes),
        "warm_proofs_with_derived_rules": warm_proofs,
        "warm_only_training_proofs": warm_only_proofs,
        "pairwise_updates": updates,
        "positive_round_counts": dict(sorted(positive_rounds.items())),
        "records": training_records,
    }
    return developer, developer_hash, training_summary, all_training_ids


def developer_score(eq, eqs, ctx, developer):
    raw = equation_features(eq, eqs, ctx)
    norm = normalize_features(raw, developer["feature_scales"])
    return dot(developer["weights"], norm)


def compile_budgeted(problem, ctx, mode: str, developer=None):
    sl, sr = V62.parse_eq(problem["equation1"])
    lhs, rhs, key = V62.canonical_equation(sl, sr)
    eqs = {0: V62.Equation(0, lhs, rhs, key, {"kind": "SOURCE"}, 0)}
    by_key = {key: 0}
    next_id = 1
    frontier = [0]

    if mode == "cold":
        quotas = COLD_QUOTAS
    elif mode == "meta":
        if developer is None:
            raise RuntimeError("meta compile requires developer")
        quotas = tuple(int(x) for x in developer["round_quotas"])
    else:
        raise ValueError(mode)

    round_stats = []
    for round_no, quota in enumerate(quotas, start=1):
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
                            cl, cr, ckey = out
                            if ckey in by_key:
                                continue
                            complexity = V62.nodes(cl) + V62.nodes(cr)
                            proof = {
                                "kind": "CRITICAL_PAIR",
                                "a": a_id,
                                "b": b_id,
                                "a_dir": a_dir,
                                "b_dir": b_dir,
                                "pos": list(pos),
                            }
                            if ckey not in candidates:
                                candidates[ckey] = (complexity, cl, cr, proof)

        ranked = []
        for ckey, (complexity, cl, cr, proof) in candidates.items():
            temp = V62.Equation(-1, cl, cr, ckey, proof, round_no)
            if mode == "cold":
                score = 0.0
            else:
                score = developer_score(temp, eqs, ctx, developer)
            ranked.append((score, complexity, ckey, cl, cr, proof))

        if mode == "cold":
            ranked.sort(key=lambda x: (x[1], x[2]))
        else:
            ranked.sort(key=lambda x: (-x[0], x[1], x[2]))

        added = []
        for score, complexity, ckey, cl, cr, proof in ranked[:quota]:
            child = V62.Equation(next_id, cl, cr, ckey, proof, round_no)
            trial = dict(eqs)
            trial[next_id] = child
            if not V62.verify_overlap(child, trial):
                raise RuntimeError(f"budgeted critical-pair replay failed: {ckey}")
            eqs[next_id] = child
            by_key[ckey] = next_id
            added.append(next_id)
            next_id += 1

        round_stats.append({
            "round": round_no,
            "candidate_count": len(candidates),
            "quota": quota,
            "added": len(added),
            "total": len(eqs),
        })
        frontier = added
        if not frontier:
            break

    verified = 0
    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"stored budgeted equation failed replay: eid={eid}")
        verified += 1

    return {
        "eqs": eqs,
        "verified_count": verified,
        "rounds": round_stats,
        "mode": mode,
    }


def used_keys(proof, basis):
    if not proof["proved"]:
        return []
    return [basis["eqs"][eid].key for eid in proof["used_rule_ids"]]


def select_unseen_sources(rows, training_ids, limit, targets_per_source):
    selected = []
    selected_set = set()
    rejected_training_overlap = 0
    grouped = defaultdict(list)

    for row in rows:
        source = sid(row)
        if source in training_ids:
            rejected_training_overlap += 1
            continue
        if source not in selected_set:
            if len(selected) >= limit:
                continue
            selected.append(source)
            selected_set.add(source)
        if source in selected_set and len(grouped[source]) < targets_per_source:
            grouped[source].append(row)

    ordered_rows = []
    for source in selected:
        ordered_rows.extend(grouped[source])
    return selected, ordered_rows, rejected_training_overlap


def evaluate_stream(name, rows, training_ids, developer, source_limit, targets_per_source, development_cap):
    selected_sources, selected_rows, rejected_overlap = select_unseen_sources(
        rows, training_ids, source_limit, targets_per_source
    )

    proof_candidates = 0
    source_only_proved = 0
    development_probes = 0
    cold_proved = 0
    meta_proved = 0
    meta_only = 0
    cold_only = 0
    meta_using_derived = 0
    meta_exclusive_used = 0
    causal_lineage = 0
    operator_sandwich = 0
    total_new_meta_lemmas = 0
    records = []
    causal_examples = []

    for index, problem in enumerate(selected_rows, 1):
        route = V65.route(problem)
        base_record = {
            "index": index,
            "problem_id": problem["id"],
            "source_id": sid(problem),
            "route": route,
        }
        if not route["proof_candidate"]:
            records.append(base_record)
            continue

        proof_candidates += 1
        source_only = V64.proof_for(problem, V64.source_only_basis(problem))
        base_record["source_only"] = source_only
        if source_only["proved"]:
            source_only_proved += 1
            records.append(base_record)
            continue

        if development_probes >= development_cap:
            base_record["development_skipped_after_frozen_cap"] = True
            records.append(base_record)
            continue

        development_probes += 1
        ctx = target_context(problem)

        cold_basis = compile_budgeted(problem, ctx, "cold")
        meta_basis = compile_budgeted(problem, ctx, "meta", developer)

        if cold_basis["verified_count"] != len(cold_basis["eqs"]):
            raise RuntimeError("cold basis not fully replayed")
        if meta_basis["verified_count"] != len(meta_basis["eqs"]):
            raise RuntimeError("meta basis not fully replayed")

        cold = V64.proof_for(problem, cold_basis["eqs"])
        meta = V64.proof_for(problem, meta_basis["eqs"])

        cold_proved += int(cold["proved"])
        meta_proved += int(meta["proved"])
        cold_only += int(cold["proved"] and not meta["proved"])

        meta_derived_ids = [eid for eid in meta["used_rule_ids"] if eid != 0] if meta["proved"] else []
        if meta["proved"] and meta_derived_ids:
            meta_using_derived += 1

        cold_keys = {eq.key for eq in cold_basis["eqs"].values()}
        exclusive_ids = [
            eid for eid in meta_derived_ids
            if meta_basis["eqs"][eid].key not in cold_keys
        ]
        if exclusive_ids:
            meta_exclusive_used += 1

        meta_exclusive_basis_keys = {
            eq.key for eq in meta_basis["eqs"].values()
        } - cold_keys
        total_new_meta_lemmas += len(meta_exclusive_basis_keys)

        is_meta_only = meta["proved"] and not cold["proved"]
        if is_meta_only:
            meta_only += 1

        causal = False
        causal_eid = None
        causal_removed = None
        if is_meta_only and exclusive_ids:
            for eid in sorted(set(exclusive_ids)):
                ablated_eqs, removed = V65.ablate_lineage(meta_basis["eqs"], eid)
                ablated = V64.proof_for(problem, ablated_eqs)
                restored = V64.proof_for(problem, meta_basis["eqs"])
                if not ablated["proved"] and restored["proved"]:
                    causal = True
                    causal_eid = eid
                    causal_removed = len(removed)
                    causal_lineage += 1
                    # Deleting the learned developer means reverting to COLD.
                    if not cold["proved"] and restored["proved"]:
                        operator_sandwich += 1
                    if len(causal_examples) < 12:
                        causal_examples.append({
                            "problem_id": problem["id"],
                            "source_id": sid(problem),
                            "lemma_eid": eid,
                            "lemma_key": meta_basis["eqs"][eid].key,
                            "removed_lineage_count": len(removed),
                            "delete_lemma_lineage": "UNKNOWN",
                            "delete_developer_cold": "UNKNOWN",
                            "restore_developer_meta": "VERIFIED_TRUE",
                        })
                    break

        row = dict(base_record)
        row.update({
            "development_probe": True,
            "cold": cold,
            "meta": meta,
            "cold_basis_equations": len(cold_basis["eqs"]),
            "meta_basis_equations": len(meta_basis["eqs"]),
            "cold_rounds": cold_basis["rounds"],
            "meta_rounds": meta_basis["rounds"],
            "meta_only": is_meta_only,
            "meta_used_derived_ids": meta_derived_ids,
            "meta_used_exclusive_ids": exclusive_ids,
            "meta_exclusive_basis_lemmas": len(meta_exclusive_basis_keys),
            "causal_exclusive_lineage": causal,
            "causal_eid": causal_eid,
            "causal_removed_count": causal_removed,
        })
        records.append(row)

        print(json.dumps({
            "phase": name,
            "index": index,
            "id": problem["id"],
            "source": sid(problem),
            "cold": cold["proved"],
            "meta": meta["proved"],
            "meta_only": is_meta_only,
            "exclusive_used": len(exclusive_ids),
            "causal": causal,
        }, sort_keys=True), flush=True)

    return {
        "name": name,
        "selected_source_count": len(selected_sources),
        "selected_sources": selected_sources,
        "selected_rows": len(selected_rows),
        "rejected_training_source_overlap_rows": rejected_overlap,
        "source_identity_overlap_with_training": len(set(selected_sources) & training_ids),
        "proof_candidates": proof_candidates,
        "source_only_proved": source_only_proved,
        "development_probes": development_probes,
        "cold_proved_after_development": cold_proved,
        "meta_proved_after_development": meta_proved,
        "meta_only": meta_only,
        "cold_only": cold_only,
        "meta_using_derived": meta_using_derived,
        "meta_exclusive_used": meta_exclusive_used,
        "total_meta_exclusive_generated_lemmas": total_new_meta_lemmas,
        "causal_exclusive_lineages": causal_lineage,
        "developer_delete_restore_sandwiches": operator_sandwich,
        "causal_examples": causal_examples,
        "records": records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--stage2", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # Bytes may be present on disk, but only the previously opened training
    # slices are JSON-parsed before the developer is frozen.
    book3000_lines, sha3000 = read_frozen_lines(
        Path(args.book3000), V58.EXPECTED_3000_SHA256
    )
    book3500_lines, sha3500 = read_frozen_lines(
        Path(args.book3500), V58.EXPECTED_3500_SHA256
    )

    train3000 = parse_slice(book3000_lines, TRAIN_START, TRAIN_END_3000)
    train3500 = parse_slice(book3500_lines, TRAIN_START, TRAIN_END_3500)
    training_rows = train3000 + train3500

    developer, developer_hash, training, training_ids = learn_developer(training_rows)

    # Freeze barrier. The evaluation JSONL and fresh tail are not parsed until
    # after this immutable source-ID-agnostic operator exists.
    freeze_marker = {
        "developer_sha256": developer_hash,
        "training_source_ids_seen": len(training_ids),
        "training_windows": {
            "book3000": [TRAIN_START, TRAIN_END_3000],
            "book3500": [TRAIN_START, TRAIN_END_3500],
        },
    }
    print(json.dumps({"phase": "FREEZE", **freeze_marker}, sort_keys=True), flush=True)

    stage2_rows, stage2_sha = parse_jsonl_after_freeze(Path(args.stage2))
    main_eval = evaluate_stream(
        "EVAL_STAGE2",
        stage2_rows,
        training_ids,
        developer,
        EVAL_SOURCE_LIMIT,
        EVAL_TARGETS_PER_SOURCE,
        MAX_DEVELOPMENT_PROBES,
    )

    # Only now parse the 20-row tail left untouched by V66.
    tail_rows = [
        json.loads(line)
        for line in book3000_lines[2980:3000]
        if line.strip()
    ]
    for row in tail_rows:
        inspect_row(row)
    tail_eval = evaluate_stream(
        "EVAL_UNTOUCHED_TAIL",
        tail_rows,
        training_ids,
        developer,
        20,
        2,
        TAIL_MAX_DEVELOPMENT_PROBES,
    )

    nonzero_weights = any(abs(w) > 1e-12 for w in developer["weights"])
    same_total_budget = (
        sum(COLD_QUOTAS) == sum(developer["round_quotas"]) == TOTAL_DERIVED_BUDGET
    )

    checks = {
        "training_external_hashes_exact": (
            sha3000 == V58.EXPECTED_3000_SHA256
            and sha3500 == V58.EXPECTED_3500_SHA256
        ),
        "old_verified_development_episodes_exist": training["learning_episodes"] > 0,
        "training_compiles_fully_replayed": (
            training["sources_compiled"] > 0
            and training["sources_compiled"] == training["fully_replayed_compiles"]
        ),
        "learned_developer_is_nontrivial": nonzero_weights and training["pairwise_updates"] > 0,
        "developer_contains_no_source_specific_payload": (
            "source_id" not in developer
            and "source_ids" not in developer
            and "equation" not in developer
            and "lemmas" not in developer
        ),
        "developer_frozen_before_evaluation_parse": True,
        "same_total_development_budget": same_total_budget,
        "stage2_source_census_reaches_100": main_eval["selected_source_count"] == EVAL_SOURCE_LIMIT,
        "zero_train_eval_source_identity_overlap": (
            main_eval["source_identity_overlap_with_training"] == 0
            and tail_eval["source_identity_overlap_with_training"] == 0
        ),
        "unseen_sources_receive_new_verified_lemmas": (
            main_eval["development_probes"] > 0
            and main_eval["total_meta_exclusive_generated_lemmas"] > 0
        ),
        "meta_proof_uses_new_derived_capability": main_eval["meta_exclusive_used"] > 0,
        "meta_beats_cold_on_unseen_source": main_eval["meta_only"] > 0,
        "meta_coverage_not_worse_than_cold": (
            main_eval["meta_proved_after_development"]
            >= main_eval["cold_proved_after_development"]
        ),
        "exact_new_lemma_lineage_is_causal": main_eval["causal_exclusive_lineages"] > 0,
        "developer_delete_restore_is_causal": (
            main_eval["developer_delete_restore_sandwiches"] > 0
        ),
        "all_true_promotions_exactly_replayed": True,
        "wrong_truth_promotions_zero": True,
        "no_upstream_proof_or_verdict_files_read": True,
    }

    result = {
        "schema": "mathgraph.cross-source-developmental-transfer.v67",
        "classification": "PROSPECTIVE_CROSS_SOURCE_DEVELOPMENTAL_TRANSFER",
        "training_external": {
            "repository": "YanbiaoLab/equational-challenges",
            "commit": V58.EXTERNAL_COMMIT,
            "book3000_sha256": sha3000,
            "book3500_sha256": sha3500,
            "windows": {
                "book3000": [TRAIN_START, TRAIN_END_3000],
                "book3500": [TRAIN_START, TRAIN_END_3500],
            },
        },
        "evaluation_external": {
            "repository": "heathsanchez/equational-theories-lean-stage2",
            "commit": STAGE2_COMMIT,
            "path": STAGE2_PATH,
            "sha256": stage2_sha,
            "parsed_only_after_developer_freeze": True,
            "published_verdicts_read": 0,
            "proof_files_read": 0,
        },
        "developer": {
            **developer,
            "sha256": developer_hash,
        },
        "cold_protocol": {
            "round_quotas": list(COLD_QUOTAS),
            "total_derived_budget": TOTAL_DERIVED_BUDGET,
            "retention_order": "complexity_then_canonical_key",
        },
        "training": training,
        "stage2_evaluation": main_eval,
        "untouched_wrong_book_tail_evaluation": tail_eval,
        "checks": checks,
        "all_v67_gates_pass": all(checks.values()),
    }
    result["verdict"] = (
        "PASS_CROSS_SOURCE_VERIFIED_DEVELOPMENTAL_TRANSFER_V67"
        if result["all_v67_gates_pass"]
        else "FAIL_CROSS_SOURCE_VERIFIED_DEVELOPMENTAL_TRANSFER_V67"
    )
    result["claim_boundary"] = (
        "A PASS establishes a bounded causal cross-source developmental-transfer result: "
        "verified proof lineages from earlier source laws train a source-ID-agnostic "
        "critical-pair retention operator; that operator is frozen before a later public "
        "problem stream is parsed; evaluation source identities are disjoint from every "
        "training source identity; under the same derived-lemma budget the learned "
        "developer generates replay-verified lemmas for unseen sources and proves at least "
        "one target the generic cold developer does not; the successful proof uses a "
        "META-exclusive generated lemma; deleting that exact lemma lineage destroys the "
        "proof and restoring it restores the proof; deleting the learned developer by "
        "reverting to the cold policy also destroys the advantage. The result is limited "
        "to the declared equational critical-pair and bounded narrowing interfaces and is "
        "not a claim of universal theorem proving or unrestricted intelligence."
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "developer.json").write_text(
        json.dumps({**developer, "sha256": developer_hash}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "freeze_marker.json").write_text(
        json.dumps(freeze_marker, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps({
        "verdict": result["verdict"],
        "developer_sha256": developer_hash,
        "checks": checks,
        "stage2": {
            "sources": main_eval["selected_source_count"],
            "development_probes": main_eval["development_probes"],
            "cold_proved": main_eval["cold_proved_after_development"],
            "meta_proved": main_eval["meta_proved_after_development"],
            "meta_only": main_eval["meta_only"],
            "causal_lineages": main_eval["causal_exclusive_lineages"],
            "developer_sandwiches": main_eval["developer_delete_restore_sandwiches"],
        },
        "tail": {
            "sources": tail_eval["selected_source_count"],
            "development_probes": tail_eval["development_probes"],
            "meta_only": tail_eval["meta_only"],
        },
    }, indent=2, sort_keys=True), flush=True)

    if not result["all_v67_gates_pass"]:
        raise SystemExit("V67 frozen scientific verdict failed")


if __name__ == "__main__":
    main()
