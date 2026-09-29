#!/usr/bin/env python3
"""Crystal Chess V35: typed opponent-reply effect as applicability guard.

V34 showed that robust backed-value intervals still leave one exact exposed
false positive.  That survivor has a stable candidate/alternative ordering but
only the candidate exposes a forcing capture on the opponent's best cheap
reply.  V35 therefore freezes V34's weakest robust parent:

    candidate_low >= alternative_high

and allows exactly one new *typed continuation effect* relation, with no
learned numeric threshold:
  A. candidate reply is not a capture unless alternative reply also is;
  B. candidate reply is no more forcing (capture/check) than alternative;
  C. candidate/alternative reply effect classes are equal
     (capture/check/zeroing).

The weakest source-exact variant is frozen before any 100k query on untouched
seeds 20261011 and 20261012.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES, PROBE_TOTAL_NODES, STOCKFISH_PIN, UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256, base_probes, guard_fires, load_guard, read_epd,
)
from crystal_chess_search_continuation_v28 import (
    CHILD_PROBE_TOTAL_NODES, continuation_features, position_key,
)
from crystal_chess_search_relative_continuation_v30 import (
    relation_features, root_alternative,
)
from crystal_chess_search_backed_arbitration_v33 import (
    parent_accepts, source_keyset, source_rows,
)
from crystal_chess_search_robust_dominance_v34 import robust_values

SCHEMA = "mathgraph.crystal-chess.search-reply-effect.v35"
FRESH_SEEDS = (20261011, 20261012)
V34_RUN = 36501648903

VARIANTS = (
    "no_capture_disadvantage",
    "no_forcing_disadvantage",
    "reply_effect_equal",
)


def reply_effect(
    board: chess.Board,
    root_move_uci: str,
    reply_uci: str,
) -> dict[str, int]:
    root_move = chess.Move.from_uci(root_move_uci)
    if root_move not in board.legal_moves:
        raise AssertionError(("illegal root move", board.fen(), root_move_uci))
    child = board.copy(stack=False)
    child.push(root_move)
    reply = chess.Move.from_uci(reply_uci)
    if reply not in child.legal_moves:
        raise AssertionError(("illegal reply", child.fen(), reply_uci))
    mover = child.piece_at(reply.from_square)
    captured = child.piece_at(reply.to_square)
    return {
        "capture": int(child.is_capture(reply)),
        "check": int(child.gives_check(reply)),
        "zeroing": int(child.is_zeroing(reply)),
        "mover_type": int(mover.piece_type) if mover else 0,
        "captured_type": int(captured.piece_type) if captured else 0,
        "promotion": int(reply.promotion or 0),
    }


def annotate_effects(row: dict[str, Any]) -> None:
    board = chess.Board(str(row["fen"]))
    meta = row["relation_meta"]
    creply = str(meta["candidate_continuation"]["probe2"]["bestmove"])
    areply = str(meta["alternative_continuation"]["probe2"]["bestmove"])
    row["candidate_reply_effect"] = reply_effect(
        board, str(row["candidate"]), creply
    )
    row["alternative_reply_effect"] = reply_effect(
        board, str(row["alternative"]), areply
    )


def interval_parent(row: dict[str, Any]) -> bool:
    return robust_values(row)["robust_gap"] >= 0


def effect_accepts(variant: str, row: dict[str, Any]) -> bool:
    c = row["candidate_reply_effect"]
    a = row["alternative_reply_effect"]
    if variant == "no_capture_disadvantage":
        return int(c["capture"]) <= int(a["capture"])
    if variant == "no_forcing_disadvantage":
        return (
            int(c["capture"]) <= int(a["capture"])
            and int(c["check"]) <= int(a["check"])
        )
    if variant == "reply_effect_equal":
        return all(
            int(c[k]) == int(a[k])
            for k in ("capture", "check", "zeroing")
        )
    raise ValueError(variant)


def choose_variant(
    rows: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any]]:
    parent = [r for r in rows if interval_parent(r)]
    if sum(not bool(r["match"]) for r in parent) != 1:
        raise AssertionError("V34 interval parent residual drift")
    diagnostics: dict[str, Any] = {}
    for variant in VARIANTS:
        kept = [r for r in parent if effect_accepts(variant, r)]
        wrong = sum(not bool(r["match"]) for r in kept)
        support = Counter(str(r["generation"]) for r in kept)
        diagnostics[variant] = {
            "accepted": len(kept),
            "wrong": wrong,
            "support": dict(support),
            "retention_ratio_of_interval_parent": (
                len(kept) / len(parent) if parent else 0.0
            ),
        }
        if len(kept) >= 20 and wrong == 0 and len(support) >= 3:
            return variant, diagnostics
    return None, diagnostics


def evaluate_target(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
    variant: str,
    relation_names_ref: list[str],
) -> dict[str, Any]:
    v25_fires = parent = interval = accepted = wrong = 0
    examples: list[dict[str, Any]] = []

    for board in boards:
        fen = board.fen()
        p1, p2 = base_probes(engine, fen)
        fires, leaf = guard_fires(guard, board, p1, p2)
        if not fires:
            continue
        v25_fires += 1

        cnames, cfeats, cmeta = continuation_features(
            engine, board, str(p2["bestmove"])
        )
        if not parent_accepts(cnames, cfeats):
            continue
        parent += 1

        alt = root_alternative(p2)
        if alt is None:
            continue
        rnames, rfeats, rmeta = relation_features(
            engine, board, str(p2["bestmove"]), alt
        )
        if rnames != relation_names_ref:
            raise AssertionError("fresh relation feature drift")

        row = {
            "fen": fen,
            "candidate": str(p2["bestmove"]),
            "alternative": alt,
            "relation_features": rfeats,
            "relation_meta": rmeta,
        }
        if not interval_parent(row):
            continue
        interval += 1
        annotate_effects(row)
        if not effect_accepts(variant, row):
            continue

        accepted += 1
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "candidate": str(p2["bestmove"]),
                "alternative": alt,
                "authority": str(auth["bestmove"]),
                "match": ok,
                **robust_values(row),
                "candidate_reply_effect": row["candidate_reply_effect"],
                "alternative_reply_effect": row["alternative_reply_effect"],
                "candidate_continuation": cmeta,
                "relation": rmeta,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * PROBE_TOTAL_NODES
        + v25_fires * CHILD_PROBE_TOTAL_NODES
        + parent * CHILD_PROBE_TOTAL_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline if baseline else 0.0
    return {
        "positions": n,
        "v25_guard_fires": v25_fires,
        "parent_admitted": parent,
        "interval_admitted": interval,
        "accepted": accepted,
        "wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "baseline_nodes": baseline,
        "hybrid_nodes": hybrid,
        "estimated_node_reduction_ratio": reduction,
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
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))
    source_generations = list(zip(args.source_generation, args.source_epd))

    engine = UCIStockfish(args.stockfish)
    try:
        rows, relation_names = source_rows(
            engine, guard, args.v22_pgn, source_generations
        )
        if sum(not bool(r["match"]) for r in rows) != 3:
            raise AssertionError("exposed source residual drift")
        for row in rows:
            annotate_effects(row)

        variant, diagnostics = choose_variant(rows)
        interval_rows = [r for r in rows if interval_parent(r)]
        bad = [
            {
                "generation": r["generation"],
                "fen": r["fen"],
                "candidate": r["candidate"],
                "alternative": r["alternative"],
                "authority": r["authority"],
                **robust_values(r),
                "candidate_reply_effect": r["candidate_reply_effect"],
                "alternative_reply_effect": r["alternative_reply_effect"],
                "relation_meta": r["relation_meta"],
            }
            for r in interval_rows if not bool(r["match"])
        ]

        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "REPLY_EFFECT_DOES_NOT_CLOSE_EXPOSED_RESIDUAL",
                "stockfish_pin": STOCKFISH_PIN,
                "v34_run": V34_RUN,
                "source_states": len(rows),
                "interval_parent_states": len(interval_rows),
                "diagnostics": diagnostics,
                "interval_false_positive": bad,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_REPLY_EFFECT_V35="
                "REPLY_EFFECT_DOES_NOT_CLOSE_EXPOSED_RESIDUAL"
            )
            print(
                f"source={len(rows)} interval={len(interval_rows)} "
                f"diagnostics={diagnostics}"
            )
            print(f"artifact={args.output}")
            return 0

        # Freeze before fresh authority.
        prior_keys = source_keyset(args.v22_pgn, list(args.source_epd))
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        target_sets: list[list[chess.Board]] = []
        source_overlaps: list[int] = []
        cross_overlaps: list[int] = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            source_overlap = {position_key(b) for b in all_boards} & prior_keys
            boards = [b for b in all_boards if position_key(b) not in prior_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            source_overlaps.append(len(source_overlap))
            cross_overlaps.append(len(cross))

        targets = [
            evaluate_target(engine, guard, boards, variant, relation_names)
            for boards in target_sets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in targets)
    combined_accepted = sum(r["accepted"] for r in targets)
    combined_wrong = sum(r["wrong"] for r in targets)
    combined_baseline = sum(r["baseline_nodes"] for r in targets)
    combined_hybrid = sum(r["hybrid_nodes"] for r in targets)
    combined_reduction = (
        1.0 - combined_hybrid / combined_baseline
        if combined_baseline else 0.0
    )

    green = (
        all(r["accepted"] > 0 for r in targets)
        and combined_wrong == 0
        and all(r["estimated_node_reduction_ratio"] > 0 for r in targets)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_REPLY_EFFECT_GUARD"
        if green else
        "FRESH_NORMAL_SEARCH_REPLY_EFFECT_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v34_run": V34_RUN,
        "source": {
            "states": len(rows),
            "interval_parent_states": len(interval_rows),
            "variant_diagnostics": diagnostics,
            "selected_variant": variant,
            "interval_false_positive": bad,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": source_overlaps[i],
                "earlier_target_overlap_removed_before_search": cross_overlaps[i],
                **targets[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": combined_positions,
            "accepted": combined_accepted,
            "wrong": combined_wrong,
            "coverage_ratio": (
                combined_accepted / combined_positions
                if combined_positions else 0.0
            ),
            "baseline_nodes": combined_baseline,
            "hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V34 interval parent is frozen and is not promoted alone",
                "the only new coordinate is the typed effect of the opponent's best cheap reply",
                "no numeric threshold is learned",
                "the weakest source-exact effect relation is frozen before fresh 100k authority queries",
                "every fresh accepted shortcut equals pinned 100k Stockfish",
                "both fresh seeds retain positive charged node reduction",
            ],
            "unknown": [
                "wall-clock gain in normal UCI games",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SEARCH_REPLY_EFFECT_V35={status}")
    print(
        f"source={len(rows)} interval={len(interval_rows)} selected={variant} "
        f"diagnostics={diagnostics}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} parent={row['parent_admitted']} "
            f"interval={row['interval_admitted']} accepted={row['accepted']} "
            f"wrong={row['wrong']} coverage={row['coverage_ratio']:.8f} "
            f"reduction={row['estimated_node_reduction_ratio']:.8f}"
        )
    print(
        f"combined accepted={combined_accepted}/{combined_positions} "
        f"wrong={combined_wrong} "
        f"coverage={result['combined']['coverage_ratio']:.8f} "
        f"reduction={combined_reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
