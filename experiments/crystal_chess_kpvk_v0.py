#!/usr/bin/env python3
"""Crystal Chess V0: exact KPvK consequential quotient discovery.

Syzygy WDL is the external authority. Crystal is asked to discover a compact,
constructive observation quotient that preserves that protected consequence,
not to imitate an engine evaluation.

Declared boundary:
* standard chess, material White K+P versus Black K;
* no castling rights or en-passant target; root halfmove clock zero;
* pawn ranks 2..7;
* protected consequence = Syzygy WDL from side to move;
* source cover = pawn files a..d, with horizontal reflection checked against
  the omitted e..h half.

This is bounded evidence only. General chess remains UNKNOWN.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Callable

import chess
import chess.syzygy


SCHEMA = "mathgraph.crystal-chess.kpvk-wdl.v0"
PROTECTED_INTERFACE = "chess.syzygy.wdl.v1"
BASE_CRYSTAL_AUTHORITY = (
    "metalogiclabs/mathgraph@00670f86e3d4d079f6d4d8e531a8850dec3a2a0f"
)
WDL_VALUES = (-2, -1, 0, 1, 2)
WDL_INDEX = {value: i for i, value in enumerate(WDL_VALUES)}


@dataclass(frozen=True)
class PositionRecord:
    wk: int
    bk: int
    pawn: int
    turn: bool
    wdl: int
    features: tuple[int, ...]


def horizontal_square(square: int) -> int:
    return chess.square(7 - chess.square_file(square), chess.square_rank(square))


def horizontal_reflection(board: chess.Board) -> chess.Board:
    reflected = chess.Board(None)
    reflected.turn = board.turn
    reflected.castling_rights = chess.BB_EMPTY
    reflected.ep_square = None
    reflected.halfmove_clock = board.halfmove_clock
    reflected.fullmove_number = board.fullmove_number
    for square, piece in board.piece_map().items():
        reflected.set_piece_at(horizontal_square(square), piece)
    return reflected


def make_kpvk(wk: int, bk: int, pawn: int, turn: bool) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    return board


def board_key(board: chess.Board) -> tuple[str, bool]:
    return board.board_fen(), board.turn


def terminal_wdl(board: chess.Board) -> int | None:
    if board.is_checkmate():
        return -2
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return None


def probe_wdl(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    cache: dict[tuple[str, bool], int],
) -> int:
    key = board_key(board)
    if key in cache:
        return cache[key]
    terminal = terminal_wdl(board)
    if terminal is not None:
        cache[key] = terminal
        return terminal
    try:
        value = int(tablebase.probe_wdl(board))
    except KeyError:
        if board.is_insufficient_material():
            value = 0
        else:
            raise
    if value not in WDL_INDEX:
        raise AssertionError(f"unexpected WDL value: {value}")
    cache[key] = value
    return value


def cheb(a: int, b: int) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def manhattan(a: int, b: int) -> int:
    return abs(chess.square_file(a) - chess.square_file(b)) + abs(
        chess.square_rank(a) - chess.square_rank(b)
    )


def edge_distance(square: int) -> int:
    f = chess.square_file(square)
    r = chess.square_rank(square)
    return min(f, 7 - f, r, 7 - r)


def coordinate_feature_bank() -> list[tuple[str, Callable[[int, int, int, bool], int]]]:
    """Generic geometry plus exact-coordinate fallbacks.

    No hand-authored chess concepts such as opposition, key squares, rook-pawn
    exceptions, or corresponding squares are included.
    """

    def f(square: int) -> int:
        return chess.square_file(square)

    def r(square: int) -> int:
        return chess.square_rank(square)

    def promo(pawn: int) -> int:
        return chess.square(f(pawn), 7)

    return [
        ("turn", lambda wk, bk, p, t: int(t)),
        ("pawn_file", lambda wk, bk, p, t: f(p)),
        ("pawn_rank", lambda wk, bk, p, t: r(p)),
        ("pawn_steps_to_promote", lambda wk, bk, p, t: 7 - r(p)),
        ("wk_file", lambda wk, bk, p, t: f(wk)),
        ("wk_rank", lambda wk, bk, p, t: r(wk)),
        ("bk_file", lambda wk, bk, p, t: f(bk)),
        ("bk_rank", lambda wk, bk, p, t: r(bk)),
        ("wk_dx_pawn", lambda wk, bk, p, t: f(wk) - f(p)),
        ("wk_dy_pawn", lambda wk, bk, p, t: r(wk) - r(p)),
        ("bk_dx_pawn", lambda wk, bk, p, t: f(bk) - f(p)),
        ("bk_dy_pawn", lambda wk, bk, p, t: r(bk) - r(p)),
        ("abs_wk_dx_pawn", lambda wk, bk, p, t: abs(f(wk) - f(p))),
        ("abs_wk_dy_pawn", lambda wk, bk, p, t: abs(r(wk) - r(p))),
        ("abs_bk_dx_pawn", lambda wk, bk, p, t: abs(f(bk) - f(p))),
        ("abs_bk_dy_pawn", lambda wk, bk, p, t: abs(r(bk) - r(p))),
        ("wk_bk_dx", lambda wk, bk, p, t: f(wk) - f(bk)),
        ("wk_bk_dy", lambda wk, bk, p, t: r(wk) - r(bk)),
        ("abs_wk_bk_dx", lambda wk, bk, p, t: abs(f(wk) - f(bk))),
        ("abs_wk_bk_dy", lambda wk, bk, p, t: abs(r(wk) - r(bk))),
        ("cheb_wk_pawn", lambda wk, bk, p, t: cheb(wk, p)),
        ("cheb_bk_pawn", lambda wk, bk, p, t: cheb(bk, p)),
        ("cheb_kings", lambda wk, bk, p, t: cheb(wk, bk)),
        ("manhattan_wk_pawn", lambda wk, bk, p, t: manhattan(wk, p)),
        ("manhattan_bk_pawn", lambda wk, bk, p, t: manhattan(bk, p)),
        ("manhattan_kings", lambda wk, bk, p, t: manhattan(wk, bk)),
        ("cheb_wk_promo", lambda wk, bk, p, t: cheb(wk, promo(p))),
        ("cheb_bk_promo", lambda wk, bk, p, t: cheb(bk, promo(p))),
        ("wk_edge_distance", lambda wk, bk, p, t: edge_distance(wk)),
        ("bk_edge_distance", lambda wk, bk, p, t: edge_distance(bk)),
        ("same_file_wk_pawn", lambda wk, bk, p, t: int(f(wk) == f(p))),
        ("same_file_bk_pawn", lambda wk, bk, p, t: int(f(bk) == f(p))),
        ("wk_ahead_of_pawn", lambda wk, bk, p, t: int(r(wk) > r(p))),
        ("bk_ahead_of_pawn", lambda wk, bk, p, t: int(r(bk) > r(p))),
        ("wk_adjacent_pawn", lambda wk, bk, p, t: int(cheb(wk, p) == 1)),
        ("bk_adjacent_pawn", lambda wk, bk, p, t: int(cheb(bk, p) == 1)),
        (
            "wk_promo_distance_minus_bk",
            lambda wk, bk, p, t: cheb(wk, promo(p)) - cheb(bk, promo(p)),
        ),
        (
            "wk_pawn_distance_minus_bk",
            lambda wk, bk, p, t: cheb(wk, p) - cheb(bk, p),
        ),
        (
            "king_file_order",
            lambda wk, bk, p, t: (f(wk) > f(bk)) - (f(wk) < f(bk)),
        ),
        (
            "king_rank_order",
            lambda wk, bk, p, t: (r(wk) > r(bk)) - (r(wk) < r(bk)),
        ),
    ]


def partition_stats(
    records: list[PositionRecord], selected: tuple[int, ...]
) -> tuple[int, int, int]:
    groups: dict[tuple[int, ...], list[int]] = {}
    for rec in records:
        key = tuple(rec.features[i] for i in selected)
        counts = groups.get(key)
        if counts is None:
            counts = [0] * len(WDL_VALUES)
            groups[key] = counts
        counts[WDL_INDEX[rec.wdl]] += 1
    conflict_mass = 0
    impure_classes = 0
    for counts in groups.values():
        total = sum(counts)
        majority = max(counts)
        conflict_mass += total - majority
        impure_classes += int(majority != total)
    return conflict_mass, len(groups), impure_classes


def greedy_exact_quotient(
    records: list[PositionRecord], feature_names: list[str]
) -> tuple[tuple[int, ...], list[dict[str, int | str]]]:
    selected: tuple[int, ...] = ()
    remaining = set(range(len(feature_names)))
    trace: list[dict[str, int | str]] = []
    conflicts, classes, impure = partition_stats(records, selected)
    trace.append(
        {
            "step": 0,
            "feature": "<none>",
            "conflict_mass": conflicts,
            "classes": classes,
            "impure_classes": impure,
        }
    )

    while conflicts:
        candidates = []
        for idx in sorted(remaining):
            trial = selected + (idx,)
            c, k, bad = partition_stats(records, trial)
            candidates.append((c, k, feature_names[idx], idx, bad))
        new_conflicts, new_classes, name, idx, new_impure = min(candidates)
        if new_conflicts >= conflicts:
            raise AssertionError(
                f"NO_CONSEQUENTIAL_SEPARATOR conflicts={conflicts} best={new_conflicts}"
            )
        selected += (idx,)
        remaining.remove(idx)
        conflicts, classes, impure = new_conflicts, new_classes, new_impure
        trace.append(
            {
                "step": len(trace),
                "feature": name,
                "conflict_mass": conflicts,
                "classes": classes,
                "impure_classes": impure,
            }
        )

    # Inclusion-minimal relative to the greedy path; no claim of globally
    # minimum feature cardinality.
    changed = True
    while changed:
        changed = False
        for idx in tuple(selected):
            trial = tuple(x for x in selected if x != idx)
            c, k, bad = partition_stats(records, trial)
            if c == 0:
                selected = trial
                changed = True
                trace.append(
                    {
                        "step": len(trace),
                        "feature": f"drop:{feature_names[idx]}",
                        "conflict_mass": c,
                        "classes": k,
                        "impure_classes": bad,
                    }
                )
                break

    c, k, bad = partition_stats(records, selected)
    assert c == 0 and bad == 0
    trace.append(
        {
            "step": len(trace),
            "feature": "<final>",
            "conflict_mass": c,
            "classes": k,
            "impure_classes": bad,
        }
    )
    return selected, trace


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def boundary_id() -> str:
    payload = {
        "material": "KPvK",
        "variant": "standard",
        "castling": False,
        "ep": False,
        "root_halfmove_clock": 0,
        "pawn_ranks": [2, 3, 4, 5, 6, 7],
        "canonical_pawn_files": ["a", "b", "c", "d"],
        "protected_interface": PROTECTED_INTERFACE,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "boundary:" + hashlib.sha256(raw).hexdigest()


def enumerate_records(
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    feature_fns: list[Callable[[int, int, int, bool], int]],
) -> tuple[list[PositionRecord], dict[str, int]]:
    records: list[PositionRecord] = []
    stats = {
        "candidate_assignments": 0,
        "legal_canonical_states": 0,
        "mirror_mismatches": 0,
        "mirror_invalid": 0,
    }
    for pawn_file in range(4):
        for pawn_rank in range(1, 7):
            pawn = chess.square(pawn_file, pawn_rank)
            for wk in chess.SQUARES:
                if wk == pawn:
                    continue
                for bk in chess.SQUARES:
                    if bk == pawn or bk == wk:
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        stats["candidate_assignments"] += 1
                        board = make_kpvk(wk, bk, pawn, turn)
                        if not board.is_valid():
                            continue
                        stats["legal_canonical_states"] += 1
                        wdl = probe_wdl(tablebase, board, cache)
                        mirror = horizontal_reflection(board)
                        if not mirror.is_valid():
                            stats["mirror_invalid"] += 1
                            continue
                        if probe_wdl(tablebase, mirror, cache) != wdl:
                            stats["mirror_mismatches"] += 1
                        features = tuple(
                            fn(wk, bk, pawn, turn) for fn in feature_fns
                        )
                        records.append(
                            PositionRecord(wk, bk, pawn, turn, wdl, features)
                        )
    return records, stats


def audit_indices(total: int, limit: int) -> list[int]:
    if limit <= 0 or limit >= total:
        return list(range(total))
    # Deterministic coverage across the whole canonical enumeration.
    return sorted({(i * total) // limit for i in range(limit)})


def action_quotient_audit(
    records: list[PositionRecord],
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    action_limit: int,
) -> dict[str, object]:
    total_moves = 0
    total_classes = 0
    audited_states = 0
    terminal_states = 0
    minimax_mismatches = 0
    class_hist: Counter[int] = Counter()
    move_hist: Counter[int] = Counter()
    mismatch_examples: list[dict[str, object]] = []

    indices = audit_indices(len(records), action_limit)
    for index in indices:
        rec = records[index]
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            terminal_states += 1
            continue
        consequences: list[int] = []
        for move in legal_moves:
            child = board.copy(stack=False)
            child.push(move)
            consequences.append(-probe_wdl(tablebase, child, cache))
        classes = len(set(consequences))
        negamax = max(consequences)
        if negamax != rec.wdl:
            minimax_mismatches += 1
            if len(mismatch_examples) < 20:
                mismatch_examples.append(
                    {
                        "fen": board.fen(),
                        "root_wdl": rec.wdl,
                        "child_consequences": sorted(set(consequences)),
                        "negamax": negamax,
                    }
                )
        audited_states += 1
        total_moves += len(legal_moves)
        total_classes += classes
        move_hist[len(legal_moves)] += 1
        class_hist[classes] += 1

    return {
        "requested_limit": action_limit,
        "selected_states": len(indices),
        "audited_nonterminal_states": audited_states,
        "audited_terminal_states": terminal_states,
        "raw_legal_moves": total_moves,
        "protected_action_classes": total_classes,
        "action_compression_ratio": (
            total_moves / total_classes if total_classes else 1.0
        ),
        "mean_legal_moves": total_moves / audited_states if audited_states else 0.0,
        "mean_protected_action_classes": (
            total_classes / audited_states if audited_states else 0.0
        ),
        "minimax_mismatches": minimax_mismatches,
        "move_count_histogram": {str(k): v for k, v in sorted(move_hist.items())},
        "action_class_histogram": {
            str(k): v for k, v in sorted(class_hist.items())
        },
        "mismatch_examples": mismatch_examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("crystal_chess_kpvk_v0.json")
    )
    parser.add_argument(
        "--action-limit",
        type=int,
        default=50000,
        help="0 audits all states; positive values select a deterministic spread.",
    )
    args = parser.parse_args()
    started = time.time()

    feature_bank = coordinate_feature_bank()
    feature_names = [name for name, _ in feature_bank]
    feature_fns = [fn for _, fn in feature_bank]
    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    if not tb_files:
        raise SystemExit(f"no .rtbw files found in {args.tablebase_dir}")
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in tb_files
    ]

    cache: dict[tuple[str, bool], int] = {}
    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(tablebase, cache, feature_fns)
        assert records
        assert enumeration["mirror_invalid"] == 0, enumeration
        assert enumeration["mirror_mismatches"] == 0, enumeration

        selected, trace = greedy_exact_quotient(records, feature_names)
        conflicts, classes, impure = partition_stats(records, selected)
        assert conflicts == 0 and impure == 0

        actions = action_quotient_audit(
            records, tablebase, cache, args.action_limit
        )
        assert actions["minimax_mismatches"] == 0, actions["mismatch_examples"]

    wdl_counts = Counter(rec.wdl for rec in records)
    selected_names = [feature_names[i] for i in selected]
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_WDL_QUOTIENT",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "boundary_id": boundary_id(),
        "protected_interface": PROTECTED_INTERFACE,
        "authority": {
            "kind": "Syzygy WDL",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "environment": {"python": sys.version, "platform": platform.platform()},
        "enumeration": enumeration,
        "wdl_distribution": {str(k): wdl_counts.get(k, 0) for k in WDL_VALUES},
        "horizontal_reflection": {
            "checked_states": len(records),
            "mismatches": enumeration["mirror_mismatches"],
            "consequence": (
                "safe canonicalization of pawn files e-h onto d-a "
                "for this declared boundary"
            ),
        },
        "representation": {
            "candidate_features": feature_names,
            "selected_features": selected_names,
            "selection_kind": (
                "greedy_then_backward_inclusion_minimal_within_declared_bank"
            ),
            "selection_trace": trace,
            "raw_canonical_states": len(records),
            "protected_classes": classes,
            "state_compression_ratio": len(records) / classes,
            "conflict_mass": conflicts,
            "impure_classes": impure,
            "oracle_label_class_ceiling": len(wdl_counts),
        },
        "actions": actions,
        "cache": {"unique_wdl_positions_probed_or_certified": len(cache)},
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "horizontal reflection preserves Syzygy WDL on the "
                    "complete declared KPvK cover"
                ),
                (
                    "selected constructive feature quotient is WDL-pure on "
                    "the complete declared canonical KPvK cover"
                ),
                (
                    "move classes by induced WDL preserve one-ply Syzygy "
                    "negamax on the declared action audit"
                ),
            ],
            "candidate": [
                "learned consequential observables transfer to richer pawn endings",
                (
                    "verified reducers can expand an exact solved basin beyond "
                    "available raw tablebases"
                ),
            ],
            "unknown": [
                "general chess solution",
                "future equivalence beyond the declared WDL interface",
            ],
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    print("CRYSTAL_CHESS_KPVK_V0=PASS")
    print(
        f"states={len(records)} classes={classes} "
        f"compression={len(records) / classes:.3f}x"
    )
    print("selected_features=" + ",".join(selected_names))
    print(
        f"actions={actions['raw_legal_moves']}->"
        f"{actions['protected_action_classes']} "
        f"compression={actions['action_compression_ratio']:.3f}x"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
