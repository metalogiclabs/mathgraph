#!/usr/bin/env python3
"""Crystal Chess V45: fail-closed sufficiency guard for normal root certificates.

V42 established the fixed certificate object:
    C(s) = union(top-16 moves at clean 1k MultiPV16,
                 top-16 moves at TT-reused 4k MultiPV16).

On 2,385 exposed normal positions C contains the pinned 100k Stockfish move
on 2,366 states (99.203354%) while eliminating 53.900407% of legal root moves.
The exact 19 misses survive width expansion; V43/V44 show that they are a
mixture of horizon and search-mode instability.

V45 does NOT enlarge C.  It learns only an applicability guard from observables
already produced by the fixed 1k/4k probes.  A compiled leaf is usable iff:
* it has zero exposed certificate misses;
* it has nontrivial support;
* its support spans multiple historical generations.

The selected guard is frozen before untouched seeds 20261025/20261026 are
queried at 100k.  Outside the guard the legal root frontier is unchanged.

This certifies move-set sufficiency relative to pinned Stockfish authority; it
does not yet claim that restricting Stockfish search to C yields node/Elo gain.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import chess
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE1_NODES,
    PROBE2_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key
from crystal_chess_normal_certificate_set_v41 import (
    collect_boards,
    search_multi,
    top_moves,
)

SCHEMA = "mathgraph.crystal-chess.certificate-sufficiency-guard.v45"
V42_RUN = 36519656689
FRESH_SEEDS = (20261025, 20261026)
MULTIPV = 16
WIDTH = 16
MIN_SAFE_LEAF_SUPPORT = 24
MIN_SAFE_GENERATIONS = 4
MIN_TOTAL_ACCEPTED = 200

CONFIGS = tuple(
    (depth, min_leaf)
    for depth in (2, 3, 4, 5, 6)
    for min_leaf in (16, 32, 64, 128)
)


def union_top16(
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for move in top_moves(p2, WIDTH) + top_moves(p1, WIDTH):
        if move not in seen:
            seen.add(move)
            out.append(move)
    return out


def ranked_map(probe: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(row["rank"]): row for row in probe["ranked"]}


def rank_of(move: str, probe: dict[str, Any]) -> int:
    for row in probe["ranked"]:
        if str(row["move"]) == move:
            return int(row["rank"])
    return MULTIPV + 1


def score_at(probe: dict[str, Any], rank: int) -> int:
    rows = ranked_map(probe)
    if rank in rows:
        return int(rows[rank]["score"])
    if rows:
        return int(rows[max(rows)]["score"])
    return 0


def depth_stats(probe: dict[str, Any]) -> tuple[int, int, int, int]:
    if not probe["ranked"]:
        return 0, 0, 0, 0
    depths = [int(r["depth"]) for r in probe["ranked"]]
    sel = [int(r["seldepth"]) for r in probe["ranked"]]
    return min(depths), max(depths), min(sel), max(sel)


def feature_row(
    board: chess.Board,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> tuple[list[str], tuple[int, ...]]:
    names: list[str] = []
    vals: list[int] = []

    def add(name: str, value: int | bool) -> None:
        names.append(name)
        vals.append(int(value))

    m1 = [str(r["move"]) for r in p1["ranked"]]
    m2 = [str(r["move"]) for r in p2["ranked"]]
    s1, s2 = set(m1), set(m2)

    add("root_best_stable", str(p1["bestmove"]) == str(p2["bestmove"]))
    add("p1_best_rank_in_p2", rank_of(str(p1["bestmove"]), p2))
    add("p2_best_rank_in_p1", rank_of(str(p2["bestmove"]), p1))
    add("p1_ranked_count", len(m1))
    add("p2_ranked_count", len(m2))
    add("union16_size", len(s1 | s2))
    add("intersection16_size", len(s1 & s2))
    add("symmetric_difference16_size", len(s1 ^ s2))
    add("legal_moves", board.legal_moves.count())

    for k in (2, 4, 8, 16):
        a = set(m1[:k])
        b = set(m2[:k])
        add(f"overlap_top{k}", len(a & b))
        add(f"union_top{k}", len(a | b))
        add(f"p1_margin_top{k}", score_at(p1, 1) - score_at(p1, k))
        add(f"p2_margin_top{k}", score_at(p2, 1) - score_at(p2, k))

    add("p1_score1", score_at(p1, 1))
    add("p2_score1", score_at(p2, 1))
    add("score1_delta_abs", abs(score_at(p2, 1) - score_at(p1, 1)))

    p1dmin, p1dmax, p1smin, p1smax = depth_stats(p1)
    p2dmin, p2dmax, p2smin, p2smax = depth_stats(p2)
    add("p1_depth_min", p1dmin)
    add("p1_depth_max", p1dmax)
    add("p2_depth_min", p2dmin)
    add("p2_depth_max", p2dmax)
    add("p1_seldepth_min", p1smin)
    add("p1_seldepth_max", p1smax)
    add("p2_seldepth_min", p2smin)
    add("p2_seldepth_max", p2smax)
    add("depth_min_delta", p2dmin - p1dmin)
    add("depth_max_delta", p2dmax - p1dmax)

    return names, tuple(vals)


def collect_source(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    feature_names: list[str] | None = None
    for generation, board in items:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES, multipv=MULTIPV, clear=True
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES, multipv=MULTIPV, clear=False
        )
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        authority = str(auth["bestmove"])
        cset = union_top16(p1, p2)
        names, feats = feature_row(board, p1, p2)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise AssertionError("feature order drift")
        records.append({
            "generation": generation,
            "fen": fen,
            "features": feats,
            "authority": authority,
            "certificate_set": cset,
            "legal_moves": board.legal_moves.count(),
            "safe": authority in cset,
        })
    return records, feature_names or []


def leaf_summary(
    model: DecisionTreeClassifier,
    records: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    X = np.asarray([r["features"] for r in records], dtype=np.int32)
    leaves = model.apply(X)
    stats: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "misses": 0,
            "generations": Counter(),
            "saved_moves": 0,
            "legal_moves": 0,
        }
    )
    for leaf, rec in zip(leaves, records):
        st = stats[int(leaf)]
        st["count"] += 1
        st["misses"] += int(not bool(rec["safe"]))
        st["generations"][str(rec["generation"])] += 1
        st["legal_moves"] += int(rec["legal_moves"])
        st["saved_moves"] += max(
            0, int(rec["legal_moves"]) - len(rec["certificate_set"])
        )
    return dict(stats)


def compile_safe_leaves(
    model: DecisionTreeClassifier,
    records: list[dict[str, Any]],
) -> tuple[set[int], dict[int, dict[str, Any]]]:
    stats = leaf_summary(model, records)
    safe = {
        leaf
        for leaf, st in stats.items()
        if int(st["misses"]) == 0
        and int(st["count"]) >= MIN_SAFE_LEAF_SUPPORT
        and len(st["generations"]) >= MIN_SAFE_GENERATIONS
    }
    return safe, stats


def evaluate_guard(
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    X = np.asarray([r["features"] for r in records], dtype=np.int32)
    leaves = model.apply(X)
    accepted = misses = saved = legal = 0
    support = Counter()
    examples = []
    for rec, leaf in zip(records, leaves):
        legal += int(rec["legal_moves"])
        if int(leaf) not in safe_leaves:
            continue
        accepted += 1
        support[str(rec["generation"])] += 1
        misses += int(not bool(rec["safe"]))
        saved += max(
            0, int(rec["legal_moves"]) - len(rec["certificate_set"])
        )
        if len(examples) < 20:
            examples.append({
                "generation": rec["generation"],
                "fen": rec["fen"],
                "authority": rec["authority"],
                "certificate_set": rec["certificate_set"],
                "safe": rec["safe"],
                "leaf": int(leaf),
            })
    n = len(records)
    return {
        "positions": n,
        "accepted": accepted,
        "misses": misses,
        "coverage_ratio": accepted / n if n else 0.0,
        "effective_root_move_elimination_ratio": saved / legal if legal else 0.0,
        "accepted_support": dict(support),
        "examples": examples,
    }


def choose_model(
    records: list[dict[str, Any]],
) -> tuple[DecisionTreeClassifier | None, set[int], dict[str, Any]]:
    X = np.asarray([r["features"] for r in records], dtype=np.int32)
    y = np.asarray([int(bool(r["safe"])) for r in records], dtype=np.int8)
    candidates = []

    for depth, min_leaf in CONFIGS:
        model = DecisionTreeClassifier(
            criterion="entropy",
            max_depth=depth,
            min_samples_leaf=min_leaf,
            random_state=0,
        )
        model.fit(X, y)
        safe, stats = compile_safe_leaves(model, records)
        ev = evaluate_guard(model, safe, records)
        if (
            ev["misses"] == 0
            and ev["accepted"] >= MIN_TOTAL_ACCEPTED
            and ev["effective_root_move_elimination_ratio"] > 0
        ):
            candidates.append(
                (
                    -float(ev["effective_root_move_elimination_ratio"]),
                    -float(ev["coverage_ratio"]),
                    depth,
                    min_leaf,
                    model,
                    safe,
                    stats,
                    ev,
                )
            )

    if not candidates:
        return None, set(), {"status": "no_supported_zero_miss_guard"}

    candidates.sort(key=lambda x: x[:4])
    _neg_elim, _neg_cov, depth, min_leaf, model, safe, stats, ev = candidates[0]
    return model, safe, {
        "status": "selected",
        "max_depth": depth,
        "min_samples_leaf": min_leaf,
        "safe_leaves": sorted(safe),
        "safe_leaf_stats": {
            str(leaf): {
                "count": int(stats[leaf]["count"]),
                "misses": int(stats[leaf]["misses"]),
                "generations": dict(stats[leaf]["generations"]),
                "saved_moves": int(stats[leaf]["saved_moves"]),
                "legal_moves": int(stats[leaf]["legal_moves"]),
            }
            for leaf in sorted(safe)
        },
        "source_evaluation": ev,
    }


def fresh_records(
    engine: UCIStockfish,
    boards: list[chess.Board],
    feature_names_ref: list[str],
) -> list[dict[str, Any]]:
    out = []
    for board in boards:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES, multipv=MULTIPV, clear=True
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES, multipv=MULTIPV, clear=False
        )
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        authority = str(auth["bestmove"])
        cset = union_top16(p1, p2)
        names, feats = feature_row(board, p1, p2)
        if names != feature_names_ref:
            raise AssertionError("fresh feature drift")
        out.append({
            "generation": "fresh",
            "fen": fen,
            "features": feats,
            "authority": authority,
            "certificate_set": cset,
            "legal_moves": board.legal_moves.count(),
            "safe": authority in cset,
        })
    return out


def export_guard(
    path: Path,
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    feature_names: list[str],
    selection: dict[str, Any],
) -> str:
    tree = model.tree_
    payload = {
        "schema": SCHEMA + ".guard",
        "stockfish_pin": STOCKFISH_PIN,
        "v42_run": V42_RUN,
        "certificate": {
            "kind": "union_p1p2_top16",
            "multipv": MULTIPV,
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "probe2_reuses_probe1_tt": True,
        },
        "feature_names": feature_names,
        "safe_leaves": sorted(safe_leaves),
        "selection": {
            "max_depth": selection["max_depth"],
            "min_samples_leaf": selection["min_samples_leaf"],
            "min_safe_leaf_support": MIN_SAFE_LEAF_SUPPORT,
            "min_safe_generations": MIN_SAFE_GENERATIONS,
        },
        "tree": {
            "children_left": [int(x) for x in tree.children_left],
            "children_right": [int(x) for x in tree.children_right],
            "feature": [int(x) for x in tree.feature],
            "threshold": [float(x) for x in tree.threshold],
        },
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(raw)
    return digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--guard-output", type=Path, required=True)
    args = ap.parse_args()

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation mismatch")

    source_items = collect_boards(
        args.v22_pgn,
        list(zip(args.source_generation, args.source_epd)),
    )

    engine = UCIStockfish(args.stockfish)
    try:
        source, feature_names = collect_source(engine, source_items)
        source_misses = sum(not bool(r["safe"]) for r in source)
        if source_misses != 19:
            raise AssertionError(("V42 source miss count drift", source_misses))

        model, safe_leaves, selection = choose_model(source)
        if model is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_SUPPORTED_ZERO_MISS_SUFFICIENCY_GUARD",
                "stockfish_pin": STOCKFISH_PIN,
                "source_positions": len(source),
                "source_certificate_misses": source_misses,
                "feature_names": feature_names,
                "selection": selection,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print(
                "CRYSTAL_CHESS_CERTIFICATE_SUFFICIENCY_GUARD_V45="
                "NO_SUPPORTED_ZERO_MISS_SUFFICIENCY_GUARD"
            )
            print(
                f"source positions={len(source)} certificate_misses={source_misses}"
            )
            print(f"artifact={args.output}")
            return 0

        # Freeze model/guard here before any fresh 100k authority search.
        guard_sha = export_guard(
            args.guard_output, model, safe_leaves, feature_names, selection
        )

        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = {position_key(b) for _, b in source_items}
        target_sets = []
        overlap_info = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            source_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            recs = fresh_records(engine, boards, feature_names)
            target_sets.append(recs)
            overlap_info.append((len(source_overlap), len(cross)))

        targets = [
            evaluate_guard(model, safe_leaves, recs)
            for recs in target_sets
        ]
    finally:
        engine.quit()

    total_pos = sum(r["positions"] for r in targets)
    total_acc = sum(r["accepted"] for r in targets)
    total_miss = sum(r["misses"] for r in targets)

    # Recompute exact combined move elimination numerator/denominator.
    combined_saved = combined_legal = 0
    Xs = [
        np.asarray([r["features"] for r in recs], dtype=np.int32)
        for recs in target_sets
    ]
    for recs, X in zip(target_sets, Xs):
        leaves = model.apply(X)
        for rec, leaf in zip(recs, leaves):
            combined_legal += int(rec["legal_moves"])
            if int(leaf) in safe_leaves:
                combined_saved += max(
                    0, int(rec["legal_moves"]) - len(rec["certificate_set"])
                )
    combined_elim = combined_saved / combined_legal if combined_legal else 0.0

    green = (
        all(r["accepted"] > 0 for r in targets)
        and total_miss == 0
        and combined_elim > 0
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_CERTIFICATE_SUFFICIENCY_GUARD"
        if green else
        "FRESH_NORMAL_CERTIFICATE_SUFFICIENCY_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v42_run": V42_RUN,
        "certificate": "union_p1p2_top16",
        "feature_names": feature_names,
        "selection": selection,
        "guard_sha256": guard_sha,
        "source": {
            "positions": len(source),
            "certificate_misses": source_misses,
            "guard_evaluation": selection["source_evaluation"],
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlap_info[i][0],
                "earlier_target_overlap_removed_before_search": overlap_info[i][1],
                **targets[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_pos,
            "accepted": total_acc,
            "misses": total_miss,
            "coverage_ratio": total_acc / total_pos if total_pos else 0.0,
            "effective_root_move_elimination_ratio": combined_elim,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "certificate set is frozen union(top16@1k,top16@4k)",
                "guard uses only already-paid shallow-search observables plus legal move count",
                "every admitted source leaf has zero exposed misses, nontrivial support, and multi-generation support",
                "guard is frozen before fresh 100k authority queries",
                "on both fresh seeds every admitted certificate set contains pinned 100k authority",
                "outside admitted states the full legal root frontier is unchanged",
            ],
            "unknown": [
                "node reduction from actually restricting Stockfish to the certificate set",
                "wall-clock gain",
                "self-play Elo gain",
                "transfer to other opening-generation protocols",
                "chess-theoretic optimality of 100k Stockfish",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_CERTIFICATE_SUFFICIENCY_GUARD_V45={status}")
    print(
        f"source positions={len(source)} certificate_misses={source_misses} "
        f"accepted={selection['source_evaluation']['accepted']} "
        f"guard_misses={selection['source_evaluation']['misses']} "
        f"coverage={selection['source_evaluation']['coverage_ratio']:.8f} "
        f"effective_elimination={selection['source_evaluation']['effective_root_move_elimination_ratio']:.8f}"
    )
    print(
        f"selected depth={selection['max_depth']} min_leaf={selection['min_samples_leaf']} "
        f"safe_leaves={selection['safe_leaves']} guard_sha256={guard_sha}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} accepted={row['accepted']} "
            f"misses={row['misses']} coverage={row['coverage_ratio']:.8f} "
            f"effective_elimination={row['effective_root_move_elimination_ratio']:.8f}"
        )
    print(
        f"combined accepted={total_acc}/{total_pos} misses={total_miss} "
        f"coverage={result['combined']['coverage_ratio']:.8f} "
        f"effective_elimination={combined_elim:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
