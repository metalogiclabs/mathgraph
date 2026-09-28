#!/usr/bin/env python3
"""Crystal Chess V25: prospective normal-search sufficiency guard.

Question:
Can a cheap 5k-node probe certify that the move chosen by pinned Stockfish at
100k nodes is already determined?

Authority and split discipline:
* Positions come from the frozen V22 normal-game corpus.
* Whole opening pairs are assigned before authority search:
    pair mod 3 = acquisition / validation / untouched holdout.
* Cross-split repeated FENs are removed.
* The guard sees only cheap-probe + board observables.
* Deep Stockfish bestmove is a label, never a feature.
* Tree/threshold selection uses acquisition + validation only.
* Holdout is opened after one configuration is selected.

This establishes a behavioral search-substitution capability relative to a
pinned Stockfish search budget. It is not a proof of the chess-theoretic move.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import chess
import chess.pgn
import numpy as np
from sklearn.tree import DecisionTreeClassifier


SCHEMA = "mathgraph.crystal-chess.search-sufficiency.v25"
STOCKFISH_PIN = "official-stockfish/Stockfish@0a215d6c9e48856ef630013b8ab8312941a59057"
V22_RUN = 36361812786
PROBE1_NODES = 1000
PROBE2_NODES = 4000
PROBE_TOTAL_NODES = PROBE1_NODES + PROBE2_NODES
AUTHORITY_NODES = 100000


class UCIStockfish:
    def __init__(self, path: Path):
        self.proc = subprocess.Popen(
            [str(path)],
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

    def send(self, line: str) -> None:
        self.stdin.write(line + "\n")
        self.stdin.flush()

    def read_until(self, token: str) -> list[str]:
        out: list[str] = []
        while True:
            line = self.stdout.readline()
            if not line:
                raise RuntimeError(f"Stockfish exited waiting for {token}")
            line = line.rstrip("\n")
            out.append(line)
            if line == token or line.startswith(token + " "):
                return out

    def ready(self) -> None:
        self.send("isready")
        self.read_until("readyok")

    def clear_hash(self) -> None:
        self.send("setoption name Clear Hash")
        self.ready()

    @staticmethod
    def _score_value(tokens: list[str]) -> int:
        try:
            i = tokens.index("score")
            kind = tokens[i + 1]
            raw = int(tokens[i + 2])
        except Exception:
            return 0
        if kind == "cp":
            return max(-100000, min(100000, raw))
        if kind == "mate":
            sign = 1 if raw > 0 else -1
            return sign * (100000 - min(abs(raw), 999) * 100)
        return 0

    @staticmethod
    def _int_after(tokens: list[str], name: str, default: int = 0) -> int:
        try:
            return int(tokens[tokens.index(name) + 1])
        except Exception:
            return default

    def search(
        self,
        fen: str,
        nodes: int,
        *,
        multipv: int,
        clear: bool,
    ) -> dict[str, Any]:
        if clear:
            self.clear_hash()
        self.send(f"setoption name MultiPV value {multipv}")
        self.send("position fen " + fen)
        self.send(f"go nodes {nodes}")
        lines = self.read_until("bestmove")
        bestmove = lines[-1].split()[1]
        pv_info: dict[int, dict[str, Any]] = {}
        for line in lines[:-1]:
            if not line.startswith("info "):
                continue
            tokens = line.split()
            if "pv" not in tokens or "score" not in tokens:
                continue
            mpv = self._int_after(tokens, "multipv", 1)
            try:
                pvi = tokens.index("pv")
                pv = tokens[pvi + 1 :]
            except ValueError:
                pv = []
            pv_info[mpv] = {
                "score": self._score_value(tokens),
                "depth": self._int_after(tokens, "depth"),
                "seldepth": self._int_after(tokens, "seldepth"),
                "nodes": self._int_after(tokens, "nodes"),
                "pv": pv,
            }

        top1 = pv_info.get(1, {"score": 0, "depth": 0, "seldepth": 0, "nodes": 0, "pv": []})
        top2 = pv_info.get(2)
        return {
            "bestmove": bestmove,
            "score1": int(top1["score"]),
            "score2": int(top2["score"]) if top2 else None,
            "depth": int(top1["depth"]),
            "seldepth": int(top1["seldepth"]),
            "reported_nodes": int(top1["nodes"]),
            "pv1": list(top1["pv"]),
            "pv2": list(top2["pv"]) if top2 else [],
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


def extract_positions(pgn: Path, max_per_split: int) -> dict[str, list[chess.Board]]:
    raw: dict[str, dict[str, chess.Board]] = {
        "train": {},
        "validation": {},
        "holdout": {},
    }
    fen_splits: dict[str, set[str]] = defaultdict(set)

    with pgn.open("r", encoding="utf-8", errors="replace") as handle:
        game_idx = 0
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            pair_idx = game_idx // 2
            split = ("train", "validation", "holdout")[pair_idx % 3]
            board = game.board()
            positions = [board.copy(stack=False)]
            for move in game.mainline_moves():
                board.push(move)
                positions.append(board.copy(stack=False))

            picked = 0
            for rel_ply, pos in enumerate(positions):
                if rel_ply % 8 != 0:
                    continue
                if pos.is_game_over(claim_draw=False):
                    continue
                if len(pos.piece_map()) < 12:
                    continue
                fen = pos.fen()
                raw[split][fen] = pos
                fen_splits[fen].add(split)
                picked += 1
                if picked >= 4:
                    break
            game_idx += 1

    out: dict[str, list[chess.Board]] = {}
    for split in raw:
        unique = [
            board
            for fen, board in raw[split].items()
            if len(fen_splits[fen]) == 1
        ]
        unique.sort(key=lambda b: hashlib.sha256(b.fen().encode()).hexdigest())
        out[split] = unique[:max_per_split]
    return out


def material_counts(board: chess.Board) -> dict[str, int]:
    out = {}
    for color, prefix in ((chess.WHITE, "w"), (chess.BLACK, "b")):
        for pt, name in (
            (chess.PAWN, "p"),
            (chess.KNIGHT, "n"),
            (chess.BISHOP, "b"),
            (chess.ROOK, "r"),
            (chess.QUEEN, "q"),
        ):
            out[prefix + name] = len(board.pieces(pt, color))
    return out


def move_observables(board: chess.Board, uci: str) -> dict[str, int]:
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return {
            "move_piece": 0,
            "move_capture": 0,
            "move_promotion": 0,
            "move_gives_check": 0,
            "move_zeroing": 0,
            "move_abs_df": 0,
            "move_abs_dr": 0,
            "move_from_edge": 0,
            "move_to_edge": 0,
        }
    if move not in board.legal_moves:
        return {
            "move_piece": 0,
            "move_capture": 0,
            "move_promotion": 0,
            "move_gives_check": 0,
            "move_zeroing": 0,
            "move_abs_df": 0,
            "move_abs_dr": 0,
            "move_from_edge": 0,
            "move_to_edge": 0,
        }
    piece = board.piece_at(move.from_square)
    captured = board.piece_at(move.to_square)
    ff, fr = chess.square_file(move.from_square), chess.square_rank(move.from_square)
    tf, tr = chess.square_file(move.to_square), chess.square_rank(move.to_square)
    def edge(sq: int) -> int:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        return min(f, 7 - f, r, 7 - r)
    return {
        "move_piece": piece.piece_type if piece else 0,
        "move_capture": captured.piece_type if captured else 0,
        "move_promotion": move.promotion or 0,
        "move_gives_check": int(board.gives_check(move)),
        "move_zeroing": int(board.is_zeroing(move)),
        "move_abs_df": abs(tf - ff),
        "move_abs_dr": abs(tr - fr),
        "move_from_edge": edge(move.from_square),
        "move_to_edge": edge(move.to_square),
    }


def feature_row(
    board: chess.Board,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> tuple[list[str], tuple[int, ...]]:
    names: list[str] = []
    vals: list[int] = []
    def add(name: str, value: int | bool) -> None:
        names.append(name)
        vals.append(int(value))

    margin1 = (
        p1["score1"] - p1["score2"]
        if p1["score2"] is not None
        else 100000
    )
    margin2 = (
        p2["score1"] - p2["score2"]
        if p2["score2"] is not None
        else 100000
    )
    add("probe_best_stable", p1["bestmove"] == p2["bestmove"])
    add("score1_probe1", p1["score1"])
    add("score1_probe2", p2["score1"])
    add("score_delta_abs", abs(p2["score1"] - p1["score1"]))
    add("margin_probe1", margin1)
    add("margin_probe2", margin2)
    add("margin_delta", margin2 - margin1)
    add("depth_probe1", p1["depth"])
    add("depth_probe2", p2["depth"])
    add("seldepth_probe1", p1["seldepth"])
    add("seldepth_probe2", p2["seldepth"])
    add("pv_prefix_stable_2", p1["pv1"][:2] == p2["pv1"][:2] and len(p2["pv1"]) >= 2)
    add("pv_prefix_stable_3", p1["pv1"][:3] == p2["pv1"][:3] and len(p2["pv1"]) >= 3)

    add("piece_count", len(board.piece_map()))
    add("legal_moves", board.legal_moves.count())
    add("in_check", board.is_check())
    add("halfmove_clock_bucket", min(board.halfmove_clock // 10, 10))
    add("side_to_move", int(board.turn))
    counts = material_counts(board)
    for key in sorted(counts):
        add(key, counts[key])

    obs = move_observables(board, str(p2["bestmove"]))
    for key in sorted(obs):
        add(key, obs[key])

    return names, tuple(vals)


def collect_records(
    engine: UCIStockfish,
    boards: list[chess.Board],
) -> tuple[list[dict[str, Any]], list[str]]:
    records = []
    feature_names: list[str] | None = None
    for idx, board in enumerate(boards):
        fen = board.fen()
        p1 = engine.search(fen, PROBE1_NODES, multipv=2, clear=True)
        p2 = engine.search(fen, PROBE2_NODES, multipv=2, clear=False)
        authority = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        names, row = feature_row(board, p1, p2)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise AssertionError("feature order drift")
        records.append(
            {
                "state_id": idx,
                "fen": fen,
                "features": row,
                "probe1": p1,
                "probe2": p2,
                "authority_bestmove": authority["bestmove"],
                "match": p2["bestmove"] == authority["bestmove"],
            }
        )
    return records, feature_names or []


def leaf_stats(
    model: DecisionTreeClassifier,
    records: list[dict[str, Any]],
) -> dict[int, list[int]]:
    X = np.asarray([r["features"] for r in records], dtype=np.int32)
    leaves = model.apply(X)
    stats: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for leaf, rec in zip(leaves, records):
        stats[int(leaf)][0] += 1
        stats[int(leaf)][1] += int(not bool(rec["match"]))
    return dict(stats)


def evaluate(
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    X = np.asarray([r["features"] for r in records], dtype=np.int32)
    leaves = model.apply(X)
    covered = 0
    wrong = 0
    examples = []
    for rec, leaf in zip(records, leaves):
        if int(leaf) not in safe_leaves:
            continue
        covered += 1
        wrong += int(not bool(rec["match"]))
        if len(examples) < 20:
            examples.append(
                {
                    "fen": rec["fen"],
                    "probe_move": rec["probe2"]["bestmove"],
                    "authority_move": rec["authority_bestmove"],
                    "match": rec["match"],
                }
            )
    coverage = covered / len(records) if records else 0.0
    expected_nodes = PROBE_TOTAL_NODES + (1.0 - coverage) * AUTHORITY_NODES
    reduction = 1.0 - expected_nodes / AUTHORITY_NODES
    return {
        "positions": len(records),
        "covered": covered,
        "coverage_ratio": coverage,
        "wrong": wrong,
        "estimated_nodes_per_position": expected_nodes,
        "estimated_node_reduction_ratio": reduction,
        "examples": examples,
    }


def export_guard(
    path: Path,
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    feature_names: list[str],
    selection: dict[str, Any],
) -> str:
    tree = model.tree_
    payload = {
        "schema": SCHEMA + ".guard",
        "stockfish_pin": STOCKFISH_PIN,
        "probe_protocol": {
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "probe2_reuses_probe1_tt": True,
            "authority_nodes": AUTHORITY_NODES,
            "multipv": 2,
        },
        "feature_names": feature_names,
        "safe_leaves": sorted(safe_leaves),
        "selection": selection,
        "tree": {
            "children_left": [int(x) for x in tree.children_left],
            "children_right": [int(x) for x in tree.children_right],
            "feature": [int(x) for x in tree.feature],
            "threshold": [float(x) for x in tree.threshold],
        },
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(raw)
    return digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--pgn", type=Path, required=True)
    ap.add_argument("--max-per-split", type=int, default=220)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--guard-output", type=Path, required=True)
    args = ap.parse_args()

    splits = extract_positions(args.pgn, args.max_per_split)
    if min(len(v) for v in splits.values()) < 30:
        raise AssertionError(("insufficient corpus", {k: len(v) for k, v in splits.items()}))

    engine = UCIStockfish(args.stockfish)
    try:
        train, feature_names = collect_records(engine, splits["train"])
        validation, names2 = collect_records(engine, splits["validation"])
        holdout, names3 = collect_records(engine, splits["holdout"])
    finally:
        engine.quit()

    if feature_names != names2 or feature_names != names3:
        raise AssertionError("feature drift")

    X = np.asarray([r["features"] for r in train], dtype=np.int32)
    y = np.asarray([int(bool(r["match"])) for r in train], dtype=np.int8)
    configs = []
    for depth in (2, 3, 4, 5, 6, 8, 10, None):
        for min_leaf in (2, 4, 8, 16):
            model = DecisionTreeClassifier(
                criterion="entropy",
                max_depth=depth,
                min_samples_leaf=min_leaf,
                random_state=0,
            )
            model.fit(X, y)
            stats = leaf_stats(model, train)
            for support in (3, 5, 10, 20):
                safe = {
                    leaf
                    for leaf, (count, failures) in stats.items()
                    if count >= support and failures == 0
                }
                if not safe:
                    continue
                val = evaluate(model, safe, validation)
                if val["wrong"] != 0:
                    continue
                configs.append(
                    {
                        "model": model,
                        "safe": safe,
                        "depth": depth,
                        "min_leaf": min_leaf,
                        "support": support,
                        "validation": val,
                        "nodes": int(model.tree_.node_count),
                    }
                )

    if not configs:
        result = {
            "schema": SCHEMA,
            "status": "NO_ZERO_ERROR_NORMAL_SEARCH_GUARD",
            "split_positions": {k: len(v) for k, v in splits.items()},
            "raw_probe_match_rates": {
                "train": sum(r["match"] for r in train) / len(train),
                "validation": sum(r["match"] for r in validation) / len(validation),
                "holdout": sum(r["match"] for r in holdout) / len(holdout),
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print("CRYSTAL_CHESS_SEARCH_SUFFICIENCY_V25=NO_ZERO_ERROR_NORMAL_SEARCH_GUARD")
        return 0

    configs.sort(
        key=lambda c: (
            -float(c["validation"]["estimated_node_reduction_ratio"]),
            -int(c["validation"]["covered"]),
            int(c["nodes"]),
            int(c["support"]),
        )
    )
    best = configs[0]
    model = best["model"]
    safe = best["safe"]
    train_eval = evaluate(model, safe, train)
    val_eval = best["validation"]
    holdout_eval = evaluate(model, safe, holdout)

    green = (
        val_eval["wrong"] == 0
        and holdout_eval["wrong"] == 0
        and holdout_eval["covered"] > 0
    )
    positive = holdout_eval["estimated_node_reduction_ratio"] > 0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_SUFFICIENCY_GUARD"
        if green and positive
        else "NORMAL_SEARCH_SUFFICIENCY_EXACT_RESIDUAL"
    )

    selection = {
        "max_depth": best["depth"],
        "min_samples_leaf": best["min_leaf"],
        "minimum_safe_leaf_support": best["support"],
        "tree_nodes": best["nodes"],
        "safe_leaf_count": len(safe),
    }
    guard_sha = export_guard(
        args.guard_output, model, safe, feature_names, selection
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source_run": V22_RUN,
        "split_rule": "V22 opening pair index modulo 3; cross-split repeated FENs removed",
        "split_positions": {k: len(v) for k, v in splits.items()},
        "probe_protocol": {
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "probe_total_nodes": PROBE_TOTAL_NODES,
            "probe2_reuses_probe1_tt": True,
            "authority_nodes": AUTHORITY_NODES,
            "probe_multipv": 2,
        },
        "raw_probe_match_rates": {
            "train": sum(r["match"] for r in train) / len(train),
            "validation": sum(r["match"] for r in validation) / len(validation),
            "holdout": sum(r["match"] for r in holdout) / len(holdout),
        },
        "selection": selection,
        "train": train_eval,
        "validation": val_eval,
        "holdout": holdout_eval,
        "guard": {
            "path": str(args.guard_output),
            "uncompressed_sha256": guard_sha,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "deep pinned Stockfish move is never a feature",
                "guard learned on acquisition and selected among zero-error validation configs",
                "untouched opening-pair holdout has zero wrong early-stop decisions",
                "holdout coverage exceeds the 5% probe overhead so expected node work is reduced",
            ],
            "unknown": [
                "performance on fresh opening corpus",
                "wall-clock systems gain",
                "self-play Elo gain",
                "chess-theoretic optimality of Stockfish authority move",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"CRYSTAL_CHESS_SEARCH_SUFFICIENCY_V25={status}")
    print(
        f"positions train/val/holdout={len(train)}/{len(validation)}/{len(holdout)} "
        f"raw_match={result['raw_probe_match_rates']}"
    )
    print(
        f"validation coverage={val_eval['covered']}/{val_eval['positions']} "
        f"wrong={val_eval['wrong']} est_reduction={val_eval['estimated_node_reduction_ratio']:.8f}"
    )
    print(
        f"holdout coverage={holdout_eval['covered']}/{holdout_eval['positions']} "
        f"wrong={holdout_eval['wrong']} est_reduction={holdout_eval['estimated_node_reduction_ratio']:.8f}"
    )
    print(f"guard_sha256={guard_sha}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
