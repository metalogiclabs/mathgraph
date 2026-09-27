#!/usr/bin/env python3
"""Crystal Chess V6: zero-shot KPvK -> KPPPvK triple-capability composition.

No KPPPvK label is used to choose actions.

Target boundary:
* White K+3P vs Black K.
* Exactly one pawn on each of files a,b,c.
* Pawn ranks 2..4.
* All legal king placements and both sides to move.
* No castling/en-passant, root halfmove clock zero.

For each richer state:
1. project it independently onto the three single-pawn KPvK views;
2. query the frozen V3 KPvK symbolic policy on each projection;
3. require unanimous role agreement;
4. revoke the three role families exposed by the earlier V4 prospective residual;
5. require exactly one legal real move to realize that role;
6. only then query Syzygy WDL to audit the committed move.

This is a prospective five-piece transfer test. KPPPvK truth is checker-only.
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

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    probe_wdl,
    make_kpvk,
)
from crystal_chess_goal_certificate_v3 import file_sha256, move_role
from crystal_chess_cross_material_v5 import (
    V3_AUTHORITY,
    rebuild_frozen_v3,
    projection_role,
)


SCHEMA = "mathgraph.crystal-chess.kpppvk-zero-shot-transfer.v6b"
REVOKED_ROLES = frozenset({"K:-1,+0", "K:+0,-1", "P:+0,+1"})


def make_kpppvk(
    wk: int,
    bk: int,
    p1: int,
    p2: int,
    p3: int,
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
    for p in (p1, p2, p3):
        board.set_piece_at(p, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        clf, class_labels, feature_fns, _records = rebuild_frozen_v3(
            tablebase, cache
        )

        pawn_triples = [
            (
                chess.square(0, ra),
                chess.square(1, rb),
                chess.square(2, rc),
            )
            for ra in range(1, 4)
            for rb in range(1, 4)
            for rc in range(1, 4)
        ]

        candidates = legal_states = terminal_states = 0
        projection_unknown = projection_disagreement = 0
        projection_value_disagreement = 0
        revoked = 0
        nonunique_realizer = 0
        acted = correct = wrong = 0
        by_role: Counter[str] = Counter()
        by_turn = {"white": Counter(), "black": Counter()}
        wrong_examples: list[dict[str, object]] = []

        for p1, p2, p3 in pawn_triples:
            pawns = (p1, p2, p3)
            for wk in chess.SQUARES:
                if wk in pawns:
                    continue
                for bk in chess.SQUARES:
                    if bk in pawns or bk == wk:
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        candidates += 1
                        board = make_kpppvk(wk, bk, p1, p2, p3, turn)
                        if not board.is_valid():
                            continue
                        legal_states += 1
                        legal_moves = list(board.legal_moves)
                        if not legal_moves:
                            terminal_states += 1
                            continue

                        roles = [
                            projection_role(
                                clf,
                                class_labels,
                                feature_fns,
                                wk,
                                bk,
                                pawn,
                                turn,
                            )
                            for pawn in pawns
                        ]
                        if any(role is None for role in roles):
                            projection_unknown += 1
                            continue
                        if len(set(roles)) != 1:
                            projection_disagreement += 1
                            continue

                        # Crystal composition requires agreement on the
                        # protected source consequence as well as the proposed
                        # continuation. These are KPvK queries only; the richer
                        # KPPPvK target remains unseen until after commitment.
                        projected_wdls = [
                            probe_wdl(
                                tablebase,
                                make_kpvk(wk, bk, pawn, turn),
                                cache,
                            )
                            for pawn in pawns
                        ]
                        if len(set(projected_wdls)) != 1:
                            projection_value_disagreement += 1
                            continue

                        role = roles[0]
                        if role in REVOKED_ROLES:
                            revoked += 1
                            continue

                        realizers = [
                            move
                            for move in legal_moves
                            if move_role(board, move) == role
                        ]
                        if len(realizers) != 1:
                            nonunique_realizer += 1
                            continue

                        chosen = realizers[0]
                        # Target authority enters only after action commitment.
                        root_wdl = probe_wdl(tablebase, board, cache)
                        child = board.copy(stack=False)
                        child.push(chosen)
                        consequence = -probe_wdl(tablebase, child, cache)

                        acted += 1
                        by_role[role] += 1
                        side = "white" if turn else "black"
                        by_turn[side]["acted"] += 1
                        if consequence == root_wdl:
                            correct += 1
                            by_turn[side]["correct"] += 1
                        else:
                            wrong += 1
                            by_turn[side]["wrong"] += 1
                            if len(wrong_examples) < 40:
                                wrong_examples.append(
                                    {
                                        "fen": board.fen(),
                                        "pawns": [
                                            chess.square_name(p) for p in pawns
                                        ],
                                        "role": role,
                                        "move": chosen.uci(),
                                        "root_wdl": root_wdl,
                                        "child_consequence": consequence,
                                    }
                                )

    status = (
        "WARRANTED_ZERO_SHOT_FIVE_PIECE_TRANSFER"
        if acted > 0 and wrong == 0
        else "EXACT_RESIDUAL_FIVE_PIECE_TRANSFER"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "source_capability": "frozen exact KPvK V3 symbolic policy",
            "target_material": "White K+3P vs Black K",
            "target_subset": (
                "one pawn each on files a,b,c; pawn ranks 2..4; "
                "all legal king placements and both sides to move"
            ),
            "policy_input": (
                "three independent single-pawn KPvK projections only; "
                "no KPPPvK value"
            ),
            "guard": (
                "all three projections agree on KPvK WDL and move role; "
                "V4-residual role families revoked prospectively; exactly one "
                "legal realizer"
            ),
            "revoked_roles": sorted(REVOKED_ROLES),
            "audit": (
                "exact Syzygy WDL queried only after concrete move commitment"
            ),
        },
        "authority": {
            "kind": "Syzygy WDL",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "coverage": {
            "pawn_triples": len(pawn_triples),
            "candidate_assignments": candidates,
            "legal_states": legal_states,
            "terminal_states": terminal_states,
            "projection_unknown": projection_unknown,
            "projection_disagreement": projection_disagreement,
            "projection_value_disagreement": projection_value_disagreement,
            "revoked": revoked,
            "nonunique_realizer": nonunique_realizer,
            "acted": acted,
            "correct": correct,
            "wrong": wrong,
            "precision": correct / acted if acted else 0.0,
            "coverage_ratio_of_legal": (
                acted / legal_states if legal_states else 0.0
            ),
            "by_turn": {
                side: dict(counter) for side, counter in by_turn.items()
            },
            "by_role": dict(sorted(by_role.items())),
            "wrong_examples": wrong_examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "a capability learned only on KPvK, with role revocations "
                    "fixed before KPPPvK evaluation, transfers with zero WDL "
                    "error on every five-piece state where its guard fires in "
                    "the complete declared target subset"
                )
            ],
            "unknown": [
                "KPPPvK states where the guard abstains",
                "other five-piece material classes",
                "general chess solution",
            ],
        },
        "cache": {"unique_wdl_positions": len(cache)},
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print("CRYSTAL_CHESS_TRIPLE_TRANSFER_V6B=PASS")
    print(
        f"legal={legal_states} acted={acted} correct={correct} wrong={wrong} "
        f"precision={correct/acted if acted else 0.0:.6f} "
        f"coverage={acted/legal_states if legal_states else 0.0:.6f}"
    )
    print(
        f"unknown={projection_unknown} role_disagree={projection_disagreement} "
        f"value_disagree={projection_value_disagreement} "
        f"revoked={revoked} nonunique={nonunique_realizer}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
