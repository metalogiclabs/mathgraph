#!/usr/bin/env python3
"""Crystal Chess V7: residual-derived connected-front interaction law.

Acquisition source:
V6B's untouched a-b-c KPPPvK boundary exposed a compact interaction residual:
its observed failures occur when at least two adjacent white pawns occupy the
same rank, so independent single-pawn continuations are not safely composable.

Prospective target:
* White K+3P vs Black K.
* Exactly one pawn on each of files b,c,d (disjoint from V6/V6B a,b,c target).
* Pawn ranks 2..4.
* All legal king placements and both sides to move.

Policy inputs remain source-side only:
1. frozen V3 KPvK policy on each pawn projection;
2. exact KPvK WDL on each projection;
3. V4-derived role revocations;
4. V6B-derived connected-front interaction guard.

KPPPvK WDL is queried only after a concrete move is committed.
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
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import file_sha256, move_role
from crystal_chess_cross_material_v5 import (
    V3_AUTHORITY,
    rebuild_frozen_v3,
    projection_role,
)
from crystal_chess_triple_transfer_v6 import REVOKED_ROLES, make_kpppvk


SCHEMA = "mathgraph.crystal-chess.connected-front-transfer.v7"
V6B_AUTHORITY = (
    "metalogiclabs/mathgraph@c08535a0b0a814efa315e35b43bb67ae9842568f"
)


def connected_front(pawns: tuple[int, int, int]) -> bool:
    for i in range(len(pawns)):
        for j in range(i + 1, len(pawns)):
            if (
                abs(chess.square_file(pawns[i]) - chess.square_file(pawns[j])) == 1
                and chess.square_rank(pawns[i]) == chess.square_rank(pawns[j])
            ):
                return True
    return False


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
                chess.square(1, rb),
                chess.square(2, rc),
                chess.square(3, rd),
            )
            for rb in range(1, 4)
            for rc in range(1, 4)
            for rd in range(1, 4)
        ]

        candidates = legal_states = terminal_states = 0
        projection_unknown = projection_role_disagreement = 0
        projection_value_disagreement = 0
        connected_front_blocked = revoked = nonunique_realizer = 0
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
                                clf, class_labels, feature_fns,
                                wk, bk, pawn, turn,
                            )
                            for pawn in pawns
                        ]
                        if any(role is None for role in roles):
                            projection_unknown += 1
                            continue
                        if len(set(roles)) != 1:
                            projection_role_disagreement += 1
                            continue

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

                        # Interaction law was fixed from the earlier a-b-c
                        # residual before this b-c-d target was evaluated.
                        if connected_front(pawns):
                            connected_front_blocked += 1
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

                        # Target authority begins here, after commitment.
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
                            if len(wrong_examples) < 50:
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
        "WARRANTED_PROSPECTIVE_INTERACTION_LAW_TRANSFER"
        if acted > 0 and wrong == 0
        else "EXACT_RESIDUAL_INTERACTION_LAW_TRANSFER"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "v6b_lineage": V6B_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "source_policy": "frozen exact KPvK V3 symbolic policy",
            "source_consequence": "exact KPvK WDL per local projection",
            "interaction_law": (
                "independent-pawn composition is disabled when any adjacent "
                "pawn pair occupies the same rank"
            ),
            "target_material": "White K+3P vs Black K",
            "target_subset": (
                "one pawn each on files b,c,d; ranks 2..4; all legal king "
                "placements and both sides to move"
            ),
            "target_disjointness": (
                "pawn-file support b,c,d is disjoint from V6/V6B a,b,c target"
            ),
            "guard": (
                "unanimous local move role + unanimous local KPvK WDL + "
                "no connected same-rank adjacent pawn pair + inherited V4 "
                "role revocations + unique legal realizer"
            ),
            "audit": (
                "KPPPvK Syzygy WDL queried only after concrete move commitment"
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
            "projection_role_disagreement": projection_role_disagreement,
            "projection_value_disagreement": projection_value_disagreement,
            "connected_front_blocked": connected_front_blocked,
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
                    "the interaction guard was derived from the earlier a-b-c "
                    "residual and then transferred prospectively with zero WDL "
                    "error to every b-c-d five-piece state where it fires"
                )
            ],
            "unknown": [
                "blocked/abstained b-c-d states",
                "other pawn-file triples and material classes",
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

    print("CRYSTAL_CHESS_INTERACTION_LAW_V7=PASS")
    print(
        f"legal={legal_states} acted={acted} correct={correct} wrong={wrong} "
        f"precision={correct/acted if acted else 0.0:.6f} "
        f"coverage={acted/legal_states if legal_states else 0.0:.6f}"
    )
    print(
        f"role_disagree={projection_role_disagreement} "
        f"value_disagree={projection_value_disagreement} "
        f"connected_blocked={connected_front_blocked} "
        f"revoked={revoked} nonunique={nonunique_realizer}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
