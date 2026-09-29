#!/usr/bin/env python3
"""Crystal Chess V39: 128-node sentinel compiler for exact V37 shortcuts.

V38 showed that a universal 1k prefilter is already too expensive at current
normal-game shortcut density. V39 therefore moves the adaptive decision one
order of magnitude earlier:

    every root: 128-node MultiPV2 sentinel
    if sentinel compiler predicts V37 may fire:
        discard sentinel TT
        run the exact frozen V37 1k -> TT-reused 4k semantic guard
        shortcut only if V37 fires
    else:
        direct unchanged 100k Stockfish fallback

The sentinel is not authoritative. A false-positive sentinel only wastes the
5k V37 confirmation; a false negative only misses a shortcut. The exact V37
guard remains the sole move-substitution authority.

Generation split:
* train: V22 through V32
* validation: V35/V36
* sentinel holdout: V37
The selected sentinel is frozen before untouched seeds 20261019/20261020.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
    extract_positions,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    load_guard,
    read_epd,
)
from crystal_chess_search_continuation_v28 import position_key
from crystal_chess_adaptive_interface_compiler_v38 import (
    TRAIN_GENERATIONS,
    VALIDATION_GENERATIONS,
    HOLDOUT_GENERATIONS,
    exact_v37_accept,
    p1_feature_row,
)

SCHEMA = "mathgraph.crystal-chess.sentinel-compiler.v39"
SENTINEL_NODES = 128
V37_CONFIRM_NODES = PROBE1_NODES + PROBE2_NODES
FRESH_SEEDS = (20261019, 20261020)
V37_RUN = 36503878346
V38_RUN = 36504660852


def collect_generation(
    engine: UCIStockfish,
    guard: dict[str, Any],
    generation: str,
    boards: list[chess.Board],
    seen: set[tuple[str, bool, str, int | None]],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    names_ref: list[str] | None = None
    for board in boards:
        key = position_key(board)
        if key in seen:
            continue
        seen.add(key)
        fen = board.fen()

        sentinel = engine.search(
            fen, SENTINEL_NODES, multipv=2, clear=True
        )
        names, features = p1_feature_row(board, sentinel)
        if names_ref is None:
            names_ref = names
        elif names_ref != names:
            raise AssertionError("sentinel feature drift")

        # Exact training label from the frozen V37 semantic guard.
        # Clear before p1 so the sentinel does not alter V37 semantics.
        p1 = engine.search(
            fen, PROBE1_NODES, multipv=2, clear=True
        )
        p2 = engine.search(
            fen, PROBE2_NODES, multipv=2, clear=False
        )
        accepts, iface, leaf = exact_v37_accept(
            guard, board, p1, p2
        )
        rows.append({
            "generation": generation,
            "fen": fen,
            "features": features,
            "sentinel": sentinel,
            "v37_accept": accepts,
            "candidate": str(p2["bestmove"]),
            "v25_leaf": leaf,
            "iface": iface,
        })
    return rows, names_ref or []


def metrics(
    model: DecisionTreeClassifier,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {
            "positions": 0, "sentinel_hits": 0, "accepted_shortcuts": 0,
            "true_v37_accepts": 0, "accept_recall": 0.0,
            "trigger_ratio": 0.0, "estimated_node_reduction_ratio": 0.0,
        }
    X = np.asarray([r["features"] for r in rows], dtype=np.int32)
    pred = model.predict(X)
    hits = accepts = 0
    support = Counter()
    total_true = sum(bool(r["v37_accept"]) for r in rows)
    for flag, row in zip(pred, rows):
        if int(flag) != 1:
            continue
        hits += 1
        if bool(row["v37_accept"]):
            accepts += 1
            support[str(row["generation"])] += 1

    n = len(rows)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * SENTINEL_NODES
        + hits * V37_CONFIRM_NODES
        + (n - accepts) * AUTHORITY_NODES
    )
    return {
        "positions": n,
        "sentinel_hits": hits,
        "accepted_shortcuts": accepts,
        "true_v37_accepts": total_true,
        "accept_recall": accepts / total_true if total_true else 1.0,
        "trigger_ratio": hits / n,
        "support": dict(support),
        "baseline_nodes": baseline,
        "hybrid_nodes": hybrid,
        "estimated_node_reduction_ratio": 1.0 - hybrid / baseline,
    }


def choose_sentinel(
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    holdout: list[dict[str, Any]],
) -> tuple[DecisionTreeClassifier | None, dict[str, Any]]:
    X = np.asarray([r["features"] for r in train], dtype=np.int32)
    y = np.asarray([int(bool(r["v37_accept"])) for r in train], dtype=np.int8)
    diagnostics: list[dict[str, Any]] = []
    candidates = []

    for depth in (2, 3, 4, 5, 6, 8):
        for min_leaf in (2, 4, 8, 12, 16):
            for weight in (2, 4, 8, 12, 16, 24):
                model = DecisionTreeClassifier(
                    criterion="entropy",
                    max_depth=depth,
                    min_samples_leaf=min_leaf,
                    class_weight={0: 1, 1: weight},
                    random_state=0,
                )
                model.fit(X, y)
                tm = metrics(model, train)
                vm = metrics(model, validation)
                hm = metrics(model, holdout)
                row = {
                    "max_depth": depth,
                    "min_samples_leaf": min_leaf,
                    "positive_weight": weight,
                    "train": tm,
                    "validation": vm,
                    "holdout": hm,
                }
                diagnostics.append(row)

                # Select strictly from train/validation economics.
                if (
                    vm["accepted_shortcuts"] >= 2
                    and vm["accept_recall"] >= 0.40
                    and vm["estimated_node_reduction_ratio"] > 0
                ):
                    candidates.append((
                        float(vm["estimated_node_reduction_ratio"]),
                        float(vm["accept_recall"]),
                        -int(vm["sentinel_hits"]),
                        -depth,
                        model,
                        row,
                    ))

    if not candidates:
        return None, {"configs": diagnostics, "selected": None}
    candidates.sort(key=lambda x: x[:4], reverse=True)
    model = candidates[0][4]
    selected = candidates[0][5]

    hm = selected["holdout"]
    if not (
        hm["accepted_shortcuts"] >= 1
        and hm["accept_recall"] >= 0.25
        and hm["estimated_node_reduction_ratio"] > 0
    ):
        return None, {
            "configs": diagnostics,
            "selected": selected,
            "holdout_rejected": True,
        }
    return model, {
        "configs": diagnostics,
        "selected": selected,
        "holdout_rejected": False,
    }


def export_sentinel(
    path: Path,
    model: DecisionTreeClassifier,
    feature_names: list[str],
    selected: dict[str, Any],
) -> str:
    tree = model.tree_
    payload = {
        "schema": SCHEMA + ".compiler",
        "stockfish_pin": STOCKFISH_PIN,
        "v37_run": V37_RUN,
        "v38_negative_run": V38_RUN,
        "runtime_protocol": {
            "sentinel_nodes": SENTINEL_NODES,
            "sentinel_multipv": 2,
            "sentinel_tt_discarded_before_v37": True,
            "v37_probe1_nodes": PROBE1_NODES,
            "v37_probe2_nodes": PROBE2_NODES,
            "v37_probe2_reuses_probe1_tt": True,
            "fallback_nodes": AUTHORITY_NODES,
        },
        "feature_names": feature_names,
        "selection": {
            "max_depth": selected["max_depth"],
            "min_samples_leaf": selected["min_samples_leaf"],
            "positive_weight": selected["positive_weight"],
        },
        "tree": {
            "children_left": [int(x) for x in tree.children_left],
            "children_right": [int(x) for x in tree.children_right],
            "feature": [int(x) for x in tree.feature],
            "threshold": [float(x) for x in tree.threshold],
            "value": [
                [float(v) for v in node[0]]
                for node in tree.value
            ],
        },
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(raw)
    return digest


def evaluate_fresh(
    engine: UCIStockfish,
    guard: dict[str, Any],
    model: DecisionTreeClassifier,
    boards: list[chess.Board],
    feature_names: list[str],
) -> dict[str, Any]:
    hits = accepted = wrong = 0
    examples: list[dict[str, Any]] = []

    for board in boards:
        fen = board.fen()
        sentinel = engine.search(
            fen, SENTINEL_NODES, multipv=2, clear=True
        )
        names, features = p1_feature_row(board, sentinel)
        if names != feature_names:
            raise AssertionError("fresh sentinel feature drift")
        flag = int(model.predict(np.asarray([features], dtype=np.int32))[0])
        if flag != 1:
            continue
        hits += 1

        # Preserve frozen V37 semantics exactly.
        p1 = engine.search(
            fen, PROBE1_NODES, multipv=2, clear=True
        )
        p2 = engine.search(
            fen, PROBE2_NODES, multipv=2, clear=False
        )
        shortcut, iface, leaf = exact_v37_accept(
            guard, board, p1, p2
        )
        if not shortcut:
            continue
        accepted += 1

        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            examples.append({
                "fen": fen,
                "candidate": str(p2["bestmove"]),
                "authority": str(auth["bestmove"]),
                "match": ok,
                "v25_leaf": leaf,
                "iface": iface,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * SENTINEL_NODES
        + hits * V37_CONFIRM_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    return {
        "positions": n,
        "sentinel_hits": hits,
        "accepted": accepted,
        "wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "sentinel_trigger_ratio": hits / n if n else 0.0,
        "baseline_nodes": baseline,
        "hybrid_nodes": hybrid,
        "estimated_node_reduction_ratio": 1.0 - hybrid / baseline,
        "examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--compiler-output", type=Path, required=True)
    args = ap.parse_args()

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation mismatch")
    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    engine = UCIStockfish(args.stockfish)
    try:
        seen: set[tuple[str, bool, str, int | None]] = set()
        rows: list[dict[str, Any]] = []
        feature_names: list[str] | None = None

        splits = extract_positions(args.v22_pgn, 220)
        v22_boards = [
            b for split in ("train", "validation", "holdout")
            for b in splits[split]
        ]
        chunk, names = collect_generation(
            engine, guard, "v22", v22_boards, seen
        )
        rows.extend(chunk)
        feature_names = names

        for generation, path in zip(args.source_generation, args.source_epd):
            chunk, names = collect_generation(
                engine, guard, generation, read_epd(path), seen
            )
            if names and names != feature_names:
                raise AssertionError("source sentinel feature drift")
            rows.extend(chunk)

        train = [r for r in rows if r["generation"] in TRAIN_GENERATIONS]
        validation = [r for r in rows if r["generation"] in VALIDATION_GENERATIONS]
        holdout = [r for r in rows if r["generation"] in HOLDOUT_GENERATIONS]
        if min(len(train), len(validation), len(holdout)) < 20:
            raise AssertionError(("source split too small", len(train), len(validation), len(holdout)))

        model, selection = choose_sentinel(train, validation, holdout)
        if model is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ECONOMIC_SENTINEL_COMPILER",
                "stockfish_pin": STOCKFISH_PIN,
                "v37_run": V37_RUN,
                "v38_negative_run": V38_RUN,
                "source": {
                    "rows": len(rows),
                    "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
                    "train": len(train),
                    "validation": len(validation),
                    "holdout": len(holdout),
                    "v37_accepts": int(sum(bool(r["v37_accept"]) for r in rows)),
                },
                "selection": selection,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print(
                "CRYSTAL_CHESS_SENTINEL_COMPILER_V39="
                "NO_ECONOMIC_SENTINEL_COMPILER"
            )
            print(
                f"source rows={len(rows)} split={len(train)}/{len(validation)}/{len(holdout)} "
                f"accepts={result['source']['v37_accepts']}"
            )
            print(f"artifact={args.output}")
            return 0

        selected = selection["selected"]
        compiler_sha = export_sentinel(
            args.compiler_output, model, feature_names or [], selected
        )

        # Frozen before any fresh authority query.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = seen
        targets: list[list[chess.Board]] = []
        source_overlaps: list[int] = []
        cross_overlaps: list[int] = []
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
            targets.append(boards)
            source_overlaps.append(len(source_overlap))
            cross_overlaps.append(len(cross))

        fresh = [
            evaluate_fresh(engine, guard, model, boards, feature_names or [])
            for boards in targets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in fresh)
    combined_hits = sum(r["sentinel_hits"] for r in fresh)
    combined_accepted = sum(r["accepted"] for r in fresh)
    combined_wrong = sum(r["wrong"] for r in fresh)
    combined_baseline = sum(r["baseline_nodes"] for r in fresh)
    combined_hybrid = sum(r["hybrid_nodes"] for r in fresh)
    combined_reduction = 1.0 - combined_hybrid / combined_baseline

    green = (
        all(r["accepted"] > 0 for r in fresh)
        and combined_wrong == 0
        and all(r["estimated_node_reduction_ratio"] > 0 for r in fresh)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_SENTINEL_COMPILER"
        if green else
        "FRESH_SENTINEL_COMPILER_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v37_run": V37_RUN,
        "v38_negative_run": V38_RUN,
        "compiler_sha256": compiler_sha,
        "source": {
            "rows": len(rows),
            "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
            "train": len(train),
            "validation": len(validation),
            "holdout": len(holdout),
            "v37_accepts": int(sum(bool(r["v37_accept"]) for r in rows)),
            "selected": selected,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": source_overlaps[i],
                "earlier_target_overlap_removed_before_search": cross_overlaps[i],
                **fresh[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": combined_positions,
            "sentinel_hits": combined_hits,
            "accepted": combined_accepted,
            "wrong": combined_wrong,
            "coverage_ratio": combined_accepted / combined_positions,
            "sentinel_trigger_ratio": combined_hits / combined_positions,
            "baseline_nodes": combined_baseline,
            "hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the 128-node sentinel cannot itself authorize a shortcut",
                "sentinel TT is discarded before the frozen V37 semantic probes",
                "V37 remains the sole shortcut authority",
                "sentinel selection uses train/validation generations and passes a disjoint V37 compiler holdout",
                "both fresh seeds have zero wrong shortcuts and positive net node reduction after sentinel plus conditional V37 costs",
            ],
            "unknown": [
                "normal UCI wall-clock gain",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SENTINEL_COMPILER_V39={status}")
    print(
        f"source rows={len(rows)} split={len(train)}/{len(validation)}/{len(holdout)} "
        f"accepts={result['source']['v37_accepts']} compiler_sha={compiler_sha}"
    )
    print(
        f"selected depth={selected['max_depth']} leaf={selected['min_samples_leaf']} "
        f"weight={selected['positive_weight']} "
        f"val_reduction={selected['validation']['estimated_node_reduction_ratio']:.8f} "
        f"holdout_reduction={selected['holdout']['estimated_node_reduction_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, fresh):
        print(
            f"seed={seed} positions={row['positions']} sentinel={row['sentinel_hits']} "
            f"accepted={row['accepted']} wrong={row['wrong']} "
            f"coverage={row['coverage_ratio']:.8f} "
            f"trigger={row['sentinel_trigger_ratio']:.8f} "
            f"reduction={row['estimated_node_reduction_ratio']:.8f}"
        )
    print(
        f"combined accepted={combined_accepted}/{combined_positions} "
        f"sentinel={combined_hits} wrong={combined_wrong} "
        f"coverage={result['combined']['coverage_ratio']:.8f} "
        f"reduction={combined_reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
