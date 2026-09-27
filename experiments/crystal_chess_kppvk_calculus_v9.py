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
3. Admit a transported move only when exact KPPvK Syzygy WDL+DTZ verifies that
   it realizes the root Bellman value.
4. If neither transported instance is exact, use one exact Syzygy-backed
   residual/backstop move. This is the Complete-Then-Specialize correctness
   floor, not a learned KPPvK capability.
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
    dtz_cache: dict[tuple[str, bool], int],
) -> tuple[list[tuple[int, int, int, int, int, int]], Counter[int]]:
    records: list[tuple[int, int, int, int, int, int]] = []
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
                dtz = probe_dtz_safe(tablebase, board, dtz_cache)
                records.append((wk, bk, p0, p1, wdl, dtz))
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


def exact_root_move(
    board: chess.Board,
    move: chess.Move,
    root_wdl: int,
    root_dtz: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> bool:
    child = board.copy(stack=False)
    child.push(move)
    child_wdl = probe_wdl(tablebase, child, wdl_cache)

    if -child_wdl != root_wdl:
        return False

    # Syzygy WDL +/-1 are 50-move draws. For this first richer slice, if they
    # occur we require exact WDL preservation but do not promote them to a
    # forced-win progress claim. The calculus classifies only +2 as forced win.
    if root_wdl in (-1, 1):
        return True
    if root_wdl == 0:
        return True

    if child.halfmove_clock == 0:
        candidate_dtz = 1 if root_wdl == 2 else -1
    else:
        child_dtz = probe_dtz_safe(tablebase, child, dtz_cache)
        candidate_dtz = -child_dtz + (1 if root_wdl == 2 else -1)
    return candidate_dtz == root_dtz


def exact_optimal_moves(
    board: chess.Board,
    root_wdl: int,
    root_dtz: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> list[chess.Move]:
    moves = [
        move
        for move in board.legal_moves
        if exact_root_move(
            board,
            move,
            root_wdl,
            root_dtz,
            tablebase,
            wdl_cache,
            dtz_cache,
        )
    ]
    if not moves:
        raise AssertionError(
            f"no exact root move wdl={root_wdl} dtz={root_dtz} fen={board.fen()}"
        )
    return moves


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
            tb, wdl_cache, dtz_cache
        )
        state_id: dict[tuple[int, int, int, int], str] = {}
        sid_record: dict[str, tuple[int, int, int, int, int, int]] = {}
        expected_wins: set[str] = set()
        expected_draws: set[str] = set()
        expected_losses: set[str] = set()

        for idx, rec in enumerate(records):
            wk, bk, p0, p1, wdl, _dtz = rec
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

        transported = 0
        transported_anchor0 = 0
        transported_anchor1 = 0
        residual_backstop = 0
        transported_role_frequency = Counter()
        residual_role_frequency = Counter()
        steps: list[CapabilityStep] = []

        for sid, rec in sid_record.items():
            wk, bk, p0, p1, root_wdl, root_dtz = rec
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

            chosen_move: chess.Move | None = None
            chosen_capability: str | None = None
            chosen_support: frozenset[str] | None = None
            chosen_anchor = None

            for anchor_index, (anchor, role_label) in enumerate(
                zip(pawns, predicted)
            ):
                candidate = role_to_move(board, role_label, anchor)
                if candidate is None:
                    continue
                if exact_root_move(
                    board,
                    candidate,
                    root_wdl,
                    root_dtz,
                    tb,
                    wdl_cache,
                    dtz_cache,
                ):
                    chosen_move = candidate
                    chosen_capability = (
                        f"transport:kpvk-anchor{anchor_index}:{role_label}"
                    )
                    chosen_support = frozenset(
                        {
                            SYZYGY_SUPPORT,
                            f"capability:kpvk-role:{role_label}",
                        }
                    )
                    chosen_anchor = anchor_index
                    transported_role_frequency[role_label] += 1
                    transported += 1
                    if anchor_index == 0:
                        transported_anchor0 += 1
                    else:
                        transported_anchor1 += 1
                    break

            if chosen_move is None:
                exact_moves = exact_optimal_moves(
                    board,
                    root_wdl,
                    root_dtz,
                    tb,
                    wdl_cache,
                    dtz_cache,
                )
                chosen_move = min(exact_moves, key=lambda m: m.uci())
                residual_role = move_role(board, chosen_move)
                chosen_capability = f"residual:{residual_role}"
                chosen_support = frozenset(
                    {SYZYGY_SUPPORT, RESIDUAL_SUPPORT}
                )
                residual_role_frequency[residual_role] += 1
                residual_backstop += 1

            after_white = board.copy(stack=False)
            after_white.push(chosen_move)
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

            steps.append(
                CapabilityStep(
                    source=sid,
                    capability_id=chosen_capability,
                    outcomes=tuple(sorted(outcomes)),
                    support_refs=chosen_support,
                    evidence_refs=(
                        V8_AUTHORITY,
                        "authority:syzygy-kppvk",
                    ),
                )
            )

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

    result = compile_strategy_calculus(
        states=states,
        goals={GOAL},
        forbidden={LOSS},
        safe_terminals={DRAW},
        steps=steps,
        live_supports=live_supports,
    )
    verify_strategy_calculus(
        result,
        states=states,
        goals={GOAL},
        forbidden={LOSS},
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
        forbidden={LOSS},
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
            "transported_exact_states": transported,
            "transported_ratio": transported / len(records),
            "transported_anchor0": transported_anchor0,
            "transported_anchor1": transported_anchor1,
            "transported_role_frequency": dict(
                transported_role_frequency
            ),
            "residual_backstop_states": residual_backstop,
            "residual_ratio": residual_backstop / len(records),
            "residual_role_frequency": dict(residual_role_frequency),
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
        f"transported={transported} ratio={transported/len(records):.6f} "
        f"residual={residual_backstop} ratio={residual_backstop/len(records):.6f}"
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
