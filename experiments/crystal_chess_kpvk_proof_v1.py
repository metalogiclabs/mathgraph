#!/usr/bin/env python3
"""Crystal Chess V1: exact KPvK reachability proof crystal.

This experiment uses chess legality as the transition relation and a tiny
externally checked base at material exit (KQvK/KRvK win, KBvK/KNvK/KvK draw,
with terminal status checked first). It computes the complete White-winning
attractor for KPvK, verifies every result against Syzygy WDL, derives a
well-founded adversarial progress rank, and compresses the resulting proof DAG
by recursive proof-obligation identity.

The protected object is not a static board feature vector. It is the proof
needed to preserve the exact game-theoretic consequence:
* White-to-move winning node: one rank-decreasing witness is sufficient.
* Black-to-move while White is winning: every legal reply must stay certified.
* rank 0 is a terminal White win or exact winning material exit.

This is a bounded exact result for KPvK, not a solution of general chess.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Iterable

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


SCHEMA = "mathgraph.crystal-chess.kpvk-proof-crystal.v1"
V0_AUTHORITY = (
    "metalogiclabs/mathgraph@d8da8268068e7d94950aadeea53ad74906683355"
)


@dataclass(frozen=True)
class Edge:
    action: str
    internal_target: int | None
    external_white_outcome: int | None

    def __post_init__(self) -> None:
        if (self.internal_target is None) == (self.external_white_outcome is None):
            raise ValueError("edge must have exactly one target kind")


def white_outcome_from_stm_wdl(turn: bool, wdl: int) -> int:
    return wdl if turn == chess.WHITE else -wdl


def action_label(board: chess.Board, move: chess.Move) -> str:
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("move has no mover")
    dx = chess.square_file(move.to_square) - chess.square_file(move.from_square)
    dy = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    role = chess.piece_name(piece.piece_type)
    promo = chess.piece_name(move.promotion) if move.promotion else "-"
    capture = int(board.is_capture(move))
    return f"{role}:dx={dx}:dy={dy}:promo={promo}:capture={capture}"


def elementary_exit_outcome(board: chess.Board) -> int:
    """White-centric exact base for reachable KPvK exits.

    Terminal status dominates. Otherwise reachable exits are bare K versus K,
    KQ/KR versus K, or KB/KN versus K after promotion.
    """
    if board.is_checkmate():
        return -2 if board.turn == chess.WHITE else 2
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    pieces = board.piece_map()
    white_nonking = [
        p.piece_type for p in pieces.values()
        if p.color == chess.WHITE and p.piece_type != chess.KING
    ]
    black_nonking = [
        p.piece_type for p in pieces.values()
        if p.color == chess.BLACK and p.piece_type != chess.KING
    ]
    if black_nonking:
        raise AssertionError(("unexpected black exit material", board.fen()))
    if white_nonking == []:
        return 0
    if len(white_nonking) != 1:
        raise AssertionError(("unexpected white exit material", board.fen()))
    if white_nonking[0] in (chess.QUEEN, chess.ROOK):
        return 2
    if white_nonking[0] in (chess.BISHOP, chess.KNIGHT):
        return 0
    raise AssertionError(("unexpected exit piece", board.fen()))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_graph(records, tablebase, cache):
    index = {
        (rec.wk, rec.bk, rec.pawn, rec.turn): i
        for i, rec in enumerate(records)
    }
    edges: list[list[Edge]] = [[] for _ in records]
    exit_oracle_mismatches = []
    raw_edges = 0
    external_edges = 0

    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        for move in board.legal_moves:
            raw_edges += 1
            label = action_label(board, move)
            child = board.copy(stack=False)
            child.push(move)

            wp = list(child.pieces(chess.PAWN, chess.WHITE))
            wk = child.king(chess.WHITE)
            bk = child.king(chess.BLACK)
            if len(wp) == 1 and wk is not None and bk is not None and len(child.piece_map()) == 3:
                key = (wk, bk, wp[0], child.turn)
                target = index.get(key)
                if target is None:
                    raise AssertionError(("missing internal target", child.fen(), key))
                edges[i].append(Edge(label, target, None))
            else:
                external_edges += 1
                elementary = elementary_exit_outcome(child)
                stm_wdl = probe_wdl(tablebase, child, cache)
                oracle = white_outcome_from_stm_wdl(child.turn, stm_wdl)
                if elementary != oracle and len(exit_oracle_mismatches) < 20:
                    exit_oracle_mismatches.append(
                        {
                            "fen": child.fen(),
                            "elementary": elementary,
                            "syzygy": oracle,
                            "move": move.uci(),
                        }
                    )
                edges[i].append(Edge(label, None, elementary))

    return edges, {
        "raw_edges": raw_edges,
        "external_edges": external_edges,
        "exit_oracle_mismatches": exit_oracle_mismatches,
    }


def solve_white_attractor(records, edges):
    """Least reachability attractor for White wins with exact progress ranks."""
    n = len(records)
    rank: list[int | None] = [None] * n

    # Terminal internal checkmates are rank-0 wins.
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        if not edges[i] and board.is_checkmate() and board.turn == chess.BLACK:
            rank[i] = 0

    changed = True
    passes = 0
    while changed:
        changed = False
        passes += 1
        for i, rec in enumerate(records):
            if rank[i] is not None:
                continue
            es = edges[i]
            if not es:
                continue

            target_ranks: list[int | None] = []
            for edge in es:
                if edge.internal_target is not None:
                    target_ranks.append(rank[edge.internal_target])
                elif edge.external_white_outcome == 2:
                    target_ranks.append(0)
                else:
                    target_ranks.append(None)

            if rec.turn == chess.WHITE:
                known = [r for r in target_ranks if r is not None]
                if known:
                    rank[i] = 1 + min(known)
                    changed = True
            else:
                if all(r is not None for r in target_ranks):
                    rank[i] = 1 + max(r for r in target_ranks if r is not None)
                    changed = True

    return rank, passes


def target_rank(edge: Edge, rank: list[int | None]) -> int | None:
    if edge.internal_target is not None:
        return rank[edge.internal_target]
    if edge.external_white_outcome == 2:
        return 0
    return None


def compress_win_proofs(records, edges, rank):
    """Bottom-up quotient of well-founded proof obligations.

    External winning exits share class 0. Internal rank-0 terminal wins share
    one terminal class. White nodes store one canonical rank-decreasing witness;
    Black nodes store the complete adversarial reply cover.
    """
    by_rank: dict[int, list[int]] = defaultdict(list)
    for i, r in enumerate(rank):
        if r is not None:
            by_rank[r].append(i)

    external_class = 0
    next_class = 1
    class_of: dict[int, int] = {}
    signature_to_class: dict[tuple, int] = {}
    class_signature: dict[int, tuple] = {external_class: ("external-white-win",)}
    class_support: Counter[int] = Counter()
    chosen_witness: dict[int, tuple[str, int]] = {}
    raw_proof_edges = 0

    for r in sorted(by_rank):
        pending: list[tuple[int, tuple]] = []
        for i in by_rank[r]:
            rec = records[i]
            es = edges[i]
            if r == 0:
                signature = ("terminal-white-win",)
                pending.append((i, signature))
                continue

            if rec.turn == chess.WHITE:
                choices = []
                for edge in es:
                    tr = target_rank(edge, rank)
                    if tr is None or tr >= r:
                        continue
                    if edge.internal_target is None:
                        tc = external_class
                    else:
                        tc = class_of[edge.internal_target]
                    choices.append((tr, edge.action, tc))
                if not choices:
                    raise AssertionError(("white win node has no progress witness", i, r))
                # Fastest exact progress first, then canonical abstract action.
                tr, action, tc = min(choices)
                if tr != r - 1:
                    raise AssertionError(("white rank gap", i, r, tr))
                signature = ("exists", action, tc)
                chosen_witness[i] = (action, tc)
                raw_proof_edges += 1
            else:
                replies = []
                for edge in es:
                    tr = target_rank(edge, rank)
                    if tr is None or tr >= r:
                        raise AssertionError(("black escape/nonprogress", i, r, tr, edge))
                    tc = (
                        external_class
                        if edge.internal_target is None
                        else class_of[edge.internal_target]
                    )
                    replies.append((edge.action, tc))
                signature = ("forall", tuple(sorted(replies)))
                raw_proof_edges += len(replies)

            pending.append((i, signature))

        # Merge equal obligations at the same (implicitly determined) rank.
        for i, signature in pending:
            cid = signature_to_class.get(signature)
            if cid is None:
                cid = next_class
                next_class += 1
                signature_to_class[signature] = cid
                class_signature[cid] = signature
            class_of[i] = cid
            class_support[cid] += 1

    abstract_edges = 0
    for cid, sig in class_signature.items():
        if cid == external_class:
            continue
        if sig[0] == "exists":
            abstract_edges += 1
        elif sig[0] == "forall":
            abstract_edges += len(sig[1])

    return {
        "external_class": external_class,
        "class_of": class_of,
        "class_signature": class_signature,
        "class_support": class_support,
        "chosen_witness": chosen_witness,
        "raw_proof_edges": raw_proof_edges,
        "abstract_proof_edges": abstract_edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("crystal_chess_kpvk_proof_v1.json")
    )
    args = parser.parse_args()
    started = time.time()

    feature_bank = coordinate_feature_bank()
    cache: dict[tuple[str, bool], int] = {}
    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, cache, [fn for _, fn in feature_bank]
        )
        if enumeration["mirror_mismatches"] or enumeration["mirror_invalid"]:
            raise AssertionError(enumeration)

        edges, graph_stats = build_graph(records, tablebase, cache)
        if graph_stats["exit_oracle_mismatches"]:
            raise AssertionError(graph_stats["exit_oracle_mismatches"])

        rank, passes = solve_white_attractor(records, edges)

        oracle_white = [
            white_outcome_from_stm_wdl(rec.turn, rec.wdl) for rec in records
        ]
        computed_win = [r is not None for r in rank]
        win_mismatches = [
            i for i, (got, oracle) in enumerate(zip(computed_win, oracle_white))
            if got != (oracle == 2)
        ]
        nonwin_nondraw = [
            i for i, (got, oracle) in enumerate(zip(computed_win, oracle_white))
            if not got and oracle != 0
        ]
        if win_mismatches or nonwin_nondraw:
            raise AssertionError(
                {
                    "win_mismatches": win_mismatches[:20],
                    "nonwin_nondraw": nonwin_nondraw[:20],
                }
            )

        proof = compress_win_proofs(records, edges, rank)

    winning_states = sum(r is not None for r in rank)
    draw_states = len(records) - winning_states
    max_rank = max(r for r in rank if r is not None)
    rank_hist = Counter(r for r in rank if r is not None)
    proof_classes = len(set(proof["class_of"].values()))
    max_support = max(proof["class_support"].values()) if proof_classes else 0
    certificate_payload = {
        "class_of": sorted(proof["class_of"].items()),
        "class_signature": sorted(proof["class_signature"].items()),
        "chosen_witness": sorted(proof["chosen_witness"].items()),
    }
    certificate_sha256 = hashlib.sha256(
        json.dumps(
            certificate_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_REACHABILITY_PROOF_CRYSTAL",
        "lineage": {
            "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
            "v0_authority": V0_AUTHORITY,
        },
        "protected_interface": "chess.white-win-reachability-with-adversarial-cover.v1",
        "authority": {
            "independent_oracle": "Syzygy WDL",
            "tablebase_files": manifest,
            "oracle_role": (
                "checks complete KPvK classification and every reachable "
                "material-exit base; it is not used by attractor recurrence"
            ),
        },
        "boundary": {
            "material": "White K+P versus Black K",
            "canonical_pawn_files": ["a", "b", "c", "d"],
            "horizontal_reflection_requalified": True,
            "states": len(records),
            "external_base": [
                "terminal checkmate/stalemate",
                "KQvK and KRvK nonterminal = White win",
                "KBvK, KNvK, KvK = draw",
            ],
        },
        "graph": {
            "legal_edges": graph_stats["raw_edges"],
            "material_exit_edges": graph_stats["external_edges"],
            "exit_oracle_mismatches": 0,
        },
        "solution": {
            "white_winning_states": winning_states,
            "draw_states": draw_states,
            "white_losing_states": 0,
            "syzygy_classification_mismatches": 0,
            "fixed_point_passes": passes,
            "max_forced_exit_rank": max_rank,
            "rank_histogram": {str(k): v for k, v in sorted(rank_hist.items())},
            "rank_semantics": (
                "White nodes use 1+min certified successor rank; Black nodes "
                "use 1+max over all legal replies; rank 0 is a certified "
                "White-win terminal/material exit."
            ),
        },
        "proof_crystal": {
            "winning_raw_states": winning_states,
            "internal_proof_classes": proof_classes,
            "state_to_proof_class_compression": (
                winning_states / proof_classes if proof_classes else 1.0
            ),
            "raw_proof_edges": proof["raw_proof_edges"],
            "abstract_proof_edges": proof["abstract_proof_edges"],
            "proof_edge_compression": (
                proof["raw_proof_edges"] / proof["abstract_proof_edges"]
                if proof["abstract_proof_edges"]
                else 1.0
            ),
            "largest_class_support": max_support,
            "certificate_sha256": certificate_sha256,
            "certificate_binding": (
                "hash of complete raw-state->proof-class map, recursive class "
                "signatures, and existential witness choices"
            ),
            "obligation_semantics": {
                "white_turn": "EXISTS one rank-decreasing certified witness",
                "black_turn": "FORALL legal replies have lower certified rank",
            },
        },
        "epistemic_boundary": {
            "warranted": [
                "complete declared KPvK White-win/draw classification matches Syzygy",
                "every White win has a finite adversarial progress rank",
                "the emitted proof quotient preserves the declared win certificate obligations",
            ],
            "rejected": [
                "static local geometry is required to identify proof identity",
            ],
            "candidate": [
                "proof-obligation classes and action schemas transfer to richer pawn endings",
                "the same attractor/quotient construction can grow a solved basin across material boundaries",
            ],
            "unknown": [
                "general chess",
                "draw-certificate compression beyond the declared safety complement",
                "transfer to unseen 8-piece op1 positions",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "python_chess_version": getattr(chess, "__version__", "unknown"),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    print("CRYSTAL_CHESS_KPVK_PROOF_V1=PASS")
    print(
        f"states={len(records)} white_win={winning_states} draw={draw_states} "
        f"max_rank={max_rank}"
    )
    print(
        f"proof_classes={proof_classes} "
        f"state_compression={result['proof_crystal']['state_to_proof_class_compression']:.3f}x"
    )
    print(
        f"proof_edges={proof['raw_proof_edges']}->{proof['abstract_proof_edges']} "
        f"compression={result['proof_crystal']['proof_edge_compression']:.3f}x"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
