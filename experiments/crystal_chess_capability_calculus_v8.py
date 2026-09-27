#!/usr/bin/env python3
"""Crystal Chess V8: instantiate the generic capability calculus on KPvK.

The source policy is learned from exact Syzygy WDL+DTZ, as in V6.  The policy
is then frozen and converted into extensional capability steps over WHITE
decision states:

    White certified move -> ALL legal Black replies -> next White state.

Thus each capability step has adversarial outcomes.  Promotions/captures that
leave KPvK are discharged into exact external Syzygy win/draw/loss basins
(Completion-by-Reversal).

The generic calculus must independently recover:
* every exact White-win KPvK state as forced-goal with a decreasing rank;
* every exact White-draw state inside the greatest safety kernel;
* zero unexplained internal residuals.

This is the first complete chess instantiation of:
guarded capability -> adversarial outcomes -> goal attractor / safety kernel ->
arbitration -> residual -> revocation-sensitive reclosure.
"""

from __future__ import annotations

import argparse
from collections import Counter
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


SCHEMA = "mathgraph.crystal-chess.capability-calculus.v8"
V6_AUTHORITY = (
    "metalogiclabs/mathgraph@7c46d0144efea61dca7899a4c8eecbd1e05186fc"
)
GOAL = "external:verified-white-win"
DRAW = "external:verified-draw"
LOSS = "external:verified-white-loss"
SYZYGY_SUPPORT = "authority:syzygy-wdl-dtz"


def probe_dtz_safe(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    cache: dict[tuple[str, bool], int],
) -> int:
    key = (board.board_fen(), board.turn)
    if key in cache:
        return cache[key]
    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
        value = 0
    else:
        value = int(tablebase.probe_dtz(board))
    cache[key] = value
    return value


