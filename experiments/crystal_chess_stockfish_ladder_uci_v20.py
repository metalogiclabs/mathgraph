#!/usr/bin/env python3
"""Crystal Chess V20: fail-closed residual-ladder UCI proxy.

The runtime uses the frozen zero-error residual guard ladder:
pair -> distance-on-pair-residual -> relational-on-distance-residual.

The same byte-identical ladder is warranted on:
* complete restricted KPPvK source boundary;
* complete KPPPvK b,c,d ranks 2..4 target;
* complete KPPPPvK b,c,d,e ranks 2..4 target.

All other positions and unsupported search modes are forwarded to the identical
pinned Stockfish fallback unchanged. Runtime admission uses no Syzygy or target
labels.
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

TIER_NAMES = ("role", "pair", "distance", "relational")


def sq_file(sq: int) -> int:
    return chess.square_file(sq)


def sq_rank(sq: int) -> int:
    return chess.square_rank(sq)


def sign(x: int) -> int:
    return (x > 0) - (x < 0)


def cheb(a: int, b: int) -> int:
    return max(abs(sq_file(a) - sq_file(b)), abs(sq_rank(a) - sq_rank(b)))


def file_edge(sq: int) -> int:
    f = sq_file(sq)
    return min(f, 7 - f)


def board_edge(sq: int) -> int:
    f, r = sq_file(sq), sq_rank(sq)
    return min(f, 7 - f, r, 7 - r)


def signature(
    board: chess.Board,
    anchor: int,
    other: int,
    role: str,
    tier: int,
) -> tuple[object, ...]:
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    if wk is None or bk is None:
        raise AssertionError("missing king")
    base: tuple[object, ...] = (int(board.turn), role)
    if tier == 0:
        return base
    df = sq_file(other) - sq_file(anchor)
    dr = sq_rank(other) - sq_rank(anchor)
    pair = base + (
        sq_rank(anchor),
        file_edge(anchor),
        abs(df),
        dr,
        sign(df),
    )
    if tier == 1:
        return pair
    dist = pair + (
        cheb(wk, anchor),
        cheb(bk, anchor),
        cheb(wk, other),
        cheb(bk, other),
        cheb(wk, bk),
    )
    if tier == 2:
        return dist
    relational = dist + (
        sign(sq_file(wk) - sq_file(anchor)),
        sign(sq_rank(wk) - sq_rank(anchor)),
        sign(sq_file(bk) - sq_file(anchor)),
        sign(sq_rank(bk) - sq_rank(anchor)),
        board_edge(wk),
        board_edge(bk),
    )
    if tier == 3:
        return relational
    raise ValueError(tier)


def parse_role_move(
    board: chess.Board,
    anchor: int,
    role: str,
) -> chess.Move | None:
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
    source = (
        board.king(chess.WHITE)
        if tag == "K"
        else anchor if tag == "P" else None
    )
    if source is None:
        return None
    f = chess.square_file(source) + df
    r = chess.square_rank(source) + dr
    if not (0 <= f < 8 and 0 <= r < 8):
        return None
    move = chess.Move(source, chess.square(f, r), promotion=promotion)
    return move if board.is_legal(move) else None


def candidate_bindings(
    board: chess.Board,
    p0: int,
    p1: int,
    wk: int,
    bk: int,
    turn: bool,
    role_map: dict[tuple[int, int, int, int], str],
) -> list[tuple[int, int, str, chess.Move]]:
    out: list[tuple[int, int, str, chess.Move]] = []
    for anchor, other in ((p0, p1), (p1, p0)):
        role = role_map[(wk, bk, anchor, int(turn))]
        move = parse_role_move(board, anchor, role)
        if move is not None:
            out.append((anchor, other, role, move))
    return out

ENGINE_NAME = "CrystalChess-Stockfish-Ladder-V20"
ENGINE_AUTHOR = "Metalogic Labs"
SOURCE_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-residual-guard-ladder-v16"
    "@4f7902ddc9e65a6357c39221203211145c85f2e2"
)
TRANSFER_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-residual-ladder-transfer-v19"
    "@5c2962265fcd2154e97a32b2ef7b40c72f2aee93"
)


def load_guard(
    path: Path,
) -> tuple[dict[str, object], dict[str, set[tuple[object, ...]]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line:
            raise ValueError("empty residual ladder")
        header = json.loads(header_line)
        tiers = {"pair": set(), "distance": set(), "relational": set()}
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            tier = str(row["tier"])
            if tier not in tiers:
                raise ValueError(f"unexpected ladder tier {tier}")
            tiers[tier].add(tuple(row["signature"]))
    if not all(tiers.values()):
        raise ValueError("incomplete residual ladder")
    return header, tiers


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


def pair_admitted(
    board: chess.Board,
    anchor: int,
    other: int,
    role: str,
    tiers: dict[str, set[tuple[object, ...]]],
) -> bool:
    if signature(board, anchor, other, role, 1) in tiers["pair"]:
        return True
    if signature(board, anchor, other, role, 2) in tiers["distance"]:
        return True
    if signature(board, anchor, other, role, 3) in tiers["relational"]:
        return True
    return False


def universal_pair_candidates(
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    role_map: dict[tuple[int, int, int, int], str],
    tiers: dict[str, set[tuple[object, ...]]],
) -> list[chess.Move]:
    """Require the frozen residual ladder against every other pawn."""
    seen: set[chess.Move] = set()
    out: list[chess.Move] = []
    for anchor in pawns:
        role = role_map[(wk, bk, anchor, int(turn))]
        move = parse_role_move(board, anchor, role)
        if move is None:
            continue
        if all(
            pair_admitted(board, anchor, other, role, tiers)
            for other in pawns
            if other != anchor
        ):
            if move not in seen:
                seen.add(move)
                out.append(move)
    return out


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
        self.guard_header, self.tiers = load_guard(guard_path)
        self.roles_header, self.role_map = load_roles(roles_path)

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
            for anchor, other in ((p0, p1), (p1, p0)):
                role = self.role_map[(wk, bk, anchor, int(board.turn))]
                move = parse_role_move(board, anchor, role)
                if move is not None and pair_admitted(
                    board, anchor, other, role, self.tiers
                ):
                    return move, "V20_KPPvK_residual_ladder"
            return None

        if pure_white_pawns_vs_black_king(board, 3):
            pawns = tuple(sorted(board.pieces(chess.PAWN, chess.WHITE)))
            files = {chess.square_file(p) for p in pawns}
            if files != {1, 2, 3}:
                return None
            if not all(1 <= chess.square_rank(p) <= 3 for p in pawns):
                return None
            candidates = universal_pair_candidates(
                board,
                pawns,
                wk,
                bk,
                board.turn,
                self.role_map,
                self.tiers,
            )
            if candidates:
                return candidates[0], "V20_KPPPvK_residual_ladder"
            return None

        if pure_white_pawns_vs_black_king(board, 4):
            pawns = tuple(sorted(board.pieces(chess.PAWN, chess.WHITE)))
            files = {chess.square_file(p) for p in pawns}
            if files != {1, 2, 3, 4}:
                return None
            if not all(1 <= chess.square_rank(p) <= 3 for p in pawns):
                return None
            candidates = universal_pair_candidates(
                board,
                pawns,
                wk,
                bk,
                board.turn,
                self.role_map,
                self.tiers,
            )
            if candidates:
                return candidates[0], "V20_KPPPPvK_residual_ladder"
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
                        f"{authority} {SOURCE_AUTHORITY} {TRANSFER_AUTHORITY}"
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
