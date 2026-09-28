#!/usr/bin/env python3
"""Crystal Chess V21 systems benchmark: residual ladder + color symmetry.

Baseline is pinned Stockfish. Hybrid is the same Stockfish behind the V21
fail-closed UCI proxy. The benchmark is deterministic and uses fixed nodes per
position. Half of each family is mirrored so both color orientations are
exercised.

Families:
* KPPvK complete-source geometry.
* KPPPvK complete V19 target geometry.
* KPPPPvK complete V19 target geometry.

Syzygy is verifier-only after both engines commit a move.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time

import chess
import chess.syzygy


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
        bestmove = lines[-1].split()[1]
        reported_nodes = 0
        shortcut = False
        authority = None
        for line in lines:
            if "Crystal certified " in line:
                shortcut = True
                authority = line.split("Crystal certified ", 1)[1]
            m = re.search(r"\bnodes (\d+)\b", line)
            if m:
                reported_nodes = int(m.group(1))
        return {
            "bestmove": bestmove,
            "wall_seconds": elapsed,
            "nodes": reported_nodes,
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


def make_board(
    wk: int, bk: int, pawns: tuple[int, ...], turn: bool
) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    for pawn in pawns:
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def random_canonical(rng: random.Random, family: str) -> chess.Board:
    if family == "KPPvK":
        squares = [chess.square(f, r) for f in range(8) for r in range(1, 6)]
        pawns = tuple(rng.sample(squares, 2))
    elif family == "KPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
        )
    elif family == "KPPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
            chess.square(4, rng.randrange(1, 4)),
        )
    else:
        raise ValueError(family)
    wk, bk = rng.sample(list(chess.SQUARES), 2)
    return make_board(wk, bk, pawns, bool(rng.getrandbits(1)))


def sample_family(
    rng: random.Random, family: str, n: int
) -> list[tuple[chess.Board, str]]:
    out: list[tuple[chess.Board, str]] = []
    seen: set[str] = set()
    while len(out) < n:
        board = random_canonical(rng, family)
        if not board.is_valid() or not any(board.legal_moves):
            continue
        orientation = "white-pawns"
        if len(out) % 2:
            board = board.mirror()
            orientation = "black-pawns"
        fen = board.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append((board, orientation))
    return out


def wdl_preserved(
    tb: chess.syzygy.Tablebase,
    board: chess.Board,
    move_uci: str,
) -> bool:
    root = int(tb.probe_wdl(board))
    move = chess.Move.from_uci(move_uci)
    if move not in board.legal_moves:
        return False
    child = board.copy(stack=False)
    child.push(move)
    return -int(tb.probe_wdl(child)) == root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--hybrid-script", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--roles", type=Path, required=True)
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--per-family", type=int, default=400)
    ap.add_argument("--nodes", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    positions: list[tuple[str, str, chess.Board]] = []
    for family in ("KPPvK", "KPPPvK", "KPPPPvK"):
        for board, orientation in sample_family(rng, family, args.per_family):
            positions.append((family, orientation, board))

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
        "crystal-v21",
    )

    totals = Counter()
    by_family: dict[str, Counter] = {
        f: Counter() for f in ("KPPvK", "KPPPvK", "KPPPPvK")
    }
    by_orientation: dict[str, Counter] = {
        "white-pawns": Counter(),
        "black-pawns": Counter(),
    }
    authorities = Counter()

    try:
        with chess.syzygy.open_tablebase(
            str(args.tablebase_dir), load_wdl=True, load_dtz=False
        ) as tb:
            for idx, (family, orientation, board) in enumerate(positions):
                fen = board.fen()
                if idx % 2:
                    cand = hybrid.search(fen, args.nodes)
                    base = baseline.search(fen, args.nodes)
                else:
                    base = baseline.search(fen, args.nodes)
                    cand = hybrid.search(fen, args.nodes)

                for c in (totals, by_family[family], by_orientation[orientation]):
                    c["positions"] += 1
                    c["baseline_nodes"] += int(base["nodes"])
                    c["hybrid_nodes"] += int(cand["nodes"])
                    c["baseline_wall_ns"] += int(float(base["wall_seconds"]) * 1e9)
                    c["hybrid_wall_ns"] += int(float(cand["wall_seconds"]) * 1e9)

                base_ok = wdl_preserved(tb, board, str(base["bestmove"]))
                cand_ok = wdl_preserved(tb, board, str(cand["bestmove"]))
                totals["baseline_wdl_wrong"] += int(not base_ok)
                totals["hybrid_wdl_wrong"] += int(not cand_ok)

                if bool(cand["shortcut"]):
                    totals["shortcuts"] += 1
                    by_family[family]["shortcuts"] += 1
                    by_orientation[orientation]["shortcuts"] += 1
                    totals["shortcut_wrong"] += int(not cand_ok)
                    authorities[str(cand["authority"])] += 1
                else:
                    totals["fallbacks"] += 1
                    same = str(base["bestmove"]) == str(cand["bestmove"])
                    totals["fallback_parity"] += int(same)
                    by_family[family]["fallbacks"] += 1
                    by_family[family]["fallback_parity"] += int(same)
                    by_orientation[orientation]["fallbacks"] += 1
                    by_orientation[orientation]["fallback_parity"] += int(same)
    finally:
        baseline.quit()
        hybrid.quit()

    def finalize(c: Counter) -> dict[str, object]:
        positions_n = int(c["positions"])
        baseline_nodes = int(c["baseline_nodes"])
        hybrid_nodes = int(c["hybrid_nodes"])
        baseline_wall = c["baseline_wall_ns"] / 1e9
        hybrid_wall = c["hybrid_wall_ns"] / 1e9
        fallbacks = int(c["fallbacks"])
        return {
            **dict(c),
            "shortcut_ratio": c["shortcuts"] / positions_n if positions_n else 0.0,
            "node_reduction_ratio": (
                (baseline_nodes - hybrid_nodes) / baseline_nodes
                if baseline_nodes else 0.0
            ),
            "wall_speedup_factor": (
                baseline_wall / hybrid_wall if hybrid_wall else 1.0
            ),
            "fallback_parity_ratio": (
                c["fallback_parity"] / fallbacks if fallbacks else 1.0
            ),
            "baseline_wall_seconds": baseline_wall,
            "hybrid_wall_seconds": hybrid_wall,
        }

    summary = finalize(totals)
    family_rows = {k: finalize(v) for k, v in by_family.items()}
    orient_rows = {k: finalize(v) for k, v in by_orientation.items()}
    green = (
        summary["shortcuts"] > 0
        and summary["shortcut_wrong"] == 0
        and summary["fallback_parity_ratio"] == 1.0
        and summary["node_reduction_ratio"] > 0.0
        and summary["wall_speedup_factor"] > 1.0
        and summary["hybrid_wdl_wrong"] <= summary["baseline_wdl_wrong"]
    )
    status = (
        "WARRANTED_LADDER_COLOR_SYMMETRIC_UCI_SYSTEM_GAIN"
        if green
        else "EXACT_V21_SYSTEM_RESIDUAL"
    )
    result = {
        "schema": "mathgraph.crystal-chess.ladder-hybrid-uci-benchmark.v21",
        "status": status,
        "benchmark": {
            "per_family": args.per_family,
            "total_positions": len(positions),
            "nodes_per_position": args.nodes,
            "seed": args.seed,
        },
        "summary": summary,
        "by_family": family_rows,
        "by_orientation": orient_rows,
        "authority_counts": dict(authorities),
        "claim_boundary": {
            "warranted_if_green": [
                "all shortcut moves preserve exact Syzygy WDL on the frozen benchmark",
                "all UNKNOWN states return the same best move as direct pinned Stockfish",
                "both pawn-color orientations are exercised",
                "measured Stockfish node work and go-to-bestmove wall time are reduced",
            ],
            "not_claimed": [
                "normal-opening Elo gain",
                "CCRL/TCEC ranking",
                "general chess superiority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_LADDER_HYBRID_UCI_V21={status}")
    print(
        f"positions={summary['positions']} shortcuts={summary['shortcuts']} "
        f"ratio={summary['shortcut_ratio']:.8f} wrong={summary['shortcut_wrong']}"
    )
    print(
        f"fallback_parity={summary['fallback_parity']}/{summary['fallbacks']} "
        f"ratio={summary['fallback_parity_ratio']:.8f}"
    )
    print(
        f"baseline_nodes={summary['baseline_nodes']} hybrid_nodes={summary['hybrid_nodes']} "
        f"node_reduction={summary['node_reduction_ratio']:.8f}"
    )
    print(
        f"wall_speedup={summary['wall_speedup_factor']:.6f}x "
        f"baseline_wdl_wrong={summary['baseline_wdl_wrong']} "
        f"hybrid_wdl_wrong={summary['hybrid_wdl_wrong']}"
    )
    for k, row in family_rows.items():
        print(
            f"{k}: shortcuts={row['shortcuts']}/{row['positions']} "
            f"ratio={row['shortcut_ratio']:.8f}"
        )
    for k, row in orient_rows.items():
        print(
            f"{k}: shortcuts={row['shortcuts']}/{row['positions']} "
            f"ratio={row['shortcut_ratio']:.8f}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
