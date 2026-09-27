#!/usr/bin/env python3
"""V17 real UCI systems benchmark: Crystal hybrid vs identical Stockfish.

The benchmark runs two persistent UCI processes:
* baseline: pinned Stockfish directly;
* hybrid: Crystal V17 proxy with the same pinned Stockfish as fail-closed fallback.

Each position is searched with the same fixed node budget. Crystal-certified
positions return immediately (zero Stockfish search nodes); unsupported states
run the identical fallback search. Syzygy is verifier-only after both engines
have committed their moves.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time

import chess
import chess.syzygy

from crystal_chess_richer_transfer_v5 import make_kppvk
from crystal_chess_hybrid_guard_transfer_v15 import make_kpppvk

SCHEMA = "mathgraph.crystal-chess.stockfish-hybrid-uci-benchmark.v17"
STOCKFISH_AUTHORITY = (
    "official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057"
)
V17_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-stockfish-hybrid-uci-v17"
)


class UCIProcess:
    def __init__(self, command: list[str], name: str):
        self.command = command
        self.name = name
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
        self.send("setoption name Ponder value false")
        self.ready()

    def send(self, line: str) -> None:
        self.stdin.write(line + "\n")
        self.stdin.flush()

    def read_until(self, token: str) -> list[str]:
        lines: list[str] = []
        while True:
            line = self.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.name} exited waiting for {token}")
            line = line.rstrip("\n")
            lines.append(line)
            if line == token or line.startswith(token + " "):
                return lines

    def ready(self) -> None:
        self.send("isready")
        self.read_until("readyok")

    def search(self, fen: str, nodes: int) -> dict[str, object]:
        self.send("ucinewgame")
        self.send("setoption name Clear Hash")
        self.ready()
        self.send("position fen " + fen)
        started = time.perf_counter()
        self.send(f"go nodes {nodes}")
        lines = self.read_until("bestmove")
        elapsed = time.perf_counter() - started

        best_line = lines[-1]
        bestmove = best_line.split()[1]
        reported_nodes = 0
        reported_time_ms = 0
        shortcut = False
        authority = None
        for line in lines:
            if "Crystal certified " in line:
                shortcut = True
                authority = line.split("Crystal certified ", 1)[1]
            m = re.search(r"\bnodes (\d+)\b", line)
            if m:
                reported_nodes = int(m.group(1))
            m = re.search(r"\btime (\d+)\b", line)
            if m:
                reported_time_ms = int(m.group(1))
        return {
            "bestmove": bestmove,
            "wall_seconds": elapsed,
            "nodes": reported_nodes,
            "engine_time_ms": reported_time_ms,
            "shortcut": shortcut,
            "authority": authority,
        }

    def quit(self) -> None:
        if self.proc.poll() is None:
            try:
                self.send("quit")
            except BrokenPipeError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def sample_kppvk(rng: random.Random, n: int) -> list[chess.Board]:
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]
    seen: set[str] = set()
    out: list[chess.Board] = []
    while len(out) < n:
        p0, p1 = rng.sample(pawn_squares, 2)
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        turn = bool(rng.getrandbits(1))
        board = make_kppvk(wk, bk, p0, p1, turn)
        if not board.is_valid() or not any(board.legal_moves):
            continue
        board.halfmove_clock = 0
        board.fullmove_number = 1
        fen = board.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append(board)
    return out


def make_kppppvk(
    wk: int,
    bk: int,
    p0: int,
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
    for pawn in (p0, p1, p2, p3):
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def sample_kpppvk(rng: random.Random, n: int) -> list[chess.Board]:
    seen: set[str] = set()
    out: list[chess.Board] = []
    while len(out) < n:
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
        )
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        turn = bool(rng.getrandbits(1))
        board = make_kpppvk(wk, bk, *pawns, turn)
        if not board.is_valid() or not any(board.legal_moves):
            continue
        board.halfmove_clock = 0
        board.fullmove_number = 1
        fen = board.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append(board)
    return out


def sample_kpppppvk(rng: random.Random, n: int) -> list[chess.Board]:
    seen: set[str] = set()
    out: list[chess.Board] = []
    while len(out) < n:
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
            chess.square(4, rng.randrange(1, 4)),
        )
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        turn = bool(rng.getrandbits(1))
        board = make_kppppvk(wk, bk, *pawns, turn)
        if not board.is_valid() or not any(board.legal_moves):
            continue
        board.halfmove_clock = 0
        board.fullmove_number = 1
        fen = board.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append(board)
    return out


def wdl_preserved(
    tb: chess.syzygy.Tablebase,
    board: chess.Board,
    move_uci: str,
) -> tuple[bool, int, int]:
    root = int(tb.probe_wdl(board))
    move = chess.Move.from_uci(move_uci)
    if move not in board.legal_moves:
        return False, root, -99
    child = board.copy(stack=False)
    child.push(move)
    consequence = -int(tb.probe_wdl(child))
    return consequence == root, root, consequence


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--hybrid-script", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--roles", type=Path, required=True)
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--kppvk", type=int, default=600)
    ap.add_argument("--kpppvk", type=int, default=500)
    ap.add_argument("--kppppvk", type=int, default=500)
    ap.add_argument("--nodes", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    boards = (
        sample_kppvk(rng, args.kppvk)
        + sample_kpppvk(rng, args.kpppvk)
        + sample_kpppppvk(rng, args.kppppvk)
    )
    labels = (
        ["KPPvK"] * args.kppvk
        + ["KPPPvK"] * args.kpppvk
        + ["KPPPPvK"] * args.kppppvk
    )

    suite_digest = hashlib.sha256()
    for label, board in zip(labels, boards):
        suite_digest.update(f"{label}\t{board.fen()}\n".encode())

    baseline = UCIProcess([str(args.stockfish)], "stockfish-baseline")
    hybrid = UCIProcess(
        [
            sys.executable,
            str(args.hybrid_script),
            "--fallback",
            str(args.stockfish),
            "--guard",
            str(args.guard),
            "--roles",
            str(args.roles),
        ],
        "crystal-hybrid",
    )

    totals = Counter()
    by_family = {
        "KPPvK": Counter(),
        "KPPPvK": Counter(),
        "KPPPPvK": Counter(),
    }
    examples: list[dict[str, object]] = []

    started = time.perf_counter()
    try:
        with chess.syzygy.open_tablebase(
            str(args.tablebase_dir), load_wdl=True, load_dtz=False
        ) as tb:
            for idx, (family, board) in enumerate(zip(labels, boards)):
                fen = board.fen()
                if idx % 2 == 0:
                    base = baseline.search(fen, args.nodes)
                    cand = hybrid.search(fen, args.nodes)
                else:
                    cand = hybrid.search(fen, args.nodes)
                    base = baseline.search(fen, args.nodes)

                totals["positions"] += 1
                by_family[family]["positions"] += 1
                totals["baseline_nodes"] += int(base["nodes"])
                totals["hybrid_nodes"] += int(cand["nodes"])
                totals["baseline_wall_ns"] += int(float(base["wall_seconds"]) * 1e9)
                totals["hybrid_wall_ns"] += int(float(cand["wall_seconds"]) * 1e9)
                by_family[family]["baseline_nodes"] += int(base["nodes"])
                by_family[family]["hybrid_nodes"] += int(cand["nodes"])

                base_ok, root, base_cons = wdl_preserved(
                    tb, board, str(base["bestmove"])
                )
                cand_ok, _root2, cand_cons = wdl_preserved(
                    tb, board, str(cand["bestmove"])
                )
                totals["baseline_wdl_preserved"] += int(base_ok)
                totals["hybrid_wdl_preserved"] += int(cand_ok)
                totals["baseline_wdl_wrong"] += int(not base_ok)
                totals["hybrid_wdl_wrong"] += int(not cand_ok)

                if bool(cand["shortcut"]):
                    totals["shortcuts"] += 1
                    by_family[family]["shortcuts"] += 1
                    totals["shortcut_wrong"] += int(not cand_ok)
                    if len(examples) < 20:
                        examples.append(
                            {
                                "family": family,
                                "fen": fen,
                                "root_wdl": root,
                                "baseline_move": base["bestmove"],
                                "baseline_consequence": base_cons,
                                "crystal_move": cand["bestmove"],
                                "crystal_consequence": cand_cons,
                                "authority": cand["authority"],
                            }
                        )
                else:
                    totals["fallbacks"] += 1
                    by_family[family]["fallbacks"] += 1
                    same = str(base["bestmove"]) == str(cand["bestmove"])
                    totals["fallback_bestmove_parity"] += int(same)
                    by_family[family]["fallback_bestmove_parity"] += int(same)
    finally:
        baseline.quit()
        hybrid.quit()

    elapsed = time.perf_counter() - started
    baseline_wall = totals["baseline_wall_ns"] / 1e9
    hybrid_wall = totals["hybrid_wall_ns"] / 1e9
    baseline_nodes = int(totals["baseline_nodes"])
    hybrid_nodes = int(totals["hybrid_nodes"])
    fallbacks = int(totals["fallbacks"])

    summary = {
        "positions": int(totals["positions"]),
        "shortcuts": int(totals["shortcuts"]),
        "fallbacks": fallbacks,
        "shortcut_ratio": totals["shortcuts"] / totals["positions"],
        "shortcut_wrong": int(totals["shortcut_wrong"]),
        "fallback_bestmove_parity": int(totals["fallback_bestmove_parity"]),
        "fallback_parity_ratio": (
            totals["fallback_bestmove_parity"] / fallbacks if fallbacks else 1.0
        ),
        "baseline_nodes": baseline_nodes,
        "hybrid_stockfish_nodes": hybrid_nodes,
        "node_reduction_ratio": (
            (baseline_nodes - hybrid_nodes) / baseline_nodes
            if baseline_nodes else 0.0
        ),
        "baseline_go_wall_seconds": baseline_wall,
        "hybrid_go_wall_seconds": hybrid_wall,
        "wall_speedup_factor": baseline_wall / hybrid_wall if hybrid_wall else 1.0,
        "baseline_wdl_preserved": int(totals["baseline_wdl_preserved"]),
        "hybrid_wdl_preserved": int(totals["hybrid_wdl_preserved"]),
        "baseline_wdl_wrong": int(totals["baseline_wdl_wrong"]),
        "hybrid_wdl_wrong": int(totals["hybrid_wdl_wrong"]),
    }

    green = (
        summary["shortcuts"] > 0
        and summary["shortcut_wrong"] == 0
        and summary["fallback_parity_ratio"] == 1.0
        and summary["node_reduction_ratio"] > 0.0
        and summary["wall_speedup_factor"] > 1.0
        and summary["hybrid_wdl_wrong"] <= summary["baseline_wdl_wrong"]
    )
    status = (
        "WARRANTED_PINNED_STOCKFISH_FAIL_CLOSED_UCI_SYSTEM_GAIN"
        if green
        else "EXACT_UCI_SYSTEM_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_authority": STOCKFISH_AUTHORITY,
        "v17_authority": V17_AUTHORITY,
        "benchmark": {
            "seed": args.seed,
            "nodes_per_position": args.nodes,
            "kppvk_positions": args.kppvk,
            "kpppvk_positions": args.kpppvk,
            "kppppvk_positions": args.kppppvk,
            "suite_sha256": suite_digest.hexdigest(),
            "wall_seconds_total_both_arms": elapsed,
        },
        "summary": summary,
        "by_family": {k: dict(v) for k, v in by_family.items()},
        "shortcut_examples": examples,
        "claim_boundary": {
            "warranted_if_green": [
                "Crystal shortcut moves preserve exact Syzygy WDL on every shortcut in the frozen benchmark",
                "every UNKNOWN position is searched by the same pinned Stockfish binary",
                "fallback best moves exactly match direct Stockfish under the fixed deterministic node-budget protocol",
                "the hybrid executes fewer Stockfish nodes and lower measured go-to-bestmove wall time",
            ],
            "not_claimed": [
                "general chess Elo improvement",
                "TCEC/CCRL rating",
                "benefit outside V14/V15 qualified material boundaries",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_STOCKFISH_HYBRID_UCI_V17={status}")
    print(
        f"positions={summary['positions']} shortcuts={summary['shortcuts']} "
        f"shortcut_ratio={summary['shortcut_ratio']:.8f} "
        f"shortcut_wrong={summary['shortcut_wrong']}"
    )
    print(
        f"fallback_parity={summary['fallback_bestmove_parity']}/{summary['fallbacks']} "
        f"ratio={summary['fallback_parity_ratio']:.8f}"
    )
    print(
        f"baseline_nodes={baseline_nodes} hybrid_nodes={hybrid_nodes} "
        f"node_reduction={summary['node_reduction_ratio']:.8f}"
    )
    print(
        f"baseline_wall={baseline_wall:.6f}s hybrid_wall={hybrid_wall:.6f}s "
        f"wall_speedup={summary['wall_speedup_factor']:.6f}x"
    )
    print(
        f"baseline_wdl_wrong={summary['baseline_wdl_wrong']} "
        f"hybrid_wdl_wrong={summary['hybrid_wdl_wrong']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
