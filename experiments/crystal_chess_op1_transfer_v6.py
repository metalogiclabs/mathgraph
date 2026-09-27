#!/usr/bin/env python3
"""Crystal Chess V6: prospective KPvK -> exact Op1 8-piece action transfer.

Frozen source capability:
  child_terminal, to_pawn_file_distance, to_center_ring,
  mover_type, to_pawn_rank_distance

This five-coordinate action schema was learned on KPvK and independently held
out there with zero consequence conflict / zero minimax mismatch.

To move from one pawn to six pawns we must adapt the distinguished "pawn"
coordinate.  Candidate anchor maps are entirely label-free.  We select the
anchor on the first 64 exact Op1 positions, freeze it, and audit the final 64
positions untouched.  If direct transfer is not exact, Crystal may add generic
move observables using discovery labels only; those additions are then frozen
and prospectively checked on the held-out 64.

Authority: Lichess exact /standard tablebase API on the same deterministic Op1
K+3P v K+3P generator used by the qualified V1 action census.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Callable

import chess

from crystal_chess_op1_action_census_v1 import (
    ENDPOINT,
    SEED,
    make_candidate,
    normalized_wdl,
    probe,
)


SCHEMA = "mathgraph.crystal-chess.op1-transfer.v6"
SOURCE_AUTHORITY = (
    "metalogiclabs/mathgraph@e8ab96412c88b8175e7116081c4cae8276a890d1"
)
OP1_CENSUS_AUTHORITY = (
    "metalogiclabs/mathgraph@97dcb2100826879f842dc15ede2b55dc6ca30801"
)
SOURCE_FEATURES = (
    "child_terminal",
    "to_anchor_file_distance",
    "to_center_ring",
    "mover_type",
    "to_anchor_rank_distance",
)


@dataclass(frozen=True)
class Action:
    state_id: int
    root_wdl: int
    uci: str
    consequence: int
    features: tuple[int, ...]


def cheb(a: int, b: int) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def edge_distance(square: int) -> int:
    f = chess.square_file(square)
    r = chess.square_rank(square)
    return min(f, 7 - f, r, 7 - r)


def center_ring(square: int) -> int:
    return (
        min(abs(chess.square_file(square) - 3), abs(chess.square_file(square) - 4))
        + min(abs(chess.square_rank(square) - 3), abs(chess.square_rank(square) - 4))
    )


def terminal_code(board: chess.Board) -> int:
    if board.is_checkmate():
        return 3
    if board.is_stalemate():
        return 2
    if board.is_insufficient_material():
        return 1
    return 0


def progress(square: int, color: bool) -> int:
    rank = chess.square_rank(square)
    return rank if color == chess.WHITE else 7 - rank


def pawn_squares(board: chess.Board, color: bool | None = None) -> list[int]:
    if color is None:
        return sorted(
            list(board.pieces(chess.PAWN, chess.WHITE))
            + list(board.pieces(chess.PAWN, chess.BLACK))
        )
    return sorted(board.pieces(chess.PAWN, color))


def choose_by_distance(
    squares: list[int],
    reference: int,
    *,
    reverse: bool = False,
) -> int:
    if not squares:
        raise AssertionError("anchor candidate has no pawns")
    key = lambda sq: (cheb(sq, reference), sq)
    return (max if reverse else min)(squares, key=key)


def anchor_square(board: chess.Board, move: chess.Move, mode: str) -> int:
    mover = board.piece_at(move.from_square)
    if mover is None:
        raise AssertionError("missing mover")
    friendly = pawn_squares(board, mover.color)
    enemy = pawn_squares(board, not mover.color)
    allp = sorted(friendly + enemy)
    if mode == "nearest_any_to_dest":
        return choose_by_distance(allp, move.to_square)
    if mode == "nearest_friendly_to_dest":
        return choose_by_distance(friendly, move.to_square)
    if mode == "nearest_enemy_to_dest":
        return choose_by_distance(enemy, move.to_square)
    if mode == "nearest_any_to_source":
        return choose_by_distance(allp, move.from_square)
    if mode == "nearest_friendly_to_source":
        return choose_by_distance(friendly, move.from_square)
    if mode == "nearest_enemy_to_source":
        return choose_by_distance(enemy, move.from_square)
    if mode == "most_advanced_friendly":
        return min(friendly, key=lambda sq: (-progress(sq, mover.color), sq))
    if mode == "least_advanced_friendly":
        return min(friendly, key=lambda sq: (progress(sq, mover.color), sq))
    if mode == "most_advanced_enemy":
        return min(enemy, key=lambda sq: (-progress(sq, not mover.color), sq))
    if mode == "least_advanced_enemy":
        return min(enemy, key=lambda sq: (progress(sq, not mover.color), sq))
    raise ValueError(mode)


ANCHOR_MODES = (
    "nearest_any_to_dest",
    "nearest_friendly_to_dest",
    "nearest_enemy_to_dest",
    "nearest_any_to_source",
    "nearest_friendly_to_source",
    "nearest_enemy_to_source",
    "most_advanced_friendly",
    "least_advanced_friendly",
    "most_advanced_enemy",
    "least_advanced_enemy",
)


def generic_features(board: chess.Board, move: chess.Move, anchor_mode: str) -> dict[str, int]:
    mover = board.piece_at(move.from_square)
    if mover is None:
        raise AssertionError("missing mover")
    captured = board.piece_at(move.to_square)
    anchor = anchor_square(board, move, anchor_mode)
    other_king = board.king(not mover.color)
    if other_king is None:
        raise AssertionError("missing other king")

    friendly = pawn_squares(board, mover.color)
    enemy = pawn_squares(board, not mover.color)
    child = board.copy(stack=False)
    child.push(move)

    dx = chess.square_file(move.to_square) - chess.square_file(move.from_square)
    dy = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    forward_dy = dy if mover.color == chess.WHITE else -dy

    return {
        "child_terminal": terminal_code(child),
        "to_anchor_file_distance": abs(
            chess.square_file(move.to_square) - chess.square_file(anchor)
        ),
        "to_center_ring": center_ring(move.to_square),
        "mover_type": mover.piece_type,
        "to_anchor_rank_distance": abs(
            chess.square_rank(move.to_square) - chess.square_rank(anchor)
        ),
        # Generic residual bank; none requires game-theoretic labels.
        "is_capture": int(captured is not None),
        "captured_type": captured.piece_type if captured else 0,
        "child_gives_check": int(child.is_check()),
        "move_file_distance": abs(dx),
        "move_forward_delta": forward_dy,
        "to_edge_distance": edge_distance(move.to_square),
        "to_other_king_cheb": cheb(move.to_square, other_king),
        "other_king_distance_change": (
            cheb(move.to_square, other_king) - cheb(move.from_square, other_king)
        ),
        "to_nearest_friendly_pawn_cheb": min(
            cheb(move.to_square, sq) for sq in friendly
        ),
        "to_nearest_enemy_pawn_cheb": min(
            cheb(move.to_square, sq) for sq in enemy
        ),
        "from_nearest_friendly_pawn_cheb": min(
            cheb(move.from_square, sq) for sq in friendly
        ),
        "from_nearest_enemy_pawn_cheb": min(
            cheb(move.from_square, sq) for sq in enemy
        ),
        "anchor_same_color": int(
            board.color_at(anchor) == mover.color
        ),
        "anchor_progress": progress(
            anchor, bool(board.color_at(anchor))
        ),
        "friendly_pawn_count": len(friendly),
        "enemy_pawn_count": len(enemy),
    }


def collect_exact(target: int, max_attempts: int) -> tuple[list[dict], dict[str, int]]:
    import random
    import urllib.error

    rng = random.Random(SEED)
    seen: set[str] = set()
    accepted: list[dict] = []
    stats = Counter()

    for _ in range(max_attempts):
        if len(accepted) >= target:
            break
        board = make_candidate(rng)
        stats["generated"] += 1
        if not board.is_valid():
            stats["invalid"] += 1
            continue
        fen = board.fen(en_passant="fen")
        key = " ".join(fen.split()[:4])
        if key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(key)
        try:
            data = probe(fen)
        except urllib.error.HTTPError as exc:
            stats[f"http_{exc.code}"] += 1
            continue
        except Exception:
            stats["request_error"] += 1
            continue
        stats["responses"] += 1

        root = normalized_wdl(str(data.get("category")))
        moves = data.get("moves")
        if root is None or not isinstance(moves, list) or not moves:
            stats["root_unknown_or_terminal"] += 1
            continue

        parsed = []
        bad = False
        consequences = []
        for item in moves:
            child = normalized_wdl(str(item.get("category")))
            uci = item.get("uci")
            if child is None or not isinstance(uci, str):
                bad = True
                break
            consequence = -child
            parsed.append((uci, consequence))
            consequences.append(consequence)
        if bad:
            stats["move_unknown"] += 1
            continue
        if max(consequences) != root:
            stats["minimax_mismatch"] += 1
            continue

        accepted.append({"fen": fen, "root_wdl": root, "moves": parsed})
        stats["accepted"] += 1
        time.sleep(0.06)

    return accepted, dict(stats)


def make_actions(states: list[dict], anchor_mode: str) -> tuple[list[Action], list[str]]:
    names: list[str] | None = None
    out: list[Action] = []
    for sid, row in enumerate(states):
        board = chess.Board(row["fen"])
        for uci, consequence in row["moves"]:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise AssertionError(f"API move not legal locally: {uci} {row['fen']}")
            feat = generic_features(board, move, anchor_mode)
            if names is None:
                names = list(feat)
            elif names != list(feat):
                raise AssertionError("feature order drift")
            out.append(
                Action(
                    state_id=sid,
                    root_wdl=int(row["root_wdl"]),
                    uci=uci,
                    consequence=int(consequence),
                    features=tuple(int(feat[n]) for n in names),
                )
            )
    if names is None:
        raise AssertionError("no actions")
    return out, names


def evaluate(actions: list[Action], selected: tuple[int, ...]) -> dict[str, object]:
    per_state: dict[int, list[Action]] = defaultdict(list)
    for action in actions:
        per_state[action.state_id].append(action)

    raw = len(actions)
    schema_classes = 0
    oracle_classes = 0
    conflict_mass = 0
    impure_groups = 0
    impure_states = 0
    minimax_mismatches = 0
    examples = []

    for sid, state_actions in per_state.items():
        oracle_classes += len({a.consequence for a in state_actions})
        groups: dict[tuple[int, ...], list[Action]] = defaultdict(list)
        for action in state_actions:
            groups[tuple(action.features[i] for i in selected)].append(action)
        schema_classes += len(groups)
        state_impure = False
        reps = []
        for key, group in groups.items():
            labels = Counter(a.consequence for a in group)
            conflict_mass += len(group) - max(labels.values())
            if len(labels) > 1:
                impure_groups += 1
                state_impure = True
                if len(examples) < 12:
                    examples.append({
                        "state_id": sid,
                        "key": list(key),
                        "moves": sorted((a.uci, a.consequence) for a in group),
                    })
            reps.append(min(group, key=lambda a: a.uci))
        impure_states += int(state_impure)
        if max(a.consequence for a in reps) != state_actions[0].root_wdl:
            minimax_mismatches += 1

    return {
        "states": len(per_state),
        "raw_moves": raw,
        "oracle_action_classes": oracle_classes,
        "schema_action_classes": schema_classes,
        "schema_compression": raw / schema_classes,
        "oracle_compression": raw / oracle_classes,
        "overfragmentation_vs_oracle": schema_classes / oracle_classes,
        "conflict_mass": conflict_mass,
        "impure_groups": impure_groups,
        "impure_states": impure_states,
        "minimax_mismatches": minimax_mismatches,
        "examples": examples,
    }


def greedy_repair(
    actions: list[Action],
    names: list[str],
    source_selected: tuple[int, ...],
) -> tuple[tuple[int, ...], list[dict[str, object]]]:
    selected = source_selected
    remaining = [i for i in range(len(names)) if i not in selected]
    trace = []
    current = evaluate(actions, selected)
    trace.append({"feature": "<source>", **{k:v for k,v in current.items() if k!="examples"}})

    while current["conflict_mass"] or current["minimax_mismatches"]:
        best = None
        best_eval = None
        best_idx = None
        for idx in remaining:
            trial = selected + (idx,)
            ev = evaluate(actions, trial)
            score = (
                ev["conflict_mass"],
                ev["minimax_mismatches"],
                ev["schema_action_classes"],
                names[idx],
            )
            if best is None or score < best:
                best = score
                best_eval = ev
                best_idx = idx
        current_score = (
            current["conflict_mass"],
            current["minimax_mismatches"],
            current["schema_action_classes"],
            "",
        )
        if best is None or best[:3] >= current_score[:3]:
            break
        selected = selected + (int(best_idx),)
        remaining.remove(int(best_idx))
        current = best_eval
        trace.append({
            "feature": names[int(best_idx)],
            **{k:v for k,v in current.items() if k!="examples"},
        })
    return selected, trace


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=128)
    ap.add_argument("--max-attempts", type=int, default=1200)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    states, collection = collect_exact(args.target, args.max_attempts)
    if len(states) != args.target:
        raise AssertionError(f"only collected {len(states)}/{args.target} exact states")
    split = len(states) // 2
    discovery_states = states[:split]
    test_states = states[split:]

    adapter_results = {}
    best = None
    best_mode = None
    best_actions = None
    best_names = None
    for mode in ANCHOR_MODES:
        actions, names = make_actions(discovery_states, mode)
        selected = tuple(names.index(name) for name in SOURCE_FEATURES)
        ev = evaluate(actions, selected)
        adapter_results[mode] = {k:v for k,v in ev.items() if k!="examples"}
        score = (
            ev["minimax_mismatches"],
            ev["conflict_mass"],
            ev["schema_action_classes"],
            mode,
        )
        if best is None or score < best:
            best = score
            best_mode = mode
            best_actions = actions
            best_names = names

    assert best_mode is not None and best_actions is not None and best_names is not None
    source_selected = tuple(best_names.index(name) for name in SOURCE_FEATURES)
    direct_discovery = evaluate(best_actions, source_selected)
    test_actions, test_names = make_actions(test_states, best_mode)
    if test_names != best_names:
        raise AssertionError("discovery/test feature drift")
    direct_test = evaluate(test_actions, source_selected)

    repaired_selected, repair_trace = greedy_repair(
        best_actions, best_names, source_selected
    )
    repaired_discovery = evaluate(best_actions, repaired_selected)
    repaired_test = evaluate(test_actions, repaired_selected)

    if (
        direct_test["conflict_mass"] == 0
        and direct_test["minimax_mismatches"] == 0
    ):
        status = "WARRANTED_HELDOUT_OP1_DIRECT_TRANSFER"
    elif (
        repaired_discovery["conflict_mass"] == 0
        and repaired_discovery["minimax_mismatches"] == 0
        and repaired_test["conflict_mass"] == 0
        and repaired_test["minimax_mismatches"] == 0
    ):
        status = "WARRANTED_HELDOUT_OP1_RESIDUAL_REPAIR"
    else:
        status = "UNKNOWN_CROSS_MATERIAL_RESIDUAL"

    result = {
        "schema": SCHEMA,
        "status": status,
        "lineage": {
            "source_action_congruence": SOURCE_AUTHORITY,
            "op1_oracle_census": OP1_CENSUS_AUTHORITY,
        },
        "authority": {
            "endpoint": ENDPOINT,
            "protected_semantics": "exact normalized 5-valued Syzygy WDL categories",
        },
        "generator": {
            "seed": SEED,
            "material": "KPPP v KPPP",
            "opposed_pawn_pairs": 3,
            "accepted": len(states),
            "discovery": len(discovery_states),
            "heldout_test": len(test_states),
            "collection_stats": collection,
        },
        "source_capability": {
            "features": list(SOURCE_FEATURES),
            "adapter_candidates": list(ANCHOR_MODES),
            "discovery_adapter_results": adapter_results,
            "selected_adapter": best_mode,
            "direct_discovery": {k:v for k,v in direct_discovery.items() if k!="examples"},
            "direct_heldout_test": direct_test,
        },
        "residual_repair": {
            "selected_features": [best_names[i] for i in repaired_selected],
            "new_features": [
                best_names[i] for i in repaired_selected if i not in source_selected
            ],
            "trace": repair_trace,
            "discovery": {k:v for k,v in repaired_discovery.items() if k!="examples"},
            "heldout_test": repaired_test,
        },
        "epistemic_boundary": {
            "warranted_if_green": (
                "the frozen KPvK-derived action schema, possibly plus the listed "
                "discovery-only residual features, preserves exact action "
                "consequence purity and minimax value on the untouched Op1 half"
            ),
            "unknown": [
                "transfer beyond this deterministic exact 8-piece sample",
                "general chess solution",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")

    print(f"CRYSTAL_CHESS_OP1_TRANSFER_V6={status}")
    print(f"adapter={best_mode}")
    print(
        "direct_test "
        f"moves={direct_test['raw_moves']} "
        f"classes={direct_test['schema_action_classes']} "
        f"compression={direct_test['schema_compression']:.3f}x "
        f"conflict={direct_test['conflict_mass']} "
        f"mm={direct_test['minimax_mismatches']}"
    )
    print("repair_features=" + ",".join(result["residual_repair"]["new_features"]))
    print(
        "repaired_test "
        f"classes={repaired_test['schema_action_classes']} "
        f"compression={repaired_test['schema_compression']:.3f}x "
        f"conflict={repaired_test['conflict_mass']} "
        f"mm={repaired_test['minimax_mismatches']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
