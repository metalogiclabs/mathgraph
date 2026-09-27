#!/usr/bin/env python3
"""Crystal Go V0: exact local capture capability and cross-board transfer.

Declared game boundary
----------------------
This is a bounded local Go/tsumego subgame, not a claim about full-board Go.

Rules:
* ordinary stone placement with orthogonal groups/liberties,
* captures after placement,
* suicide forbidden,
* simple-ko immediate board repetition forbidden,
* pass is legal,
* Black attacks a marked White target stone,
* Black wins iff that original target stone is captured within H plies,
* otherwise White survives the bounded encounter,
* legal move alphabet is a declared 3x3 region.

Acquisition world:
* complete 3x3 board, target at center, Black to move,
* every assignment of the other 8 intersections in {empty, black, white},
  filtered to legal static Go positions,
* exact minimax over the declared H-ply encounter.

Transfer world:
* 5x5 board with the same central 3x3 move region and marked target,
* deterministic sparse outer-ring contexts alter liberties, connections and
  capture consequences but are frozen/unplayable,
* for every outer context we exhaust every inner 3x3 assignment,
* no 5x5 labels enter policy acquisition.

The learned tree is only a compact certificate constructor. The recursive
rules engine is the independent authority.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import sys
import time

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from mathgraph.crystal import content_id


EMPTY = 0
BLACK = 1
WHITE = -1
PASS = -1
SCHEMA = "mathgraph.crystal-go.local-capture.v0"


def neighbors(i: int, n: int) -> tuple[int, ...]:
    r, c = divmod(i, n)
    out = []
    if r > 0:
        out.append(i - n)
    if r + 1 < n:
        out.append(i + n)
    if c > 0:
        out.append(i - 1)
    if c + 1 < n:
        out.append(i + 1)
    return tuple(out)


def group_and_liberties(board: tuple[int, ...], n: int, start: int) -> tuple[frozenset[int], frozenset[int]]:
    color = board[start]
    if color == EMPTY:
        return frozenset(), frozenset()
    group = {start}
    liberties = set()
    stack = [start]
    while stack:
        i = stack.pop()
        for j in neighbors(i, n):
            if board[j] == EMPTY:
                liberties.add(j)
            elif board[j] == color and j not in group:
                group.add(j)
                stack.append(j)
    return frozenset(group), frozenset(liberties)


def static_legal(board: tuple[int, ...], n: int) -> bool:
    seen = set()
    for i, stone in enumerate(board):
        if stone == EMPTY or i in seen:
            continue
        group, liberties = group_and_liberties(board, n, i)
        seen.update(group)
        if not liberties:
            return False
    return True


def play(
    board: tuple[int, ...],
    n: int,
    turn: int,
    move: int,
    previous_board: tuple[int, ...] | None,
    allowed_moves: frozenset[int],
) -> tuple[tuple[int, ...], int, tuple[int, ...]] | None:
    if move == PASS:
        return board, -turn, board
    if move not in allowed_moves or board[move] != EMPTY:
        return None

    work = list(board)
    work[move] = turn
    enemy = -turn

    # Capture adjacent enemy groups with no liberties after placement.
    checked: set[int] = set()
    for j in neighbors(move, n):
        if work[j] != enemy or j in checked:
            continue
        group, liberties = group_and_liberties(tuple(work), n, j)
        checked.update(group)
        if not liberties:
            for k in group:
                work[k] = EMPTY

    candidate = tuple(work)
    own_group, own_liberties = group_and_liberties(candidate, n, move)
    if not own_group or not own_liberties:
        return None
    if previous_board is not None and candidate == previous_board:
        return None
    return candidate, -turn, board


@dataclass
class ExactCaptureSolver:
    n: int
    target: int
    allowed_moves: frozenset[int]
    horizon: int

    def __post_init__(self) -> None:
        self.cache: dict[tuple, bool] = {}
        self.calls = 0

    def can_black_force(
        self,
        board: tuple[int, ...],
        turn: int = BLACK,
        previous_board: tuple[int, ...] | None = None,
        plies_left: int | None = None,
    ) -> bool:
        if board[self.target] != WHITE:
            return True
        if plies_left is None:
            plies_left = self.horizon
        if plies_left <= 0:
            return False

        key = (board, turn, previous_board, plies_left)
        if key in self.cache:
            return self.cache[key]
        self.calls += 1

        children = []
        for move in tuple(sorted(self.allowed_moves)) + (PASS,):
            child = play(board, self.n, turn, move, previous_board, self.allowed_moves)
            if child is not None:
                children.append(child)

        if turn == BLACK:
            value = any(
                self.can_black_force(b, t, prev, plies_left - 1)
                for b, t, prev in children
            )
        else:
            # White chooses a reply that survives if one exists.
            value = all(
                self.can_black_force(b, t, prev, plies_left - 1)
                for b, t, prev in children
            )
        self.cache[key] = value
        return value

    def winning_black_moves(self, board: tuple[int, ...]) -> tuple[int, ...]:
        if not self.can_black_force(board, BLACK, None, self.horizon):
            return ()
        out = []
        for move in tuple(sorted(self.allowed_moves)) + (PASS,):
            child = play(board, self.n, BLACK, move, None, self.allowed_moves)
            if child is None:
                continue
            b, t, prev = child
            if self.can_black_force(b, t, prev, self.horizon - 1):
                out.append(move)
        return tuple(out)


def center_region(n: int) -> tuple[frozenset[int], int]:
    center = n // 2
    target = center * n + center
    region = {
        (center + dr) * n + (center + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
    }
    return frozenset(region), target


def role(move: int, n: int, target: int) -> str:
    if move == PASS:
        return "PASS"
    tr, tc = divmod(target, n)
    r, c = divmod(move, n)
    return f"PLAY:{c-tc:+d},{r-tr:+d}"


def move_from_role(label: str, n: int, target: int) -> int | None:
    if label == "PASS":
        return PASS
    if not label.startswith("PLAY:"):
        return None
    body = label.split(":", 1)[1]
    dx_text, dy_text = body.split(",")
    dx, dy = int(dx_text), int(dy_text)
    tr, tc = divmod(target, n)
    r, c = tr + dy, tc + dx
    if not (0 <= r < n and 0 <= c < n):
        return None
    return r * n + c


def local_features(board: tuple[int, ...], n: int, target: int) -> tuple[int, ...]:
    tr, tc = divmod(target, n)
    cells = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            cells.append(board[(tr + dr) * n + (tc + dc)])
    target_group, target_libs = group_and_liberties(board, n, target)
    black = sum(stone == BLACK for stone in cells)
    white = sum(stone == WHITE for stone in cells)
    return tuple(cells) + (
        len(target_group),
        len(target_libs),
        black,
        white,
    )


def enumerate_inner_assignments(
    n: int,
    outer: tuple[int, ...] | None = None,
) -> list[tuple[int, ...]]:
    region, target = center_region(n)
    others = [i for i in sorted(region) if i != target]
    if outer is None:
        base = [EMPTY] * (n * n)
    else:
        base = list(outer)
    out = []
    for assignment in itertools.product((EMPTY, BLACK, WHITE), repeat=len(others)):
        work = list(base)
        for i in region:
            work[i] = EMPTY
        work[target] = WHITE
        for i, stone in zip(others, assignment):
            work[i] = stone
        board = tuple(work)
        if static_legal(board, n):
            out.append(board)
    return out


def deterministic_outer_contexts(n: int, count: int, seed: int) -> list[tuple[int, ...]]:
    region, _target = center_region(n)
    outer_cells = [i for i in range(n * n) if i not in region]
    rng = random.Random(seed)
    contexts = []
    seen = set()
    while len(contexts) < count:
        work = [EMPTY] * (n * n)
        for i in outer_cells:
            x = rng.random()
            if x < 0.14:
                work[i] = BLACK
            elif x < 0.28:
                work[i] = WHITE
        key = tuple(work)
        if key in seen:
            continue
        seen.add(key)
        contexts.append(key)
    return contexts


def sha256_json(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--outer-contexts", type=int, default=16)
    ap.add_argument("--outer-seed", type=int, default=20260928)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_go_local_capture_v0.json"),
    )
    args = ap.parse_args()
    started = time.time()

    # Complete acquisition world.
    source_n = 3
    source_region, source_target = center_region(source_n)
    source_boards = enumerate_inner_assignments(source_n)
    source_solver = ExactCaptureSolver(
        source_n, source_target, source_region, args.horizon
    )

    winning_boards = []
    winning_move_sets = []
    move_frequency = Counter()
    win_count = 0
    lose_count = 0
    for board in source_boards:
        moves = source_solver.winning_black_moves(board)
        if moves:
            win_count += 1
            winning_boards.append(board)
            winning_move_sets.append(moves)
            move_frequency.update(role(m, source_n, source_target) for m in moves)
        else:
            lose_count += 1

    role_rank = {
        label: rank
        for rank, (label, _n) in enumerate(
            sorted(move_frequency.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }
    labels = []
    X = []
    for board, moves in zip(winning_boards, winning_move_sets):
        roles = [role(m, source_n, source_target) for m in moves]
        label = min(roles, key=lambda x: (role_rank[x], x))
        labels.append(label)
        X.append(local_features(board, source_n, source_target))

    tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    tree.fit(np.asarray(X, dtype=np.int16), labels)
    source_pred = [str(x) for x in tree.predict(np.asarray(X, dtype=np.int16))]

    source_invalid = 0
    for pred, moves in zip(source_pred, winning_move_sets):
        if pred not in {role(m, source_n, source_target) for m in moves}:
            source_invalid += 1
    if source_invalid:
        raise AssertionError(f"source policy invalid on {source_invalid} winning states")

    # Cross-board transfer across many complete inner worlds.
    target_n = 5
    target_region, target_target = center_region(target_n)
    contexts = deterministic_outer_contexts(
        target_n, args.outer_contexts, args.outer_seed
    )

    transfer_total = 0
    transfer_success = 0
    baseline_success = 0
    target_wins = 0
    target_losses = 0
    context_rows = []
    residual_examples = []
    default_label = sorted(
        move_frequency.items(), key=lambda kv: (-kv[1], kv[0])
    )[0][0]

    for context_index, outer in enumerate(contexts):
        boards = enumerate_inner_assignments(target_n, outer)
        solver = ExactCaptureSolver(
            target_n, target_target, target_region, args.horizon
        )
        ctx_total = 0
        ctx_success = 0
        ctx_baseline = 0
        ctx_wins = 0

        for board in boards:
            winning_moves = solver.winning_black_moves(board)
            if not winning_moves:
                continue

            target_wins += 1
            ctx_wins += 1
            transfer_total += 1
            ctx_total += 1

            features = np.asarray(
                [local_features(board, target_n, target_target)],
                dtype=np.int16,
            )
            predicted = str(tree.predict(features)[0])
            predicted_move = move_from_role(predicted, target_n, target_target)
            winning_roles = {role(m, target_n, target_target) for m in winning_moves}
            ok = predicted in winning_roles
            transfer_success += int(ok)
            ctx_success += int(ok)

            base_ok = default_label in winning_roles
            baseline_success += int(base_ok)
            ctx_baseline += int(base_ok)

            if not ok and len(residual_examples) < 40:
                residual_examples.append(
                    {
                        "context": context_index,
                        "board": list(board),
                        "predicted_role": predicted,
                        "winning_roles": sorted(winning_roles),
                        "features": [int(x) for x in features[0]],
                    }
                )

        target_losses += len(boards) - ctx_wins
        context_rows.append(
            {
                "context": context_index,
                "legal_inner_states": len(boards),
                "winning_states": ctx_wins,
                "policy_success": ctx_success,
                "policy_ratio": ctx_success / ctx_total if ctx_total else 1.0,
                "baseline_success": ctx_baseline,
                "baseline_ratio": ctx_baseline / ctx_total if ctx_total else 1.0,
                "solver_cache_states": len(solver.cache),
                "solver_calls": solver.calls,
                "outer_sha256": sha256_json(list(outer)),
            }
        )

    tree_info = {
        "nodes": int(tree.tree_.node_count),
        "leaves": int(tree.tree_.n_leaves),
        "max_depth": int(tree.tree_.max_depth),
    }
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_GO_LOCAL_CAPTURE_TRANSFER",
        "rules": {
            "capture": "ordinary orthogonal Go group capture",
            "suicide": "forbidden",
            "ko": "simple immediate board repetition forbidden",
            "pass": "legal and consumes one ply",
            "objective": "Black captures marked original White target within bounded horizon",
            "horizon_plies": args.horizon,
            "move_region": "declared central 3x3 only",
            "outside_5x5_context": "frozen stones affect liberties/connections/captures but cannot receive new plays",
        },
        "acquisition": {
            "board_size": 3,
            "complete_static_legal_states": len(source_boards),
            "winning_states": win_count,
            "surviving_states": lose_count,
            "distinct_winning_roles": len(move_frequency),
            "role_frequency": dict(move_frequency),
            "tree": tree_info,
            "source_invalid_certificates": source_invalid,
            "states_per_leaf": len(winning_boards) / tree_info["leaves"],
            "solver_cache_states": len(source_solver.cache),
            "solver_calls": source_solver.calls,
        },
        "prospective_transfer": {
            "board_size": 5,
            "outer_contexts": args.outer_contexts,
            "outer_seed": args.outer_seed,
            "all_inner_assignments_exhausted_per_context": True,
            "winning_states_checked": transfer_total,
            "policy_success": transfer_success,
            "policy_ratio": transfer_success / transfer_total if transfer_total else 1.0,
            "baseline_role": default_label,
            "baseline_success": baseline_success,
            "baseline_ratio": baseline_success / transfer_total if transfer_total else 1.0,
            "absolute_gain": (
                (transfer_success - baseline_success) / transfer_total
                if transfer_total
                else 0.0
            ),
            "remaining_residual": transfer_total - transfer_success,
            "contexts": context_rows,
            "residual_examples": residual_examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the source policy is exact on every winning legal state in the declared complete 3x3 acquisition world",
                "no 5x5 labels enter source policy acquisition",
                "every reported 5x5 transfer success is independently checked by exact bounded minimax under the declared local Go rules",
            ],
            "unknown": [
                "standard unbounded full-board Go",
                "territory/scoring optimality",
                "superko beyond the declared simple-ko boundary",
                "transfer to unrestricted move regions",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print("CRYSTAL_GO_LOCAL_CAPTURE_V0=PASS")
    print(
        f"source legal={len(source_boards)} wins={win_count} "
        f"tree_leaves={tree_info['leaves']} depth={tree_info['max_depth']}"
    )
    print(
        f"transfer wins={transfer_total} success={transfer_success} "
        f"ratio={transfer_success/transfer_total if transfer_total else 1.0:.6f} "
        f"baseline={baseline_success/transfer_total if transfer_total else 1.0:.6f} "
        f"residual={transfer_total-transfer_success}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
