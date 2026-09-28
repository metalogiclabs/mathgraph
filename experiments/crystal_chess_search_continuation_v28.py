#!/usr/bin/env python3
"""Crystal Chess V28: continuation-structure residual separator.

V25 leaves one exact normal-search false positive. V26 proves that merely
continuing the same root search to 8k/16k/32k does not recover the protected
100k Stockfish move. V27 proves that one additional pre-existing scalar
root/board/move feature also fails prospectively.

V28 therefore adds exactly one new *kind* of observation: the cheap future
structure exposed after the frozen V25 candidate move is played.

For a V25-covered root only:
  1. play the 4k candidate move,
  2. probe the opponent continuation at 1k then TT-reused 4k MultiPV=2,
  3. record reply stability, reply margin/PV stability, branch size and reply
     move effects,
  4. allow the single V25 source counterexample to earn the smallest
     one-predicate continuation separator,
  5. freeze the separator,
  6. test on a brand-new deterministic normal-opening corpus (seed 20260930).

The 100k Stockfish authority is never a feature and is queried on the fresh
target only after guard+continuation-separator commitment.

This is a behavioral search-substitution capability relative to pinned
Stockfish, not a proof of chess-theoretic optimality.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE1_NODES,
    PROBE2_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
    collect_records,
    extract_positions,
    move_observables,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    base_probes,
    guard_fires,
    load_guard,
    read_epd,
)


SCHEMA = "mathgraph.crystal-chess.search-continuation.v28"
V22_RUN = 36361812786
V25_RUN = 36362896141
V26_RUN = 36367418497
V27_RUN = 36367712262
FRESH_SEED = 20260930

CHILD_PROBE1_NODES = 1000
CHILD_PROBE2_NODES = 4000
CHILD_PROBE_TOTAL_NODES = CHILD_PROBE1_NODES + CHILD_PROBE2_NODES

MIN_SOURCE_SUPPORT = 12
MIN_SOURCE_SPLITS = 2


def position_key(board: chess.Board) -> tuple[str, bool, str, int | None]:
    return (
        board.board_fen(),
        board.turn,
        board.castling_xfen(),
        board.ep_square,
    )


def margin(search: dict[str, Any]) -> int:
    if search["score2"] is None:
        return 100000
    return int(search["score1"]) - int(search["score2"])


def continuation_features(
    engine: UCIStockfish,
    board: chess.Board,
    candidate_uci: str,
) -> tuple[list[str], tuple[int, ...], dict[str, Any]]:
    try:
        move = chess.Move.from_uci(candidate_uci)
    except ValueError as exc:
        raise AssertionError(("bad candidate UCI", candidate_uci)) from exc
    if move not in board.legal_moves:
        raise AssertionError(("candidate not legal", board.fen(), candidate_uci))

    child = board.copy(stack=False)
    child.push(move)
    child_fen = child.fen()

    c1 = engine.search(
        child_fen,
        CHILD_PROBE1_NODES,
        multipv=2,
        clear=True,
    )
    c2 = engine.search(
        child_fen,
        CHILD_PROBE2_NODES,
        multipv=2,
        clear=False,
    )

    names: list[str] = []
    vals: list[int] = []

    def add(name: str, value: int | bool) -> None:
        names.append(name)
        vals.append(int(value))

    m1 = margin(c1)
    m2 = margin(c2)
    add("reply_best_stable", c1["bestmove"] == c2["bestmove"])
    add("reply_score1_probe1", c1["score1"])
    add("reply_score1_probe2", c2["score1"])
    add("reply_score_delta_abs", abs(int(c2["score1"]) - int(c1["score1"])))
    add("reply_margin_probe1", m1)
    add("reply_margin_probe2", m2)
    add("reply_margin_delta", m2 - m1)
    add("reply_depth_probe1", c1["depth"])
    add("reply_depth_probe2", c2["depth"])
    add("reply_seldepth_probe1", c1["seldepth"])
    add("reply_seldepth_probe2", c2["seldepth"])
    add(
        "reply_pv_prefix_stable_2",
        c1["pv1"][:2] == c2["pv1"][:2] and len(c2["pv1"]) >= 2,
    )
    add(
        "reply_pv_prefix_stable_3",
        c1["pv1"][:3] == c2["pv1"][:3] and len(c2["pv1"]) >= 3,
    )
    add("child_legal_moves", child.legal_moves.count())
    add("child_in_check", child.is_check())
    add("child_halfmove_bucket", min(child.halfmove_clock // 10, 10))

    reply_obs = move_observables(child, str(c2["bestmove"]))
    for key in sorted(reply_obs):
        add("reply_" + key, reply_obs[key])

    meta = {
        "candidate_move": candidate_uci,
        "child_fen": child_fen,
        "probe1": {
            "bestmove": c1["bestmove"],
            "score1": c1["score1"],
            "score2": c1["score2"],
            "depth": c1["depth"],
            "seldepth": c1["seldepth"],
            "pv1": c1["pv1"][:4],
        },
        "probe2": {
            "bestmove": c2["bestmove"],
            "score1": c2["score1"],
            "score2": c2["score2"],
            "depth": c2["depth"],
            "seldepth": c2["seldepth"],
            "pv1": c2["pv1"][:4],
        },
    }
    return names, tuple(vals), meta


def predicate_eval(spec: dict[str, Any], value: int) -> bool:
    op = str(spec["op"])
    ref = int(spec["value"])
    if op == "lt":
        return value < ref
    if op == "gt":
        return value > ref
    if op == "ne":
        return value != ref
    raise ValueError(op)


def candidate_predicates(
    failure_features: tuple[int, ...],
    rows: list[dict[str, Any]],
    feature_names: list[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for j, name in enumerate(feature_names):
        fv = int(failure_features[j])
        values = [int(row["continuation_features"][j]) for row in rows]
        specs = [
            {"feature": j, "feature_name": name, "op": "lt", "value": fv},
            {"feature": j, "feature_name": name, "op": "gt", "value": fv},
        ]
        if len(set(values)) <= 8:
            specs.append(
                {"feature": j, "feature_name": name, "op": "ne", "value": fv}
            )
        out.extend(specs)
    return out


def select_separator(
    source_rows: list[dict[str, Any]],
    feature_names: list[str],
) -> dict[str, Any] | None:
    failures = [row for row in source_rows if not bool(row["match"])]
    if len(failures) != 1:
        raise AssertionError(("expected one V25 source residual", len(failures)))
    failure = failures[0]
    ffeatures = tuple(int(x) for x in failure["continuation_features"])

    candidates: list[dict[str, Any]] = []
    for spec in candidate_predicates(ffeatures, source_rows, feature_names):
        j = int(spec["feature"])
        kept = [
            row
            for row in source_rows
            if predicate_eval(spec, int(row["continuation_features"][j]))
        ]
        if not kept:
            continue
        wrong = sum(not bool(row["match"]) for row in kept)
        splits = sorted({str(row["split"]) for row in kept})
        if wrong != 0:
            continue
        if len(kept) < MIN_SOURCE_SUPPORT or len(splits) < MIN_SOURCE_SPLITS:
            continue
        candidates.append(
            {
                **spec,
                "source_support": len(kept),
                "source_split_count": len(splits),
                "source_splits": splits,
                "source_retention_ratio": len(kept) / len(source_rows),
            }
        )

    if not candidates:
        return None

    op_rank = {"lt": 0, "gt": 0, "ne": 1}
    candidates.sort(
        key=lambda c: (
            -int(c["source_support"]),
            -int(c["source_split_count"]),
            op_rank[str(c["op"])],
            str(c["feature_name"]),
            int(c["value"]),
        )
    )
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--source-pgn", type=Path, required=True)
    ap.add_argument("--fresh-epd", type=Path, required=True)
    ap.add_argument("--fresh-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, guard_sha = load_guard(args.guard)
    if guard_sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard digest drift", guard_sha))

    fresh_manifest = json.loads(args.fresh_manifest.read_text(encoding="utf-8"))
    if int(fresh_manifest["seed"]) != FRESH_SEED:
        raise AssertionError(("fresh seed drift", fresh_manifest["seed"]))

    source_splits = extract_positions(args.source_pgn, 220)
    fresh = read_epd(args.fresh_epd)
    if len(fresh) < 100:
        raise AssertionError(("fresh target too small", len(fresh)))

    source_keys = {
        position_key(board)
        for boards in source_splits.values()
        for board in boards
    }
    fresh_keys = {position_key(board) for board in fresh}
    overlap = source_keys & fresh_keys
    if overlap:
        raise AssertionError(("source/fresh overlap", len(overlap)))

    engine = UCIStockfish(args.stockfish)
    try:
        # Reproduce V25 source labels exactly, then compute continuation
        # structure only for the states where its frozen guard fires.
        source_records: list[dict[str, Any]] = []
        source_parent_covered: list[dict[str, Any]] = []
        continuation_names: list[str] | None = None

        for split in ("train", "validation", "holdout"):
            recs, _root_names = collect_records(engine, source_splits[split])
            for rec in recs:
                board = chess.Board(rec["fen"])
                fires, leaf = guard_fires(
                    guard, board, rec["probe1"], rec["probe2"]
                )
                row = dict(rec)
                row["split"] = split
                row["leaf"] = leaf
                source_records.append(row)
                if not fires:
                    continue

                names, features, meta = continuation_features(
                    engine,
                    board,
                    str(rec["probe2"]["bestmove"]),
                )
                if continuation_names is None:
                    continuation_names = names
                elif continuation_names != names:
                    raise AssertionError("continuation feature order drift")
                row["continuation_features"] = features
                row["continuation_meta"] = meta
                source_parent_covered.append(row)

        source_wrong = sum(
            not bool(row["match"]) for row in source_parent_covered
        )
        if len(source_parent_covered) != 50 or source_wrong != 1:
            raise AssertionError(
                (
                    "V25 parent replay drift",
                    len(source_parent_covered),
                    source_wrong,
                )
            )

        separator = select_separator(
            source_parent_covered,
            continuation_names or [],
        )
        if separator is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ONE_FEATURE_CONTINUATION_SEPARATOR",
                "stockfish_pin": STOCKFISH_PIN,
                "v25_run": V25_RUN,
                "source_parent_covered": len(source_parent_covered),
                "source_parent_wrong": source_wrong,
                "fresh_seed": FRESH_SEED,
                "fresh_positions": len(fresh),
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_CONTINUATION_V28="
                "NO_ONE_FEATURE_CONTINUATION_SEPARATOR"
            )
            print(f"artifact={args.output}")
            return 0

        # Separator is frozen at this line. Fresh deep authority has not been
        # queried yet.
        j = int(separator["feature"])
        parent_guard_fires = 0
        separator_rejects = 0
        accepted = 0
        accepted_wrong = 0
        examples: list[dict[str, Any]] = []

        for board in fresh:
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue

            parent_guard_fires += 1
            names, cfeatures, meta = continuation_features(
                engine,
                board,
                str(p2["bestmove"]),
            )
            if names != continuation_names:
                raise AssertionError("fresh continuation feature order drift")

            if not predicate_eval(separator, int(cfeatures[j])):
                separator_rejects += 1
                continue

            # Commitment complete. Protected 100k authority starts here.
            accepted += 1
            authority = engine.search(
                fen,
                AUTHORITY_NODES,
                multipv=1,
                clear=True,
            )
            ok = str(p2["bestmove"]) == str(authority["bestmove"])
            accepted_wrong += int(not ok)

            if len(examples) < 30:
                examples.append(
                    {
                        "fen": fen,
                        "leaf": leaf,
                        "separator_feature": separator["feature_name"],
                        "separator_value": int(cfeatures[j]),
                        "candidate_move": p2["bestmove"],
                        "authority_move": authority["bestmove"],
                        "match": ok,
                        "continuation": meta,
                    }
                )
    finally:
        engine.quit()

    n = len(fresh)
    baseline_nodes = n * AUTHORITY_NODES
    hybrid_nodes = (
        n * PROBE_TOTAL_NODES
        + parent_guard_fires * CHILD_PROBE_TOTAL_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid_nodes / baseline_nodes

    green = accepted > 0 and accepted_wrong == 0 and reduction > 0.0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_CONTINUATION_SEPARATOR"
        if green
        else "FRESH_NORMAL_SEARCH_CONTINUATION_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v22_run": V22_RUN,
        "v25_run": V25_RUN,
        "v26_run": V26_RUN,
        "v27_run": V27_RUN,
        "v25_guard_sha256": guard_sha,
        "source": {
            "positions": len(source_records),
            "parent_guard_covered": len(source_parent_covered),
            "parent_guard_wrong": source_wrong,
            "continuation_feature_names": continuation_names,
            "separator": separator,
        },
        "continuation_protocol": {
            "candidate": "frozen V25 4k probe bestmove",
            "child_probe1_nodes": CHILD_PROBE1_NODES,
            "child_probe2_nodes": CHILD_PROBE2_NODES,
            "child_probe2_reuses_probe1_tt": True,
            "runs_only_when_v25_guard_fires": True,
        },
        "fresh_target": {
            "seed": FRESH_SEED,
            "book_sha256": fresh_manifest["book_sha256"],
            "positions": n,
            "source_position_overlap": len(overlap),
            "parent_guard_fires": parent_guard_fires,
            "separator_rejects": separator_rejects,
            "accepted_shortcuts": accepted,
            "accepted_coverage_ratio": accepted / n,
            "accepted_wrong": accepted_wrong,
            "baseline_node_budget": baseline_nodes,
            "expected_hybrid_node_budget": hybrid_nodes,
            "estimated_node_reduction_ratio": reduction,
            "examples": examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V25 root guard is unchanged",
                "only states inside the frozen V25 guard pay the new continuation probe",
                "one source false positive earns one separator in continuation-feature space only",
                "separator is frozen before any fresh 100k authority query",
                "fresh target uses a new opening seed and no selected source position overlaps it",
                "every prospectively accepted shortcut matches pinned 100k Stockfish and total expected node work is lower",
            ],
            "unknown": [
                "replication on another fresh normal-opening seed",
                "real UCI wall-clock gain",
                "self-play Elo gain",
                "chess-theoretic optimality of the pinned Stockfish authority",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_CONTINUATION_V28={status}")
    print(
        f"source parent={len(source_parent_covered)} wrong={source_wrong} "
        f"separator={separator}"
    )
    print(
        f"fresh positions={n} parent_guard={parent_guard_fires} "
        f"separator_rejects={separator_rejects}"
    )
    print(
        f"accepted={accepted} wrong={accepted_wrong} "
        f"coverage={accepted/n:.8f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
