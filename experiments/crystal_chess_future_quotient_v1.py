#!/usr/bin/env python3
"""Crystal Chess V1: exact action-quotiented future fixed point on KPvK.

V0 showed that one-ply WDL collapses many legal moves, but WDL is deliberately
coarse.  V1 computes the stronger recursive object directly.

Two KPvK states may share a class only when:
1. their protected observation (Syzygy WDL + side to move) agrees; and
2. the SET of protected successor classes reachable by legal moves agrees.

Action strings and multiplicity are intentionally quotiented away: multiple
legal moves into the same protected successor class are one consequential
action.  The partition is refined to the greatest fixed point satisfying these
conditions.

The first implementation used synchronous depth refinement and did not
stabilise within 512 rounds (run 36349028488).  This implementation computes
the same fixed point event-wise.  Whenever a target block splits, only
predecessors whose successor-block signature can change are reconsidered.
Largest split parts retain their block id, so moved targets always enter a
strictly smaller block.

Boundary:
* Standard White K+P vs Black K states with pawn files a..d, ranks 2..7.
* Horizontal reflection is inherited from qualified Crystal Chess V0.
* Internal continuation is exact while the position remains KPvK.
* Exit from KPvK is observed by exact Syzygy WDL plus exit material class.
* No claim is made about futures after that exit observation.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-future-quotient.v1"
V0_AUTHORITY = (
    "metalogiclabs/mathgraph@d8da8268068e7d94950aadeea53ad74906683355"
)
NAIVE_DEPTH_RUN = "metalogiclabs/mathgraph actions run 36349028488"
NAIVE_DEPTH_LOWER_BOUND = 512


def state_key(wk: int, bk: int, pawn: int, turn: bool) -> tuple[int, int, int, int]:
    return wk, bk, pawn, int(turn)


def child_kpvk_key(board: chess.Board) -> tuple[int, int, int, int] | None:
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if len(pawns) != 1:
        return None
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


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def initialise_partition(
    records,
) -> tuple[dict[int, set[int]], list[int], int]:
    by_observation: dict[tuple[int, int], list[int]] = {}
    for i, rec in enumerate(records):
        by_observation.setdefault((rec.wdl, int(rec.turn)), []).append(i)
    blocks: dict[int, set[int]] = {}
    block_of = [-1] * len(records)
    for block_id, observation in enumerate(sorted(by_observation)):
        members = set(by_observation[observation])
        blocks[block_id] = members
        for state in members:
            block_of[state] = block_id
    assert all(block >= 0 for block in block_of)
    return blocks, block_of, len(blocks)


def partition_digest(blocks: dict[int, set[int]]) -> str:
    canonical = sorted(tuple(sorted(members)) for members in blocks.values())
    raw = json.dumps(canonical, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def direct_future_fixed_point(
    records,
    adjacency: list[tuple[int, ...]],
    max_splits: int,
) -> tuple[list[int], dict[int, set[int]], dict[str, int | float]]:
    """Event-driven coarsest successor-set partition.

    Successor multiplicity and concrete action names are not protected.
    Distinct target *states* inside one target block count only as presence of
    that block.  Counts are maintained internally only so a target split can
    update predecessor presence exactly.
    """

    n = len(records)
    blocks, block_of, next_block_id = initialise_partition(records)
    initial_blocks = len(blocks)

    # Remove duplicate action targets because action multiplicity is quotiented.
    unique_adjacency = [tuple(sorted(set(edges))) for edges in adjacency]

    # Reverse incidence for internal target states only.  One source appears at
    # most once per target because unique_adjacency removed duplicate moves.
    reverse: list[list[int]] = [[] for _ in range(n)]
    for source, edges in enumerate(unique_adjacency):
        for target in edges:
            if target >= 0:
                reverse[target].append(source)

    # Per source: number of DISTINCT target states currently lying in each
    # internal block; external typed observations remain fixed negative keys.
    successor_counts: list[dict[int, int]] = []
    for edges in unique_adjacency:
        counts: dict[int, int] = {}
        for target in edges:
            key = target if target < 0 else block_of[target]
            counts[key] = counts.get(key, 0) + 1
        successor_counts.append(counts)

    queue = deque(sorted(blocks))
    pending = set(blocks)
    splits = 0
    moved_states = 0
    reverse_edge_updates = 0
    blocks_reconsidered = 0
    max_queue = len(queue)
    largest_split_arity = 1

    def state_signature(state: int) -> tuple[int, int, tuple[int, ...]]:
        rec = records[state]
        return (
            rec.wdl,
            int(rec.turn),
            tuple(sorted(successor_counts[state])),
        )

    def enqueue(block_id: int) -> None:
        nonlocal max_queue
        if block_id in blocks and block_id not in pending:
            pending.add(block_id)
            queue.append(block_id)
            if len(queue) > max_queue:
                max_queue = len(queue)

    while queue:
        block_id = queue.popleft()
        pending.discard(block_id)
        members = blocks.get(block_id)
        if not members or len(members) <= 1:
            continue
        blocks_reconsidered += 1

        groups: dict[tuple[int, int, tuple[int, ...]], list[int]] = {}
        for state in members:
            groups.setdefault(state_signature(state), []).append(state)
        if len(groups) == 1:
            continue

        splits += len(groups) - 1
        if splits > max_splits:
            raise AssertionError(
                f"direct partition exceeded max_splits={max_splits}"
            )
        largest_split_arity = max(largest_split_arity, len(groups))

        # Determinism: largest group keeps the old id; ties choose the group
        # with the smallest member. Every moved group is <= half the old block.
        grouped = sorted(
            groups.values(),
            key=lambda g: (-len(g), min(g)),
        )
        keep = grouped[0]
        old_size = len(members)
        blocks[block_id] = set(keep)

        moved: list[tuple[int, int]] = []
        new_ids: list[int] = []
        for group in grouped[1:]:
            new_id = next_block_id
            next_block_id += 1
            new_ids.append(new_id)
            blocks[new_id] = set(group)
            for state in group:
                block_of[state] = new_id
                moved.append((state, new_id))
            if len(group) * 2 > old_size:
                raise AssertionError("moved split part is not <= half old block")

        # Target partition changed. Update only predecessor successor-block
        # counts touched by moved target states.
        dirty_source_blocks: set[int] = set()
        for target_state, new_id in moved:
            moved_states += 1
            for source in reverse[target_state]:
                counts = successor_counts[source]
                old_count = counts.get(block_id, 0)
                if old_count <= 0:
                    raise AssertionError("missing predecessor old-block count")
                if old_count == 1:
                    del counts[block_id]
                else:
                    counts[block_id] = old_count - 1
                counts[new_id] = counts.get(new_id, 0) + 1
                reverse_edge_updates += 1
                dirty_source_blocks.add(block_of[source])

        # The just-created groups are homogeneous under the pre-update
        # signatures, but self/cyclic predecessor updates can immediately make
        # them dirty. Queue all affected source blocks. Also queue every new
        # target block once: their appearance as distinct successor blocks may
        # separate predecessors that were not touched by the retained part.
        for dirty in sorted(dirty_source_blocks):
            enqueue(dirty)
        enqueue(block_id)
        for new_id in new_ids:
            enqueue(new_id)

    # Fixed-point validation: every block has one protected successor signature.
    for block_id, members in blocks.items():
        if not members:
            raise AssertionError("empty final block")
        signatures = {state_signature(state) for state in members}
        if len(signatures) != 1:
            raise AssertionError(
                f"non-fixed block {block_id}: {len(signatures)} signatures"
            )

    stats: dict[str, int | float] = {
        "initial_blocks": initial_blocks,
        "final_blocks": len(blocks),
        "splits": splits,
        "moved_states": moved_states,
        "reverse_edge_updates": reverse_edge_updates,
        "blocks_reconsidered": blocks_reconsidered,
        "max_queue": max_queue,
        "largest_split_arity": largest_split_arity,
        "partition_sha256": partition_digest(blocks),
    }
    return block_of, blocks, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_future_quotient_v1.json"),
    )
    parser.add_argument("--max-splits", type=int, default=500000)
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

        fixed_started = time.time()
        block_of, blocks, refine_stats = direct_future_fixed_point(
            records, adjacency, args.max_splits
        )
        fixed_seconds = time.time() - fixed_started

        class_sizes = Counter(block_of)
        size_hist = Counter(class_sizes.values())
        final_action_classes = 0
        for state, edges in enumerate(adjacency):
            successor_classes = {
                edge if edge < 0 else block_of[edge]
                for edge in edges
            }
            final_action_classes += len(successor_classes)

        # Strong post-check: all members in a class expose exactly the same set
        # of final protected successor classes.
        class_signatures: dict[int, tuple] = {}
        for state, rec in enumerate(records):
            sig = (
                rec.wdl,
                int(rec.turn),
                tuple(
                    sorted(
                        {
                            edge if edge < 0 else block_of[edge]
                            for edge in adjacency[state]
                        }
                    )
                ),
            )
            previous = class_signatures.setdefault(block_of[state], sig)
            if previous != sig:
                raise AssertionError("inhomogeneous final future class")

        result = {
            "schema": SCHEMA,
            "status": "WARRANTED_BOUNDED_KPVK_ACTION_QUOTIENTED_FUTURE_FIXED_POINT",
            "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
            "v0_authority": V0_AUTHORITY,
            "protected_interface": PROTECTED_INTERFACE,
            "lineage": {
                "naive_depth_run": NAIVE_DEPTH_RUN,
                "naive_depth_nonstabilisation_rounds": NAIVE_DEPTH_LOWER_BOUND,
                "consequence": (
                    "synchronous unfolding is rejected as the fixed-point "
                    "algorithm; direct event-driven partition refinement is used"
                ),
            },
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
                **refine_stats,
                "state_compression_ratio": len(records) / len(blocks),
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
                "fixed_point_seconds": fixed_seconds,
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
        f"states={len(records)} classes={len(blocks)} "
        f"state_compression={len(records) / len(blocks):.6f}x"
    )
    print(
        f"moves={raw_legal_moves}->{final_action_classes} "
        f"action_compression={raw_legal_moves / final_action_classes:.6f}x"
    )
    print(
        f"splits={refine_stats['splits']} "
        f"moved_states={refine_stats['moved_states']} "
        f"largest_class={max(class_sizes.values())} "
        f"singletons={sum(v == 1 for v in class_sizes.values())}"
    )
    print(f"partition_sha256={refine_stats['partition_sha256']}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
