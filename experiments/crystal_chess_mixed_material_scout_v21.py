#!/usr/bin/env python3
"""Crystal Chess V21: prospective mixed-material constituent-capability scout.

Question:
Do exact capabilities learned independently on KXvK and KPvK survive when
their pieces coexist in KX+P v K?

No target labels influence either source policy. For every sampled target root:
1. project to KXvK; if that source position is valid, ask the frozen exact
   piece-family DTZ policy for one role and instantiate it back in the target;
2. project to KPvK; if valid, ask the frozen exact pawn policy for one role;
3. only then query exact target Syzygy WDL and audit whether either candidate
   preserves the root WDL.

This is a transfer census / scout, not an admitted mixed-material guard.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import random
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_dtz_certificate_v6 import probe_dtz_safe
from crystal_chess_kpvk_v0 import (
    coordinate_feature_bank,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy as acquire_pawn_policy,
    parse_role_move as parse_pawn_role,
    precompute_roles,
)
from crystal_chess_piece_family_v10 import (
    PIECE_MAP,
    features as piece_features,
    make_board as make_piece_board,
    optimal_roles as piece_optimal_roles,
)


SCHEMA = "mathgraph.crystal-chess.mixed-material-scout.v21"
SOURCE_PIECE_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-piece-family-v10"
    "@7446999cc1b25b9d44e812d4e192c9455910623e"
)
SOURCE_PAWN_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-kpvk-capability-lineage"
)


def make_target(
    wk: int,
    bk: int,
    x: int,
    pawn: int,
    turn: bool,
    piece_type: int,
) -> chess.Board:
    b = chess.Board(None)
    b.turn = turn
    b.castling_rights = chess.BB_EMPTY
    b.ep_square = None
    b.halfmove_clock = 0
    b.fullmove_number = 1
    b.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    b.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    b.set_piece_at(x, chess.Piece(piece_type, chess.WHITE))
    b.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return b


def acquire_piece_policy(
    tb: chess.syzygy.Tablebase,
    letter: str,
) -> tuple[DecisionTreeClassifier, dict[str, object]]:
    ptype = PIECE_MAP[letter]
    wcache: dict[tuple[str, bool], int] = {}
    dcache: dict[tuple[str, bool], int] = {}
    rows: list[tuple[int, ...]] = []
    role_sets: list[tuple[str, ...]] = []

    for x in chess.SQUARES:
        for wk in chess.SQUARES:
            if wk == x:
                continue
            for bk in chess.SQUARES:
                if bk in (wk, x):
                    continue
                for turn in (False, True):
                    b = make_piece_board(wk, bk, x, turn, ptype)
                    if not b.is_valid():
                        continue
                    rw = probe_wdl(tb, b, wcache)
                    rd = probe_dtz_safe(tb, b, dcache)
                    rs = piece_optimal_roles(
                        b, rw, rd, tb, wcache, dcache, letter
                    )
                    rows.append(piece_features(wk, bk, x, turn))
                    role_sets.append(rs)

    nonterm = [i for i, rs in enumerate(role_sets) if rs]
    frequency = Counter()
    for i in nonterm:
        frequency.update(role_sets[i])
    ranking = {
        role: k
        for k, (role, _n) in enumerate(
            sorted(frequency.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }
    labels = [
        min(role_sets[i], key=lambda role: (ranking[role], role))
        for i in nonterm
    ]
    tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    X = np.asarray(rows, dtype=np.int16)
    tree.fit(X[nonterm], labels)
    predicted = [str(x) for x in tree.predict(X[nonterm])]
    invalid = sum(
        pred not in role_sets[i]
        for i, pred in zip(nonterm, predicted)
    )
    if invalid:
        raise AssertionError(("source piece policy not exact", letter, invalid))
    return tree, {
        "source_states": len(rows),
        "source_nonterminal": len(nonterm),
        "source_roles": len(frequency),
        "audit_invalid": invalid,
    }


def parse_piece_role(
    board: chess.Board,
    x: int,
    role: str,
    letter: str,
) -> chess.Move | None:
    try:
        tag, body = role.split(":", 1)
        df_text, dr_text = body.split(",", 1)
        df, dr = int(df_text), int(dr_text)
    except Exception:
        return None
    source = board.king(chess.WHITE) if tag == "K" else x if tag == letter else None
    if source is None:
        return None
    f = chess.square_file(source) + df
    r = chess.square_rank(source) + dr
    if not (0 <= f < 8 and 0 <= r < 8):
        return None
    move = chess.Move(source, chess.square(f, r))
    return move if board.is_legal(move) else None


def sample_targets(
    rng: random.Random,
    n: int,
    piece_type: int,
) -> list[tuple[int, int, int, int, bool, chess.Board]]:
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)  # root ranks 2..6, no one-ply promotion
    ]
    out = []
    seen: set[str] = set()
    while len(out) < n:
        x = rng.choice(list(chess.SQUARES))
        pawn = rng.choice(pawn_squares)
        if x == pawn:
            continue
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        if wk in (x, pawn) or bk in (x, pawn):
            continue
        turn = bool(rng.getrandbits(1))
        board = make_target(wk, bk, x, pawn, turn, piece_type)
        if not board.is_valid() or not any(board.legal_moves):
            continue
        fen = board.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append((wk, bk, x, pawn, turn, board))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--piece", choices=sorted(PIECE_MAP), required=True)
    ap.add_argument("--sample-size", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    letter = args.piece
    ptype = PIECE_MAP[letter]
    rng = random.Random(args.seed + ord(letter))

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tb:
        piece_policy, piece_source = acquire_piece_policy(tb, letter)

        bank = coordinate_feature_bank()
        feature_fns = [fn for _name, fn in bank]
        pawn_policy, pawn_frequency, pawn_enum, pawn_nonterminal = (
            acquire_pawn_policy(tb, feature_fns)
        )
        pawn_squares = [
            chess.square(f, r)
            for f in range(8)
            for r in range(1, 6)
        ]
        pawn_roles = precompute_roles(
            pawn_policy, feature_fns, pawn_squares
        )

        targets = sample_targets(rng, args.sample_size, ptype)
        c = Counter()
        examples: list[dict[str, object]] = []

        for wk, bk, x, pawn, turn, board in targets:
            c["roots"] += 1
            root = int(tb.probe_wdl(board))

            candidates: list[tuple[str, chess.Move]] = []

            piece_projection = make_piece_board(
                wk, bk, x, turn, ptype
            )
            if piece_projection.is_valid() and any(piece_projection.legal_moves):
                c["piece_projection_valid"] += 1
                row = np.asarray(
                    [piece_features(wk, bk, x, turn)],
                    dtype=np.int16,
                )
                role = str(piece_policy.predict(row)[0])
                move = parse_piece_role(board, x, role, letter)
                if move is not None:
                    candidates.append(("piece", move))
                    c["piece_candidates"] += 1

            pawn_projection = make_kpvk(wk, bk, pawn, turn)
            if pawn_projection.is_valid() and any(pawn_projection.legal_moves):
                c["pawn_projection_valid"] += 1
                role = pawn_roles[(wk, bk, pawn, int(turn))]
                move = parse_pawn_role(board, pawn, role)
                if move is not None:
                    if not any(existing == move for _kind, existing in candidates):
                        candidates.append(("pawn", move))
                    c["pawn_candidates"] += 1

            if not candidates:
                c["no_candidate_roots"] += 1
                continue

            c["candidate_roots"] += 1
            any_safe = False
            first_safe = False
            for idx, (kind, move) in enumerate(candidates):
                child = board.copy(stack=False)
                child.push(move)
                consequence = -int(tb.probe_wdl(child))
                safe = consequence == root
                c[f"{kind}_safe"] += int(safe)
                c[f"{kind}_wrong"] += int(not safe)
                c["candidate_moves"] += 1
                c["safe_moves"] += int(safe)
                any_safe = any_safe or safe
                if idx == 0:
                    first_safe = safe
                if len(examples) < 30 and not safe:
                    examples.append(
                        {
                            "fen": board.fen(),
                            "kind": kind,
                            "move": move.uci(),
                            "root_wdl": root,
                            "child_consequence": consequence,
                        }
                    )

            c["any_safe_roots"] += int(any_safe)
            c["first_safe_roots"] += int(first_safe)

    roots = int(c["roots"])
    candidate_roots = int(c["candidate_roots"])
    result = {
        "schema": SCHEMA,
        "status": "CANDIDATE_PROSPECTIVE_MIXED_MATERIAL_TRANSFER_SCOUT",
        "piece": letter,
        "target_material": f"K{letter}PvK",
        "source_authorities": {
            "piece": SOURCE_PIECE_AUTHORITY,
            "pawn": SOURCE_PAWN_AUTHORITY,
        },
        "protocol": {
            "sample_size": args.sample_size,
            "seed": args.seed + ord(letter),
            "pawn_root_ranks": [2, 3, 4, 5, 6],
            "target_labels_used_for_candidate_generation": False,
        },
        "source_piece": piece_source,
        "source_pawn": {
            "nonterminal": pawn_nonterminal,
            "role_frequency": pawn_frequency,
            "enumeration": pawn_enum,
        },
        "census": {
            **dict(c),
            "candidate_root_ratio": candidate_roots / roots,
            "any_safe_root_ratio": c["any_safe_roots"] / roots,
            "first_safe_root_ratio": c["first_safe_roots"] / roots,
            "conditional_any_safe_ratio": (
                c["any_safe_roots"] / candidate_roots
                if candidate_roots else 0.0
            ),
            "candidate_move_precision": (
                c["safe_moves"] / c["candidate_moves"]
                if c["candidate_moves"] else 1.0
            ),
            "wrong_examples": examples,
        },
        "epistemic_boundary": {
            "interpretation": (
                "raw prospective candidate-set transfer only; no mixed-material "
                "guard has been acquired or admitted"
            ),
            "next_if_signal": (
                "compile a zero-false-positive guard only from exact residuals, "
                "then transfer it to a richer mixed-material family"
            ),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_MIXED_MATERIAL_SCOUT_V21=PASS")
    print(
        f"piece={letter} roots={roots} candidate_roots={candidate_roots} "
        f"any_safe={c['any_safe_roots']} ratio={c['any_safe_roots']/roots:.8f} "
        f"first_safe={c['first_safe_roots']/roots:.8f} "
        f"move_precision={result['census']['candidate_move_precision']:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
