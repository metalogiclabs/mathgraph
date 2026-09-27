#!/usr/bin/env python3
"""Crystal Chess V1: transferable action-congruence discovery on exact KPvK.

Goal: learn a constructive equivalence relation on legal moves that permits
one representative per schema class while preserving exact Syzygy minimax.

Data split is structural, not random:
  pawn files a,b -> discovery train
  pawn file c    -> development separator repair
  pawn file d    -> untouched final transfer test

The learner never uses WDL as a feature. WDL is verifier authority only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.syzygy

from experiments.crystal_chess_kpvk_v0 import (
    WDL_INDEX,
    WDL_VALUES,
    edge_distance,
    make_kpvk,
    probe_wdl,
)

SCHEMA = "mathgraph.crystal-chess.action-congruence.v1"
BASE_AUTHORITY = "metalogiclabs/mathgraph@d8da8268068e7d94950aadeea53ad74906683355"


@dataclass(frozen=True)
class ActionRecord:
    state_id: int
    pawn_file: int
    root_wdl: int
    move_uci: str
    consequence: int
    features: tuple[int, ...]


def sign(x: int) -> int:
    return (x > 0) - (x < 0)


def cheb(a: int, b: int) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def manhattan(a: int, b: int) -> int:
    return abs(chess.square_file(a) - chess.square_file(b)) + abs(
        chess.square_rank(a) - chess.square_rank(b)
    )


def promo_square(pawn: int) -> int:
    return chess.square(chess.square_file(pawn), 7)


def piece_square(board: chess.Board, piece_type: int, color: bool) -> int | None:
    squares = board.pieces(piece_type, color)
    if not squares:
        return None
    return next(iter(squares))


def terminal_code(board: chess.Board) -> int:
    if board.is_checkmate():
        return 1
    if board.is_stalemate():
        return 2
    if board.is_insufficient_material():
        return 3
    return 0


def relation_values(square: int, anchor: int) -> tuple[int, int, int, int, int]:
    dx = chess.square_file(square) - chess.square_file(anchor)
    dy = chess.square_rank(square) - chess.square_rank(anchor)
    return sign(dx), sign(dy), abs(dx), abs(dy), max(abs(dx), abs(dy))


def delta_relation(before: int, after: int | None) -> int:
    if after is None:
        return 9
    return sign(after - before)


def move_feature_bank(board: chess.Board, move: chess.Move) -> dict[str, int]:
    mover = board.piece_at(move.from_square)
    if mover is None:
        raise AssertionError("legal move has no mover")
    captured = board.piece_at(move.to_square)

    wk0 = piece_square(board, chess.KING, chess.WHITE)
    bk0 = piece_square(board, chess.KING, chess.BLACK)
    p0 = piece_square(board, chess.PAWN, chess.WHITE)
    if wk0 is None or bk0 is None or p0 is None:
        raise AssertionError("root is not KPvK")
    ps0 = promo_square(p0)

    mover0_to_pawn = cheb(move.from_square, p0)
    mover0_to_promo = cheb(move.from_square, ps0)
    mover0_to_other_king = cheb(move.from_square, bk0 if mover.color else wk0)
    mover0_edge = edge_distance(move.from_square)

    child = board.copy(stack=False)
    child.push(move)

    wk1 = piece_square(child, chess.KING, chess.WHITE)
    bk1 = piece_square(child, chess.KING, chess.BLACK)
    p1 = piece_square(child, chess.PAWN, chess.WHITE)
    other1 = bk1 if mover.color else wk1

    moved_to = move.to_square
    to_pawn_rel = relation_values(moved_to, p0)
    to_promo_rel = relation_values(moved_to, ps0)
    to_other_rel = relation_values(moved_to, bk0 if mover.color else wk0)

    mover1_to_pawn = cheb(moved_to, p1) if p1 is not None else None
    mover1_to_promo = cheb(moved_to, promo_square(p1)) if p1 is not None else None
    mover1_to_other = cheb(moved_to, other1) if other1 is not None else None

    king_distance0 = cheb(wk0, bk0)
    king_distance1 = cheb(wk1, bk1) if wk1 is not None and bk1 is not None else 99
    wk_pawn0 = cheb(wk0, p0)
    bk_pawn0 = cheb(bk0, p0)
    wk_pawn1 = cheb(wk1, p1) if wk1 is not None and p1 is not None else 99
    bk_pawn1 = cheb(bk1, p1) if bk1 is not None and p1 is not None else 99

    if p1 is not None:
        p1_file = chess.square_file(p1)
        p1_rank = chess.square_rank(p1)
        ps1 = promo_square(p1)
        wk_promo1 = cheb(wk1, ps1) if wk1 is not None else 99
        bk_promo1 = cheb(bk1, ps1) if bk1 is not None else 99
        bk_same_file = int(bk1 is not None and chess.square_file(bk1) == p1_file)
        wk_same_file = int(wk1 is not None and chess.square_file(wk1) == p1_file)
        bk_ahead = int(
            bk1 is not None
            and chess.square_file(bk1) == p1_file
            and chess.square_rank(bk1) > p1_rank
        )
        wk_ahead = int(
            wk1 is not None
            and chess.square_file(wk1) == p1_file
            and chess.square_rank(wk1) > p1_rank
        )
        p_rank = p1_rank
        p_steps = 7 - p1_rank
    else:
        wk_promo1 = bk_promo1 = 99
        bk_same_file = wk_same_file = bk_ahead = wk_ahead = 0
        p_rank = p_steps = -1

    same_axis_kings = 0
    opposition_gap = 0
    if wk1 is not None and bk1 is not None:
        same_axis_kings = int(
            chess.square_file(wk1) == chess.square_file(bk1)
            or chess.square_rank(wk1) == chess.square_rank(bk1)
        )
        opposition_gap = int(same_axis_kings and cheb(wk1, bk1) == 2)

    pawn_push = 0
    if mover.piece_type == chess.PAWN:
        pawn_push = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)

    return {
        "mover_type": mover.piece_type,
        "is_capture": int(captured is not None),
        "captured_type": captured.piece_type if captured is not None else 0,
        "is_promotion": int(move.promotion is not None),
        "promotion_type": move.promotion or 0,
        "pawn_push": pawn_push,
        "child_gives_check": int(child.is_check()),
        "child_terminal": terminal_code(child),
        "mover_toward_pawn": delta_relation(mover0_to_pawn, mover1_to_pawn),
        "mover_toward_promo": delta_relation(mover0_to_promo, mover1_to_promo),
        "mover_toward_other_king": delta_relation(mover0_to_other_king, mover1_to_other),
        "mover_edge_change": sign(edge_distance(moved_to) - mover0_edge),
        "to_pawn_file_side": to_pawn_rel[0],
        "to_pawn_rank_side": to_pawn_rel[1],
        "to_pawn_file_distance": to_pawn_rel[2],
        "to_pawn_rank_distance": to_pawn_rel[3],
        "to_pawn_cheb": to_pawn_rel[4],
        "to_promo_file_side": to_promo_rel[0],
        "to_promo_rank_side": to_promo_rel[1],
        "to_promo_cheb": to_promo_rel[4],
        "to_other_king_file_side": to_other_rel[0],
        "to_other_king_rank_side": to_other_rel[1],
        "to_other_king_cheb": to_other_rel[4],
        "king_distance_change": sign(king_distance1 - king_distance0),
        "wk_pawn_distance_change": sign(wk_pawn1 - wk_pawn0),
        "bk_pawn_distance_change": sign(bk_pawn1 - bk_pawn0),
        "after_wk_pawn_cheb": wk_pawn1,
        "after_bk_pawn_cheb": bk_pawn1,
        "after_wk_promo_cheb": wk_promo1,
        "after_bk_promo_cheb": bk_promo1,
        "after_pawn_rank": p_rank,
        "after_pawn_steps": p_steps,
        "after_wk_same_file_pawn": wk_same_file,
        "after_bk_same_file_pawn": bk_same_file,
        "after_wk_ahead_pawn": wk_ahead,
        "after_bk_ahead_pawn": bk_ahead,
        "after_same_axis_kings": same_axis_kings,
        "after_opposition_gap": opposition_gap,
        "to_edge_distance": edge_distance(moved_to),
        "to_center_ring": min(
            abs(chess.square_file(moved_to) - 3),
            abs(chess.square_file(moved_to) - 4),
        )
        + min(
            abs(chess.square_rank(moved_to) - 3),
            abs(chess.square_rank(moved_to) - 4),
        ),
        "to_square_parity": (chess.square_file(moved_to) + chess.square_rank(moved_to)) & 1,
    }


def collect_actions(
    tablebase: chess.syzygy.Tablebase,
) -> tuple[list[ActionRecord], list[str], dict[str, int]]:
    cache: dict[tuple[str, bool], int] = {}
    feature_names: list[str] | None = None
    out: list[ActionRecord] = []
    state_id = 0
    stats = Counter()

    for pawn_file in range(4):
        for pawn_rank in range(1, 7):
            pawn = chess.square(pawn_file, pawn_rank)
            for wk in chess.SQUARES:
                if wk == pawn:
                    continue
                for bk in chess.SQUARES:
                    if bk in (pawn, wk):
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        board = make_kpvk(wk, bk, pawn, turn)
                        if not board.is_valid():
                            continue
                        root_wdl = probe_wdl(tablebase, board, cache)
                        legal = list(board.legal_moves)
                        stats["states"] += 1
                        stats[f"states_file_{pawn_file}"] += 1
                        if not legal:
                            stats["terminal_states"] += 1
                            state_id += 1
                            continue
                        for move in legal:
                            child = board.copy(stack=False)
                            child.push(move)
                            consequence = -probe_wdl(tablebase, child, cache)
                            feat = move_feature_bank(board, move)
                            if feature_names is None:
                                feature_names = list(feat)
                            elif list(feat) != feature_names:
                                raise AssertionError("feature order drift")
                            out.append(
                                ActionRecord(
                                    state_id=state_id,
                                    pawn_file=pawn_file,
                                    root_wdl=root_wdl,
                                    move_uci=move.uci(),
                                    consequence=consequence,
                                    features=tuple(feat[n] for n in feature_names),
                                )
                            )
                            stats["moves"] += 1
                            stats[f"moves_file_{pawn_file}"] += 1
                        state_id += 1
    if feature_names is None:
        raise AssertionError("no moves")
    stats["unique_wdl_cache"] = len(cache)
    return out, feature_names, dict(stats)


def split_records(records: Iterable[ActionRecord], files: set[int]) -> list[ActionRecord]:
    return [r for r in records if r.pawn_file in files]


def evaluate(
    records: list[ActionRecord],
    selected: tuple[int, ...],
) -> dict[str, object]:
    per_state: dict[int, list[ActionRecord]] = defaultdict(list)
    for r in records:
        per_state[r.state_id].append(r)

    raw_moves = len(records)
    oracle_classes = 0
    schema_classes = 0
    conflict_mass = 0
    impure_groups = 0
    impure_states = 0
    minimax_mismatches = 0
    examples: list[dict[str, object]] = []

    for state, actions in per_state.items():
        oracle_classes += len({a.consequence for a in actions})
        groups: dict[tuple[int, ...], list[ActionRecord]] = defaultdict(list)
        for a in actions:
            key = tuple(a.features[i] for i in selected)
            groups[key].append(a)
        schema_classes += len(groups)
        state_impure = False
        reps = []
        for key, group in groups.items():
            labels = Counter(a.consequence for a in group)
            total = len(group)
            majority = max(labels.values())
            conflict_mass += total - majority
            if len(labels) > 1:
                impure_groups += 1
                state_impure = True
                if len(examples) < 12:
                    examples.append(
                        {
                            "state_id": state,
                            "schema": list(key),
                            "moves": sorted(
                                (a.move_uci, a.consequence) for a in group
                            ),
                        }
                    )
            reps.append(min(group, key=lambda a: a.move_uci))
        impure_states += int(state_impure)
        pruned = max(a.consequence for a in reps)
        root = actions[0].root_wdl
        if pruned != root:
            minimax_mismatches += 1

    states = len(per_state)
    return {
        "states": states,
        "raw_moves": raw_moves,
        "oracle_action_classes": oracle_classes,
        "schema_action_classes": schema_classes,
        "oracle_compression": raw_moves / oracle_classes if oracle_classes else 1.0,
        "schema_compression": raw_moves / schema_classes if schema_classes else 1.0,
        "overfragmentation_vs_oracle": (
            schema_classes / oracle_classes if oracle_classes else 1.0
        ),
        "conflict_mass": conflict_mass,
        "impure_groups": impure_groups,
        "impure_states": impure_states,
        "pruned_minimax_mismatches": minimax_mismatches,
        "examples": examples,
    }


def choose_next_feature(
    records: list[ActionRecord],
    selected: tuple[int, ...],
    remaining: set[int],
) -> tuple[int | None, dict[str, object], dict[str, object]]:
    base = evaluate(records, selected)
    scored = []
    for idx in sorted(remaining):
        trial = selected + (idx,)
        ev = evaluate(records, trial)
        scored.append(
            (
                int(ev["conflict_mass"]),
                int(ev["schema_action_classes"]),
                int(ev["pruned_minimax_mismatches"]),
                idx,
                ev,
            )
        )
    if not scored:
        return None, base, base
    best = min(scored, key=lambda x: (x[0], x[2], x[1], x[3]))
    if best[0] >= int(base["conflict_mass"]):
        return None, base, best[4]
    return best[3], base, best[4]


def refine_to_purity(
    records: list[ActionRecord],
    feature_names: list[str],
    selected: tuple[int, ...] = (),
    stage: str = "train",
) -> tuple[tuple[int, ...], list[dict[str, object]]]:
    remaining = set(range(len(feature_names))) - set(selected)
    trace: list[dict[str, object]] = []
    current = evaluate(records, selected)
    trace.append({"stage": stage, "event": "start", "selected": [feature_names[i] for i in selected], **current})

    while int(current["conflict_mass"]) > 0:
        idx, base, best = choose_next_feature(records, selected, remaining)
        if idx is None:
            trace.append(
                {
                    "stage": stage,
                    "event": "no_separator",
                    "selected": [feature_names[i] for i in selected],
                    **base,
                }
            )
            break
        selected = selected + (idx,)
        remaining.remove(idx)
        current = best
        trace.append(
            {
                "stage": stage,
                "event": "add",
                "feature": feature_names[idx],
                "selected": [feature_names[i] for i in selected],
                **current,
            }
        )

    # Backward inclusion minimization while retaining zero conflict.
    if int(current["conflict_mass"]) == 0:
        changed = True
        while changed:
            changed = False
            for idx in tuple(selected):
                trial = tuple(i for i in selected if i != idx)
                ev = evaluate(records, trial)
                if int(ev["conflict_mass"]) == 0:
                    selected = trial
                    current = ev
                    trace.append(
                        {
                            "stage": stage,
                            "event": "drop",
                            "feature": feature_names[idx],
                            "selected": [feature_names[i] for i in selected],
                            **current,
                        }
                    )
                    changed = True
                    break
    return selected, trace


def hash_files(directory: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(directory.glob("*.rtbw")):
        rows.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        records, feature_names, collection = collect_actions(tb)

    train = split_records(records, {0, 1})
    dev = split_records(records, {2})
    test = split_records(records, {3})

    selected, train_trace = refine_to_purity(
        train, feature_names, stage="train_ab"
    )
    train_eval = evaluate(train, selected)
    dev_before = evaluate(dev, selected)

    dev_trace: list[dict[str, object]] = []
    if int(dev_before["conflict_mass"]) > 0:
        selected, dev_trace = refine_to_purity(
            dev, feature_names, selected=selected, stage="dev_c_repair"
        )

    train_final = evaluate(train, selected)
    dev_final = evaluate(dev, selected)
    test_final = evaluate(test, selected)

    transfer_exact = (
        int(test_final["conflict_mass"]) == 0
        and int(test_final["pruned_minimax_mismatches"]) == 0
    )
    status = (
        "WARRANTED_HELDOUT_KPVK_ACTION_CONGRUENCE"
        if transfer_exact
        else "CANDIDATE_ACTION_CONGRUENCE_WITH_HELDOUT_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_authority": BASE_AUTHORITY,
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": hash_files(args.tablebase_dir),
        },
        "split": {
            "train": "pawn files a,b",
            "development": "pawn file c",
            "final_untouched_test": "pawn file d",
        },
        "collection": collection,
        "candidate_features": feature_names,
        "selected_features": [feature_names[i] for i in selected],
        "selection": {
            "train_trace": train_trace,
            "dev_before": dev_before,
            "dev_trace": dev_trace,
        },
        "final": {
            "train": train_final,
            "development": dev_final,
            "test": test_final,
        },
        "claim_boundary": {
            "warranted_if_transfer_exact": (
                "on the declared KPvK boundary, equal selected action schemas "
                "are consequence-pure on the untouched d-file cover and one "
                "lexicographic representative per schema preserves exact minimax"
            ),
            "not_claimed": [
                "global minimum schema",
                "transfer to other material classes",
                "general chess solution",
            ],
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    print(f"CRYSTAL_CHESS_ACTION_CONGRUENCE_V1={status}")
    print("selected_features=" + ",".join(result["selected_features"]))
    for name, ev in (("train", train_final), ("dev", dev_final), ("test", test_final)):
        print(
            f"{name}: moves={ev['raw_moves']} schema={ev['schema_action_classes']} "
            f"oracle={ev['oracle_action_classes']} compression={ev['schema_compression']:.3f}x "
            f"over={ev['overfragmentation_vs_oracle']:.3f} "
            f"conflict={ev['conflict_mass']} minimax_mismatch={ev['pruned_minimax_mismatches']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
