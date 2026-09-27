#!/usr/bin/env python3
"""Crystal Chess V3: DTZ-ranked terminating KPvK strategy certificate.

V2 compiled exact WDL-preserving strategy rules, but a WDL-preserving winning
move can in principle cycle forever.  V3 asks for a stronger verified action.

For every winning KPvK state s, seek a legal WIN-preserving move a such that:
* if a exits KPvK (promotion/checkmate), the winning phase closes; otherwise
* after EVERY legal reply by the losing side, the resulting winning KPvK state
  u has strictly smaller lexicographic rank

      R(s) = (white-pawn pushes remaining to promotion, positive Syzygy DTZ).

Pawn advances strictly reduce the first coordinate and may reset DTZ.  Between
pawn advances, DTZ must strictly decrease across each full winning/losing ply
pair.  Therefore any policy using only these certified actions must leave the
KPvK phase in finite time.

Draw states retain V2's WDL-preserving viability policy.  Losing states remain
universal local proof obligations.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_minimax_policy_v2 import (
    action_for_schema,
    canonical_policy_for_digest,
    choose_schema_from_tree,
    compile_policy,
    file_sha256,
    relative_move_schema,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-dtz-progress-policy.v3"
V2_AUTHORITY = (
    "metalogiclabs/mathgraph@5ae16e08ec4eb03e52c138f8e03137502ab97f44"
)


def board_key(board: chess.Board) -> tuple[str, bool]:
    return board.board_fen(), board.turn


def probe_dtz_cached(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    cache: dict[tuple[str, bool], int],
) -> int:
    key = board_key(board)
    if key not in cache:
        cache[key] = int(tablebase.probe_dtz(board))
    return cache[key]


def is_internal_kpvk(board: chess.Board) -> bool:
    if len(board.pieces(chess.PAWN, chess.WHITE)) != 1:
        return False
    if any(
        board.pieces(piece_type, chess.WHITE)
        for piece_type in (
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
        )
    ):
        return False
    if any(
        board.pieces(piece_type, chess.BLACK)
        for piece_type in (
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        )
    ):
        return False
    return board.king(chess.WHITE) is not None and board.king(chess.BLACK) is not None


def win_rank(
    board: chess.Board,
    tablebase: chess.syzygy.Tablebase,
    dtz_cache: dict[tuple[str, bool], int],
) -> tuple[int, int]:
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if len(pawns) != 1:
        raise AssertionError(f"rank requested outside KPvK: {board.fen()}")
    pawn = pawns[0]
    steps = 7 - chess.square_rank(pawn)
    dtz = probe_dtz_cached(tablebase, board, dtz_cache)
    if dtz <= 0:
        raise AssertionError(
            f"winning-side rank requires positive DTZ, got {dtz}: {board.fen()}"
        )
    return steps, dtz


def progress_safe_schema_set(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    root_wdl: int,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> tuple[set[str], dict[str, Any]]:
    if root_wdl != 2:
        raise ValueError("progress-safe audit is only for winning states")
    root_rank = win_rank(board, tablebase, dtz_cache)
    safe: set[str] = set()
    candidate_count = 0
    reply_checks = 0
    rank_failures: list[dict[str, Any]] = []

    for move in board.legal_moves:
        child = board.copy(stack=False)
        child.push(move)
        child_wdl = probe_wdl(tablebase, child, wdl_cache)
        if -child_wdl != 2:
            continue
        candidate_count += 1
        schema = relative_move_schema(board, move)

        # Promotion or immediate mate leaves the declared KPvK phase while
        # preserving WIN. That is a certified phase-closing action.
        if not is_internal_kpvk(child) or not any(child.legal_moves):
            safe.add(schema)
            continue

        # The opponent is now in an exact losing state. Every legal reply must
        # return a winning state for White. Require two-ply rank descent against
        # all such replies.
        move_safe = True
        local_failure = None
        for reply in child.legal_moves:
            reply_checks += 1
            grandchild = child.copy(stack=False)
            grandchild.push(reply)
            grandchild_wdl = probe_wdl(tablebase, grandchild, wdl_cache)
            if grandchild_wdl != 2:
                move_safe = False
                local_failure = {
                    "reason": "loss_state_has_nonwinning_reply",
                    "move": move.uci(),
                    "reply": reply.uci(),
                    "grandchild_wdl": grandchild_wdl,
                }
                break
            if not is_internal_kpvk(grandchild):
                # A black reply leaving KPvK while White remains winning would
                # be a phase exit. Preserve it as progress.
                continue
            next_rank = win_rank(grandchild, tablebase, dtz_cache)
            if not next_rank < root_rank:
                move_safe = False
                local_failure = {
                    "reason": "rank_not_decreased",
                    "move": move.uci(),
                    "reply": reply.uci(),
                    "root_rank": root_rank,
                    "next_rank": next_rank,
                }
                break

        if move_safe:
            safe.add(schema)
        elif len(rank_failures) < 8 and local_failure is not None:
            rank_failures.append(local_failure)

    return safe, {
        "root_rank": root_rank,
        "value_preserving_candidate_moves": candidate_count,
        "reply_checks": reply_checks,
        "sample_rank_failures": rank_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_dtz_progress_v3.json"),
    )
    args = parser.parse_args()
    started = time.time()

    wdl_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    dtz_files = sorted(args.tablebase_dir.glob("*.rtbz"))
    if not wdl_files or not dtz_files:
        raise SystemExit("both WDL (.rtbw) and DTZ (.rtbz) files are required")
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(wdl_files + dtz_files)
    ]

    base_bank = coordinate_feature_bank()
    feature_names = ["protected_wdl"] + [name for name, _ in base_bank]
    feature_fns = [fn for _, fn in base_bank]

    wdl_cache: dict[tuple[str, bool], int] = {}
    dtz_cache: dict[tuple[str, bool], int] = {}
    raw_rows: list[tuple[Any, tuple[int, ...], set[str]]] = []
    all_schemas: set[str] = set()

    losing_universal_failures = 0
    terminal_nonlosing = 0
    winning_states = 0
    draw_states = 0
    winning_without_progress = 0
    progress_reply_checks = 0
    progress_candidate_moves = 0
    progress_safe_moves = 0
    residual_examples: list[dict[str, Any]] = []

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, wdl_cache, feature_fns
        )
        assert enumeration["mirror_invalid"] == 0
        assert enumeration["mirror_mismatches"] == 0

        for rec in records:
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            legal_moves = list(board.legal_moves)

            consequences: list[tuple[chess.Move, int]] = []
            for move in legal_moves:
                child = board.copy(stack=False)
                child.push(move)
                consequence = -probe_wdl(tablebase, child, wdl_cache)
                consequences.append((move, consequence))

            if rec.wdl < 0:
                if any(value != rec.wdl for _, value in consequences):
                    losing_universal_failures += 1
                continue

            if not legal_moves:
                terminal_nonlosing += 1
                continue

            if rec.wdl == 2:
                winning_states += 1
                safe, diag = progress_safe_schema_set(
                    tablebase,
                    board,
                    rec.wdl,
                    wdl_cache,
                    dtz_cache,
                )
                progress_reply_checks += int(diag["reply_checks"])
                progress_candidate_moves += int(
                    diag["value_preserving_candidate_moves"]
                )
                progress_safe_moves += len(safe)
                if not safe:
                    winning_without_progress += 1
                    if len(residual_examples) < 20:
                        residual_examples.append(
                            {
                                "fen": board.fen(),
                                "root_rank": diag["root_rank"],
                                "rank_failures": diag["sample_rank_failures"],
                            }
                        )
                    continue
                admissible = safe
            elif rec.wdl == 0:
                draw_states += 1
                admissible = {
                    relative_move_schema(board, move)
                    for move, consequence in consequences
                    if consequence == 0
                }
                if not admissible:
                    raise AssertionError(
                        f"draw state has no draw-preserving move: {board.fen()}"
                    )
            else:
                raise AssertionError(f"unexpected KPvK WDL: {rec.wdl}")

            all_schemas.update(admissible)
            vector = (rec.wdl,) + rec.features
            raw_rows.append((rec, vector, admissible))

        assert losing_universal_failures == 0

        scientific_status = (
            "WARRANTED_KPVK_DTZ_TWO_PLY_PROGRESS"
            if winning_without_progress == 0
            else "REJECTED_KPVK_DTZ_TWO_PLY_PROGRESS"
        )

        compiler_result = None
        if winning_without_progress == 0:
            schema_names = sorted(all_schemas)
            schema_index = {name: i for i, name in enumerate(schema_names)}
            features: list[tuple[int, ...]] = []
            allowed_masks: list[int] = []
            for _, vector, admissible in raw_rows:
                mask = 0
                for schema in admissible:
                    mask |= 1 << schema_index[schema]
                features.append(vector)
                allowed_masks.append(mask)

            tree, policy_stats = compile_policy(
                features, allowed_masks, feature_names
            )

            verification_errors: list[dict[str, Any]] = []
            chosen_counts: Counter[str] = Counter()
            for row_index, (rec, vector, admissible) in enumerate(raw_rows):
                schema = choose_schema_from_tree(tree, vector, schema_names)
                chosen_counts[schema] += 1
                board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
                try:
                    move = action_for_schema(board, schema)
                except AssertionError as exc:
                    if len(verification_errors) < 20:
                        verification_errors.append(
                            {
                                "row": row_index,
                                "fen": board.fen(),
                                "schema": schema,
                                "error": str(exc),
                            }
                        )
                    continue

                child = board.copy(stack=False)
                child.push(move)
                consequence = -probe_wdl(tablebase, child, wdl_cache)
                if consequence != rec.wdl or schema not in admissible:
                    if len(verification_errors) < 20:
                        verification_errors.append(
                            {
                                "row": row_index,
                                "fen": board.fen(),
                                "schema": schema,
                                "move": move.uci(),
                                "expected_wdl": rec.wdl,
                                "actual_consequence": consequence,
                            }
                        )
                    continue

                if rec.wdl == 2:
                    safe_again, _ = progress_safe_schema_set(
                        tablebase,
                        board,
                        rec.wdl,
                        wdl_cache,
                        dtz_cache,
                    )
                    if schema not in safe_again:
                        if len(verification_errors) < 20:
                            verification_errors.append(
                                {
                                    "row": row_index,
                                    "fen": board.fen(),
                                    "schema": schema,
                                    "error": "chosen win schema lost DTZ progress property",
                                }
                            )

            if verification_errors:
                raise AssertionError(
                    f"compiled V3 policy verification errors: {verification_errors}"
                )

            canonical_policy = canonical_policy_for_digest(tree, schema_names)
            policy_bytes = json.dumps(
                canonical_policy,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            compiler_result = {
                **policy_stats,
                "schema_names": schema_names,
                "chosen_schema_counts": dict(chosen_counts),
                "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
                "canonical_policy": canonical_policy,
                "verification_errors": 0,
            }

    result = {
        "schema": SCHEMA,
        "status": scientific_status,
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v2_authority": V2_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "authority": {
            "kind": "Syzygy WDL + DTZ",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "enumeration": enumeration,
        "progress_law": {
            "rank": "(pawn pushes remaining to promotion, positive DTZ)",
            "ordering": "lexicographic on natural numbers",
            "scope": "winning KPvK state -> chosen move -> every losing-side reply",
            "winning_states": winning_states,
            "winning_states_without_progress_action": winning_without_progress,
            "value_preserving_candidate_moves_checked": progress_candidate_moves,
            "progress_safe_action_schemas_counted_per_state": progress_safe_moves,
            "opponent_replies_checked": progress_reply_checks,
            "residual_examples": residual_examples,
        },
        "other_obligations": {
            "draw_states_with_policy": draw_states,
            "terminal_nonlosing_states": terminal_nonlosing,
            "losing_universal_failures": losing_universal_failures,
        },
        "compiler": compiler_result,
        "epistemic_boundary": {
            "warranted_if_status_warranted": [
                (
                    "every winning KPvK state admits a relative action schema "
                    "that preserves WIN and, against every losing-side reply, "
                    "either exits KPvK or strictly decreases the declared rank"
                ),
                (
                    "the lexicographic rank is well-founded, so repeated "
                    "certified winning choices cannot remain in KPvK forever"
                ),
            ],
            "unknown": [
                "termination after promotion outside KPvK",
                "cross-material reuse of the compiled policy",
                "general chess solution",
            ],
        },
        "cache": {
            "unique_wdl_positions_probed_or_certified": len(wdl_cache),
            "unique_dtz_positions_probed": len(dtz_cache),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print("CRYSTAL_CHESS_DTZ_PROGRESS_V3=PASS")
    print(f"scientific_status={scientific_status}")
    print(
        f"winning_states={winning_states} "
        f"without_progress={winning_without_progress} "
        f"reply_checks={progress_reply_checks}"
    )
    if compiler_result is not None:
        print(
            f"policy_states={compiler_result['states']} "
            f"leaves={compiler_result['leaves']} "
            f"compression={compiler_result['state_per_leaf_compression']:.3f}x"
        )
        print(f"policy_sha256={compiler_result['policy_sha256']}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
