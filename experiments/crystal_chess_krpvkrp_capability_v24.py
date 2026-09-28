#!/usr/bin/env python3
"""Crystal Chess V24: prospective KRPvKRP action-guard acquisition.

Source of relevance:
* V22 normal-game exposure selected KRPvKRP as the most frequent unsupported
  six-piece material class (348 occurrences / 174 unique positions).

Protocol:
* Split by V22 opening pair before looking at KRPvKRP labels:
    pair mod 3 = 0 acquisition, 1 validation, 2 untouched holdout.
* Remove any FEN occurring in more than one split.
* Exact Syzygy WDL is verifier authority.
* Learn a structural action partition only on acquisition actions.
* A leaf is an admissible capability only if it has support >= threshold and
  zero acquisition failures.
* Hyperparameters are selected on validation solely among zero-error configs.
* The untouched holdout is opened exactly once after selection.
* Emit the frozen decision-tree guard for later UCI integration.

Boundary is deliberately narrow: K+R+P vs K+R+P, no castling/en-passant,
halfmove clock zero, and neither pawn one move from promotion.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import sys

import chess
import chess.pgn
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier


SCHEMA = "mathgraph.crystal-chess.krpvkrp-action-guard.v24"
V22_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-normal-exposure-v22"
    "@ebd19051f4a09bf085f5c2beefae7d86e675cb20"
)
V22_RUN = 36361812786


def horizontal_square(sq: int) -> int:
    return chess.square(7 - chess.square_file(sq), chess.square_rank(sq))


def mirror_move(move: chess.Move) -> chess.Move:
    return chess.Move(
        chess.square_mirror(move.from_square),
        chess.square_mirror(move.to_square),
        promotion=move.promotion,
        drop=move.drop,
    )


def horizontal_move(move: chess.Move) -> chess.Move:
    return chess.Move(
        horizontal_square(move.from_square),
        horizontal_square(move.to_square),
        promotion=move.promotion,
        drop=move.drop,
    )


def exact_material(board: chess.Board) -> bool:
    if not board.is_valid():
        return False
    if board.castling_rights != chess.BB_EMPTY or board.ep_square is not None:
        return False
    if board.halfmove_clock != 0:
        return False
    for color in (chess.WHITE, chess.BLACK):
        if len(board.pieces(chess.KING, color)) != 1:
            return False
        if len(board.pieces(chess.ROOK, color)) != 1:
            return False
        if len(board.pieces(chess.PAWN, color)) != 1:
            return False
        if any(
            board.pieces(pt, color)
            for pt in (chess.QUEEN, chess.BISHOP, chess.KNIGHT)
        ):
            return False
    wp = next(iter(board.pieces(chess.PAWN, chess.WHITE)))
    bp = next(iter(board.pieces(chess.PAWN, chess.BLACK)))
    # Exclude any one-ply promotion dependency from this first capability gate.
    if chess.square_rank(wp) == 6 or chess.square_rank(bp) == 1:
        return False
    return not board.is_game_over(claim_draw=False)


def canonicalize(
    board: chess.Board, move: chess.Move
) -> tuple[chess.Board, chess.Move, bool, bool]:
    """Normalize side-to-move to White, then choose horizontal reflection."""
    color_mirrored = False
    if board.turn == chess.BLACK:
        board = board.mirror()
        move = mirror_move(move)
        color_mirrored = True

    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    wr = next(iter(board.pieces(chess.ROOK, chess.WHITE)))
    br = next(iter(board.pieces(chess.ROOK, chess.BLACK)))
    wp = next(iter(board.pieces(chess.PAWN, chess.WHITE)))
    bp = next(iter(board.pieces(chess.PAWN, chess.BLACK)))
    orig = (wk, wr, wp, bk, br, bp)
    refl = tuple(horizontal_square(s) for s in orig)
    horizontal = refl < orig
    if horizontal:
        board = board.transform(chess.flip_horizontal)
        move = horizontal_move(move)
    return board, move, color_mirrored, horizontal


def sgn(x: int) -> int:
    return (x > 0) - (x < 0)


def cheb(a: int, b: int) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def manhattan(a: int, b: int) -> int:
    return (
        abs(chess.square_file(a) - chess.square_file(b))
        + abs(chess.square_rank(a) - chess.square_rank(b))
    )


def edge(sq: int) -> int:
    f, r = chess.square_file(sq), chess.square_rank(sq)
    return min(f, 7 - f, r, 7 - r)


def features(board: chess.Board, move: chess.Move) -> tuple[list[str], tuple[int, ...]]:
    board, move, _cm, _hm = canonicalize(board.copy(stack=False), move)
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("move source empty after canonicalization")
    captured = board.piece_at(move.to_square)

    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    wr = next(iter(board.pieces(chess.ROOK, chess.WHITE)))
    br = next(iter(board.pieces(chess.ROOK, chess.BLACK)))
    wp = next(iter(board.pieces(chess.PAWN, chess.WHITE)))
    bp = next(iter(board.pieces(chess.PAWN, chess.BLACK)))
    assert wk is not None and bk is not None
    squares = [wk, wr, wp, bk, br, bp]
    labels = ["wk", "wr", "wp", "bk", "br", "bp"]

    ff, fr = chess.square_file(move.from_square), chess.square_rank(move.from_square)
    tf, tr = chess.square_file(move.to_square), chess.square_rank(move.to_square)
    df, dr = tf - ff, tr - fr

    child = board.copy(stack=False)
    child.push(move)

    names: list[str] = []
    vals: list[int] = []

    def add(name: str, value: int | bool) -> None:
        names.append(name)
        vals.append(int(value))

    add("mover_type", piece.piece_type)
    add("capture_type", captured.piece_type if captured else 0)
    add("is_capture", captured is not None)
    add("promotion_type", move.promotion or 0)
    add("move_df_sign", sgn(df))
    add("move_dr_sign", sgn(dr))
    add("move_abs_df", abs(df))
    add("move_abs_dr", abs(dr))
    add("from_edge", edge(move.from_square))
    add("to_edge", edge(move.to_square))
    add("from_rank", fr)
    add("to_rank", tr)
    add("gives_check", child.is_check())
    add("zeroing", board.is_zeroing(move))
    add("wp_rank", chess.square_rank(wp))
    add("bp_rank", chess.square_rank(bp))
    add("wp_file_edge", min(chess.square_file(wp), 7 - chess.square_file(wp)))
    add("bp_file_edge", min(chess.square_file(bp), 7 - chess.square_file(bp)))

    # Destination relation to each semantically typed piece.
    for lab, sq in zip(labels, squares):
        dx = tf - chess.square_file(sq)
        dy = tr - chess.square_rank(sq)
        add(f"to_{lab}_dx_sign", sgn(dx))
        add(f"to_{lab}_dy_sign", sgn(dy))
        add(f"to_{lab}_abs_dx", abs(dx))
        add(f"to_{lab}_abs_dy", abs(dy))
        add(f"to_{lab}_cheb", max(abs(dx), abs(dy)))

    # State relation bank. Exact relative geometry is available to the tree,
    # but no absolute FEN/state ID, WDL, DTZ or Stockfish score is present.
    for i in range(len(squares)):
        for j in range(i + 1, len(squares)):
            a, b = squares[i], squares[j]
            add(f"{labels[i]}_{labels[j]}_cheb", cheb(a, b))
            add(f"{labels[i]}_{labels[j]}_manhattan", manhattan(a, b))
            add(
                f"{labels[i]}_{labels[j]}_same_file",
                chess.square_file(a) == chess.square_file(b),
            )
            add(
                f"{labels[i]}_{labels[j]}_same_rank",
                chess.square_rank(a) == chess.square_rank(b),
            )

    return names, tuple(vals)


def extract_split_positions(pgn: Path) -> dict[str, list[chess.Board]]:
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
            pair = game_idx // 2
            split = ("train", "validation", "holdout")[pair % 3]
            board = game.board()
            positions = [board.copy(stack=False)]
            for move in game.mainline_moves():
                board.push(move)
                positions.append(board.copy(stack=False))
            for pos in positions:
                if not exact_material(pos):
                    continue
                fen = pos.fen()
                raw[split][fen] = pos
                fen_splits[fen].add(split)
            game_idx += 1

    # Remove cross-split repeats to make the prospective boundary strict.
    out: dict[str, list[chess.Board]] = {}
    for split in raw:
        out[split] = [
            board
            for fen, board in raw[split].items()
            if len(fen_splits[fen]) == 1
        ]
    return out


def action_records(
    tb: chess.syzygy.Tablebase, boards: list[chess.Board]
) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    feature_names: list[str] | None = None
    for sid, board in enumerate(boards):
        root = int(tb.probe_wdl(board))
        for move in list(board.legal_moves):
            # Boundary excluded one-ply promotion roots; keep assertion explicit.
            if move.promotion is not None:
                continue
            names, row = features(board, move)
            if feature_names is None:
                feature_names = names
            elif feature_names != names:
                raise AssertionError("feature order drift")
            child = board.copy(stack=False)
            child.push(move)
            consequence = -int(tb.probe_wdl(child))
            records.append(
                {
                    "state_id": sid,
                    "move": move.uci(),
                    "features": row,
                    "safe": consequence == root,
                    "root_wdl": root,
                    "child_wdl_for_root": consequence,
                }
            )
    if feature_names is None:
        feature_names = []
    return records, feature_names


def leaf_stats(
    model: DecisionTreeClassifier,
    records: list[dict[str, object]],
) -> dict[int, list[int]]:
    if not records:
        return {}
    X = np.asarray([r["features"] for r in records], dtype=np.int16)
    leaves = model.apply(X)
    out: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for leaf, rec in zip(leaves, records):
        out[int(leaf)][0] += 1
        out[int(leaf)][1] += int(not bool(rec["safe"]))
    return dict(out)


def evaluate(
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    records: list[dict[str, object]],
    state_count: int,
) -> dict[str, object]:
    by_state: dict[int, list[tuple[dict[str, object], int]]] = defaultdict(list)
    if records:
        X = np.asarray([r["features"] for r in records], dtype=np.int16)
        leaves = model.apply(X)
        for rec, leaf in zip(records, leaves):
            by_state[int(rec["state_id"])].append((rec, int(leaf)))

    covered = 0
    admitted_actions = 0
    wrong_actions = 0
    selected_wrong = 0
    selected_moves: list[dict[str, object]] = []
    for sid in range(state_count):
        candidates = [
            (rec, leaf)
            for rec, leaf in by_state.get(sid, [])
            if leaf in safe_leaves
        ]
        if not candidates:
            continue
        covered += 1
        admitted_actions += len(candidates)
        wrong_actions += sum(int(not bool(rec["safe"])) for rec, _ in candidates)

        # Deterministic runtime choice: strongest acquisition support, then UCI.
        candidates.sort(key=lambda rl: (-rl[1], str(rl[0]["move"])))
        chosen = candidates[0][0]
        selected_wrong += int(not bool(chosen["safe"]))
        if len(selected_moves) < 30:
            selected_moves.append(
                {
                    "state_id": sid,
                    "move": chosen["move"],
                    "safe": chosen["safe"],
                }
            )

    return {
        "states": state_count,
        "covered_states": covered,
        "coverage_ratio": covered / state_count if state_count else 0.0,
        "admitted_actions": admitted_actions,
        "wrong_actions": wrong_actions,
        "selected_wrong": selected_wrong,
        "examples": selected_moves,
    }


def export_guard(
    path: Path,
    model: DecisionTreeClassifier,
    safe_leaves: set[int],
    feature_names: list[str],
    selected: dict[str, object],
) -> str:
    tree = model.tree_
    payload = {
        "schema": SCHEMA + ".guard",
        "source": V22_AUTHORITY,
        "source_run": V22_RUN,
        "feature_names": feature_names,
        "safe_leaves": sorted(safe_leaves),
        "selection": selected,
        "tree": {
            "children_left": [int(x) for x in tree.children_left],
            "children_right": [int(x) for x in tree.children_right],
            "feature": [int(x) for x in tree.feature],
            "threshold": [float(x) for x in tree.threshold],
        },
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    import hashlib
    digest = hashlib.sha256(raw).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as handle:
        handle.write(raw)
    return digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pgn", type=Path, required=True)
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--guard-output", type=Path, required=True)
    args = ap.parse_args()

    splits = extract_split_positions(args.pgn)

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        train, feature_names = action_records(tb, splits["train"])
        validation, names2 = action_records(tb, splits["validation"])
        holdout, names3 = action_records(tb, splits["holdout"])

    if feature_names != names2 or feature_names != names3:
        raise AssertionError("split feature drift")
    if not train or not validation or not holdout:
        raise AssertionError(
            ("insufficient split corpus", {k: len(v) for k, v in splits.items()})
        )

    X_train = np.asarray([r["features"] for r in train], dtype=np.int16)
    y_train = np.asarray([int(bool(r["safe"])) for r in train], dtype=np.int8)

    candidates = []
    for depth in (3, 4, 5, 6, 8, 10, 12, 16, None):
        for min_leaf in (1, 2, 4, 8):
            model = DecisionTreeClassifier(
                criterion="entropy",
                splitter="best",
                max_depth=depth,
                min_samples_leaf=min_leaf,
                random_state=0,
            )
            model.fit(X_train, y_train)
            stats = leaf_stats(model, train)
            for support in (2, 4, 8):
                safe_leaves = {
                    leaf
                    for leaf, (count, failures) in stats.items()
                    if count >= support and failures == 0
                }
                if not safe_leaves:
                    continue
                val = evaluate(
                    model, safe_leaves, validation, len(splits["validation"])
                )
                if val["wrong_actions"] != 0 or val["selected_wrong"] != 0:
                    continue
                candidates.append(
                    {
                        "model": model,
                        "safe_leaves": safe_leaves,
                        "depth": depth,
                        "min_leaf": min_leaf,
                        "support": support,
                        "validation": val,
                        "nodes": int(model.tree_.node_count),
                    }
                )

    if not candidates:
        result = {
            "schema": SCHEMA,
            "status": "NO_ZERO_ERROR_VALIDATION_GUARD",
            "split_states": {k: len(v) for k, v in splits.items()},
            "action_counts": {
                "train": len(train),
                "validation": len(validation),
                "holdout": len(holdout),
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print("CRYSTAL_CHESS_KRPVKRP_CAPABILITY_V24=NO_ZERO_ERROR_VALIDATION_GUARD")
        return 0

    candidates.sort(
        key=lambda c: (
            -int(c["validation"]["covered_states"]),
            -int(c["validation"]["admitted_actions"]),
            int(c["nodes"]),
            int(c["support"]),
            999 if c["depth"] is None else int(c["depth"]),
        )
    )
    best = candidates[0]
    model = best["model"]
    safe_leaves = best["safe_leaves"]

    train_eval = evaluate(model, safe_leaves, train, len(splits["train"]))
    validation_eval = best["validation"]
    holdout_eval = evaluate(
        model, safe_leaves, holdout, len(splits["holdout"])
    )

    green = (
        validation_eval["wrong_actions"] == 0
        and holdout_eval["wrong_actions"] == 0
        and holdout_eval["selected_wrong"] == 0
        and holdout_eval["covered_states"] > 0
    )
    status = (
        "WARRANTED_PROSPECTIVE_KRPVKRP_ACTION_GUARD"
        if green
        else "EXACT_KRPVKRP_HOLDOUT_RESIDUAL"
    )

    selection = {
        "max_depth": best["depth"],
        "min_samples_leaf": best["min_leaf"],
        "minimum_safe_leaf_support": best["support"],
        "tree_nodes": best["nodes"],
        "safe_leaf_count": len(safe_leaves),
    }
    guard_sha = export_guard(
        args.guard_output, model, safe_leaves, feature_names, selection
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "source_relevance": {
            "v22_authority": V22_AUTHORITY,
            "v22_run": V22_RUN,
            "selected_residual": "KRPvKRP",
            "v22_occurrences": 348,
            "v22_unique_positions": 174,
        },
        "boundary": {
            "material": "KRPvKRP",
            "halfmove_clock": 0,
            "castling": False,
            "en_passant": False,
            "one_ply_promotion_excluded": True,
        },
        "split_rule": "V22 opening pair index modulo 3; cross-split FEN repeats removed",
        "split_states": {k: len(v) for k, v in splits.items()},
        "action_counts": {
            "train": len(train),
            "validation": len(validation),
            "holdout": len(holdout),
        },
        "safe_action_fraction_train": (
            sum(int(bool(r["safe"])) for r in train) / len(train)
        ),
        "selection": selection,
        "train": train_eval,
        "validation": validation_eval,
        "holdout": holdout_eval,
        "guard": {
            "path": str(args.guard_output),
            "uncompressed_sha256": guard_sha,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "guard tree trained only on acquisition actions",
                "hyperparameters selected only among zero-error validation configurations",
                "untouched holdout opened only after selection",
                "every admitted holdout action preserves exact Syzygy WDL",
            ],
            "unknown": [
                "coverage on new normal-game corpus",
                "DTZ quality inside WDL class",
                "Elo gain",
                "full KRPvKRP state-space zero-error",
            ],
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_KRPVKRP_CAPABILITY_V24={status}")
    print(
        f"states train/val/holdout={len(splits['train'])}/"
        f"{len(splits['validation'])}/{len(splits['holdout'])}"
    )
    print(
        f"validation coverage={validation_eval['covered_states']}/"
        f"{validation_eval['states']} wrong={validation_eval['wrong_actions']}"
    )
    print(
        f"holdout coverage={holdout_eval['covered_states']}/"
        f"{holdout_eval['states']} wrong={holdout_eval['wrong_actions']} "
        f"selected_wrong={holdout_eval['selected_wrong']}"
    )
    print(f"guard_sha256={guard_sha}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
