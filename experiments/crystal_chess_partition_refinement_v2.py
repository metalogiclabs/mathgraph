#!/usr/bin/env python3
"""Crystal Chess V2: direct backward partition refinement on exact KPvK.

This is the ROS-native version of the chess quotient:
complete authority -> freeze truth -> split only on witnessed future separators.

It computes the coarsest partition refining protected observation (Syzygy WDL,
side to move) that is stable under the SET of reachable successor classes.
That is the action-quotiented future congruence for the declared boundary.

Unlike V1, this does not propagate distinctions one ply per global round.
It uses splitter/predecessor refinement directly from the complete transition
graph, i.e. the finite verifier-driven separator recovery already warranted by
MSI/VDN and the completion-by-reversal direction exposed by Nucleus.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
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
from crystal_chess_future_quotient_v1 import (
    V0_AUTHORITY,
    child_kpvk_key,
    external_label,
    file_sha256,
    state_key,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-partition-refinement.v2"
V1_LINEAGE = (
    "metalogiclabs/mathgraph@f2d7a5c1b887a924471d6e725eea3b2f2c910cab"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_partition_refinement_v2.json"),
    )
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

        keys = [state_key(rec.wk, rec.bk, rec.pawn, rec.turn) for rec in records]
        index = {key: i for i, key in enumerate(keys)}
        assert len(index) == len(records)

        n = len(records)
        adjacency: list[tuple[int, ...]] = []
        predecessors: list[list[int]] = [[] for _ in range(n)]
        external_ids: dict[str, int] = {}
        external_labels: list[str] = []
        external_predecessors: dict[int, list[int]] = defaultdict(list)
        raw_legal_moves = 0
        one_ply_mismatches = 0
        terminal_states = 0

        def ext_token(label: str) -> int:
            if label not in external_ids:
                external_ids[label] = -(len(external_ids) + 1)
                external_labels.append(label)
            return external_ids[label]

        for i, rec in enumerate(records):
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
                    j = index.get(key)
                    if j is None:
                        raise AssertionError(
                            f"internal child missing from complete cover: {child.fen()}"
                        )
                    succ.append(j)
                    predecessors[j].append(i)
                else:
                    token = ext_token(external_label(child, tablebase, cache))
                    succ.append(token)
                    external_predecessors[token].append(i)

            if max(child_consequences) != rec.wdl:
                one_ply_mismatches += 1
            raw_legal_moves += len(moves)
            adjacency.append(tuple(succ))

        assert one_ply_mismatches == 0

        # Initial partition is exactly the protected observation.
        obs_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i, rec in enumerate(records):
            obs_groups[(rec.wdl, int(rec.turn))].append(i)

        block_members: dict[int, set[int]] = {}
        state_block = [-1] * n
        next_block = 0
        for obs in sorted(obs_groups):
            members = set(obs_groups[obs])
            block_members[next_block] = members
            for s in members:
                state_block[s] = next_block
            next_block += 1

        initial_block_count = len(block_members)

        # External observations are immutable splitter atoms. Internal blocks
        # enter a Hopcroft/Paige-Tarjan style worklist.
        queue: deque[tuple[str, int]] = deque()
        queued_internal: set[int] = set()
        for token in sorted(external_predecessors):
            queue.append(("external", token))
        for b in sorted(block_members):
            queue.append(("internal", b))
            queued_internal.add(b)

        split_events = 0
        processed_splitters = 0
        max_queue = len(queue)
        largest_predecessor = 0

        while queue:
            kind, splitter = queue.popleft()
            processed_splitters += 1
            if kind == "internal":
                queued_internal.discard(splitter)
                members = block_members.get(splitter)
                if not members:
                    # A queued block id may have been replaced by a split.
                    continue
                pred_set: set[int] = set()
                for target in members:
                    pred_set.update(predecessors[target])
            else:
                pred_set = set(external_predecessors.get(splitter, ()))

            if not pred_set:
                continue
            largest_predecessor = max(largest_predecessor, len(pred_set))

            touched: dict[int, list[int]] = defaultdict(list)
            for s in pred_set:
                touched[state_block[s]].append(s)

            for b, inside_list in list(touched.items()):
                members = block_members.get(b)
                if not members:
                    continue
                if len(inside_list) == len(members):
                    continue

                inside = set(inside_list)
                outside = members - inside
                assert inside and outside

                # Retain the larger side at b to reduce relabel work.
                if len(inside) <= len(outside):
                    small, large = inside, outside
                else:
                    small, large = outside, inside

                block_members[b] = large
                new_b = next_block
                next_block += 1
                block_members[new_b] = small
                for s in small:
                    state_block[s] = new_b

                split_events += 1

                # Hopcroft rule: if b was already scheduled, both children
                # must eventually act as splitters. Otherwise the smaller child
                # suffices to preserve O(m log n)-style refinement behaviour.
                if b in queued_internal:
                    if new_b not in queued_internal:
                        queue.append(("internal", new_b))
                        queued_internal.add(new_b)
                    # b remains queued already.
                else:
                    if new_b not in queued_internal:
                        queue.append(("internal", new_b))
                        queued_internal.add(new_b)

            max_queue = max(max_queue, len(queue))

        # Canonical dense class ids.
        live_blocks = sorted(block_members)
        dense = {b: i for i, b in enumerate(live_blocks)}
        classes = [dense[state_block[i]] for i in range(n)]
        class_count = len(live_blocks)

        # Independent fixed-point verification against the exact recursive
        # signature used in V1.
        class_signature: dict[int, tuple] = {}
        final_action_classes = 0
        signature_mismatches = 0
        for i, rec in enumerate(records):
            mapped = tuple(
                sorted(
                    {
                        edge if edge < 0 else classes[edge]
                        for edge in adjacency[i]
                    }
                )
            )
            final_action_classes += len(mapped)
            sig = (rec.wdl, int(rec.turn), mapped)
            c = classes[i]
            prev = class_signature.setdefault(c, sig)
            if prev != sig:
                signature_mismatches += 1

        if signature_mismatches:
            raise AssertionError(
                f"partition not stable: {signature_mismatches} signature mismatches"
            )

        # Stronger check: equal recursive signatures must receive equal class
        # ids, proving there is no unnecessary split relative to this boundary.
        sig_to_class: dict[tuple, int] = {}
        over_split = 0
        for i, rec in enumerate(records):
            mapped = tuple(
                sorted(
                    {
                        edge if edge < 0 else classes[edge]
                        for edge in adjacency[i]
                    }
                )
            )
            sig = (rec.wdl, int(rec.turn), mapped)
            c = classes[i]
            old = sig_to_class.setdefault(sig, c)
            if old != c:
                over_split += 1
        if over_split:
            raise AssertionError(f"partition unnecessarily split: {over_split}")

        sizes = Counter(classes)
        size_hist = Counter(sizes.values())

        result = {
            "schema": SCHEMA,
            "status": "WARRANTED_BOUNDED_KPVK_COARSEST_ACTION_QUOTIENTED_FUTURE_CONGRUENCE",
            "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
            "v0_authority": V0_AUTHORITY,
            "v1_lineage": V1_LINEAGE,
            "protected_interface": PROTECTED_INTERFACE,
            "method": {
                "direction": "complete-authority -> backward future-separator refinement",
                "algorithm": "predecessor splitter worklist partition refinement",
                "protected_observation": "Syzygy WDL + side-to-move",
                "action_identity": "set of induced protected successor classes",
                "minimality_check": "equal final recursive signatures iff equal quotient class",
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
                "states": n,
                "raw_legal_moves": raw_legal_moves,
                "terminal_states": terminal_states,
                "external_exit_observations": len(external_ids),
                "external_labels": sorted(external_labels),
                "one_ply_minimax_mismatches": one_ply_mismatches,
            },
            "refinement": {
                "initial_protected_classes": initial_block_count,
                "split_events": split_events,
                "processed_splitters": processed_splitters,
                "max_worklist": max_queue,
                "largest_predecessor_set": largest_predecessor,
                "final_classes": class_count,
                "state_compression_ratio": n / class_count,
                "largest_class": max(sizes.values()),
                "singleton_classes": sum(v == 1 for v in sizes.values()),
                "class_size_histogram": {
                    str(k): v for k, v in sorted(size_hist.items())
                },
                "final_signature_mismatches": signature_mismatches,
                "final_over_split_witnesses": over_split,
            },
            "actions": {
                "raw_legal_moves": raw_legal_moves,
                "final_protected_action_classes": final_action_classes,
                "action_compression_ratio": (
                    raw_legal_moves / final_action_classes
                    if final_action_classes
                    else 1.0
                ),
                "mean_raw_branching": raw_legal_moves / n,
                "mean_consequential_branching": final_action_classes / n,
            },
            "epistemic_boundary": {
                "warranted_if_green": [
                    "coarsest stable finite quotient for the declared recursive protected signature",
                    "all merged states preserve WDL, side-to-move, and action-quotiented successor-class sets until KPvK exit",
                    "all quotient actions lift to at least one concrete legal move by construction",
                ],
                "unknown": [
                    "transfer of quotient classes to richer material",
                    "symbolic recognition of quotient classes without exact enumeration",
                    "general chess game-theoretic value",
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
    print("CRYSTAL_CHESS_PARTITION_REFINEMENT_V2=PASS")
    print(
        f"states={n} classes={class_count} "
        f"state_compression={n / class_count:.6f}x"
    )
    print(
        f"moves={raw_legal_moves}->{final_action_classes} "
        f"action_compression={raw_legal_moves / final_action_classes:.6f}x"
    )
    print(
        f"splits={split_events} splitters={processed_splitters} "
        f"largest_class={max(sizes.values())} "
        f"singletons={sum(v == 1 for v in sizes.values())}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
