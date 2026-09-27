#!/usr/bin/env python3
"""Crystal Chess V9: complete richer-material KPPvK slice calculus.

Stateful continuation from the fully green V8 calculus.

Boundary
--------
* White K+2P vs Black K.
* White to move.
* Both pawns are on files a-b and ranks 2-6 at root states.
* Every legal king placement in that material slice is enumerated.
* A White move may leave the slice (for example advance a rank-6 pawn to
  rank 7); any resulting White-to-move state outside the slice is discharged
  by exact Syzygy WDL as a Completion-by-Reversal terminal basin.
* If Black captures one pawn, the resulting KPvK state is likewise discharged
  by the already-complete exact authority.

Capability order
----------------
1. Train/freeze the exact KPvK DTZ certificate policy before reading KPPvK
   labels.
2. In each KPPvK state, instantiate that single-pawn capability against each
   pawn independently.
3. Admit a transported move only when exact KPPvK Syzygy WDL verifies that
   it preserves the protected result.
4. Expose every exact WDL-preserving move as a Syzygy-backed alternative
   backstop capability. This is the Complete-Then-Specialize correctness
   floor, not a learned KPPvK capability. The generic calculus arbitrates
   among alternatives by forced progress / safety rather than a hand-written
   richer-material DTZ recurrence.
5. Compile two-ply White-move/all-Black-replies capability steps and require
   the generic V8 calculus to reconstruct the exact richer-material win/draw
   partition with zero internal residuals.
6. Revoke the residual backstop and reclose to measure how much of the richer
   strategic kernel is already covered by transported KPvK capabilities alone.

No KPPvK label enters KPvK policy acquisition.
"""

from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from mathgraph.capability_calculus import (
    CapabilityStep,
    compile_strategy_calculus,
    verify_strategy_calculus,
)
from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    move_role,
    tree_summary,
)
from crystal_chess_capability_calculus_v8 import (
    V6_AUTHORITY,
    probe_dtz_safe,
    dtz_optimal_roles,
)


SCHEMA = "mathgraph.crystal-chess.kppvk-calculus.v9"
V8_AUTHORITY = (
    "metalogiclabs/mathgraph@c6f81c20ef165eab0939443f1a8944c522f68bf3"
)
GOAL = "external:verified-white-win"
DRAW = "external:verified-draw"
LOSS = "external:verified-white-loss"
SYZYGY_SUPPORT = "authority:syzygy-wdl-dtz"
RESIDUAL_SUPPORT = "capability:kppvk-exact-residual-backstop"


