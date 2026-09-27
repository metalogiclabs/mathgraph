#!/usr/bin/env python3
"""Crystal Chess V1: exact action-quotiented future fixed point on KPvK.

This strengthens V0.  States are not merged merely because they share Syzygy
WDL.  They are merged only when they have the same protected observation and
the same SET of quotient-successor consequences, iterated to a fixed point.

The action names themselves are intentionally quotiented by induced protected
transition, matching MathGraph Crystal's action_quotient principle.  Therefore
this is a bounded minimax congruence, not literal equality of UCI move strings.

Boundary:
* Standard White K+P vs Black K states with pawn files a..d, ranks 2..7.
* Horizontal reflection is already qualified by Crystal Chess V0.
* Internal continuation is exact while the position remains KPvK.
* Exit from KPvK is observed by exact Syzygy WDL plus exit material class.
* No claim is made about futures after that exit observation.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Iterable

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    WDL_VALUES,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-future-quotient.v1"
V0_AUTHORITY = (
    "metalogiclabs/mathgraph@d8da8268068e7d94950aadeea53ad74906683355"
)


def state_key(wk: int, bk: int, pawn: int, turn: bool) -> tuple[int, int, int, int]:
    return wk, bk, pawn, int(turn)


def child_kpvk_key(board: chess.Board) -> tuple[int, int, int, int] | None:
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if len(pawns) != 1:
        return None
    # The declared world has no black non-king material and exactly one white
    # pawn.  Promotion or capture therefore leaves the internal boundary.
    extras = (
        len(board.pieces(chess.QUEEN, chess.WHITE))
        + len(board.pieces(chess.ROOK, chess.WHITE))
        + len(board.pieces(chess.BISHOP, chess.WHITE))
        + len(board.pieces(chess.KNIGHT, chess.WHITE))
    )
    if extras:
        return None
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    if wk is None or bk is None:
        return None
    pawn = pawns[0]
    if chess.square_file(pawn) >= 4:
        # Starting from files a..d a pawn cannot cross files without capturing;
        # there is no capturable black non-king piece.  Keep this as a hard
        # boundary assertion rather than silently canonicalising.
        raise AssertionError(f"unexpected pawn-file escape: {board.fen()}")
    if not 1 <= chess.square_rank(pawn) <= 6:
        return None
    return state_key(wk, bk, pawn, board.turn)


def material_label(board: chess.Board) -> str:
    pieces: list[str] = []
    names = {
        chess.QUEEN: "Q",
        chess.ROOK: "R",
        chess.BISHOP: "B",
        chess.KNIGHT: "N",
        chess.PAWN: "P",
    }
    for color, prefix in ((chess.WHITE, "W"), (chess.BLACK, "B")):
        for piece_type in (
            chess.QUEEN,
            chess.ROOK,
            chess.BISHOP,
            chess.KNIGHT,
            chess.PAWN,
        ):
            count = len(board.pieces(piece_type, color))
            if count:
                pieces.append(prefix + names[piece_type] * count)
    return "KvK" if not pieces else "K+" + "+".join(pieces) + "vK"


def external_label(
    board: chess.Board,
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
) -> str:
    wdl = probe_wdl(tablebase, board, cache)
    return f"exit:{material_label(board)}:turn={int(board.turn)}:wdl={wdl}"


def stable_ids(signatures: Iterable[tuple]) -> tuple[list[int], int]:
    sigs = list(signatures)
    unique = sorted(set(sigs))
    mapping = {sig: idx for idx, sig in enumerate(unique)}
    return [mapping[sig] for sig in sigs], len(unique)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_future_quotient_v1.json"),
    )
    parser.add_argument("--max-iterations", type=int, default=512)
    args = parser.parse_args()
    started = time.time()

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
        records, enumeration = enumerate_records(tablebase, cache, [])
        assert records
        assert enumeration["mirror_invalid"] == 0
        assert enumeration["mirror_mismatches"] == 0

        keys = [
            state_key(rec.wk, rec.bk, rec.pawn, rec.turn) for rec in records
        ]
        index = {key: i for i, key in enumerate(keys)}
        assert len(index) == len(records), "duplicate canonical KPvK state"

        # Adjacency uses non-negative ints for internal node ids and negative
        # ints for typed boundary-exit observations.
        external_ids: dict[str, int] = {}
        external_labels: list[str] = []
        adjacency: list[tuple[int, ...]] = []
        raw_legal_moves = 0
        one_ply_mismatches = 0
        terminal_states = 0

        def ext_token(label: str) -> int:
            token = external_ids.get(label)
            if token is None:
                token = -(len(external_ids) + 1)
                external_ids[label] = token
                external_labels.append(label)
            return token

        for rec in records:
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            moves = list(board.legal_moves)
            if not moves:
                terminal_states += 1
                adjacency.append(())
                continue

            succ: list[int] = []
            child_consequences: list[int] = []
            for move in moves:
                child = board.copy(stack=False)
                child.push(move)
                child_wdl = probe_wdl(tablebase, child, cache)
                child_consequences.append(-child_wdl)
                key = child_kpvk_key(child)
                if key is not None:
                    try:
                        succ.append(index[key])
                    except KeyError as exc:
                        raise AssertionError(
                            f"internal child missing from complete cover: {child.fen()}"
                        ) from exc
                else:
                    succ.append(ext_token(external_label(child, tablebase, cache)))

            if max(child_consequences) != rec.wdl:
                one_ply_mismatches += 1
            raw_legal_moves += len(moves)
            adjacency.append(tuple(succ))

        assert one_ply_mismatches == 0, one_ply_mismatches

        base_signatures = [(rec.wdl, int(rec.turn)) for rec in records]
        classes, class_count = stable_ids(base_signatures)
        trace: list[dict[str, int | float]] = []

        def mapped_successors(node: int, cls: list[int]) -> tuple[int, ...]:
            values = {
                edge if edge < 0 else cls[edge]
                for edge in adjacency[node]
            }
            return tuple(sorted(values))

        for iteration in range(args.max_iterations + 1):
            quotient_actions = sum(
                len(mapped_successors(i, classes)) for i in range(len(records))
            )
            sizes = Counter(classes)
            trace.append(
                {
                    "iteration": iteration,
                    "classes": class_count,
                    "state_compression_ratio": len(records) / class_count,
                    "protected_action_classes": quotient_actions,
                    "action_compression_ratio": (
                        raw_legal_moves / quotient_actions
                        if quotient_actions
                        else 1.0
                    ),
                    "largest_class": max(sizes.values()),
                    "singleton_classes": sum(v == 1 for v in sizes.values()),
                }
            )

            signatures = [
                (
                    rec.wdl,
                    int(rec.turn),
                    mapped_successors(i, classes),
                )
                for i, rec in enumerate(records)
            ]
            new_classes, new_count = stable_ids(signatures)
            if new_classes == classes:
                break
            classes = new_classes
            class_count = new_count
        else:
            raise AssertionError(
                f"future quotient did not stabilise within {args.max_iterations}"
            )

        final_action_classes = sum(
            len(mapped_successors(i, classes)) for i in range(len(records))
        )
        class_sizes = Counter(classes)
        size_hist = Counter(class_sizes.values())

        # Every final class must have exactly one recursive signature.
        final_signatures: dict[int, tuple] = {}
        for i, rec in enumerate(records):
            sig = (
                rec.wdl,
                int(rec.turn),
                mapped_successors(i, classes),
            )
            previous = final_signatures.setdefault(classes[i], sig)
            if previous != sig:
                raise AssertionError("inhomogeneous fixed-point class")

        result = {
            "schema": SCHEMA,
            "status": "WARRANTED_BOUNDED_KPVK_ACTION_QUOTIENTED_FUTURE_FIXED_POINT",
            "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
            "v0_authority": V0_AUTHORITY,
            "protected_interface": PROTECTED_INTERFACE,
            "boundary": {
                "material": "White K+P vs Black K",
                "canonical_pawn_files": ["a", "b", "c", "d"],
                "pawn_ranks": [2, 3, 4, 5, 6, 7],
                "internal_future": "exact while material remains KPvK",
                "exit_observation": "exact Syzygy WDL plus exit material and side-to-move",
                "action_identity": "quotiented by induced protected successor class",
            },
            "authority": {
                "kind": "Syzygy WDL",
                "python_chess_version": getattr(chess, "__version__", "unknown"),
                "tablebase_files": manifest,
            },
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
            },
            "enumeration": enumeration,
            "graph": {
                "states": len(records),
                "raw_legal_moves": raw_legal_moves,
                "terminal_states": terminal_states,
                "external_exit_observations": len(external_ids),
                "external_labels": sorted(external_labels),
                "one_ply_minimax_mismatches": one_ply_mismatches,
            },
            "fixed_point": {
                "iterations": trace[-1]["iteration"],
                "initial_classes": trace[0]["classes"],
                "final_classes": class_count,
                "state_compression_ratio": len(records) / class_count,
                "final_protected_action_classes": final_action_classes,
                "action_compression_ratio": (
                    raw_legal_moves / final_action_classes
                    if final_action_classes
                    else 1.0
                ),
                "largest_class": max(class_sizes.values()),
                "singleton_classes": sum(v == 1 for v in class_sizes.values()),
                "class_size_histogram": {
                    str(k): v for k, v in sorted(size_hist.items())
                },
                "trace": trace,
            },
            "epistemic_boundary": {
                "warranted_if_green": [
                    (
                        "the reported partition is a complete fixed point of the "
                        "declared action-quotiented recursive protected signature"
                    ),
                    (
                        "all merged states preserve WDL, side-to-move, and the "
                        "set of recursively quotiented continuation consequences "
                        "until KPvK boundary exit"
                    ),
                    (
                        "the final action quotient preserves exact one-ply Syzygy "
                        "minimax on the complete canonical KPvK cover"
                    ),
                ],
                "unknown": [
                    "literal UCI-action FutureEq",
                    "futures after the declared KPvK exit observation",
                    "transfer to richer material",
                    "general chess solution",
                ],
            },
            "cache": {
                "unique_wdl_positions_probed_or_certified": len(cache)
            },
            "elapsed_seconds": time.time() - started,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_FUTURE_QUOTIENT_V1=PASS")
    print(
        f"states={len(records)} classes={class_count} "
        f"state_compression={len(records) / class_count:.6f}x"
    )
    print(
        f"moves={raw_legal_moves}->{final_action_classes} "
        f"action_compression={raw_legal_moves / final_action_classes:.6f}x"
    )
    print(
        f"iterations={trace[-1]['iteration']} "
        f"largest_class={max(class_sizes.values())} "
        f"singletons={sum(v == 1 for v in class_sizes.values())}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