def dtz_optimal_roles(
    board: chess.Board,
    root_wdl: int,
    root_dtz: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> tuple[str, ...]:
    if root_wdl not in (-2, 0, 2):
        raise AssertionError(f"unexpected cursed/blessed KPvK WDL {root_wdl}")

    roles: set[str] = set()
    legal = 0
    for move in board.legal_moves:
        legal += 1
        child = board.copy(stack=False)
        child.push(move)
        child_wdl = probe_wdl(tablebase, child, wdl_cache)
        if -child_wdl != root_wdl:
            continue

        if root_wdl == 0:
            candidate_dtz = 0
        elif child.halfmove_clock == 0:
            candidate_dtz = 1 if root_wdl == 2 else -1
        else:
            child_dtz = probe_dtz_safe(tablebase, child, dtz_cache)
            candidate_dtz = -child_dtz + (1 if root_wdl == 2 else -1)

        if candidate_dtz == root_dtz:
            roles.add(move_role(board, move))

    if legal == 0:
        return ()
    if not roles:
        raise AssertionError(
            f"no root-DTZ-realizing role wdl={root_wdl} dtz={root_dtz} fen={board.fen()}"
        )
    return tuple(sorted(roles))


def material_is_kpvk(board: chess.Board) -> bool:
    return (
        len(board.pieces(chess.PAWN, chess.WHITE)) == 1
        and not board.pieces(chess.QUEEN, chess.WHITE)
        and not board.pieces(chess.ROOK, chess.WHITE)
        and not board.pieces(chess.BISHOP, chess.WHITE)
        and not board.pieces(chess.KNIGHT, chess.WHITE)
        and not board.pieces(chess.PAWN, chess.BLACK)
        and not board.pieces(chess.QUEEN, chess.BLACK)
        and not board.pieces(chess.ROOK, chess.BLACK)
        and not board.pieces(chess.BISHOP, chess.BLACK)
        and not board.pieces(chess.KNIGHT, chess.BLACK)
    )


def white_state_key(board: chess.Board) -> tuple[int, int, int]:
    if board.turn != chess.WHITE:
        raise ValueError("white state key requires White to move")
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if wk is None or bk is None or len(pawns) != 1:
        raise ValueError("not KPvK")
    return wk, bk, pawns[0]


def external_outcome(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    wdl_cache: dict[tuple[str, bool], int],
) -> str:
    wdl = probe_wdl(tablebase, board, wdl_cache)
    white_value = wdl if board.turn == chess.WHITE else -wdl
    if white_value > 0:
        return GOAL
    if white_value == 0:
        return DRAW
    return LOSS


def exact_policy_move(
    board: chess.Board,
    predicted_role: str,
    root_wdl: int,
    root_dtz: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> chess.Move:
    candidates: list[chess.Move] = []
    for move in board.legal_moves:
        if move_role(board, move) != predicted_role:
            continue
        child = board.copy(stack=False)
        child.push(move)
        child_wdl = probe_wdl(tablebase, child, wdl_cache)
        if -child_wdl != root_wdl:
            continue
        if root_wdl == 0:
            candidate_dtz = 0
        elif child.halfmove_clock == 0:
            candidate_dtz = 1 if root_wdl == 2 else -1
        else:
            child_dtz = probe_dtz_safe(tablebase, child, dtz_cache)
            candidate_dtz = -child_dtz + (1 if root_wdl == 2 else -1)
        if candidate_dtz == root_dtz:
            candidates.append(move)
    if not candidates:
        raise AssertionError(
            f"compiled role has no exact DTZ witness role={predicted_role} fen={board.fen()}"
        )
    return min(candidates, key=lambda move: move.uci())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_capability_calculus_v8.json"),
    )
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtb*"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]
    bank = coordinate_feature_bank()
    feature_fns = [fn for _, fn in bank]
    wdl_cache: dict[tuple[str, bool], int] = {}
    dtz_cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tb:
        records, enumeration = enumerate_records(tb, wdl_cache, feature_fns)

        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        white_indices: list[int] = []
        terminal_white: list[int] = []
        root_dtz_by_index: dict[int, int] = {}

        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            if rec.turn:
                white_indices.append(i)
            moves = list(board.legal_moves)
            if not moves:
                role_sets.append(())
                if rec.turn:
                    terminal_white.append(i)
                continue
            root_dtz = probe_dtz_safe(tb, board, dtz_cache)
            root_dtz_by_index[i] = root_dtz
            roles = dtz_optimal_roles(
                board, rec.wdl, root_dtz, tb, wdl_cache, dtz_cache
            )
            role_sets.append(roles)
            nonterminal.append(i)

        labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
        X = np.asarray([rec.features for rec in records], dtype=np.int16)
        policy = DecisionTreeClassifier(
            criterion="entropy", splitter="best", random_state=0
        )
        policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
        policy_summary = tree_summary(policy)

        # Complete White-to-move internal state map.
        white_state_id: dict[tuple[int, int, int], str] = {}
        record_state_id: dict[int, str] = {}
        expected_wins: set[str] = set()
        expected_draws: set[str] = set()
        safe_terminals: set[str] = {DRAW}

        for i in white_indices:
            rec = records[i]
            sid = f"kpvk:{rec.wk}:{rec.bk}:{rec.pawn}:W"
            record_state_id[i] = sid
            white_state_id[(rec.wk, rec.bk, rec.pawn)] = sid
            if rec.wdl == 2:
                expected_wins.add(sid)
            elif rec.wdl == 0:
                expected_draws.add(sid)
            elif rec.wdl == -2:
                # Retain the possibility in the verifier even though KPvK
                # should not contain a White loss.
                pass
            else:
                raise AssertionError(f"unexpected KPvK WDL {rec.wdl}")

        steps: list[CapabilityStep] = []
        role_use: Counter[str] = Counter()
        direct_external = Counter()

        for i in white_indices:
            rec = records[i]
            sid = record_state_id[i]
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, True)
            moves = list(board.legal_moves)
            if not moves:
                if rec.wdl == 0:
                    safe_terminals.add(sid)
                elif rec.wdl == 2:
                    raise AssertionError("winning White state has no legal move")
                continue

            predicted_role = str(policy.predict(X[[i]])[0])
            move = exact_policy_move(
                board,
                predicted_role,
                rec.wdl,
                root_dtz_by_index[i],
                tb,
                wdl_cache,
                dtz_cache,
            )
            role_use[predicted_role] += 1

            after_white = board.copy(stack=False)
            after_white.push(move)
            outcomes: set[str] = set()

            black_replies = list(after_white.legal_moves)
            if not black_replies:
                outcome = external_outcome(tb, after_white, wdl_cache)
                outcomes.add(outcome)
                direct_external[outcome] += 1
            else:
                for reply in black_replies:
                    child = after_white.copy(stack=False)
                    child.push(reply)

                    if child.turn != chess.WHITE:
                        raise AssertionError("two-ply macro did not return White turn")

                    if material_is_kpvk(child):
                        key = white_state_key(child)
                        target = white_state_id.get(key)
                        if target is None:
                            raise AssertionError(
                                f"internal White KPvK child missing: {child.fen()}"
                            )
                        outcomes.add(target)
                    else:
                        outcome = external_outcome(tb, child, wdl_cache)
                        outcomes.add(outcome)
                        direct_external[outcome] += 1

            steps.append(
                CapabilityStep(
                    source=sid,
                    capability_id=f"dtz-role:{predicted_role}",
                    outcomes=tuple(sorted(outcomes)),
                    support_refs=frozenset(
                        {SYZYGY_SUPPORT, f"capability:dtz-role:{predicted_role}"}
                    ),
                    evidence_refs=(V6_AUTHORITY,),
                )
            )

    states = set(record_state_id.values()) | {GOAL, DRAW, LOSS}
    all_role_supports = {
        f"capability:dtz-role:{role}" for role in role_frequency
    }
    live_supports = {SYZYGY_SUPPORT} | all_role_supports

    result = compile_strategy_calculus(
        states=states,
        goals={GOAL},
        forbidden={LOSS},
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=live_supports,
    )
    verify_strategy_calculus(
        result,
        states=states,
        goals={GOAL},
        forbidden={LOSS},
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=live_supports,
    )

    forced_internal = set(result.forced_goal_states) - {GOAL, DRAW, LOSS}
    safety_internal = set(result.safety_states) - {GOAL, DRAW, LOSS}
    internal_residuals = [
        residual
        for residual in result.residuals
        if residual.state.startswith("kpvk:")
    ]

    win_missing = expected_wins - forced_internal
    win_extra = forced_internal - expected_wins
    draw_missing_safety = expected_draws - safety_internal

    if win_missing or win_extra:
        raise AssertionError(
            f"calculus/Syzygy win mismatch missing={len(win_missing)} extra={len(win_extra)}"
        )
    if draw_missing_safety:
        raise AssertionError(
            f"draw states outside safety kernel: {len(draw_missing_safety)}"
        )
    if internal_residuals:
        raise AssertionError(
            f"unexpected internal calculus residuals: {len(internal_residuals)}"
        )

    # Causal capability ablation: remove the most-used compiled role support
    # and reclose the same calculus.
    ablated_role, ablated_direct = max(
        role_use.items(), key=lambda kv: (kv[1], kv[0])
    )
    ablated_supports = set(live_supports)
    ablated_supports.remove(f"capability:dtz-role:{ablated_role}")
    ablated = compile_strategy_calculus(
        states=states,
        goals={GOAL},
        forbidden={LOSS},
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=ablated_supports,
    )
    ablated_internal_residuals = [
        residual
        for residual in ablated.residuals
        if residual.state.startswith("kpvk:")
    ]
    lost_forced_wins = expected_wins - (
        set(ablated.forced_goal_states) - {GOAL, DRAW, LOSS}
    )

    ranks = result.rank_map
    internal_win_ranks = [ranks[state] for state in expected_wins]
    mode_counts = Counter(decision.mode for decision in result.decisions)

    evidence = {
        "schema": SCHEMA,
        "status": "WARRANTED_COMPLETE_KPVK_CAPABILITY_CALCULUS",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v6_authority": V6_AUTHORITY,
        "protected_interfaces": [PROTECTED_INTERFACE, "chess.syzygy.wdl-dtz.v1"],
        "authority": {
            "kind": "Syzygy WDL + DTZ",
            "tablebase_files": manifest,
        },
        "compiled_policy": {
            "tree": policy_summary,
            "role_frequency": role_frequency,
            "white_decision_states": len(white_indices),
            "capability_steps": len(steps),
            "distinct_capability_roles": len(role_use),
        },
        "calculus": {
            "result_id": result.id,
            "forced_goal_internal_states": len(forced_internal),
            "expected_syzygy_white_wins": len(expected_wins),
            "safety_internal_states": len(safety_internal),
            "expected_syzygy_white_draws": len(expected_draws),
            "internal_residuals": len(internal_residuals),
            "win_missing": len(win_missing),
            "win_extra": len(win_extra),
            "draw_missing_safety": len(draw_missing_safety),
            "max_forced_goal_rank": max(internal_win_ranks) if internal_win_ranks else 0,
            "decision_modes": dict(mode_counts),
            "direct_external_outcomes": dict(direct_external),
        },
        "ablation": {
            "removed_capability_role": ablated_role,
            "direct_states_using_removed_role": ablated_direct,
            "internal_residuals_after_reclosure": len(ablated_internal_residuals),
            "forced_win_states_lost_after_reclosure": len(lost_forced_wins),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the generic capability calculus exactly reconstructs the Syzygy White-win region on the complete declared canonical KPvK boundary",
                "every forced-goal decision has a strict finite rank decrease against all legal Black replies",
                "every exact Syzygy White-draw state lies in the greatest safety kernel",
                "there are zero unexplained internal residuals with all qualified capability supports live",
                "revoking one compiled capability support and reclosing exposes its direct and dependent consequence",
            ],
            "unknown": [
                "complete KPPvK calculus closure",
                "capability-basis sufficiency for general chess",
                "game-theoretic value of the standard initial chess position",
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
        "enumeration": enumeration,
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")

    print("CRYSTAL_CHESS_CAPABILITY_CALCULUS_V8=PASS")
    print(
        f"white_states={len(white_indices)} steps={len(steps)} roles={len(role_use)}"
    )
    print(
        f"wins calculus={len(forced_internal)} syzygy={len(expected_wins)} "
        f"draws_safe={len(expected_draws - draw_missing_safety)}/{len(expected_draws)} "
        f"residuals={len(internal_residuals)}"
    )
    print(
        f"max_goal_rank={max(internal_win_ranks) if internal_win_ranks else 0} "
        f"ablate={ablated_role} direct={ablated_direct} "
        f"residuals_after={len(ablated_internal_residuals)} "
        f"wins_lost={len(lost_forced_wins)}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
