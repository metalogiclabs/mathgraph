#!/usr/bin/env python3
"""Crystal Chess V4: close winning KPvK through promotion to checkmate.

This composes the V3 KPvK two-ply progress certificate with exact KQvK/KRvK
promotion basins.

For each legal winning strong-side-to-move KQvK or KRvK state, seek a legal
WIN-preserving move such that either it checkmates immediately, or after EVERY
legal losing-side reply the next strong-side winning state has strictly smaller
positive Syzygy DTZ.

Because KQvK/KRvK contain no pawns and no capturable weak-side material, a
WIN-preserving line has no nonterminal zeroing event other than eventual mate.
Thus positive DTZ is a natural well-founded rank for this phase.

The experiment also checks every exact WIN-preserving KPvK promotion: it must
enter KQvK or KRvK (underpromotion to B/N cannot preserve WIN) and the resulting
black-to-move position must be exact LOSS or immediate checkmate.

Combined with Crystal Chess DTZ Progress V3, green status gives a complete
terminating strategy certificate for the winning KPvK material class, relative
to exact Syzygy verification.
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

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    enumerate_records,
    make_kpvk,
    probe_wdl,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-promotion-closure.v4"
V3_AUTHORITY = (
    "metalogiclabs/mathgraph@eea3a153287b2d3f979ca57e049a4b6c96b38afc"
)


def board_key(board: chess.Board) -> tuple[str, bool]:
    return board.board_fen(), board.turn


def probe_dtz(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    cache: dict[tuple[str, bool], int],
) -> int:
    key = board_key(board)
    if key not in cache:
        cache[key] = int(tablebase.probe_dtz(board))
    return cache[key]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_major(
    piece_type: int, wk: int, piece_sq: int, bk: int, turn: bool
) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(piece_sq, chess.Piece(piece_type, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    return board


def exact_major_material(board: chess.Board, piece_type: int) -> bool:
    return (
        board.king(chess.WHITE) is not None
        and board.king(chess.BLACK) is not None
        and len(board.pieces(piece_type, chess.WHITE)) == 1
        and sum(
            len(board.pieces(pt, chess.WHITE))
            for pt in (
                chess.QUEEN,
                chess.ROOK,
                chess.BISHOP,
                chess.KNIGHT,
                chess.PAWN,
            )
        ) == 1
        and not any(
            board.pieces(pt, chess.BLACK)
            for pt in (
                chess.QUEEN,
                chess.ROOK,
                chess.BISHOP,
                chess.KNIGHT,
                chess.PAWN,
            )
        )
    )


def audit_major_phase(
    tablebase: chess.syzygy.Tablebase,
    piece_type: int,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
) -> dict[str, object]:
    stats = Counter()
    residuals: list[dict[str, object]] = []
    dtz_hist = Counter()
    safe_kind = Counter()

    for piece_sq in chess.SQUARES:
        for wk in chess.SQUARES:
            if wk == piece_sq:
                continue
            for bk in chess.SQUARES:
                if bk in (wk, piece_sq):
                    continue
                board = make_major(
                    piece_type, wk, piece_sq, bk, chess.WHITE
                )
                stats["candidate"] += 1
                if not board.is_valid():
                    stats["invalid"] += 1
                    continue
                stats["legal"] += 1
                root_wdl = probe_wdl(tablebase, board, wdl_cache)
                if root_wdl != 2:
                    stats[f"root_wdl_{root_wdl}"] += 1
                    continue
                if not any(board.legal_moves):
                    raise AssertionError("winning strong-side state is terminal")

                root_dtz = probe_dtz(tablebase, board, dtz_cache)
                if root_dtz <= 0:
                    raise AssertionError(
                        f"winning strong-side DTZ is not positive: {board.fen()} {root_dtz}"
                    )
                dtz_hist[root_dtz] += 1
                stats["winning_states"] += 1

                found = False
                candidate_moves = 0
                reply_checks = 0
                sample_failure = None
                for move in board.legal_moves:
                    child = board.copy(stack=False)
                    child.push(move)
                    consequence = -probe_wdl(tablebase, child, wdl_cache)
                    if consequence != 2:
                        continue
                    candidate_moves += 1

                    if child.is_checkmate():
                        found = True
                        safe_kind["mate_now"] += 1
                        break
                    if not any(child.legal_moves):
                        # WDL-preserving WIN cannot stalemate.
                        sample_failure = {
                            "reason": "non-checkmate terminal after winning move",
                            "move": move.uci(),
                        }
                        continue

                    move_safe = True
                    for reply in child.legal_moves:
                        reply_checks += 1
                        grand = child.copy(stack=False)
                        grand.push(reply)
                        gw = probe_wdl(tablebase, grand, wdl_cache)
                        if gw != 2:
                            move_safe = False
                            sample_failure = {
                                "reason": "losing-side reply escaped WIN",
                                "move": move.uci(),
                                "reply": reply.uci(),
                                "grand_wdl": gw,
                            }
                            break
                        if not exact_major_material(grand, piece_type):
                            move_safe = False
                            sample_failure = {
                                "reason": "material escaped while still marked WIN",
                                "move": move.uci(),
                                "reply": reply.uci(),
                                "fen": grand.fen(),
                            }
                            break
                        next_dtz = probe_dtz(tablebase, grand, dtz_cache)
                        if next_dtz <= 0 or next_dtz >= root_dtz:
                            move_safe = False
                            sample_failure = {
                                "reason": "DTZ rank did not strictly decrease",
                                "move": move.uci(),
                                "reply": reply.uci(),
                                "root_dtz": root_dtz,
                                "next_dtz": next_dtz,
                            }
                            break

                    if move_safe:
                        found = True
                        safe_kind["two_ply_dtz"] += 1
                        break

                stats["value_preserving_candidate_moves_examined"] += candidate_moves
                stats["opponent_replies_checked"] += reply_checks
                if not found:
                    stats["without_progress"] += 1
                    if len(residuals) < 24:
                        residuals.append(
                            {
                                "fen": board.fen(),
                                "root_dtz": root_dtz,
                                "sample_failure": sample_failure,
                            }
                        )

    return {
        "piece": chess.piece_name(piece_type),
        "stats": dict(stats),
        "safe_kind": dict(safe_kind),
        "dtz_min": min(dtz_hist) if dtz_hist else None,
        "dtz_max": max(dtz_hist) if dtz_hist else None,
        "dtz_distinct": len(dtz_hist),
        "residual_examples": residuals,
    }


def audit_promotions(
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
) -> dict[str, object]:
    records, enumeration = enumerate_records(tablebase, wdl_cache, [])
    stats = Counter()
    promotion_types = Counter()
    entries: set[tuple[str, bool]] = set()
    examples: list[dict[str, object]] = []

    for rec in records:
        if rec.wdl != 2:
            continue
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        if board.turn != chess.WHITE:
            continue
        for move in board.legal_moves:
            if move.promotion is None:
                continue
            stats["promotion_moves"] += 1
            child = board.copy(stack=False)
            child.push(move)
            consequence = -probe_wdl(tablebase, child, wdl_cache)
            if consequence != 2:
                stats["nonwinning_promotions"] += 1
                continue
            stats["win_preserving_promotions"] += 1
            promotion_types[chess.piece_name(move.promotion)] += 1
            if move.promotion not in (chess.QUEEN, chess.ROOK):
                stats["bad_winning_underpromotion"] += 1
                if len(examples) < 16:
                    examples.append({
                        "fen": board.fen(),
                        "move": move.uci(),
                        "consequence": consequence,
                    })
            if child.is_checkmate():
                stats["promotion_checkmates"] += 1
                continue
            child_wdl = probe_wdl(tablebase, child, wdl_cache)
            if child_wdl != -2:
                stats["bad_entry_wdl"] += 1
                if len(examples) < 16:
                    examples.append({
                        "fen": child.fen(),
                        "entry_wdl": child_wdl,
                        "move": move.uci(),
                    })
            entries.add(board_key(child))

    return {
        "enumeration": enumeration,
        "stats": dict(stats),
        "winning_promotion_types": dict(promotion_types),
        "unique_nonterminal_major_entries": len(entries),
        "error_examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    started = time.time()
    files = sorted(args.tablebase_dir.glob("*.rtb*"))
    if not files:
        raise SystemExit("missing Syzygy files")
    manifest = [
        {"name":p.name, "size":p.stat().st_size, "sha256":file_sha256(p)}
        for p in files
    ]

    wdl_cache: dict[tuple[str, bool], int] = {}
    dtz_cache: dict[tuple[str, bool], int] = {}
    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tablebase:
        promotions = audit_promotions(tablebase, wdl_cache)
        queen = audit_major_phase(
            tablebase, chess.QUEEN, wdl_cache, dtz_cache
        )
        rook = audit_major_phase(
            tablebase, chess.ROOK, wdl_cache, dtz_cache
        )

    pstats = promotions["stats"]
    qbad = int(queen["stats"].get("without_progress", 0))
    rbad = int(rook["stats"].get("without_progress", 0))
    errors = (
        int(pstats.get("bad_winning_underpromotion", 0))
        + int(pstats.get("bad_entry_wdl", 0))
        + qbad + rbad
    )
    status = (
        "WARRANTED_KPVK_PROMOTION_TO_MATE_CLOSURE"
        if errors == 0
        else "REJECTED_KPVK_PROMOTION_CLOSURE_CANDIDATE"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "v3_authority": V3_AUTHORITY,
        "authority": {
            "kind": "Syzygy WDL + DTZ",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "files": manifest,
        },
        "promotion_bridge": promotions,
        "major_phase": {"queen": queen, "rook": rook},
        "composition": {
            "kpvk_phase": (
                "V3: every winning KPvK strong-side state has a certified "
                "two-ply lexicographic (pawn-steps,DTZ) progress action"
            ),
            "phase_exit": (
                "green V4: every WIN-preserving promotion is Q/R and enters "
                "an exact losing KQvK/KRvK opponent state or checkmate"
            ),
            "major_phase": (
                "green V4: every winning KQvK/KRvK strong-side state has a "
                "WIN-preserving action that mates or strictly decreases DTZ "
                "after every opponent reply"
            ),
            "closeout": (
                "well-founded progress in each phase excludes an infinite "
                "goal-avoiding strategy play; winning KPvK reaches checkmate"
            ),
        },
        "epistemic_boundary": {
            "warranted_if_green": (
                "complete terminating strategy existence for winning KPvK, "
                "relative to the exact enumerated three-piece Syzygy boundary"
            ),
            "unknown": [
                "compressed observable-only KQvK/KRvK policy",
                "transfer to richer material",
                "general chess solution",
            ],
        },
        "cache": {
            "wdl_positions": len(wdl_cache),
            "dtz_positions": len(dtz_cache),
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")

    print(f"CRYSTAL_CHESS_PROMOTION_CLOSURE_V4={status}")
    print(
        "promotions "
        f"winning={pstats.get('win_preserving_promotions',0)} "
        f"bad_under={pstats.get('bad_winning_underpromotion',0)} "
        f"bad_entry={pstats.get('bad_entry_wdl',0)} "
        f"entries={promotions['unique_nonterminal_major_entries']}"
    )
    for label, data in (("KQvK",queen),("KRvK",rook)):
        s=data["stats"]
        print(
            f"{label} winning={s.get('winning_states',0)} "
            f"without_progress={s.get('without_progress',0)} "
            f"reply_checks={s.get('opponent_replies_checked',0)} "
            f"dtz={data['dtz_min']}..{data['dtz_max']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
