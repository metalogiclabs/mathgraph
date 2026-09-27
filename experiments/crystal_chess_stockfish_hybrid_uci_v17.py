#!/usr/bin/env python3
"""Crystal Chess V17: fail-closed UCI proxy in front of pinned Stockfish.

Crystal is allowed to bypass search only inside previously-qualified exact
boundaries:
* V14 complete KPPvK ranks 2..6 with the frozen pair@8 guard.
* V15 complete KPPPvK target: one pawn each on b,c,d, ranks 2..4, with the
  byte-identical V14 guard required pairwise against every other pawn.

All other positions, unsupported UCI search modes, and disabled Crystal states
are forwarded to the fallback engine unchanged.

The runtime does not query Syzygy or learn from target labels.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import TextIO

import chess

from crystal_chess_verified_hybrid_search_v14 import (
    TIER_NAMES,
    candidate_bindings,
    signature,
)
from crystal_chess_hybrid_guard_transfer_v15 import guarded_candidates

ENGINE_NAME = "CrystalChess-Stockfish-Hybrid-V17"
ENGINE_AUTHOR = "Metalogic Labs"
V14_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-verified-hybrid-search-v14"
    "@55be612bbf8cf3bd26ef10d5474873443f0f7edd"
)
V15_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v15"
    "@7f258e22057e8ffe1bb51c72ddca5d1ca3316949"
)


def load_guard(path: Path) -> tuple[dict[str, object], set[tuple[object, ...]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line:
            raise ValueError("empty V14 guard")
        header = json.loads(header_line)
        signatures = {
            tuple(json.loads(line)["signature"])
            for line in handle
            if line.strip()
        }
    if not signatures:
        raise ValueError("no V14 signatures")
    return header, signatures


def load_roles(path: Path) -> tuple[dict[str, object], dict[tuple[int, int, int, int], str]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line:
            raise ValueError("empty role map")
        header = json.loads(header_line)
        roles: dict[tuple[int, int, int, int], str] = {}
        for line in handle:
            if not line.strip():
                continue
            wk, bk, anchor, turn, role = json.loads(line)
            roles[(int(wk), int(bk), int(anchor), int(turn))] = str(role)
    if not roles:
        raise ValueError("empty role map")
    return header, roles


def parse_position_command(line: str) -> chess.Board:
    parts = line.strip().split()
    if len(parts) < 2 or parts[0] != "position":
        raise ValueError(line)

    if parts[1] == "startpos":
        board = chess.Board()
        idx = 2
    elif parts[1] == "fen":
        try:
            moves_idx = parts.index("moves", 2)
        except ValueError:
            moves_idx = len(parts)
        fen_parts = parts[2:moves_idx]
        if len(fen_parts) != 6:
            raise ValueError(f"bad UCI FEN: {fen_parts}")
        board = chess.Board(" ".join(fen_parts))
        idx = moves_idx
    else:
        raise ValueError(f"unsupported position command: {line}")

    if idx < len(parts) and parts[idx] == "moves":
        for token in parts[idx + 1 :]:
            move = chess.Move.from_uci(token)
            if move not in board.legal_moves:
                raise ValueError(f"illegal UCI history move {token} in {board.fen()}")
            board.push(move)
    return board


def pure_white_pawns_vs_black_king(board: chess.Board, pawn_count: int) -> bool:
    if not board.is_valid():
        return False
    if board.castling_rights != chess.BB_EMPTY or board.ep_square is not None:
        return False
    if board.halfmove_clock != 0:
        return False
    if len(board.pieces(chess.KING, chess.WHITE)) != 1:
        return False
    if len(board.pieces(chess.KING, chess.BLACK)) != 1:
        return False
    if len(board.pieces(chess.PAWN, chess.WHITE)) != pawn_count:
        return False
    if board.pieces(chess.PAWN, chess.BLACK):
        return False
    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
        ):
            if board.pieces(piece_type, color):
                return False
    return True


class CrystalOracle:
    def __init__(self, guard_path: Path, roles_path: Path):
        self.guard_header, self.safe_signatures = load_guard(guard_path)
        self.roles_header, self.role_map = load_roles(roles_path)
        self.tier = int(self.guard_header["tier_index"])
        self.tier_name = str(self.guard_header["tier"])
        if self.tier_name != TIER_NAMES[self.tier]:
            raise ValueError("guard tier metadata mismatch")

    def choose(self, board: chess.Board) -> tuple[chess.Move, str] | None:
        if board.is_game_over(claim_draw=False):
            return None

        wk = board.king(chess.WHITE)
        bk = board.king(chess.BLACK)
        if wk is None or bk is None:
            return None

        if pure_white_pawns_vs_black_king(board, 2):
            pawns = tuple(sorted(board.pieces(chess.PAWN, chess.WHITE)))
            if not all(1 <= chess.square_rank(p) <= 5 for p in pawns):
                return None
            p0, p1 = pawns
            for anchor, other, role, move in candidate_bindings(
                board, p0, p1, wk, bk, board.turn, self.role_map
            ):
                sig = signature(board, anchor, other, role, self.tier)
                if sig in self.safe_signatures:
                    return move, "V14_KPPvK_pair8"
            return None

        if pure_white_pawns_vs_black_king(board, 3):
            pawns = tuple(sorted(board.pieces(chess.PAWN, chess.WHITE)))
            files = {chess.square_file(p) for p in pawns}
            if files != {1, 2, 3}:
                return None
            if not all(1 <= chess.square_rank(p) <= 3 for p in pawns):
                return None
            candidates = guarded_candidates(
                board,
                pawns,
                wk,
                bk,
                board.turn,
                self.role_map,
                self.tier,
                self.safe_signatures,
                block_connected_front=False,
            )
            if candidates:
                return candidates[0], "V15_KPPPvK_universal_pair"
            return None

        return None


class FallbackEngine:
    def __init__(self, command: list[str]):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1,
        )
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        self.stdin: TextIO = self.proc.stdin
        self.stdout: TextIO = self.proc.stdout
        self.lock = threading.Lock()
        self.options: list[str] = []
        self._send("uci")
        while True:
            line = self.stdout.readline()
            if not line:
                raise RuntimeError("fallback exited during UCI init")
            line = line.rstrip("\n")
            if line.startswith("option "):
                self.options.append(line)
            if line == "uciok":
                break

    def _send(self, line: str) -> None:
        with self.lock:
            self.stdin.write(line + "\n")
            self.stdin.flush()

    def send(self, line: str) -> None:
        self._send(line)

    def ready(self) -> None:
        self._send("isready")
        while True:
            line = self.stdout.readline()
            if not line:
                raise RuntimeError("fallback exited during isready")
            if line.rstrip("\n") == "readyok":
                return

    def quit(self) -> None:
        if self.proc.poll() is None:
            try:
                self._send("quit")
            except BrokenPipeError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class HybridUCI:
    def __init__(self, fallback: list[str], oracle: CrystalOracle):
        self.fallback = FallbackEngine(fallback)
        self.oracle = oracle
        self.current_board: chess.Board | None = None
        self.crystal_enabled = True
        self.search_thread: threading.Thread | None = None
        self.search_active = threading.Event()
        self.print_lock = threading.Lock()

    def emit(self, line: str) -> None:
        with self.print_lock:
            print(line, flush=True)

    def wait_search(self) -> None:
        thread = self.search_thread
        if thread is not None and thread.is_alive():
            thread.join()
        self.search_thread = None
        self.search_active.clear()

    def relay_search(self, command: str) -> None:
        try:
            self.search_active.set()
            self.fallback.send(command)
            while True:
                line = self.fallback.stdout.readline()
                if not line:
                    self.emit("info string Crystal fallback engine exited")
                    self.emit("bestmove 0000")
                    return
                line = line.rstrip("\n")
                self.emit(line)
                if line.startswith("bestmove "):
                    return
        finally:
            self.search_active.clear()

    def start_fallback_search(self, command: str) -> None:
        self.wait_search()
        self.search_thread = threading.Thread(
            target=self.relay_search,
            args=(command,),
            daemon=True,
        )
        self.search_thread.start()

    def handle(self, raw: str) -> bool:
        line = raw.strip()
        if not line:
            return True

        if line == "uci":
            self.emit(f"id name {ENGINE_NAME}")
            self.emit(f"id author {ENGINE_AUTHOR}")
            self.emit("option name CrystalEnabled type check default true")
            for option in self.fallback.options:
                self.emit(option)
            self.emit("uciok")
            return True

        if line == "isready":
            self.wait_search()
            self.fallback.ready()
            self.emit("readyok")
            return True

        if line.startswith("setoption name CrystalEnabled"):
            lower = line.lower()
            self.crystal_enabled = not lower.endswith("value false")
            return True

        if line.startswith("setoption "):
            self.wait_search()
            self.fallback.send(line)
            return True

        if line == "ucinewgame":
            self.wait_search()
            self.fallback.send(line)
            return True

        if line.startswith("position "):
            self.wait_search()
            try:
                self.current_board = parse_position_command(line)
            except Exception as exc:
                self.current_board = None
                self.emit(f"info string Crystal position parse error: {exc}")
            self.fallback.send(line)
            return True

        if line.startswith("go"):
            unsupported = any(
                token in line.split()
                for token in ("ponder", "mate", "searchmoves")
            )
            if (
                self.crystal_enabled
                and not unsupported
                and self.current_board is not None
            ):
                choice = self.oracle.choose(self.current_board)
                if choice is not None:
                    move, authority = choice
                    self.emit(
                        "info string Crystal certified "
                        f"{authority} {V14_AUTHORITY} {V15_AUTHORITY}"
                    )
                    self.emit(
                        f"info depth 0 seldepth 0 nodes 0 time 0 pv {move.uci()}"
                    )
                    self.emit(f"bestmove {move.uci()}")
                    return True
            self.start_fallback_search(line)
            return True

        if line == "stop":
            if self.search_active.is_set():
                self.fallback.send("stop")
            return True

        if line == "ponderhit":
            if self.search_active.is_set():
                self.fallback.send("ponderhit")
            return True

        if line == "quit":
            if self.search_active.is_set():
                self.fallback.send("stop")
            self.wait_search()
            self.fallback.quit()
            return False

        # Forward harmless UCI extensions/debug commands fail-closed.
        self.wait_search()
        self.fallback.send(line)
        return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fallback", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--roles", type=Path, required=True)
    args = ap.parse_args()

    oracle = CrystalOracle(args.guard, args.roles)
    engine = HybridUCI([str(args.fallback)], oracle)
    try:
        for raw in sys.stdin:
            if not engine.handle(raw):
                break
    finally:
        try:
            engine.fallback.quit()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
