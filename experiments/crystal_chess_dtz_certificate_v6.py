#!/usr/bin/env python3
"""Crystal Chess V6: exact DTZ progress-certificate compiler on KPvK.

V3 compiled a WDL-preserving selector. That is not yet a conversion strategy:
preserving a winning WDL class alone need not certify progress against
repetition/50-move effects.

Syzygy DTZ is the stronger protected observer. For each legal move we inspect
the exact child (WDL, DTZ) from the opponent's point of view. Standard
tablebase minimax prefers the minimum child WDL and, among equal WDL, the
maximum child DTZ. This keeps the opponent in the worst WDL class and applies
the DTZ progress tiebreak. The python-chess Syzygy documentation states that
minmaxing DTZ guarantees winning a won position and drawing a drawn position.

The learned tree is only a compact certificate constructor. Exact Syzygy
WDL+DTZ remains authority, and every emitted role is exhaustively replayed.
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
    tree_summary,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-dtz-goal-certificate.v6"
V3_AUTHORITY = (
    "metalogiclabs/mathgraph@73be9f4159816bf18a3ca70a1fb3eeb9793536a6"
)
DTZ_INTERFACE = "chess.syzygy.wdl-dtz.v1"


def probe_dtz_safe(tablebase: chess.syzygy.Tablebase, board: chess.Board) -> int:
    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
        return 0
    return int(tablebase.probe_dtz(board))


def dtz_optimal_roles(
    board: chess.Board,
    root_wdl: int,
    root_dtz: int,
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
) -> tuple[str, ...]:
    # The exact KPvK census contains only unconditional wins/draws/losses.
    # This lets us use the unconditional Syzygy Bellman recurrence directly.
    if root_wdl not in (-2, 0, 2):
        raise AssertionError(f"unexpected cursed/blessed KPvK state: {root_wdl}")

    roles: set[str] = set()
    legal_count = 0
    for move in board.legal_moves:
        legal_count += 1
        child = board.copy(stack=False)
        child.push(move)
        child_wdl = probe_wdl(tablebase, child, wdl_cache)

        # First preserve the exact game-theoretic WDL value.
        if -child_wdl != root_wdl:
            continue

        if root_wdl == 0:
            candidate_dtz = 0
        elif child.halfmove_clock == 0:
            # A capture or pawn move is itself the next zeroing move.
            candidate_dtz = 1 if root_wdl == 2 else -1
        else:
            child_dtz = probe_dtz_safe(tablebase, child)
            candidate_dtz = -child_dtz + (1 if root_wdl == 2 else -1)

        # Independent replay criterion: the chosen edge must satisfy the exact
        # root DTZ Bellman value, including zeroing moves.
        if candidate_dtz == root_dtz:
            roles.add(move_role(board, move))

    if legal_count == 0:
        return ()
    if not roles:
        raise AssertionError(
            f"nonterminal state has no root-DTZ-realizing role "
            f"wdl={root_wdl} dtz={root_dtz} fen={board.fen()}"
        )
    return tuple(sorted(roles))


def audit_predictions(
    clf: DecisionTreeClassifier,
    X: np.ndarray,
    indices: list[int],
    role_sets: list[tuple[str, ...]],
) -> dict[str, object]:
    pred = [str(x) for x in clf.predict(X[indices])]
    invalid: list[dict[str, object]] = []
    good = 0
    for role, i in zip(pred, indices):
        if role in role_sets[i]:
            good += 1
        elif len(invalid) < 20:
            invalid.append(
                {
                    "state_index": i,
                    "predicted_role": role,
                    "dtz_optimal_roles": list(role_sets[i]),
                }
            )
    return {
        "states": len(indices),
        "valid": good,
        "invalid": len(indices) - good,
        "valid_ratio": good / len(indices) if indices else 1.0,
        "invalid_examples": invalid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_dtz_certificate_v6.json"),
    )
    args = parser.parse_args()
    started = time.time()

    wdl_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    dtz_files = sorted(args.tablebase_dir.glob("*.rtbz"))
    if not wdl_files or not dtz_files:
        raise SystemExit("both WDL (.rtbw) and DTZ (.rtbz) files are required")
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(wdl_files + dtz_files)
    ]

    bank = coordinate_feature_bank()
    feature_names = [name for name, _ in bank]
    feature_fns = [fn for _, fn in bank]
    wdl_cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, wdl_cache, feature_fns
        )
        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        terminal: list[int] = []
        dtz_distribution: Counter[int] = Counter()

        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            if list(board.legal_moves):
                root_dtz = probe_dtz_safe(tablebase, board)
                dtz_distribution[root_dtz] += 1
                if rec.wdl not in (-2, 0, 2):
                    raise AssertionError(
                        f"KPvK unexpectedly contains WDL={rec.wdl}"
                    )
                roles = dtz_optimal_roles(
                    board, rec.wdl, root_dtz, tablebase, wdl_cache
                )
                role_sets.append(roles)
                nonterminal.append(i)
            else:
                role_sets.append(())
                terminal.append(i)

    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
    tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    tree.fit(X[nonterminal], [labels[i] for i in nonterminal])
    audit = audit_predictions(tree, X, nonterminal, role_sets)
    if audit["invalid"] != 0:
        raise AssertionError(audit["invalid_examples"])

    summary = tree_summary(tree)
    summary["used_features"] = [
        feature_names[int(k)]
        for k in sorted(map(int, summary["used_feature_counts"].keys()))
    ]

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_DTZ_PROGRESS_CERTIFICATE",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "protected_interfaces": [PROTECTED_INTERFACE, DTZ_INTERFACE],
        "method": {
            "move_order": "exact unconditional Syzygy DTZ Bellman recurrence",
            "child_view": "opponent side-to-move",
            "zeroing_move_rule": "candidate DTZ = +1 on win / -1 on loss",
            "nonzeroing_rule": "candidate DTZ = -child_DTZ +1 on win / -1 on loss",
            "obligation": "emit one role whose concrete legal move exactly realizes root WDL and root DTZ",
            "representation": "generic geometry -> symbolic CART policy",
        },
        "authority": {
            "kind": "Syzygy WDL + DTZ50''",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "enumeration": enumeration,
        "coverage": {
            "states": len(records),
            "nonterminal_states": len(nonterminal),
            "terminal_states": len(terminal),
            "distinct_dtz_optimal_roles": len(
                {role for roles in role_sets for role in roles}
            ),
            "dtz_distribution": {
                str(k): v for k, v in sorted(dtz_distribution.items())
            },
        },
        "exact_progress_policy": {
            "role_frequency": role_frequency,
            "tree": summary,
            "audit": audit,
            "states_per_leaf": len(nonterminal) / int(summary["leaves"]),
            "compression_vs_state_table": len(nonterminal) / int(summary["leaves"]),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "every nonterminal state in the declared canonical KPvK cover receives a role matching at least one legal move that exactly reproduces the root Syzygy WDL and DTZ Bellman value",
                "the symbolic policy is a compact certificate constructor for the exact tablebase objective, not a replacement authority",
            ],
            "external_semantic_fact": (
                "python-chess documents that minmaxing Syzygy DTZ guarantees "
                "winning a won position and drawing a drawn position"
            ),
            "unknown": [
                "transfer of the DTZ policy to richer material",
                "general chess solution",
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
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_DTZ_CERTIFICATE_V6=PASS")
    print(
        f"states={len(records)} nonterminal={len(nonterminal)} "
        f"roles={result['coverage']['distinct_dtz_optimal_roles']}"
    )
    print(
        f"tree leaves={summary['leaves']} depth={summary['max_depth']} "
        f"compression={result['exact_progress_policy']['compression_vs_state_table']:.3f}x"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
