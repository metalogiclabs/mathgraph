#!/usr/bin/env python3
"""Crystal Chess V2: exact minimax-preserving move-schema policy for KPvK.

V1 showed that preserving *all* lawful continuations almost reconstructs the
entire board.  For solving chess that boundary is unnecessarily strong.

V2 protects the actual strategy obligation:
* winning state: choose any legal move that preserves WIN;
* drawing state: choose any legal move that preserves DRAW;
* losing state: no policy choice is needed here; loss is a universal verifier
  obligation over all legal moves and is audited separately by Syzygy.

The compiler receives, for every nonterminal non-losing KPvK state, the SET of
verified admissible relative move schemas.  It then residual-splits generic
geometry only until every leaf has a common admissible schema.  A leaf therefore
represents a reusable strategy capability, not a memorized score.

Every compiled leaf is replayed against the actual board and Syzygy.  No engine
evaluation or statistical label is trusted.
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
from typing import Any

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-minimax-policy.v2"
V1_AUTHORITY = (
    "metalogiclabs/mathgraph@966bc53867303e7c22e394fed182cc13d77707cf"
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_move_schema(board: chess.Board, move: chess.Move) -> str:
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("legal move has no moving piece")
    if piece.piece_type not in (chess.KING, chess.PAWN):
        raise AssertionError(f"unexpected KPvK mover: {piece}")
    dx = chess.square_file(move.to_square) - chess.square_file(move.from_square)
    dy = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    promotion = (
        chess.piece_symbol(move.promotion).upper()
        if move.promotion is not None
        else "-"
    )
    mover = "K" if piece.piece_type == chess.KING else "P"
    return f"{mover}:{dx}:{dy}:{promotion}"


def action_for_schema(board: chess.Board, schema: str) -> chess.Move:
    matches = [
        move for move in board.legal_moves
        if relative_move_schema(board, move) == schema
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"schema {schema} has {len(matches)} legal realizations in {board.fen()}"
        )
    return matches[0]


def lowest_bit(mask: int) -> int:
    if mask <= 0:
        raise ValueError("mask has no set bit")
    return (mask & -mask).bit_length() - 1


def compile_policy(
    features: list[tuple[int, ...]],
    allowed_masks: list[int],
    feature_names: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    all_indices = list(range(len(features)))
    all_features = tuple(range(len(feature_names)))
    trace: list[dict[str, Any]] = []
    feature_use: Counter[str] = Counter()
    leaf_depths: list[int] = []
    leaf_sizes: list[int] = []
    nodes = 0
    leaves = 0
    max_depth = 0

    def intersection(indices: list[int]) -> int:
        mask = allowed_masks[indices[0]]
        for idx in indices[1:]:
            mask &= allowed_masks[idx]
            if mask == 0:
                break
        return mask

    def build(
        indices: list[int],
        remaining: tuple[int, ...],
        depth: int,
    ) -> dict[str, Any]:
        nonlocal nodes, leaves, max_depth
        common = intersection(indices)
        if common:
            leaves += 1
            max_depth = max(max_depth, depth)
            leaf_depths.append(depth)
            leaf_sizes.append(len(indices))
            return {
                "leaf_mask": common,
                "size": len(indices),
                "depth": depth,
            }

        if not remaining:
            raise AssertionError(
                "NO_POLICY_SEPARATOR: identical full feature vector has "
                "incompatible verified move-schema sets"
            )

        best = None
        best_groups = None
        for feature in remaining:
            groups: dict[int, list[int]] = {}
            group_masks: dict[int, int] = {}
            for idx in indices:
                value = features[idx][feature]
                groups.setdefault(value, []).append(idx)
                if value in group_masks:
                    group_masks[value] &= allowed_masks[idx]
                else:
                    group_masks[value] = allowed_masks[idx]
            if len(groups) <= 1:
                continue

            unresolved_mass = sum(
                len(groups[value])
                for value, mask in group_masks.items()
                if mask == 0
            )
            unresolved_sizes = [
                len(groups[value])
                for value, mask in group_masks.items()
                if mask == 0
            ]
            max_unresolved = max(unresolved_sizes, default=0)
            resolved_mass = len(indices) - unresolved_mass
            # First maximize immediate certified coverage, then shrink the
            # hardest residual, then prefer fewer branches.
            score = (
                unresolved_mass,
                max_unresolved,
                len(groups),
                feature_names[feature],
            )
            if best is None or score < best:
                best = score
                best_groups = (feature, groups, resolved_mass)

        if best_groups is None:
            raise AssertionError(
                "NO_POLICY_SEPARATOR: remaining features are constant on an "
                "incompatible residual"
            )

        feature, groups, resolved_mass = best_groups
        feature_use[feature_names[feature]] += 1
        nodes += 1
        trace.append(
            {
                "depth": depth,
                "states": len(indices),
                "feature": feature_names[feature],
                "branch_count": len(groups),
                "immediately_resolved_states": resolved_mass,
                "unresolved_states": best[0],
                "largest_unresolved_branch": best[1],
            }
        )
        next_remaining = tuple(x for x in remaining if x != feature)
        branches: dict[str, Any] = {}
        for value in sorted(groups):
            branches[str(value)] = build(
                groups[value], next_remaining, depth + 1
            )
        return {
            "feature": feature,
            "feature_name": feature_names[feature],
            "size": len(indices),
            "depth": depth,
            "branches": branches,
        }

    tree = build(all_indices, all_features, 0)
    stats = {
        "states": len(features),
        "decision_nodes": nodes,
        "leaves": leaves,
        "state_per_leaf_compression": len(features) / leaves,
        "max_depth": max_depth,
        "mean_leaf_depth": sum(leaf_depths) / len(leaf_depths),
        "mean_leaf_size": sum(leaf_sizes) / len(leaf_sizes),
        "largest_leaf": max(leaf_sizes),
        "singleton_leaves": sum(size == 1 for size in leaf_sizes),
        "feature_use": dict(feature_use.most_common()),
        "leaf_size_histogram": {
            str(k): v for k, v in sorted(Counter(leaf_sizes).items())
        },
        "split_trace": trace,
    }
    return tree, stats


def choose_schema_from_tree(
    tree: dict[str, Any],
    feature_vector: tuple[int, ...],
    schema_names: list[str],
) -> str:
    node = tree
    while "leaf_mask" not in node:
        feature = int(node["feature"])
        value = str(feature_vector[feature])
        branches = node["branches"]
        if value not in branches:
            raise KeyError(
                f"unseen feature value {node['feature_name']}={value}"
            )
        node = branches[value]
    return schema_names[lowest_bit(int(node["leaf_mask"]))]


def canonical_policy_for_digest(
    tree: dict[str, Any], schema_names: list[str]
) -> Any:
    if "leaf_mask" in tree:
        return {
            "action": schema_names[lowest_bit(int(tree["leaf_mask"]))],
            "admissible_mask": int(tree["leaf_mask"]),
        }
    return {
        "feature": tree["feature_name"],
        "branches": {
            key: canonical_policy_for_digest(value, schema_names)
            for key, value in sorted(tree["branches"].items(), key=lambda kv: int(kv[0]))
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_minimax_policy_v2.json"),
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

    base_bank = coordinate_feature_bank()
    feature_names = ["protected_wdl"] + [name for name, _ in base_bank]
    feature_fns = [fn for _, fn in base_bank]

    cache: dict[tuple[str, bool], int] = {}
    raw_rows: list[
        tuple[Any, tuple[int, ...], set[str], int]
    ] = []
    all_schemas: set[str] = set()
    losing_universal_failures = 0
    policy_terminal_states = 0
    raw_legal_moves = 0
    value_preserving_moves = 0

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, cache, feature_fns
        )
        assert enumeration["mirror_invalid"] == 0
        assert enumeration["mirror_mismatches"] == 0

        for rec in records:
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            legal_moves = list(board.legal_moves)
            raw_legal_moves += len(legal_moves)

            consequences: list[tuple[chess.Move, int]] = []
            for move in legal_moves:
                child = board.copy(stack=False)
                child.push(move)
                consequence = -probe_wdl(tablebase, child, cache)
                consequences.append((move, consequence))

            if rec.wdl < 0:
                # LOSS is a universal verifier obligation: every legal move
                # must preserve the losing value.
                if any(value != rec.wdl for _, value in consequences):
                    losing_universal_failures += 1
                continue

            if not legal_moves:
                # Terminal draw (stalemate) needs no policy action.
                policy_terminal_states += 1
                continue

            admissible = {
                relative_move_schema(board, move)
                for move, consequence in consequences
                if consequence == rec.wdl
            }
            if not admissible:
                raise AssertionError(
                    f"non-losing state has no value-preserving move: {board.fen()}"
                )
            value_preserving_moves += sum(
                consequence == rec.wdl for _, consequence in consequences
            )
            all_schemas.update(admissible)
            vector = (rec.wdl,) + rec.features
            raw_rows.append((rec, vector, admissible, len(legal_moves)))

        assert losing_universal_failures == 0

        schema_names = sorted(all_schemas)
        schema_index = {name: i for i, name in enumerate(schema_names)}
        features: list[tuple[int, ...]] = []
        allowed_masks: list[int] = []
        for _, vector, admissible, _ in raw_rows:
            mask = 0
            for schema in admissible:
                mask |= 1 << schema_index[schema]
            features.append(vector)
            allowed_masks.append(mask)

        tree, policy_stats = compile_policy(
            features, allowed_masks, feature_names
        )

        verification_errors: list[dict[str, Any]] = []
        chosen_schema_counts: Counter[str] = Counter()
        outcome_counts: Counter[int] = Counter()
        for row_index, (rec, vector, admissible, _) in enumerate(raw_rows):
            schema = choose_schema_from_tree(tree, vector, schema_names)
            chosen_schema_counts[schema] += 1
            outcome_counts[rec.wdl] += 1
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            try:
                move = action_for_schema(board, schema)
            except AssertionError as exc:
                if len(verification_errors) < 20:
                    verification_errors.append(
                        {
                            "row": row_index,
                            "fen": board.fen(),
                            "schema": schema,
                            "error": str(exc),
                        }
                    )
                continue
            child = board.copy(stack=False)
            child.push(move)
            consequence = -probe_wdl(tablebase, child, cache)
            if consequence != rec.wdl or schema not in admissible:
                if len(verification_errors) < 20:
                    verification_errors.append(
                        {
                            "row": row_index,
                            "fen": board.fen(),
                            "schema": schema,
                            "move": move.uci(),
                            "expected_wdl": rec.wdl,
                            "actual_consequence": consequence,
                        }
                    )

        if verification_errors:
            raise AssertionError(
                f"compiled policy verification errors: {verification_errors}"
            )

    canonical_policy = canonical_policy_for_digest(tree, schema_names)
    policy_bytes = json.dumps(
        canonical_policy,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()

    # Keep the durable artifact consequentially small: store the canonical
    # action policy, not training row identities.
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_MINIMAX_POLICY",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v1_authority": V1_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "boundary": {
            "material": "White K+P vs Black K",
            "canonical_pawn_files": ["a", "b", "c", "d"],
            "pawn_ranks": [2, 3, 4, 5, 6, 7],
            "policy_domain": "all nonterminal states with Syzygy WDL >= 0",
            "loss_obligation": "universal audit of all legal moves",
            "action_schema": "mover piece + relative displacement + promotion",
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
        "certificate": {
            "policy_states": len(raw_rows),
            "terminal_nonlosing_states": policy_terminal_states,
            "losing_universal_failures": losing_universal_failures,
            "raw_legal_moves": raw_legal_moves,
            "value_preserving_moves_on_policy_domain": value_preserving_moves,
            "available_relative_action_schemas": schema_names,
            "schema_count": len(schema_names),
            "chosen_schema_counts": dict(chosen_schema_counts),
            "policy_outcome_counts": {
                str(k): v for k, v in sorted(outcome_counts.items())
            },
            "verification_errors": 0,
        },
        "compiler": {
            **policy_stats,
            "candidate_features": feature_names,
            "policy_sha256": policy_sha256,
            "canonical_policy": canonical_policy,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "every compiled policy leaf names one relative move schema "
                    "that is legal and WDL-preserving for every KPvK state "
                    "routed to that leaf"
                ),
                (
                    "every losing KPvK state satisfies the universal local "
                    "minimax obligation that all legal moves preserve LOSS"
                ),
            ],
            "candidate": [
                "the policy schemas transfer to held-out/richer pawn endings",
                "adding a well-founded DTZ rank turns WDL preservation into a terminating win certificate",
            ],
            "unknown": [
                "cross-material transfer",
                "well-founded termination of the compiled winning policy",
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
    print("CRYSTAL_CHESS_MINIMAX_POLICY_V2=PASS")
    print(
        f"policy_states={len(raw_rows)} leaves={policy_stats['leaves']} "
        f"compression={policy_stats['state_per_leaf_compression']:.3f}x"
    )
    print(
        f"nodes={policy_stats['decision_nodes']} "
        f"max_depth={policy_stats['max_depth']} "
        f"largest_leaf={policy_stats['largest_leaf']}"
    )
    print(
        f"action_schemas={len(schema_names)} "
        f"verification_errors=0 loss_universal_failures=0"
    )
    print(f"policy_sha256={policy_sha256}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
