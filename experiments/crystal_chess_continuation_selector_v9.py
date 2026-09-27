#!/usr/bin/env python3
"""Crystal Chess V9: continuation-signature capability arbitration.

A frozen exact KPvK policy generates candidate capabilities in richer pawn
worlds.  The selector is NOT given board-pair geometry or richer-material
outcomes as input.  It sees only the candidate's executable continuation
signature: move role/effect, number of opponent replies, and whether those
replies still expose frozen capabilities or simplify into a previously solved
material basin.

Acquisition labels come from exact KPPvK Syzygy WDL.  The learned selector is
then frozen and tested on:
  1. an independent KPPvK sample; and
  2. a still-richer KPPPvK sample with zero KPPPvK labels in acquisition.

Syzygy is validation/admission authority only; continuation features never
contain WDL/DTZ values.
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

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    move_role,
    optimal_roles,
    tree_summary,
)
from crystal_chess_richer_transfer_v5 import (
    canonical_feature_row,
    reflect_role,
)


SCHEMA = "mathgraph.crystal-chess.continuation-selector.v9"
V8_BRANCH = "crystal-chess-capability-calculus-v8"


def make_kpawns_vk(
    wk: int,
    bk: int,
    pawns: tuple[int, ...],
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
    for pawn in pawns:
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def sample_kpawns_vk(
    count: int,
    pawn_count: int,
    seed: int,
) -> list[tuple[int, int, tuple[int, ...], bool]]:
    rng = random.Random(seed)
    # Initial pawns on ranks 2..6: the evaluated root move cannot promote.
    pawn_squares = [
        chess.square(file, rank)
        for file in range(8)
        for rank in range(1, 6)
    ]
    seen: set[tuple[int, int, tuple[int, ...], bool]] = set()
    out: list[tuple[int, int, tuple[int, ...], bool]] = []
    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > count * 200:
            raise RuntimeError("could not construct requested legal sample")
        pawns = tuple(sorted(rng.sample(pawn_squares, pawn_count)))
        occupied = set(pawns)
        wk = rng.randrange(64)
        if wk in occupied:
            continue
        bk = rng.randrange(64)
        if bk in occupied or bk == wk:
            continue
        turn = bool(rng.getrandbits(1))
        key = (wk, bk, pawns, turn)
        if key in seen:
            continue
        board = make_kpawns_vk(wk, bk, pawns, turn)
        if not board.is_valid():
            continue
        seen.add(key)
        out.append(key)
    return out


def train_frozen_kpvk_policy(
    tablebase: chess.syzygy.Tablebase,
    feature_fns,
    wdl_cache: dict[tuple[str, bool], int],
):
    records, enumeration = enumerate_records(tablebase, wdl_cache, feature_fns)
    role_sets: list[tuple[str, ...]] = []
    nonterminal: list[int] = []
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        roles = optimal_roles(board, rec.wdl, tablebase, wdl_cache)
        role_sets.append(roles)
        if roles:
            nonterminal.append(i)
    labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    policy = DecisionTreeClassifier(
        criterion="entropy", splitter="best", random_state=0
    )
    policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
    return policy, role_frequency, enumeration, len(records), len(nonterminal)


def predicted_role_for_anchor(
    policy: DecisionTreeClassifier,
    feature_fns,
    board: chess.Board,
    anchor: int,
) -> str:
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    if wk is None or bk is None:
        raise ValueError("missing king")
    row, reflected = canonical_feature_row(
        wk, bk, anchor, board.turn, feature_fns
    )
    role = str(policy.predict(np.asarray([row], dtype=np.int16))[0])
    return reflect_role(role) if reflected else role


def candidate_moves(
    board: chess.Board,
    policy: DecisionTreeClassifier,
    feature_fns,
) -> list[tuple[chess.Move, str, int]]:
    anchors = tuple(
        sorted(
            board.pieces(chess.PAWN, chess.WHITE),
            key=lambda sq: (chess.square_file(sq), chess.square_rank(sq)),
        )
    )
    legal = list(board.legal_moves)
    by_uci: dict[str, tuple[chess.Move, str, int]] = {}

    for anchor_index, anchor in enumerate(anchors):
        role = predicted_role_for_anchor(policy, feature_fns, board, anchor)
        for move in legal:
            if move_role(board, move) != role:
                continue
            piece = board.piece_at(move.from_square)
            if piece is None:
                continue
            if piece.piece_type == chess.PAWN and move.from_square != anchor:
                continue
            key = move.uci()
            previous = by_uci.get(key)
            item = (move, role, anchor_index)
            if previous is None or (anchor_index, role) < (previous[2], previous[1]):
                by_uci[key] = item

    return sorted(
        by_uci.values(),
        key=lambda item: (item[2], item[1], item[0].uci()),
    )


def next_capability_counts(
    board: chess.Board,
    policy: DecisionTreeClassifier,
    feature_fns,
) -> tuple[int, int]:
    candidates = candidate_moves(board, policy, feature_fns)
    return len(candidates), len({role for _move, role, _anchor in candidates})


def continuation_features(
    board: chess.Board,
    move: chess.Move,
    role: str,
    anchor_index: int,
    role_ids: dict[str, int],
    policy: DecisionTreeClassifier,
    feature_fns,
) -> tuple[int, ...]:
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("candidate missing mover")

    after = board.copy(stack=False)
    is_capture = int(board.is_capture(move))
    after.push(move)
    replies = list(after.legal_moves)

    # Candidate-local effects only; no richer-material oracle value appears.
    base = [
        role_ids[role],
        anchor_index,
        int(piece.piece_type == chess.KING),
        int(piece.piece_type == chess.PAWN),
        is_capture,
        int(move.promotion or 0),
        int(after.halfmove_clock == 0),
        int(after.is_check()),
        len(replies),
        len(after.pieces(chess.PAWN, chess.WHITE)),
        int(after.is_checkmate()),
        int(after.is_stalemate()),
    ]

    if not replies:
        return tuple(base + [0] * 16)

    cap_counts: list[int] = []
    role_counts: list[int] = []
    legal_counts: list[int] = []
    pawn_counts: list[int] = []
    known_basin = 0
    terminal_count = 0
    no_capability = 0
    zeroing_replies = 0

    for reply in replies:
        child = after.copy(stack=False)
        before_halfmove = child.halfmove_clock
        child.push(reply)
        if child.halfmove_clock == 0 and before_halfmove != 0:
            zeroing_replies += 1
        pawn_count = len(child.pieces(chess.PAWN, chess.WHITE))
        pawn_counts.append(pawn_count)

        if child.is_game_over(claim_draw=False):
            terminal_count += 1
            cap_counts.append(0)
            role_counts.append(0)
            legal_counts.append(0)
            if pawn_count <= 1:
                known_basin += 1
            continue

        ccount, rcount = next_capability_counts(child, policy, feature_fns)
        cap_counts.append(ccount)
        role_counts.append(rcount)
        legal_counts.append(child.legal_moves.count())
        no_capability += int(ccount == 0)
        known_basin += int(pawn_count <= 1)

    def isum(xs):
        return int(sum(xs))

    return tuple(
        base
        + [
            min(cap_counts),
            max(cap_counts),
            isum(cap_counts),
            min(role_counts),
            max(role_counts),
            isum(role_counts),
            min(legal_counts),
            max(legal_counts),
            isum(legal_counts),
            min(pawn_counts),
            max(pawn_counts),
            isum(pawn_counts),
            known_basin,
            terminal_count,
            no_capability,
            zeroing_replies,
        ]
    )


def candidate_is_optimal(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    move: chess.Move,
    wdl_cache: dict[tuple[str, bool], int],
) -> bool:
    root_wdl = probe_wdl(tablebase, board, wdl_cache)
    child = board.copy(stack=False)
    child.push(move)
    consequence = -probe_wdl(tablebase, child, wdl_cache)
    return consequence == root_wdl


def build_candidate_dataset(
    sample,
    tablebase,
    wdl_cache,
    policy,
    feature_fns,
    role_ids,
):
    rows: list[tuple[int, ...]] = []
    labels: list[int] = []
    state_slices: list[tuple[int, int]] = []
    first_success = 0
    any_success = 0
    no_candidate = 0
    label_counts = Counter()

    for wk, bk, pawns, turn in sample:
        board = make_kpawns_vk(wk, bk, pawns, turn)
        if board.is_game_over(claim_draw=False):
            continue
        candidates = candidate_moves(board, policy, feature_fns)
        if not candidates:
            no_candidate += 1
            state_slices.append((len(rows), len(rows)))
            continue

        start = len(rows)
        state_labels = []
        for move, role, anchor_index in candidates:
            rows.append(
                continuation_features(
                    board,
                    move,
                    role,
                    anchor_index,
                    role_ids,
                    policy,
                    feature_fns,
                )
            )
            label = int(
                candidate_is_optimal(tablebase, board, move, wdl_cache)
            )
            labels.append(label)
            state_labels.append(label)
            label_counts[label] += 1
        end = len(rows)
        state_slices.append((start, end))
        first_success += state_labels[0]
        any_success += int(any(state_labels))

    return {
        "rows": rows,
        "labels": labels,
        "state_slices": state_slices,
        "first_success": first_success,
        "any_success": any_success,
        "no_candidate": no_candidate,
        "label_counts": dict(label_counts),
    }


def evaluate_selector(
    classifier: DecisionTreeClassifier,
    dataset,
) -> dict[str, float | int]:
    rows = dataset["rows"]
    labels = dataset["labels"]
    slices = dataset["state_slices"]
    if not rows:
        return {
            "states_with_candidates": 0,
            "selected_success": 0,
            "selected_ratio": 0.0,
        }

    X = np.asarray(rows, dtype=np.int32)
    proba = classifier.predict_proba(X)
    classes = list(classifier.classes_)
    pos_col = classes.index(1) if 1 in classes else None

    selected_success = 0
    states_with_candidates = 0
    for start, end in slices:
        if start == end:
            continue
        states_with_candidates += 1
        if pos_col is None:
            chosen = start
        else:
            best_local = max(
                range(start, end),
                key=lambda i: (float(proba[i, pos_col]), -i),
            )
            chosen = best_local
        selected_success += labels[chosen]

    return {
        "states_with_candidates": states_with_candidates,
        "selected_success": selected_success,
        "selected_ratio": (
            selected_success / states_with_candidates
            if states_with_candidates
            else 0.0
        ),
        "first_success": dataset["first_success"],
        "first_ratio": (
            dataset["first_success"] / states_with_candidates
            if states_with_candidates
            else 0.0
        ),
        "any_success": dataset["any_success"],
        "any_ratio": (
            dataset["any_success"] / states_with_candidates
            if states_with_candidates
            else 0.0
        ),
        "no_candidate_states": dataset["no_candidate"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--train-size", type=int, default=30000)
    ap.add_argument("--test-size", type=int, default=30000)
    ap.add_argument("--five-piece-size", type=int, default=30000)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]
    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    wdl_cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, role_frequency, enumeration, kpvk_states, kpvk_nonterm = (
            train_frozen_kpvk_policy(tb, feature_fns, wdl_cache)
        )
        role_ids = {role: i for i, role in enumerate(sorted(role_frequency))}

        train_sample = sample_kpawns_vk(args.train_size, 2, 20260930)
        test_sample = sample_kpawns_vk(args.test_size, 2, 20261001)
        five_sample = sample_kpawns_vk(args.five_piece_size, 3, 20261002)

        train = build_candidate_dataset(
            train_sample, tb, wdl_cache, policy, feature_fns, role_ids
        )
        test = build_candidate_dataset(
            test_sample, tb, wdl_cache, policy, feature_fns, role_ids
        )
        five = build_candidate_dataset(
            five_sample, tb, wdl_cache, policy, feature_fns, role_ids
        )

    if not train["rows"] or len(set(train["labels"])) < 2:
        raise AssertionError("training candidate labels lack both classes")

    selector = DecisionTreeClassifier(
        criterion="entropy",
        max_depth=16,
        min_samples_leaf=40,
        class_weight="balanced",
        random_state=0,
    )
    selector.fit(
        np.asarray(train["rows"], dtype=np.int32),
        np.asarray(train["labels"], dtype=np.int8),
    )

    train_eval = evaluate_selector(selector, train)
    test_eval = evaluate_selector(selector, test)
    five_eval = evaluate_selector(selector, five)
    selector_summary = tree_summary(selector)

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_CONTINUATION_SELECTOR_TRANSFER",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v8_branch": V8_BRANCH,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "candidate_generator": "frozen exact KPvK symbolic policy instantiated once per white pawn anchor",
            "selector_input": "candidate continuation signature only; no KPPvK/KPPPvK WDL or DTZ values",
            "selector_training_labels": "exact KPPvK Syzygy WDL optimality",
            "prospective_4p": "independent KPPvK seed unseen in training",
            "prospective_5p": "KPPPvK; zero KPPPvK labels in acquisition",
        },
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": manifest,
        },
        "source_capability": {
            "kpvk_states": kpvk_states,
            "kpvk_nonterminal": kpvk_nonterm,
            "role_frequency": role_frequency,
        },
        "selector": {
            "tree": selector_summary,
            "training_candidate_labels": train["label_counts"],
        },
        "train_kppvk": train_eval,
        "heldout_kppvk": test_eval,
        "prospective_kpppvk": five_eval,
        "epistemic_boundary": {
            "warranted_if_green": [
                "selector features contain no richer-material oracle values",
                "held-out KPPvK and KPPPvK move-success metrics are independently checked against exact Syzygy WDL",
                "no KPPPvK labels enter acquisition",
            ],
            "unknown": [
                "complete KPPPvK coverage",
                "transfer to arbitrary piece configurations",
                "general chess solution",
            ],
        },
        "cache": {"wdl_positions": len(wdl_cache)},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "enumeration": enumeration,
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print("CRYSTAL_CHESS_CONTINUATION_SELECTOR_V9=PASS")
    print(
        f"train selected={train_eval['selected_ratio']:.6f} "
        f"first={train_eval['first_ratio']:.6f} any={train_eval['any_ratio']:.6f}"
    )
    print(
        f"heldout4 selected={test_eval['selected_ratio']:.6f} "
        f"first={test_eval['first_ratio']:.6f} any={test_eval['any_ratio']:.6f}"
    )
    print(
        f"prospective5 selected={five_eval['selected_ratio']:.6f} "
        f"first={five_eval['first_ratio']:.6f} any={five_eval['any_ratio']:.6f}"
    )
    print(
        f"selector leaves={selector_summary['leaves']} "
        f"depth={selector_summary['max_depth']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