def make_kppvk(
    wk: int,
    bk: int,
    p0: int,
    p1: int,
    turn: bool = chess.WHITE,
) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(p0, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(p1, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def root_pawn_squares() -> tuple[int, ...]:
    # Files a-b; ranks 2-6. Rank 7 is intentionally an exact external basin.
    return tuple(sorted(
        chess.square(file_index, rank_index)
        for file_index in (0, 1)
        for rank_index in range(1, 6)
    ))


def state_tuple(board: chess.Board) -> tuple[int, int, int, int]:
    if board.turn != chess.WHITE:
        raise ValueError("state_tuple requires White to move")
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    pawns = tuple(sorted(board.pieces(chess.PAWN, chess.WHITE)))
    if wk is None or bk is None or len(pawns) != 2:
        raise ValueError("not KPPvK")
    return wk, bk, pawns[0], pawns[1]


def in_root_slice(board: chess.Board) -> bool:
    if board.turn != chess.WHITE:
        return False
    if board.king(chess.WHITE) is None or board.king(chess.BLACK) is None:
        return False
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if len(pawns) != 2:
        return False
    allowed = set(root_pawn_squares())
    if any(pawn not in allowed for pawn in pawns):
        return False
    # No other non-king material.
    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
        ):
            if board.pieces(piece_type, color):
                return False
    if board.pieces(chess.PAWN, chess.BLACK):
        return False
    return True


def enumerate_root_slice(
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
) -> tuple[list[tuple[int, int, int, int, int]], Counter[int]]:
    records: list[tuple[int, int, int, int, int]] = []
    wdl_counts: Counter[int] = Counter()
    pawns = root_pawn_squares()

    for p0, p1 in itertools.combinations(pawns, 2):
        occupied_pawns = {p0, p1}
        for wk in range(64):
            if wk in occupied_pawns:
                continue
            for bk in range(64):
                if bk == wk or bk in occupied_pawns:
                    continue
                board = make_kppvk(wk, bk, p0, p1, chess.WHITE)
                if not board.is_valid():
                    continue
                wdl = probe_wdl(tablebase, board, wdl_cache)
                if wdl not in (-2, -1, 0, 1, 2):
                    raise AssertionError(wdl)
                records.append((wk, bk, p0, p1, wdl))
                wdl_counts[wdl] += 1
    return records, wdl_counts


def train_frozen_kpvk_policy(
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
):
    bank = coordinate_feature_bank()
    feature_fns = [fn for _, fn in bank]
    records, enumeration = enumerate_records(tablebase, wdl_cache, feature_fns)
    role_sets: list[tuple[str, ...]] = []
    nonterminal: list[int] = []
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        moves = list(board.legal_moves)
        if not moves:
            role_sets.append(())
            continue
        root_dtz = probe_dtz_safe(tablebase, board, dtz_cache)
        roles = dtz_optimal_roles(
            board,
            rec.wdl,
            root_dtz,
            tablebase,
            wdl_cache,
            dtz_cache,
        )
        role_sets.append(roles)
        nonterminal.append(i)

    labels, frequency = choose_preferred_roles(role_sets, nonterminal)
    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    tree.fit(X[nonterminal], [labels[i] for i in nonterminal])
    return tree, frequency, tree_summary(tree), feature_fns, enumeration


def role_to_move(
    board: chess.Board,
    role_label: str,
    anchor: int,
) -> chess.Move | None:
    wk = board.king(chess.WHITE)
    if wk is None:
        return None

    if role_label.startswith("K:"):
        body = role_label.split(":", 1)[1]
        dx_text, dy_text = body.split(",")
        dx, dy = int(dx_text), int(dy_text)
        ff = chess.square_file(wk)
        fr = chess.square_rank(wk)
        tf, tr = ff + dx, fr + dy
        if not (0 <= tf < 8 and 0 <= tr < 8):
            return None
        candidate = chess.Move(wk, chess.square(tf, tr))
    elif role_label.startswith("P:"):
        body = role_label.split(":", 1)[1]
        promo = None
        if "=" in body:
            delta, promo_text = body.split("=", 1)
            promo = {
                "Q": chess.QUEEN,
                "R": chess.ROOK,
                "B": chess.BISHOP,
                "N": chess.KNIGHT,
            }[promo_text]
        else:
            delta = body
        dx_text, dy_text = delta.split(",")
        dx, dy = int(dx_text), int(dy_text)
        ff = chess.square_file(anchor)
        fr = chess.square_rank(anchor)
        tf, tr = ff + dx, fr + dy
        if not (0 <= tf < 8 and 0 <= tr < 8):
            return None
        candidate = chess.Move(anchor, chess.square(tf, tr), promotion=promo)
    else:
        return None

    return candidate if candidate in board.legal_moves else None


def preserves_root_wdl(
    board: chess.Board,
    move: chess.Move,
    root_wdl: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
) -> bool:
    child = board.copy(stack=False)
    child.push(move)
    child_wdl = probe_wdl(tablebase, child, wdl_cache)
    return -child_wdl == root_wdl


def projected_features(
    wk: int,
    bk: int,
    anchor: int,
    feature_fns,
) -> tuple[int, ...]:
    return tuple(fn(wk, bk, anchor, chess.WHITE) for fn in feature_fns)


def white_value_outcome(
    board: chess.Board,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
) -> str:
    wdl = probe_wdl(tablebase, board, wdl_cache)
    white_value = wdl if board.turn == chess.WHITE else -wdl
    if white_value == 2:
        return GOAL
    if white_value == -2:
        return LOSS
    # Draw, cursed win and blessed loss are all non-forced wins under the
    # 50-move-aware WDL objective.
    return DRAW


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kppvk_calculus_v9.json"),
    )
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtb*"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]
    wdl_cache: dict[tuple[str, bool], int] = {}
    dtz_cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tb:
        # Acquisition order matters: KPvK policy is frozen before any KPPvK
        # labels are enumerated.
        (
            base_tree,
            base_frequency,
            base_tree_summary,
            feature_fns,
            kpvk_enumeration,
        ) = train_frozen_kpvk_policy(tb, wdl_cache, dtz_cache)

        records, wdl_counts = enumerate_root_slice(
            tb, wdl_cache
        )
        state_id: dict[tuple[int, int, int, int], str] = {}
        sid_record: dict[str, tuple[int, int, int, int, int]] = {}
        expected_wins: set[str] = set()
        expected_draws: set[str] = set()
        expected_losses: set[str] = set()

        for idx, rec in enumerate(records):
            wk, bk, p0, p1, wdl = rec
            sid = f"s{idx}"
            key = (wk, bk, p0, p1)
            state_id[key] = sid
            sid_record[sid] = rec
            if wdl == 2:
                expected_wins.add(sid)
            elif wdl == -2:
                expected_losses.add(sid)
            else:
                expected_draws.add(sid)

        transported_states = 0
        transported_anchor0 = 0
        transported_anchor1 = 0
        transported_steps = 0
        backstop_steps = 0
        transported_role_frequency = Counter()
        backstop_role_frequency = Counter()
        steps: list[CapabilityStep] = []

        def macro_outcomes(
            board: chess.Board,
            move: chess.Move,
        ) -> tuple[str, ...]:
            after_white = board.copy(stack=False)
            after_white.push(move)
            outcomes: set[str] = set()
            black_replies = list(after_white.legal_moves)
            if not black_replies:
                outcomes.add(
                    white_value_outcome(after_white, tb, wdl_cache)
                )
            else:
                for reply in black_replies:
                    child = after_white.copy(stack=False)
                    child.push(reply)
                    if in_root_slice(child):
                        key = state_tuple(child)
                        target = state_id.get(key)
                        if target is None:
                            raise AssertionError(
                                f"slice child missing: {child.fen()}"
                            )
                        outcomes.add(target)
                    else:
                        outcomes.add(
                            white_value_outcome(child, tb, wdl_cache)
                        )
            return tuple(sorted(outcomes))

        for sid, rec in sid_record.items():
            wk, bk, p0, p1, root_wdl = rec
            board = make_kppvk(wk, bk, p0, p1, chess.WHITE)
            pawns = (p0, p1)

            candidate_rows = np.asarray(
                [
                    projected_features(wk, bk, p0, feature_fns),
                    projected_features(wk, bk, p1, feature_fns),
                ],
                dtype=np.int16,
            )
            predicted = [str(x) for x in base_tree.predict(candidate_rows)]

            exact_transport_moves: dict[str, tuple[chess.Move, int, str]] = {}
            for anchor_index, (anchor, role_label) in enumerate(
                zip(pawns, predicted)
            ):
                candidate = role_to_move(board, role_label, anchor)
                if candidate is None:
                    continue
                if preserves_root_wdl(
                    board,
                    candidate,
                    root_wdl,
                    tb,
                    wdl_cache,
                ):
                    key = candidate.uci()
                    exact_transport_moves.setdefault(
                        key, (candidate, anchor_index, role_label)
                    )

            if exact_transport_moves:
                transported_states += 1

            outcome_cache: dict[str, tuple[str, ...]] = {}
            for key, (candidate, anchor_index, role_label) in sorted(
                exact_transport_moves.items()
            ):
                outcomes = outcome_cache.setdefault(
                    key, macro_outcomes(board, candidate)
                )
                steps.append(
                    CapabilityStep(
                        source=sid,
                        capability_id=(
                            f"transport:kpvk-anchor{anchor_index}:{role_label}"
                        ),
                        outcomes=outcomes,
                        support_refs=frozenset(
                            {
                                SYZYGY_SUPPORT,
                                f"capability:kpvk-role:{role_label}",
                            }
                        ),
                        evidence_refs=(
                            V8_AUTHORITY,
                            "authority:syzygy-kppvk",
                        ),
                    )
                )
                transported_steps += 1
                transported_role_frequency[role_label] += 1
                if anchor_index == 0:
                    transported_anchor0 += 1
                else:
                    transported_anchor1 += 1

            # Complete-Then-Specialize backstop: expose every exact
            # WDL-preserving move as an alternative certified capability.
            # The calculus—not a hand-written richer-material scorer—decides
            # which one actually belongs to the forced-goal attractor or
            # greatest safety kernel.
            preserving_moves = [
                move
                for move in board.legal_moves
                if preserves_root_wdl(
                    board, move, root_wdl, tb, wdl_cache
                )
            ]
            if not preserving_moves and list(board.legal_moves):
                raise AssertionError(
                    f"no WDL-preserving legal move: {board.fen()}"
                )

            for move in preserving_moves:
                key = move.uci()
                outcomes = outcome_cache.setdefault(
                    key, macro_outcomes(board, move)
                )
                role_label = move_role(board, move)
                steps.append(
                    CapabilityStep(
                        source=sid,
                        capability_id=f"backstop:{key}",
                        outcomes=outcomes,
                        support_refs=frozenset(
                            {SYZYGY_SUPPORT, RESIDUAL_SUPPORT}
                        ),
                        evidence_refs=("authority:syzygy-kppvk",),
                    )
                )
                backstop_steps += 1
                backstop_role_frequency[role_label] += 1

    states = set(sid_record) | {GOAL, DRAW, LOSS}
    all_base_supports = {
        f"capability:kpvk-role:{role}"
        for role in base_frequency
    }
    live_supports = {
        SYZYGY_SUPPORT,
        RESIDUAL_SUPPORT,
        *all_base_supports,
    }

    forbidden_states = {LOSS} | expected_losses

    result = compile_strategy_calculus(
        states=states,
        goals={GOAL},
        forbidden=forbidden_states,
        safe_terminals={DRAW},
        steps=steps,
        live_supports=live_supports,
    )
    verify_strategy_calculus(
        result,
        states=states,
        goals={GOAL},
        forbidden=forbidden_states,
        safe_terminals={DRAW},
        steps=steps,
        live_supports=live_supports,
    )

    forced_internal = set(result.forced_goal_states) - {GOAL, DRAW, LOSS}
    safety_internal = set(result.safety_states) - {GOAL, DRAW, LOSS}
    internal_residuals = [
        residual
        for residual in result.residuals
        if residual.state.startswith("s")
    ]

    win_missing = expected_wins - forced_internal
    win_extra = forced_internal - expected_wins
    draw_missing = expected_draws - safety_internal
    loss_in_safe = expected_losses & safety_internal

    if win_missing or win_extra:
        raise AssertionError(
            f"win mismatch missing={len(win_missing)} extra={len(win_extra)}"
        )
    if draw_missing:
        raise AssertionError(f"draw states outside safety: {len(draw_missing)}")
    if loss_in_safe:
        raise AssertionError(f"loss states inside safety: {len(loss_in_safe)}")
    if internal_residuals:
        raise AssertionError(
            f"unexpected internal residuals: {len(internal_residuals)}"
        )

    # Ablate only the exact residual/backstop support. Transported KPvK
    # capabilities stay live. Reclose to expose the richer-material frontier.
    base_only_supports = set(live_supports)
    base_only_supports.remove(RESIDUAL_SUPPORT)
    base_only = compile_strategy_calculus(
        states=states,
        goals={GOAL},
        forbidden=forbidden_states,
        safe_terminals={DRAW},
        steps=steps,
        live_supports=base_only_supports,
    )
    base_only_internal_residuals = [
        residual
        for residual in base_only.residuals
        if residual.state.startswith("s")
    ]
    base_only_forced = (
        set(base_only.forced_goal_states) - {GOAL, DRAW, LOSS}
    )
    base_only_safe = (
        set(base_only.safety_states) - {GOAL, DRAW, LOSS}
    )

    rank_map = result.rank_map
    win_ranks = [rank_map[s] for s in expected_wins]
    evidence = {
        "schema": SCHEMA,
        "status": "WARRANTED_COMPLETE_KPPVK_SLICE_CAPABILITY_CALCULUS",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v6_authority": V6_AUTHORITY,
        "v8_authority": V8_AUTHORITY,
        "boundary": {
            "material": "White K+2P vs Black K",
            "side_to_move": "White",
            "root_pawn_files": ["a", "b"],
            "root_pawn_ranks": [2, 3, 4, 5, 6],
            "all_legal_king_placements": True,
            "outside_slice": "exact Syzygy WDL terminal basin",
        },
        "authority": {
            "kind": "Syzygy WDL + DTZ",
            "tablebase_files": manifest,
        },
        "frozen_kpvk_capability": {
            "tree": base_tree_summary,
            "role_frequency": base_frequency,
            "kppvk_labels_used_in_acquisition": 0,
            "kpvk_enumeration": kpvk_enumeration,
        },
        "slice": {
            "states": len(records),
            "wdl_distribution": {
                str(k): v for k, v in sorted(wdl_counts.items())
            },
            "expected_wins": len(expected_wins),
            "expected_draws_50move": len(expected_draws),
            "expected_losses": len(expected_losses),
        },
        "capability_cover": {
            "transported_exact_states": transported_states,
            "transported_state_ratio": transported_states / len(records),
            "transported_steps": transported_steps,
            "transported_anchor0_steps": transported_anchor0,
            "transported_anchor1_steps": transported_anchor1,
            "transported_role_frequency": dict(
                transported_role_frequency
            ),
            "exact_backstop_steps": backstop_steps,
            "backstop_role_frequency": dict(backstop_role_frequency),
        },
        "calculus": {
            "capability_steps": len(steps),
            "forced_goal_internal_states": len(forced_internal),
            "expected_syzygy_wins": len(expected_wins),
            "safety_internal_states": len(safety_internal),
            "expected_syzygy_draws": len(expected_draws),
            "win_missing": len(win_missing),
            "win_extra": len(win_extra),
            "draw_missing_safety": len(draw_missing),
            "loss_in_safety": len(loss_in_safe),
            "internal_residuals": len(internal_residuals),
            "max_forced_goal_rank": max(win_ranks) if win_ranks else 0,
        },
        "transport_only_ablation": {
            "residual_support_removed": True,
            "internal_residuals": len(base_only_internal_residuals),
            "forced_win_states_retained": len(
                expected_wins & base_only_forced
            ),
            "forced_win_states_lost": len(
                expected_wins - base_only_forced
            ),
            "draw_states_retained_safe": len(
                expected_draws & base_only_safe
            ),
            "draw_states_lost_safe": len(
                expected_draws - base_only_safe
            ),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the generic V8 capability calculus exactly reconstructs the Syzygy win/draw partition on every legal root state in the declared complete KPPvK slice",
                "the KPvK policy is frozen before KPPvK labels are read",
                "every transported capability is independently admitted only after exact KPPvK WDL+DTZ verification",
                "removing the exact residual/backstop support exposes precisely the remaining strategic frontier under transported capabilities",
            ],
            "unknown": [
                "complete unrestricted KPPvK closure",
                "symbolic compression of the KPPvK residual/backstop",
                "full chess",
            ],
        },
        "cache": {
            "wdl_positions": len(wdl_cache),
            "dtz_positions": len(dtz_cache),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n"
    )

    print("CRYSTAL_CHESS_KPPVK_CALCULUS_V9=PASS")
    print(
        f"states={len(records)} wins={len(expected_wins)} "
        f"draws={len(expected_draws)} losses={len(expected_losses)}"
    )
    print(
        f"transported_states={transported_states} "
        f"ratio={transported_states/len(records):.6f} "
        f"transport_steps={transported_steps} "
        f"backstop_steps={backstop_steps}"
    )
    print(
        f"calculus wins={len(forced_internal)}/{len(expected_wins)} "
        f"draws_safe={len(expected_draws-draw_missing)}/{len(expected_draws)} "
        f"residuals={len(internal_residuals)} "
        f"max_rank={max(win_ranks) if win_ranks else 0}"
    )
    print(
        f"transport_only residuals={len(base_only_internal_residuals)} "
        f"wins_retained={len(expected_wins & base_only_forced)} "
        f"wins_lost={len(expected_wins-base_only_forced)} "
        f"draws_retained={len(expected_draws & base_only_safe)}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
