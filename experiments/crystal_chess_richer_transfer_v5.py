#!/usr/bin/env python3
"""Crystal Chess V5: frozen KPvK capability -> exact richer KPPvK transfer.

No KPPvK labels enter acquisition.  A symbolic policy is learned only from the
complete exact KPvK boundary, frozen, and then applied prospectively to a
deterministic sample of legal KPPvK positions whose pawns are at most on rank 6
(so one-ply children need only KPPvK/KPvK WDL files, never promoted material).

Adapter: each of the two pawns is independently offered as the 'anchor' for the
single-pawn capability.  Horizontal reflection canonicalizes that anchor onto
files a-d using the already-qualified V0 symmetry.  A transfer succeeds only
when the frozen predicted role corresponds to a concrete legal move and that
move preserves the exact KPPvK Syzygy WDL.  For pawn roles, the move must be by
the nominated anchor pawn; king roles are anchor-independent.

This is a prospective cross-material transfer diagnostic, not a proof over all
KPPvK states.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    horizontal_square,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    move_role,
    optimal_roles,
    tree_summary,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-to-kppvk-transfer.v5"
V4_AUTHORITY = (
    "metalogiclabs/mathgraph@cb6c3d4a215b359e02fe802521cf2f9b5b39c3a5"
)


def make_kppvk(
    wk: int,
    bk: int,
    p1: int,
    p2: int,
    turn: bool,
) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(p1, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(p2, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def sample_kppvk(
    count: int,
    seed: int,
) -> list[tuple[int, int, int, int, bool]]:
    rng = random.Random(seed)
    # Rank indices 1..5 = chess ranks 2..6. One legal pawn push cannot promote.
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]
    seen: set[tuple[int, int, int, int, bool]] = set()
    out: list[tuple[int, int, int, int, bool]] = []
    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > count * 100:
            raise RuntimeError("could not construct requested legal KPPvK sample")
        p1, p2 = rng.sample(pawn_squares, 2)
        if p2 < p1:
            p1, p2 = p2, p1
        occupied = {p1, p2}
        wk = rng.randrange(64)
        if wk in occupied:
            continue
        bk = rng.randrange(64)
        if bk in occupied or bk == wk:
            continue
        turn = bool(rng.getrandbits(1))
        key = (wk, bk, p1, p2, turn)
        if key in seen:
            continue
        board = make_kppvk(wk, bk, p1, p2, turn)
        if not board.is_valid():
            continue
        seen.add(key)
        out.append(key)
    return out


def canonical_feature_row(
    wk: int,
    bk: int,
    anchor: int,
    turn: bool,
    feature_fns,
) -> tuple[tuple[int, ...], bool]:
    reflected = chess.square_file(anchor) >= 4
    if reflected:
        wk = horizontal_square(wk)
        bk = horizontal_square(bk)
        anchor = horizontal_square(anchor)
    return tuple(fn(wk, bk, anchor, turn) for fn in feature_fns), reflected


def reflect_role(role: str) -> str:
    if role.startswith("P:"):
        # KPvK contains only non-capturing pawn roles; df is zero.
        return role
    if not role.startswith("K:"):
        return role
    body = role.split(":", 1)[1]
    df_text, dr_text = body.split(",")
    df = int(df_text)
    dr = int(dr_text)
    return f"K:{-df:+d},{dr:+d}"


def role_is_optimal_for_anchor(
    predicted_role: str,
    anchor: int,
    optimal_moves: list[chess.Move],
    board: chess.Board,
) -> bool:
    for move in optimal_moves:
        if move_role(board, move) != predicted_role:
            continue
        piece = board.piece_at(move.from_square)
        if piece is None:
            continue
        if piece.piece_type == chess.PAWN and move.from_square != anchor:
            continue
        return True
    return False


def exact_optimal_moves(
    board: chess.Board,
    root_wdl: int,
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
) -> list[chess.Move]:
    scored: list[tuple[chess.Move, int]] = []
    best = -99
    for move in board.legal_moves:
        child = board.copy(stack=False)
        child.push(move)
        consequence = -probe_wdl(tablebase, child, cache)
        scored.append((move, consequence))
        best = max(best, consequence)
    if not scored:
        return []
    if best != root_wdl:
        raise AssertionError(
            f"KPPvK negamax mismatch root={root_wdl} best={best} fen={board.fen()}"
        )
    return [move for move, value in scored if value == root_wdl]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260928)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_to_kppvk_transfer_v5.json"),
    )
    args = parser.parse_args()
    started = time.time()

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in tb_files
    ]
    names = {p.name for p in tb_files}
    if "KPPvK.rtbw" not in names or "KPvK.rtbw" not in names:
        raise SystemExit(f"required KPPvK/KPvK WDL files missing: {sorted(names)}")

    bank = coordinate_feature_bank()
    feature_names = [name for name, _ in bank]
    feature_fns = [fn for _, fn in bank]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        # Acquire/freeze policy strictly from KPvK.
        records, enumeration = enumerate_records(tablebase, cache, feature_fns)
        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            roles = optimal_roles(board, rec.wdl, tablebase, cache)
            role_sets.append(roles)
            if roles:
                nonterminal.append(i)
        labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
        X = np.asarray([rec.features for rec in records], dtype=np.int16)
        policy = DecisionTreeClassifier(
            criterion="entropy",
            splitter="best",
            random_state=0,
        )
        policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
        # Freeze: all KPPvK work begins only after this point.
        policy_summary = tree_summary(policy)
        default_role = sorted(
            role_frequency.items(), key=lambda kv: (-kv[1], kv[0])
        )[0][0]

        sample = sample_kppvk(args.sample_size, args.seed)

        feature_rows: list[tuple[int, ...]] = []
        reflected_flags: list[bool] = []
        anchor_squares: list[int] = []
        state_for_candidate: list[int] = []
        for state_i, (wk, bk, p1, p2, turn) in enumerate(sample):
            for anchor in (p1, p2):
                row, reflected = canonical_feature_row(
                    wk, bk, anchor, turn, feature_fns
                )
                feature_rows.append(row)
                reflected_flags.append(reflected)
                anchor_squares.append(anchor)
                state_for_candidate.append(state_i)

        candidate_pred = [
            str(x)
            for x in policy.predict(
                np.asarray(feature_rows, dtype=np.int16)
            )
        ]
        candidate_roles = [
            reflect_role(role) if reflected else role
            for role, reflected in zip(candidate_pred, reflected_flags)
        ]
        default_roles = [
            reflect_role(default_role) if reflected else default_role
            for reflected in reflected_flags
        ]

        states_with_moves = 0
        tree_any_anchor_success = 0
        tree_first_anchor_success = 0
        default_any_anchor_success = 0
        exact_terminal = 0
        wdl_counts: Counter[int] = Counter()
        success_by_turn = {
            "white": [0, 0],
            "black": [0, 0],
        }
        failures: list[dict[str, object]] = []

        for state_i, (wk, bk, p1, p2, turn) in enumerate(sample):
            board = make_kppvk(wk, bk, p1, p2, turn)
            root_wdl = probe_wdl(tablebase, board, cache)
            wdl_counts[root_wdl] += 1
            optimal = exact_optimal_moves(board, root_wdl, tablebase, cache)
            if not optimal:
                exact_terminal += 1
                continue
            states_with_moves += 1

            offset = 2 * state_i
            tree_hits = []
            default_hits = []
            for j, anchor in enumerate((p1, p2)):
                tree_hits.append(
                    role_is_optimal_for_anchor(
                        candidate_roles[offset + j],
                        anchor,
                        optimal,
                        board,
                    )
                )
                default_hits.append(
                    role_is_optimal_for_anchor(
                        default_roles[offset + j],
                        anchor,
                        optimal,
                        board,
                    )
                )

            tree_ok = any(tree_hits)
            default_ok = any(default_hits)
            tree_any_anchor_success += int(tree_ok)
            tree_first_anchor_success += int(tree_hits[0])
            default_any_anchor_success += int(default_ok)
            bucket = "white" if turn else "black"
            success_by_turn[bucket][1] += 1
            success_by_turn[bucket][0] += int(tree_ok)

            if not tree_ok and len(failures) < 30:
                failures.append(
                    {
                        "fen": board.fen(),
                        "root_wdl": root_wdl,
                        "anchors": [chess.square_name(p1), chess.square_name(p2)],
                        "predicted_roles": candidate_roles[offset : offset + 2],
                        "optimal_moves": [move.uci() for move in optimal],
                        "optimal_move_roles": [
                            move_role(board, move) for move in optimal
                        ],
                    }
                )

    tree_ratio = (
        tree_any_anchor_success / states_with_moves if states_with_moves else 1.0
    )
    first_ratio = (
        tree_first_anchor_success / states_with_moves
        if states_with_moves
        else 1.0
    )
    default_ratio = (
        default_any_anchor_success / states_with_moves
        if states_with_moves
        else 1.0
    )
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_PROSPECTIVE_KPVK_TO_KPPVK_TRANSFER",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v4_authority": V4_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "acquisition_material": "KPvK only",
            "evaluation_material": "KPPvK only",
            "kppvk_labels_used_in_acquisition": 0,
            "adapter": "try each pawn as single-pawn capability anchor; canonicalize anchor by horizontal reflection",
            "sample_restriction": "both white pawns initially on ranks 2..6; no one-ply promotion children",
        },
        "authority": {
            "kind": "Syzygy WDL",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "kpvk_frozen_capability": {
            "states": len(records),
            "nonterminal_states": len(nonterminal),
            "role_frequency": role_frequency,
            "default_role": default_role,
            "tree": policy_summary,
            "feature_names": feature_names,
        },
        "kppvk_sample": {
            "seed": args.seed,
            "requested_states": args.sample_size,
            "sampled_states": len(sample),
            "nonterminal_states": states_with_moves,
            "terminal_states": exact_terminal,
            "wdl_distribution": {
                str(k): v for k, v in sorted(wdl_counts.items())
            },
        },
        "transfer": {
            "tree_any_anchor_success": tree_any_anchor_success,
            "tree_any_anchor_ratio": tree_ratio,
            "tree_first_anchor_success": tree_first_anchor_success,
            "tree_first_anchor_ratio": first_ratio,
            "default_role_any_anchor_success": default_any_anchor_success,
            "default_role_any_anchor_ratio": default_ratio,
            "absolute_gain_over_default": tree_ratio - default_ratio,
            "success_by_turn": {
                key: {
                    "success": value[0],
                    "states": value[1],
                    "ratio": value[0] / value[1] if value[1] else 1.0,
                }
                for key, value in success_by_turn.items()
            },
            "failure_examples": failures,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the KPvK policy is acquired without any KPPvK labels",
                "every reported KPPvK transfer success is independently checked against exact Syzygy WDL",
                "the transfer ratio is valid only for the deterministic declared sample/restriction",
            ],
            "unknown": [
                "complete KPPvK coverage",
                "transfer to arbitrary richer material",
                "general chess solution",
            ],
        },
        "cache": {
            "unique_wdl_positions_probed_or_certified": len(cache)
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
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_RICHER_TRANSFER_V5=PASS")
    print(
        f"kppvk nonterminal={states_with_moves} "
        f"tree_any={tree_any_anchor_success} ratio={tree_ratio:.6f}"
    )
    print(
        f"tree_first={tree_first_anchor_success} ratio={first_ratio:.6f} "
        f"default_any={default_any_anchor_success} ratio={default_ratio:.6f} "
        f"gain={tree_ratio-default_ratio:.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
