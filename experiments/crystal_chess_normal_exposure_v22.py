#!/usr/bin/env python3
"""Crystal Chess V22: normal-game exposure and exact residual census.

This is not a strength claim by itself. It answers:
1. How often does the current fail-closed Crystal runtime actually fire in
   normal paired games?
2. Which low-material classes are reached most often by normal Stockfish play?
3. Which exact six-piece family is the highest-leverage unsupported residual?

Opening generation is deterministic and uses shallow pinned Stockfish MultiPV
only to create diverse, plausible starting positions. Match play uses a fixed
node budget per move, with colors reversed per opening.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re

import chess
import chess.engine
import chess.pgn


SCHEMA = "mathgraph.crystal-chess.normal-exposure.v22"


def elo_from_score(score: float) -> float | None:
    if not (0.0 < score < 1.0):
        return None
    return 400.0 * math.log10(score / (1.0 - score))


def generate(args) -> int:
    rng = random.Random(args.seed)
    engine = chess.engine.SimpleEngine.popen_uci(str(args.stockfish))
    engine.configure({"Threads": 1, "Hash": 16})
    fens: list[str] = []
    seen: set[str] = set()
    try:
        attempts = 0
        while len(fens) < args.openings:
            attempts += 1
            if attempts > args.openings * 100:
                raise RuntimeError("could not generate enough unique openings")
            board = chess.Board()
            for _ply in range(args.plies):
                if board.is_game_over(claim_draw=False):
                    break
                infos = engine.analyse(
                    board,
                    chess.engine.Limit(depth=args.depth),
                    multipv=args.multipv,
                )
                if isinstance(infos, dict):
                    infos = [infos]
                moves: list[chess.Move] = []
                for info in infos:
                    pv = info.get("pv") or []
                    if pv and pv[0] in board.legal_moves and pv[0] not in moves:
                        moves.append(pv[0])
                if not moves:
                    break
                weights = [8, 4, 2, 1][: len(moves)]
                move = rng.choices(moves, weights=weights, k=1)[0]
                board.push(move)
            if board.is_game_over(claim_draw=False):
                continue
            fen = board.fen()
            if fen in seen:
                continue
            seen.add(fen)
            fens.append(fen)
    finally:
        engine.quit()

    args.book.parent.mkdir(parents=True, exist_ok=True)
    with args.book.open("w", encoding="utf-8") as out:
        for fen in fens:
            out.write(chess.Board(fen).epd() + "\n")

    h = hashlib.sha256()
    for fen in fens:
        h.update((fen + "\n").encode("utf-8"))
    manifest = {
        "schema": SCHEMA + ".book",
        "seed": args.seed,
        "openings": len(fens),
        "plies": args.plies,
        "depth": args.depth,
        "multipv": args.multipv,
        "book_sha256": h.hexdigest(),
        "fens": fens,
    }
    args.manifest.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_NORMAL_BOOK_V22=PASS")
    print(f"openings={len(fens)} sha256={h.hexdigest()}")
    return 0


PIECE_ORDER = (
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
    chess.PAWN,
)
PIECE_LETTER = {
    chess.QUEEN: "Q",
    chess.ROOK: "R",
    chess.BISHOP: "B",
    chess.KNIGHT: "N",
    chess.PAWN: "P",
}


def side_material(board: chess.Board, color: bool) -> str:
    text = "K"
    for pt in PIECE_ORDER:
        text += PIECE_LETTER[pt] * len(board.pieces(pt, color))
    return text


def normalized_material(board: chess.Board) -> str:
    white = side_material(board, chess.WHITE)
    black = side_material(board, chess.BLACK)
    a = f"{white}v{black}"
    b = f"{black}v{white}"
    return min(a, b)


def crystal_points(game: chess.pgn.Game, crystal_name: str) -> float:
    result = game.headers.get("Result", "*")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    if result == "1/2-1/2":
        return 0.5
    if result == "1-0":
        return 1.0 if white == crystal_name else 0.0
    if result == "0-1":
        return 1.0 if black == crystal_name else 0.0
    return 0.5


def analyse(args) -> int:
    games: list[chess.pgn.Game] = []
    with args.pgn.open("r", encoding="utf-8", errors="replace") as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            games.append(game)

    if len(games) % 2:
        raise AssertionError(f"expected paired games, got {len(games)}")

    wins = losses = draws = 0
    pair_points: list[float] = []
    piece_counts = Counter()
    low_material = Counter()
    low_material_unique: dict[str, set[str]] = defaultdict(set)
    six_piece = Counter()
    six_piece_unique: dict[str, set[str]] = defaultdict(set)
    five_piece = Counter()
    games_reaching_six = 0
    games_reaching_current_material = 0
    current_materials = {"KPPPPvK", "KPPPvK", "KPPvK"}

    for i in range(0, len(games), 2):
        pts = 0.0
        for game in games[i : i + 2]:
            p = crystal_points(game, args.crystal_name)
            pts += p
            if p == 1.0:
                wins += 1
            elif p == 0.0:
                losses += 1
            else:
                draws += 1

            board = game.board()
            reached_six = False
            reached_current = False
            positions = [board.copy(stack=False)]
            for move in game.mainline_moves():
                board.push(move)
                positions.append(board.copy(stack=False))

            for pos in positions:
                n = len(pos.piece_map())
                piece_counts[n] += 1
                if n <= 8:
                    mat = normalized_material(pos)
                    low_material[mat] += 1
                    low_material_unique[mat].add(pos.fen())
                    if mat in current_materials:
                        reached_current = True
                    if n == 6:
                        six_piece[mat] += 1
                        six_piece_unique[mat].add(pos.fen())
                        reached_six = True
                    if n == 5:
                        five_piece[mat] += 1

            games_reaching_six += int(reached_six)
            games_reaching_current_material += int(reached_current)
        pair_points.append(pts)

    total = len(games)
    score = (wins + 0.5 * draws) / total if total else 0.5
    elo = elo_from_score(score)

    rng = random.Random(20260928)
    boot: list[float] = []
    if pair_points:
        for _ in range(20000):
            sampled = [pair_points[rng.randrange(len(pair_points))] for _ in pair_points]
            s = sum(sampled) / (2.0 * len(sampled))
            e = elo_from_score(s)
            if e is not None:
                boot.append(e)
    boot.sort()
    ci = None
    if boot:
        ci = [
            boot[int(0.025 * (len(boot) - 1))],
            boot[int(0.975 * (len(boot) - 1))],
        ]

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    shortcut_lines = [
        line for line in log_text.splitlines() if "Crystal certified " in line
    ]
    shortcut_authorities = Counter()
    for line in shortcut_lines:
        m = re.search(r"Crystal certified ([^\s]+)", line)
        if m:
            shortcut_authorities[m.group(1)] += 1

    six_rows = []
    for mat, count in six_piece.most_common():
        six_rows.append(
            {
                "material": mat,
                "occurrences": count,
                "unique_positions": len(six_piece_unique[mat]),
                "currently_covered_material_class": mat == "KPPPPvK",
            }
        )

    unsupported_six = [row for row in six_rows if not row["currently_covered_material_class"]]
    top_residual = unsupported_six[0] if unsupported_six else None

    result = {
        "schema": SCHEMA + ".result",
        "games": total,
        "opening_pairs": len(pair_points),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "score_fraction": score,
        "bounded_logistic_elo_estimate": elo,
        "paired_bootstrap_95pct_elo_interval": ci,
        "crystal_shortcut_events": len(shortcut_lines),
        "shortcut_authorities": dict(shortcut_authorities),
        "games_reaching_six_pieces": games_reaching_six,
        "games_reaching_current_material_class": games_reaching_current_material,
        "piece_count_occurrences": {
            str(k): v for k, v in sorted(piece_counts.items())
        },
        "top_low_material_classes": [
            {
                "material": mat,
                "occurrences": count,
                "unique_positions": len(low_material_unique[mat]),
            }
            for mat, count in low_material.most_common(20)
        ],
        "six_piece_classes": six_rows[:30],
        "five_piece_classes": [
            {"material": mat, "occurrences": count}
            for mat, count in five_piece.most_common(20)
        ],
        "highest_leverage_unsupported_six_piece_residual": top_residual,
        "claim_boundary": {
            "purpose": "normal-game exposure and residual selection",
            "not_a_leaderboard_rating": True,
            "next_family_rule": (
                "choose the most frequent unsupported exact six-piece material "
                "class observed in the frozen paired normal-game corpus"
            ),
        },
    }
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_NORMAL_EXPOSURE_V22=PASS")
    print(
        f"games={total} W/L/D={wins}/{losses}/{draws} score={score:.6f} "
        f"elo={elo} ci95={ci} shortcuts={len(shortcut_lines)}"
    )
    print(
        f"games_reaching_six={games_reaching_six} "
        f"top_six_residual={top_residual}"
    )
    print(f"artifact={args.output}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--stockfish", type=Path, required=True)
    g.add_argument("--book", type=Path, required=True)
    g.add_argument("--manifest", type=Path, required=True)
    g.add_argument("--openings", type=int, default=96)
    g.add_argument("--plies", type=int, default=12)
    g.add_argument("--depth", type=int, default=6)
    g.add_argument("--multipv", type=int, default=4)
    g.add_argument("--seed", type=int, default=20260928)

    a = sub.add_parser("analyse")
    a.add_argument("--pgn", type=Path, required=True)
    a.add_argument("--log", type=Path, required=True)
    a.add_argument("--crystal-name", default="CrystalV22")
    a.add_argument("--output", type=Path, required=True)

    args = ap.parse_args()
    return generate(args) if args.mode == "generate" else analyse(args)


if __name__ == "__main__":
    raise SystemExit(main())
