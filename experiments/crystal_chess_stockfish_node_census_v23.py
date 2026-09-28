#!/usr/bin/env python3
"""Crystal Chess V23: census of low-material classes inside Stockfish search.

The instrumented Stockfish is decision-identical source code plus counters.
Only the main worker is used (Threads=1). For a deterministic suite of normal
positions, every regular/qsearch node with <=8 pieces contributes a compact
material code. The script ranks the exact six-piece residual by node mass.

This is diagnostic evidence only. It does not change Stockfish strength.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys

import chess
import chess.engine


PT_NAMES = ("P", "N", "B", "R", "Q")
DISPLAY_ORDER = (4, 3, 2, 1, 0)  # Q R B N P


class CensusUCI:
    def __init__(self, command: list[str]):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1,
        )
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.stdin = self.proc.stdin
        self.stdout = self.proc.stdout
        self.send("uci")
        self.read_until("uciok")
        self.send("setoption name Threads value 1")
        self.send("setoption name Hash value 16")
        self.ready()

    def send(self, s: str) -> None:
        self.stdin.write(s + "\n")
        self.stdin.flush()

    def read_until(self, token: str) -> list[str]:
        out = []
        while True:
            line = self.stdout.readline()
            if not line:
                raise RuntimeError(f"instrumented Stockfish exited waiting for {token}")
            line = line.rstrip("\n")
            out.append(line)
            if line == token or line.startswith(token + " "):
                return out

    def ready(self) -> None:
        self.send("isready")
        self.read_until("readyok")

    def census(self, fen: str, nodes: int) -> tuple[str, Counter]:
        self.send("ucinewgame")
        self.send("setoption name Clear Hash")
        self.ready()
        self.send("position fen " + fen)
        self.send(f"go nodes {nodes}")
        lines = self.read_until("bestmove")
        counts = Counter()
        for line in lines:
            m = re.match(r"info string CRYSTAL_SEARCH_MATERIAL (\d+) (\d+)$", line)
            if m:
                counts[int(m.group(1))] += int(m.group(2))
        bestmove = lines[-1].split()[1]
        return bestmove, counts

    def quit(self) -> None:
        if self.proc.poll() is None:
            self.send("quit")
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def decode(code: int) -> tuple[list[int], list[int]]:
    sides = [[], []]
    shift = 0
    for c in range(2):
        for _ in range(5):
            sides[c].append((code >> shift) & 0xF)
            shift += 4
    return sides[0], sides[1]


def side_name(counts: list[int]) -> str:
    s = "K"
    for idx in DISPLAY_ORDER:
        s += PT_NAMES[idx] * counts[idx]
    return s


def material_name(code: int) -> tuple[str, int]:
    white, black = decode(code)
    a = side_name(white)
    b = side_name(black)
    name = min(f"{a}v{b}", f"{b}v{a}")
    pieces = 2 + sum(white) + sum(black)
    return name, pieces


def generate_positions(
    stockfish: Path,
    *,
    openings: int,
    plies: int,
    depth: int,
    multipv: int,
    seed: int,
) -> list[str]:
    rng = random.Random(seed)
    engine = chess.engine.SimpleEngine.popen_uci(str(stockfish))
    engine.configure({"Threads": 1, "Hash": 16})
    out: list[str] = []
    seen: set[str] = set()
    try:
        attempts = 0
        while len(out) < openings:
            attempts += 1
            if attempts > openings * 100:
                raise RuntimeError("opening generation exhausted")
            board = chess.Board()
            for _ in range(plies):
                if board.is_game_over(claim_draw=False):
                    break
                infos = engine.analyse(
                    board,
                    chess.engine.Limit(depth=depth),
                    multipv=multipv,
                )
                if isinstance(infos, dict):
                    infos = [infos]
                moves = []
                for info in infos:
                    pv = info.get("pv") or []
                    if pv and pv[0] in board.legal_moves and pv[0] not in moves:
                        moves.append(pv[0])
                if not moves:
                    break
                weights = [8, 4, 2, 1][: len(moves)]
                board.push(rng.choices(moves, weights=weights, k=1)[0])
            if board.is_game_over(claim_draw=False):
                continue
            fen = board.fen()
            if fen not in seen:
                seen.add(fen)
                out.append(fen)
    finally:
        engine.quit()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generator-stockfish", type=Path, required=True)
    ap.add_argument("--instrumented-stockfish", type=Path, required=True)
    ap.add_argument("--openings", type=int, default=64)
    ap.add_argument("--plies", type=int, default=12)
    ap.add_argument("--opening-depth", type=int, default=6)
    ap.add_argument("--multipv", type=int, default=4)
    ap.add_argument("--nodes", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    fens = generate_positions(
        args.generator_stockfish,
        openings=args.openings,
        plies=args.plies,
        depth=args.opening_depth,
        multipv=args.multipv,
        seed=args.seed,
    )
    h = hashlib.sha256()
    for fen in fens:
        h.update((fen + "\n").encode())

    engine = CensusUCI([str(args.instrumented_stockfish)])
    total = Counter()
    reached = Counter()
    bestmoves = []
    try:
        for fen in fens:
            bestmove, counts = engine.census(fen, args.nodes)
            bestmoves.append((fen, bestmove))
            for code, count in counts.items():
                total[code] += count
                if count:
                    reached[code] += 1
    finally:
        engine.quit()

    material_nodes = Counter()
    material_searches = Counter()
    code_rows = []
    for code, count in total.items():
        material, pieces = material_name(code)
        material_nodes[material] += count
        material_searches[material] += reached[code]
        code_rows.append(
            {
                "code": code,
                "material": material,
                "pieces": pieces,
                "nodes": count,
                "searches_reached": reached[code],
            }
        )

    six_rows = []
    current_six = {"KPPPPvK"}
    for material, nodes in material_nodes.most_common():
        # Piece count is invariant across codes collapsed to a material name.
        code = next(c for c in total if material_name(c)[0] == material)
        pieces = material_name(code)[1]
        if pieces == 6:
            six_rows.append(
                {
                    "material": material,
                    "nodes": nodes,
                    "searches_reached": material_searches[material],
                    "currently_covered_material_class": material in current_six,
                }
            )

    unsupported_six = [r for r in six_rows if not r["currently_covered_material_class"]]
    top = unsupported_six[0] if unsupported_six else None

    low_rows = []
    for material, nodes in material_nodes.most_common(40):
        code = next(c for c in total if material_name(c)[0] == material)
        low_rows.append(
            {
                "material": material,
                "pieces": material_name(code)[1],
                "nodes": nodes,
                "searches_reached": material_searches[material],
            }
        )

    status = (
        "WARRANTED_SEARCH_NODE_RESIDUAL_CENSUS"
        if top is not None and sum(total.values()) > 0
        else "NO_SIX_PIECE_SEARCH_RESIDUAL_OBSERVED"
    )
    result = {
        "schema": "mathgraph.crystal-chess.stockfish-node-census.v23",
        "status": status,
        "stockfish_pin": "official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057",
        "diagnostic": {
            "decision_logic_changed": False,
            "threads": 1,
            "openings": len(fens),
            "opening_sha256": h.hexdigest(),
            "nodes_per_root": args.nodes,
            "instrumented_node_mass_leq8": sum(total.values()),
        },
        "top_low_material_classes": low_rows,
        "six_piece_classes": six_rows[:40],
        "highest_leverage_unsupported_six_piece_residual": top,
        "bestmoves": bestmoves,
        "claim_boundary": {
            "purpose": "rank exact-capability acquisition targets by Stockfish internal node mass",
            "not_strength_evidence": True,
            "next_target_rule": (
                "choose the highest-node-mass unsupported six-piece material class "
                "that is supported by exact Syzygy authority"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_STOCKFISH_NODE_CENSUS_V23={status}")
    print(
        f"openings={len(fens)} low_material_nodes={sum(total.values())} "
        f"top_six_residual={top}"
    )
    for row in six_rows[:10]:
        print(
            f"six:{row['material']} nodes={row['nodes']} "
            f"searches={row['searches_reached']} covered={row['currently_covered_material_class']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
