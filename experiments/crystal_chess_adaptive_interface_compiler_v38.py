#!/usr/bin/env python3
"""Crystal Chess V38: adaptive compiler for the zero-error V37 interface.

V36/V37 found a cheap root-PV semantic interface that is prospectively
zero-error, but paying the full 1k -> TT-reused 4k root probe on every normal
position is uneconomic at ~1.4% shortcut coverage.

V38 changes no chess semantics.  It compiles only an *admission-to-probe*
prefilter from the 1k root probe:

    every root: pay 1k MultiPV2
    if compiler predicts V37 might fire: buy the extra 4k TT-reused probe
    if and only if the exact frozen V37 guard then fires: shortcut
    otherwise: unchanged 100k Stockfish fallback

The compiler is not authoritative.  False-positive prefilter decisions merely
waste 4k nodes; they cannot cause a shortcut.  The exact V37 interface remains
the only shortcut authority.

Source split is generation-based:
* train: V22 through V32
* validation: V35/V36
* compiler holdout: V37
The selected compiler is frozen before fresh seeds 20261017/20261018.
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
    material_counts,
    move_observables,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    guard_fires,
    load_guard,
    read_epd,
)
from crystal_chess_search_continuation_v28 import position_key
from crystal_chess_root_pv_interface_v36 import (
    reply_effect,
    root_alternative,
    root_interface,
)
from crystal_chess_root_reply_zeroing_v37 import (
    parent_accepts,
    separator_accepts,
)

SCHEMA = "mathgraph.crystal-chess.adaptive-interface-compiler.v38"
FRESH_SEEDS = (20261017, 20261018)
V37_RUN = 36503878346

TRAIN_GENERATIONS = {
    "v22", "v28", "v29", "v30", "v31a", "v31b", "v32a", "v32b"
}
VALIDATION_GENERATIONS = {"v35a", "v35b", "v36a", "v36b"}
HOLDOUT_GENERATIONS = {"v37a", "v37b"}


def effect_or_zero(
    board: chess.Board,
    root_move: str,
    reply: str | None,
) -> dict[str, int]:
    if not reply:
        return {
            "capture": 0, "check": 0, "zeroing": 0,
            "mover_type": 0, "captured_type": 0, "promotion": 0,
        }
    try:
        return reply_effect(board, root_move, reply)
    except Exception:
        return {
            "capture": 0, "check": 0, "zeroing": 0,
            "mover_type": 0, "captured_type": 0, "promotion": 0,
        }


def p1_feature_row(
    board: chess.Board,
    p1: dict[str, Any],
) -> tuple[list[str], tuple[int, ...]]:
    names: list[str] = []
    vals: list[int] = []

    def add(name: str, value: int | bool | None) -> None:
        names.append(name)
        vals.append(int(value or 0))

    candidate = str(p1.get("bestmove") or "")
    alternative = root_alternative(p1)
    score2 = p1.get("score2")
    margin = (
        int(p1["score1"]) - int(score2)
        if score2 is not None else 100000
    )

    add("score1", p1.get("score1"))
    add("score2", score2 if score2 is not None else -100000)
    add("margin", margin)
    add("depth", p1.get("depth"))
    add("seldepth", p1.get("seldepth"))
    add("pv1_len", len(p1.get("pv1") or []))
    add("pv2_len", len(p1.get("pv2") or []))
    add("piece_count", len(board.piece_map()))
    add("legal_moves", board.legal_moves.count())
    add("in_check", board.is_check())
    add("side_to_move", int(board.turn))
    add("halfmove_bucket", min(board.halfmove_clock // 10, 10))

    for key, value in sorted(material_counts(board).items()):
        add("material_" + key, value)

    for prefix, move in (
        ("cand", candidate),
        ("alt", alternative or ""),
    ):
        for key, value in sorted(move_observables(board, move).items()):
            add(prefix + "_" + key, value)

    pv1 = list(p1.get("pv1") or [])
    pv2 = list(p1.get("pv2") or [])
    ce = effect_or_zero(
        board,
        candidate,
        str(pv1[1]) if len(pv1) >= 2 else None,
    )
    ae = effect_or_zero(
        board,
        alternative or "",
        str(pv2[1]) if alternative and len(pv2) >= 2 else None,
    )
    for key in ("capture", "check", "zeroing", "mover_type", "captured_type", "promotion"):
        add("cand_reply_" + key, ce[key])
        add("alt_reply_" + key, ae[key])
        add("reply_" + key + "_equal", ce[key] == ae[key])

    return names, tuple(vals)


def exact_v37_accept(
    guard: dict[str, Any],
    board: chess.Board,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> tuple[bool, dict[str, Any] | None, int | None]:
    fires, leaf = guard_fires(guard, board, p1, p2)
    if not fires:
        return False, None, leaf
    iface = root_interface(board, p1, p2)
    if iface is None:
        return False, None, leaf
    accepted = parent_accepts(iface) and separator_accepts(iface)
    return accepted, iface, leaf


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
        p1 = engine.search(
            fen, PROBE1_NODES, multipv=2, clear=True
        )
        names, features = p1_feature_row(board, p1)
        if names_ref is None:
            names_ref = names
        elif names_ref != names:
            raise AssertionError("p1 feature drift")

        # Training/qualification authority only. Runtime V38 pays this 4k
        # probe only after the compiler fires.
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
            "p1": p1,
            "expensive_accept": accepts,
            "candidate": str(p2["bestmove"]),
            "leaf": leaf,
            "iface": iface,
        })
    return rows, names_ref or []


def compiler_metrics(
    model: DecisionTreeClassifier,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {
            "positions": 0, "prefilter_hits": 0,
            "accepted_shortcuts": 0, "accept_recall": 0.0,
            "trigger_ratio": 0.0, "estimated_node_reduction_ratio": 0.0,
        }
    X = np.asarray([r["features"] for r in rows], dtype=np.int32)
    pred = model.predict(X)
    hits = 0
    accepts = 0
    total_true = sum(bool(r["expensive_accept"]) for r in rows)
    support = Counter()
    for flag, row in zip(pred, rows):
        if int(flag) != 1:
            continue
        hits += 1
        if bool(row["expensive_accept"]):
            accepts += 1
            support[str(row["generation"])] += 1
    n = len(rows)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * PROBE1_NODES
        + hits * PROBE2_NODES
        + (n - accepts) * AUTHORITY_NODES
    )
    return {
        "positions": n,
        "prefilter_hits": hits,
        "accepted_shortcuts": accepts,
        "true_expensive_accepts": total_true,
        "accept_recall": accepts / total_true if total_true else 1.0,
        "trigger_ratio": hits / n,
        "support": dict(support),
        "baseline_nodes": baseline,
        "hybrid_nodes": hybrid,
        "estimated_node_reduction_ratio": 1.0 - hybrid / baseline,
    }


def choose_compiler(
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    holdout: list[dict[str, Any]],
    feature_names: list[str],
) -> tuple[DecisionTreeClassifier | None, dict[str, Any]]:
    X = np.asarray([r["features"] for r in train], dtype=np.int32)
    y = np.asarray([int(bool(r["expensive_accept"])) for r in train], dtype=np.int8)
    diagnostics: list[dict[str, Any]] = []
    candidates: list[tuple[float, float, int, int, DecisionTreeClassifier, dict[str, Any]]] = []

    for depth in (2, 3, 4, 5, 6):
        for min_leaf in (2, 4, 8, 12, 16):
            for weight in (2, 4, 8, 12):
                model = DecisionTreeClassifier(
                    criterion="entropy",
                    max_depth=depth,
                    min_samples_leaf=min_leaf,
                    class_weight={0: 1, 1: weight},
                    random_state=0,
                )
                model.fit(X, y)
                tm = compiler_metrics(model, train)
                vm = compiler_metrics(model, validation)
                hm = compiler_metrics(model, holdout)
                row = {
                    "max_depth": depth,
                    "min_samples_leaf": min_leaf,
                    "positive_weight": weight,
                    "train": tm,
                    "validation": vm,
                    "holdout": hm,
                }
                diagnostics.append(row)

                # Selection uses train+validation economics. Holdout is a
                # qualification gate, never a ranking signal.
                if (
                    vm["accepted_shortcuts"] >= 2
                    and vm["accept_recall"] >= 0.40
                    and vm["estimated_node_reduction_ratio"] > 0
                ):
                    score = float(vm["estimated_node_reduction_ratio"])
                    candidates.append(
                        (
                            score,
                            float(vm["accept_recall"]),
                            -int(vm["prefilter_hits"]),
                            -depth,
                            model,
                            row,
                        )
                    )

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


def export_compiler(
    path: Path,
    model: DecisionTreeClassifier,
    feature_names: list[str],
    selection: dict[str, Any],
) -> str:
    tree = model.tree_
    payload = {
        "schema": SCHEMA + ".compiler",
        "stockfish_pin": STOCKFISH_PIN,
        "v37_run": V37_RUN,
        "runtime_protocol": {
            "universal_probe_nodes": PROBE1_NODES,
            "conditional_confirmation_nodes": PROBE2_NODES,
            "confirmation_reuses_probe1_tt": True,
            "fallback_nodes": AUTHORITY_NODES,
        },
        "feature_names": feature_names,
        "selection": {
            "max_depth": selection["max_depth"],
            "min_samples_leaf": selection["min_samples_leaf"],
            "positive_weight": selection["positive_weight"],
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
    prefilter_hits = confirmations = accepted = wrong = 0
    examples: list[dict[str, Any]] = []
    for board in boards:
        fen = board.fen()
        p1 = engine.search(
            fen, PROBE1_NODES, multipv=2, clear=True
        )
        names, features = p1_feature_row(board, p1)
        if names != feature_names:
            raise AssertionError("fresh p1 feature drift")
        pred = int(model.predict(np.asarray([features], dtype=np.int32))[0])
        if pred != 1:
            continue
        prefilter_hits += 1

        p2 = engine.search(
            fen, PROBE2_NODES, multipv=2, clear=False
        )
        confirmations += 1
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
        n * PROBE1_NODES
        + confirmations * PROBE2_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    return {
        "positions": n,
        "prefilter_hits": prefilter_hits,
        "confirmations": confirmations,
        "accepted": accepted,
        "wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "prefilter_ratio": prefilter_hits / n if n else 0.0,
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
            board
            for split in ("train", "validation", "holdout")
            for board in splits[split]
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
                raise AssertionError("source p1 feature drift")
            rows.extend(chunk)

        train = [r for r in rows if r["generation"] in TRAIN_GENERATIONS]
        validation = [r for r in rows if r["generation"] in VALIDATION_GENERATIONS]
        holdout = [r for r in rows if r["generation"] in HOLDOUT_GENERATIONS]
        if min(len(train), len(validation), len(holdout)) < 20:
            raise AssertionError((
                "insufficient compiler source split",
                len(train), len(validation), len(holdout)
            ))

        model, selection = choose_compiler(
            train, validation, holdout, feature_names or []
        )
        if model is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ECONOMIC_ADAPTIVE_COMPILER",
                "stockfish_pin": STOCKFISH_PIN,
                "v37_run": V37_RUN,
                "source": {
                    "rows": len(rows),
                    "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
                    "train": len(train),
                    "validation": len(validation),
                    "holdout": len(holdout),
                    "expensive_accepts": int(sum(bool(r["expensive_accept"]) for r in rows)),
                },
                "selection": selection,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print(
                "CRYSTAL_CHESS_ADAPTIVE_INTERFACE_COMPILER_V38="
                "NO_ECONOMIC_ADAPTIVE_COMPILER"
            )
            print(
                f"source rows={len(rows)} split={len(train)}/{len(validation)}/{len(holdout)} "
                f"accepts={result['source']['expensive_accepts']}"
            )
            print(f"artifact={args.output}")
            return 0

        selected = selection["selected"]
        compiler_sha = export_compiler(
            args.compiler_output, model, feature_names or [], selected
        )

        # Freeze compiler here, before any fresh authority query.
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
            evaluate_fresh(
                engine, guard, model, boards, feature_names or []
            )
            for boards in targets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in fresh)
    combined_hits = sum(r["prefilter_hits"] for r in fresh)
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
        "WARRANTED_REPLICATED_NORMAL_SEARCH_ADAPTIVE_INTERFACE_COMPILER"
        if green else
        "FRESH_ADAPTIVE_INTERFACE_COMPILER_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v37_run": V37_RUN,
        "compiler_sha256": compiler_sha,
        "source": {
            "rows": len(rows),
            "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
            "train": len(train),
            "validation": len(validation),
            "holdout": len(holdout),
            "expensive_accepts": int(sum(bool(r["expensive_accept"]) for r in rows)),
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
            "prefilter_hits": combined_hits,
            "accepted": combined_accepted,
            "wrong": combined_wrong,
            "coverage_ratio": combined_accepted / combined_positions,
            "prefilter_ratio": combined_hits / combined_positions,
            "baseline_nodes": combined_baseline,
            "hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V37 remains the sole semantic shortcut authority",
                "the compiler sees only 1k-root observables and can only decide whether to buy the 4k confirmation",
                "compiler false positives cannot produce shortcuts",
                "compiler is selected on train/validation generations and passes a disjoint exposed V37 compiler holdout before fresh labels",
                "both fresh seeds have zero wrong final shortcuts and positive net node reduction after universal 1k plus conditional 4k costs",
            ],
            "unknown": [
                "normal-game wall-clock gain",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_ADAPTIVE_INTERFACE_COMPILER_V38={status}")
    print(
        f"source rows={len(rows)} split={len(train)}/{len(validation)}/{len(holdout)} "
        f"accepts={result['source']['expensive_accepts']} compiler_sha={compiler_sha}"
    )
    print(
        f"selected depth={selected['max_depth']} leaf={selected['min_samples_leaf']} "
        f"weight={selected['positive_weight']} "
        f"val_reduction={selected['validation']['estimated_node_reduction_ratio']:.8f} "
        f"holdout_reduction={selected['holdout']['estimated_node_reduction_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, fresh):
        print(
            f"seed={seed} positions={row['positions']} prefilter={row['prefilter_hits']} "
            f"accepted={row['accepted']} wrong={row['wrong']} "
            f"coverage={row['coverage_ratio']:.8f} "
            f"prefilter_ratio={row['prefilter_ratio']:.8f} "
            f"reduction={row['estimated_node_reduction_ratio']:.8f}"
        )
    print(
        f"combined accepted={combined_accepted}/{combined_positions} "
        f"prefilter={combined_hits} wrong={combined_wrong} "
        f"coverage={result['combined']['coverage_ratio']:.8f} "
        f"reduction={combined_reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
