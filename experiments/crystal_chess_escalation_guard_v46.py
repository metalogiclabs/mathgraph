#!/usr/bin/env python3
"""Crystal Chess V46: zero-miss escalation guard for normal-game search.

V42-V45 compress the normal-game candidate-generation residual:
* 2,385 exposed source positions;
* 19 positions have the frozen 100k authority outside both shallow top-16 lists;
* 18/19 are recoverable below authority cost by deeper and/or native single-PV search;
* one known case remains authority-scale.

V46 asks the next minimum question:
    Can already-existing cheap shallow-search observables identify EVERY hard
    top-16 miss while triggering escalation on only a minority of positions?

No new chess feature is introduced.  The feature vocabulary is byte-for-byte
the existing V25 shallow root feature_row over 1k -> TT-reused 4k MultiPV2.

Hyperparameters are selected by leave-one-generation-out source replay:
* every held-out hard case must trigger;
* source-final hard false negatives must be zero;
* among such models, minimize trigger rate / complexity.
The frozen final tree is then tested on untouched normal-opening seeds
20261025 and 20261026, where "hard" means the 100k authority is absent from
union(top16@1k, top16@4k).
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
    feature_row,
)
from crystal_chess_normal_certificate_set_v41 import (
    collect_boards,
    search_multi,
    top_moves,
)
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key

SCHEMA = "mathgraph.crystal-chess.escalation-guard.v46"
V42_RUN = 36519656689
FRESH_SEEDS = (20261025, 20261026)
MAX_TRIGGER_RATE = 0.25
MULTIPV_CERT = 16

DEPTHS = (1, 2, 3, 4, 5, 6, 8, None)
MIN_LEAVES = (2, 4, 8, 16, 32)
CLASS_WEIGHTS = (10, 25, 50, 100, 250)


def hard_fens(v42: dict[str, Any]) -> set[str]:
    if v42.get("schema") != "mathgraph.crystal-chess.normal-certificate-width.v42":
        raise AssertionError(("V42 schema drift", v42.get("schema")))
    rows = list(v42["source"]["variants"]["union_top16"].get("miss_examples", []))
    if len(rows) != 19:
        raise AssertionError(("expected V42 hard residual 19", len(rows)))
    return {str(r["fen"]) for r in rows}


def collect_feature_records(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
    hard: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    names_ref: list[str] | None = None
    for generation, board in items:
        fen = board.fen()
        p1 = engine.search(fen, PROBE1_NODES, multipv=2, clear=True)
        p2 = engine.search(fen, PROBE2_NODES, multipv=2, clear=False)
        names, feats = feature_row(board, p1, p2)
        if names_ref is None:
            names_ref = names
        elif names_ref != names:
            raise AssertionError("feature order drift")
        rows.append({
            "generation": generation,
            "fen": fen,
            "features": feats,
            "hard": fen in hard,
        })
    return rows, names_ref or []


def fit_model(
    rows: list[dict[str, Any]],
    depth: int | None,
    min_leaf: int,
    hard_weight: int,
) -> DecisionTreeClassifier:
    X = np.asarray([r["features"] for r in rows], dtype=np.int32)
    y = np.asarray([int(bool(r["hard"])) for r in rows], dtype=np.int8)
    model = DecisionTreeClassifier(
        criterion="entropy",
        max_depth=depth,
        min_samples_leaf=min_leaf,
        class_weight={0: 1, 1: hard_weight},
        random_state=0,
    )
    model.fit(X, y)
    return model


def eval_model(
    model: DecisionTreeClassifier,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    X = np.asarray([r["features"] for r in rows], dtype=np.int32)
    pred = model.predict(X)
    hard = np.asarray([int(bool(r["hard"])) for r in rows], dtype=np.int8)
    trigger = pred.astype(np.int8)
    hard_count = int(hard.sum())
    hard_missed = int(((hard == 1) & (trigger == 0)).sum())
    trigger_count = int(trigger.sum())
    easy_triggered = int(((hard == 0) & (trigger == 1)).sum())
    n = len(rows)
    return {
        "positions": n,
        "hard": hard_count,
        "hard_missed": hard_missed,
        "triggered": trigger_count,
        "easy_triggered": easy_triggered,
        "trigger_rate": trigger_count / n if n else 0.0,
        "hard_recall": (
            (hard_count - hard_missed) / hard_count if hard_count else 1.0
        ),
    }


def select_config(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    generations = sorted({str(r["generation"]) for r in rows})
    hard_gens = sorted({
        str(r["generation"]) for r in rows if bool(r["hard"])
    })
    diagnostics = []

    for depth in DEPTHS:
        for min_leaf in MIN_LEAVES:
            for hard_weight in CLASS_WEIGHTS:
                folds = []
                valid = True
                for held in hard_gens:
                    train = [r for r in rows if str(r["generation"]) != held]
                    test = [r for r in rows if str(r["generation"]) == held]
                    if not train or not test:
                        valid = False
                        break
                    model = fit_model(train, depth, min_leaf, hard_weight)
                    ev = eval_model(model, test)
                    folds.append({"held_generation": held, **ev})
                    if ev["hard_missed"] != 0:
                        valid = False

                final_model = fit_model(rows, depth, min_leaf, hard_weight)
                source = eval_model(final_model, rows)
                if source["hard_missed"] != 0:
                    valid = False

                row = {
                    "depth": depth,
                    "min_leaf": min_leaf,
                    "hard_weight": hard_weight,
                    "hard_generations": hard_gens,
                    "all_generations": generations,
                    "folds": folds,
                    "source": source,
                    "node_count": int(final_model.tree_.node_count),
                    "leaf_count": int(final_model.get_n_leaves()),
                    "valid_zero_miss": valid,
                }
                diagnostics.append(row)

    candidates = [
        d for d in diagnostics
        if d["valid_zero_miss"]
        and float(d["source"]["trigger_rate"]) <= MAX_TRIGGER_RATE
        and all(float(f["trigger_rate"]) <= 0.50 for f in d["folds"])
    ]
    if not candidates:
        return None, diagnostics

    candidates.sort(key=lambda d: (
        float(d["source"]["trigger_rate"]),
        int(d["node_count"]),
        int(d["leaf_count"]),
        999 if d["depth"] is None else int(d["depth"]),
        int(d["min_leaf"]),
        int(d["hard_weight"]),
    ))
    return candidates[0], diagnostics


def export_guard(
    path: Path,
    model: DecisionTreeClassifier,
    feature_names: list[str],
    selected: dict[str, Any],
) -> str:
    t = model.tree_
    payload = {
        "schema": SCHEMA + ".guard",
        "stockfish_pin": STOCKFISH_PIN,
        "probe_protocol": {
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "probe2_reuses_probe1_tt": True,
            "multipv": 2,
        },
        "feature_names": feature_names,
        "selection": selected,
        "tree": {
            "children_left": [int(x) for x in t.children_left],
            "children_right": [int(x) for x in t.children_right],
            "feature": [int(x) for x in t.feature],
            "threshold": [float(x) for x in t.threshold],
            "value": [x.tolist() for x in t.value],
        },
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as h:
        h.write(raw)
    return digest


def probe16_to_v25(probe: dict[str, Any]) -> dict[str, Any]:
    ranked = list(probe.get("ranked") or [])
    r1 = ranked[0] if ranked else {}
    r2 = ranked[1] if len(ranked) > 1 else None
    return {
        "bestmove": str(probe.get("bestmove") or (r1.get("move") or "")),
        "score1": int(r1.get("score", 0)),
        "score2": int(r2["score"]) if r2 else None,
        "depth": int(r1.get("depth", 0)),
        "seldepth": int(r1.get("seldepth", 0)),
        "reported_nodes": 0,
        "pv1": list(r1.get("pv") or []),
        "pv2": list(r2.get("pv") or []) if r2 else [],
    }


def union_top16(p1: dict[str, Any], p2: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in top_moves(p2, 16) + top_moves(p1, 16):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def fresh_eval(
    engine: UCIStockfish,
    model: DecisionTreeClassifier,
    feature_names: list[str],
    boards: list[chess.Board],
) -> dict[str, Any]:
    records = []
    hard_count = hard_missed = trigger_count = easy_triggered = 0
    examples = []

    for board in boards:
        fen = board.fen()
        p1x = search_multi(
            engine, fen, PROBE1_NODES, multipv=MULTIPV_CERT, clear=True
        )
        p2x = search_multi(
            engine, fen, PROBE2_NODES, multipv=MULTIPV_CERT, clear=False
        )
        p1 = probe16_to_v25(p1x)
        p2 = probe16_to_v25(p2x)
        names, feats = feature_row(board, p1, p2)
        if names != feature_names:
            raise AssertionError("fresh feature drift")

        trigger = bool(model.predict(np.asarray([feats], dtype=np.int32))[0])
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        authority = str(auth["bestmove"])
        cset = union_top16(p1x, p2x)
        hard = authority not in cset

        hard_count += int(hard)
        hard_missed += int(hard and not trigger)
        trigger_count += int(trigger)
        easy_triggered += int((not hard) and trigger)

        if (hard or trigger) and len(examples) < 40:
            examples.append({
                "fen": fen,
                "authority": authority,
                "hard": hard,
                "trigger": trigger,
                "candidate_set_size": len(cset),
                "candidate_set": cset,
            })

        records.append((hard, trigger))

    n = len(boards)
    return {
        "positions": n,
        "hard": hard_count,
        "hard_missed": hard_missed,
        "triggered": trigger_count,
        "easy_triggered": easy_triggered,
        "trigger_rate": trigger_count / n if n else 0.0,
        "hard_recall": (
            (hard_count - hard_missed) / hard_count if hard_count else 1.0
        ),
        "examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v42-result", type=Path, required=True)
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

    v42 = json.loads(args.v42_result.read_text())
    hard = hard_fens(v42)
    source_items = collect_boards(
        args.v22_pgn,
        list(zip(args.source_generation, args.source_epd)),
    )
    source_fens = {b.fen() for _, b in source_items}
    if hard - source_fens:
        raise AssertionError(("hard FEN missing from source corpus", len(hard - source_fens)))

    engine = UCIStockfish(args.stockfish)
    try:
        rows, feature_names = collect_feature_records(engine, source_items, hard)
        selected, diagnostics = select_config(rows)
        if selected is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ECONOMIC_ZERO_MISS_ESCALATION_GUARD",
                "stockfish_pin": STOCKFISH_PIN,
                "v42_run": V42_RUN,
                "source": {
                    "positions": len(rows),
                    "hard": sum(bool(r["hard"]) for r in rows),
                    "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
                },
                "diagnostics": diagnostics,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print("CRYSTAL_CHESS_ESCALATION_GUARD_V46=NO_ECONOMIC_ZERO_MISS_ESCALATION_GUARD")
            print(f"source positions={len(rows)} hard={sum(bool(r['hard']) for r in rows)}")
            print(f"artifact={args.output}")
            return 0

        model = fit_model(
            rows,
            selected["depth"],
            int(selected["min_leaf"]),
            int(selected["hard_weight"]),
        )
        source_eval = eval_model(model, rows)
        digest = export_guard(args.guard_output, model, feature_names, selected)

        # Freeze here, before fresh 100k authority queries.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = {position_key(b) for _, b in source_items}
        target_sets = []
        overlap = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            src_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            overlap.append((len(src_overlap), len(cross)))

        fresh = [
            fresh_eval(engine, model, feature_names, boards)
            for boards in target_sets
        ]
    finally:
        engine.quit()

    total_n = sum(r["positions"] for r in fresh)
    total_hard = sum(r["hard"] for r in fresh)
    total_missed = sum(r["hard_missed"] for r in fresh)
    total_trigger = sum(r["triggered"] for r in fresh)
    combined_trigger = total_trigger / total_n if total_n else 0.0

    green = (
        total_missed == 0
        and all(r["hard_missed"] == 0 for r in fresh)
        and combined_trigger <= MAX_TRIGGER_RATE
        and all(r["trigger_rate"] <= 0.35 for r in fresh)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_ESCALATION_GUARD"
        if green else
        "FRESH_ESCALATION_GUARD_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v42_run": V42_RUN,
        "feature_vocabulary": feature_names,
        "selected": selected,
        "guard_sha256": digest,
        "source": {
            "positions": len(rows),
            "hard": sum(bool(r["hard"]) for r in rows),
            "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
            "evaluation": source_eval,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlap[i][0],
                "earlier_target_overlap_removed_before_search": overlap[i][1],
                **fresh[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_n,
            "hard": total_hard,
            "hard_missed": total_missed,
            "triggered": total_trigger,
            "trigger_rate": combined_trigger,
            "hard_recall": (
                (total_hard - total_missed) / total_hard if total_hard else 1.0
            ),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "hard/easy source labels are frozen by V42 before V46 fitting",
                "only the pre-existing V25 shallow feature vocabulary is used",
                "hyperparameters must achieve zero hard misses under leave-one-hard-generation-out replay",
                "final source hard misses are zero",
                "tree is frozen before fresh 100k authority queries",
                "fresh hard means only that pinned 100k authority is absent from the shallow union-top16 candidate set",
                "both fresh targets have zero missed hard states and bounded trigger rate",
            ],
            "unknown": [
                "whether escalated 32k/64k/safe fallback policy is itself sufficient prospectively",
                "actual node/wall-clock gain of candidate-restricted search",
                "self-play Elo gain",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_ESCALATION_GUARD_V46={status}")
    print(
        f"source positions={len(rows)} hard={result['source']['hard']} "
        f"trigger={source_eval['triggered']} rate={source_eval['trigger_rate']:.8f} "
        f"hard_missed={source_eval['hard_missed']} selected={selected}"
    )
    for seed, r in zip(FRESH_SEEDS, fresh):
        print(
            f"seed={seed} positions={r['positions']} hard={r['hard']} "
            f"hard_missed={r['hard_missed']} triggered={r['triggered']} "
            f"trigger_rate={r['trigger_rate']:.8f}"
        )
    print(
        f"combined hard={total_hard} missed={total_missed} "
        f"triggered={total_trigger}/{total_n} rate={combined_trigger:.8f}"
    )
    print(f"guard_sha256={digest}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
