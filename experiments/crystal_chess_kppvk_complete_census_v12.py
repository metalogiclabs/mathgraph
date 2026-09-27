#!/usr/bin/env python3
"""Crystal Chess V12: complete KPPvK portfolio census on a no-promotion boundary.

Boundary:
* White K+2P vs Black K.
* Both pawns are on ranks 2..6 at the root.
* No castling/en-passant; halfmove clock 0.
* Every legal root state in this finite boundary is enumerated exactly.
* The KPvK symbolic policy is frozen before KPPvK evaluation.
* For each pawn, instantiate the frozen single-pawn constructor once.
* A state is covered iff at least one generated concrete legal move preserves
  the exact root Syzygy WDL.

Because roots exclude rank-7 pawns, one-ply white pawn moves cannot promote.
Black king captures reduce to KPvK. Thus KPPvK + KPvK WDL (plus KPvK
promotion dependencies for acquisition) form a complete one-ply verifier
boundary.

This is an exact census of portfolio coverage, not a standalone selector.
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

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    optimal_roles,
    tree_summary,
)
from crystal_chess_richer_transfer_v5 import (
    make_kppvk,
    canonical_feature_row,
    reflect_role,
)


SCHEMA = "mathgraph.crystal-chess.kppvk-complete-census.v12"
V5_AUTHORITY = (
    "metalogiclabs/mathgraph@0b8da1aee8ffecfb351c0211dc8513631fd106cd"
)


def parse_role_move(board: chess.Board, anchor: int, role: str) -> chess.Move | None:
    try:
        tag, body = role.split(":", 1)
        df_text, dr_text = body.split(",", 1)
        promotion = None
        if "=" in dr_text:
            dr_text, promo_text = dr_text.split("=", 1)
            promotion = {
                "Q": chess.QUEEN,
                "R": chess.ROOK,
                "B": chess.BISHOP,
                "N": chess.KNIGHT,
            }.get(promo_text)
        df = int(df_text)
        dr = int(dr_text)
    except Exception:
        return None

    source = board.king(chess.WHITE) if tag == "K" else anchor if tag == "P" else None
    if source is None:
        return None
    f = chess.square_file(source) + df
    r = chess.square_rank(source) + dr
    if not (0 <= f < 8 and 0 <= r < 8):
        return None
    move = chess.Move(source, chess.square(f, r), promotion=promotion)
    return move if board.is_legal(move) else None


def exact_wdl(tb: chess.syzygy.Tablebase, board: chess.Board) -> int:
    if board.is_checkmate():
        return -2
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return int(tb.probe_wdl(board))


def acquire_policy(tb, feature_fns):
    cache = {}
    records, enumeration = enumerate_records(tb, cache, feature_fns)
    role_sets = []
    nonterminal = []
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        roles = optimal_roles(board, rec.wdl, tb, cache)
        role_sets.append(roles)
        if roles:
            nonterminal.append(i)
    labels, frequency = choose_preferred_roles(role_sets, nonterminal)
    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    policy = DecisionTreeClassifier(
        criterion="entropy", splitter="best", random_state=0
    )
    policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
    return policy, frequency, enumeration, len(nonterminal)


def precompute_roles(policy, feature_fns, pawn_squares):
    keys = []
    rows = []
    refls = []
    for anchor in pawn_squares:
        for wk in chess.SQUARES:
            for bk in chess.SQUARES:
                for turn in (False, True):
                    row, refl = canonical_feature_row(
                        wk, bk, anchor, turn, feature_fns
                    )
                    keys.append((wk, bk, anchor, int(turn)))
                    rows.append(row)
                    refls.append(refl)
    pred = [str(x) for x in policy.predict(np.asarray(rows, dtype=np.int16))]
    out = {}
    for key, role, refl in zip(keys, pred, refls):
        out[key] = reflect_role(role) if refl else role
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kppvk_complete_census_v12.json"),
    )
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtbw"))
    names = {p.name for p in files}
    for req in ("KPvK.rtbw", "KPPvK.rtbw"):
        if req not in names:
            raise SystemExit(f"missing {req}")
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)  # ranks 2..6
    ]

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, kpvk_enum, kpvk_nonterminal = acquire_policy(
            tb, feature_fns
        )
        policy_summary = tree_summary(policy)
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        candidate_assignments = 0
        legal_states = 0
        terminal_states = 0
        any_success = 0
        first_success = 0
        wdl_counts = Counter()
        failure_by_turn = Counter()
        failures = []
        candidate_probe_count = 0

        for p0_i, p0 in enumerate(pawn_squares):
            for p1 in pawn_squares[p0_i + 1 :]:
                for wk in chess.SQUARES:
                    if wk == p0 or wk == p1:
                        continue
                    for bk in chess.SQUARES:
                        if bk in (p0, p1, wk):
                            continue
                        for turn in (False, True):
                            candidate_assignments += 1
                            board = make_kppvk(wk, bk, p0, p1, turn)
                            if not board.is_valid():
                                continue
                            legal_states += 1
                            root = exact_wdl(tb, board)
                            wdl_counts[root] += 1

                            roles = (
                                role_map[(wk, bk, p0, int(turn))],
                                role_map[(wk, bk, p1, int(turn))],
                            )
                            moves = []
                            for anchor, role in ((p0, roles[0]), (p1, roles[1])):
                                move = parse_role_move(board, anchor, role)
                                if move is not None and move not in moves:
                                    moves.append(move)

                            hits = []
                            for move in moves:
                                candidate_probe_count += 1
                                board.push(move)
                                consequence = -exact_wdl(tb, board)
                                board.pop()
                                hits.append((move, consequence == root))

                            # Map first anchor separately, even if same concrete king move.
                            first_move = parse_role_move(board, p0, roles[0])
                            first_ok = False
                            if first_move is not None:
                                for move, ok in hits:
                                    if move == first_move:
                                        first_ok = ok
                                        break

                            ok = any(flag for _move, flag in hits)
                            if ok:
                                any_success += 1
                                first_success += int(first_ok)
                                continue

                            # Distinguish actual residual from terminal states.
                            if not any(board.legal_moves):
                                terminal_states += 1
                                continue

                            failure_by_turn["white" if turn else "black"] += 1
                            if len(failures) < 100:
                                failures.append(
                                    {
                                        "fen": board.fen(),
                                        "root_wdl": root,
                                        "roles": list(roles),
                                        "candidate_moves": [m.uci() for m, _ok in hits],
                                    }
                                )

        nonterminal = legal_states - terminal_states
        residual = nonterminal - any_success
        ratio = any_success / nonterminal if nonterminal else 1.0
        first_ratio = first_success / nonterminal if nonterminal else 1.0

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_COMPLETE_RESTRICTED_KPPVK_PORTFOLIO_CENSUS",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v5_authority": V5_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "boundary": {
            "material": "KPPvK",
            "white_pawn_root_ranks": [2, 3, 4, 5, 6],
            "castling": False,
            "en_passant": False,
            "root_halfmove_clock": 0,
            "coverage": "complete enumeration of every legal state satisfying boundary",
        },
        "authority": {"kind": "Syzygy WDL", "tablebase_files": manifest},
        "frozen_capability": {
            "kpvk_nonterminal_states": kpvk_nonterminal,
            "role_frequency": frequency,
            "tree": policy_summary,
            "precomputed_contexts": len(role_map),
        },
        "census": {
            "candidate_assignments": candidate_assignments,
            "legal_states": legal_states,
            "terminal_states": terminal_states,
            "nonterminal_states": nonterminal,
            "portfolio_success": any_success,
            "portfolio_ratio": ratio,
            "first_anchor_success": first_success,
            "first_anchor_ratio": first_ratio,
            "residual_states": residual,
            "candidate_child_probes": candidate_probe_count,
            "wdl_distribution": {
                str(k): v for k, v in sorted(wdl_counts.items())
            },
            "failure_by_turn": dict(failure_by_turn),
            "failure_examples": failures,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "every legal KPPvK root with both pawns on ranks 2..6 is enumerated exactly",
                "KPvK policy is frozen before KPPvK evaluation",
                "portfolio success means at least one generated concrete legal move preserves exact root Syzygy WDL",
                "reported residual is the complete all-generated-candidates-fail set on this boundary",
            ],
            "unknown": [
                "rank-7 KPPvK roots requiring promotion dependencies",
                "certified selector/guard for portfolio sufficiency",
                "general chess solution",
            ],
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
    print("CRYSTAL_CHESS_KPPVK_COMPLETE_CENSUS_V12=PASS")
    print(
        f"legal={legal_states} nonterminal={nonterminal} terminal={terminal_states} "
        f"portfolio={any_success} ratio={ratio:.8f}"
    )
    print(
        f"first={first_success} ratio={first_ratio:.8f} residual={residual} "
        f"candidate_probes={candidate_probe_count}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
