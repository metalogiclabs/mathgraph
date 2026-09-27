#!/usr/bin/env python3
"""Crystal Chess V16: prospective transfer of the frozen V14 hybrid guard to six-piece chess.

Source authority:
* V14 compiles a zero-false-positive structural guard on the complete KPPvK
  ranks-2..6 boundary.
* V16 loads that exact serialized guard artifact. It does not relearn the guard.

Target:
* White K+4P vs Black K.
* Exactly one pawn on each of files b,c,d,e, ranks 2..4.
* All legal king placements and both sides to move.
* Exact KPPPPvK six-piece Syzygy WDL is used only after a concrete shortcut
  candidate is committed.

Go-inspired boundary discipline:
* A local anchor capability is eligible only if the frozen V14 pair guard
  accepts the anchor against EVERY other pawn in the richer position.
* The pre-existing V7 connected-front law can additionally disable independent
  local composition when adjacent-file pawns occupy the same rank.
* Outside a certified shortcut, the ordinary full legal-move frontier is
  unchanged.

The experiment reports both:
1. raw V14 pairwise universal transfer; and
2. V14 + previously-earned V7 interaction boundary.

No target labels influence guard selection or admission.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy,
    exact_wdl,
    precompute_roles,
)
from crystal_chess_verified_hybrid_search_v14 import (
    BASE_V12_AUTHORITY,
    TIER_NAMES,
    candidate_bindings,
    signature,
)


SCHEMA = "mathgraph.crystal-chess.hybrid-guard-transfer.v16"
V14_RUN = 36357299241
V14_BRANCH_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-verified-hybrid-search-v14"
    "@55be612bbf8cf3bd26ef10d5474873443f0f7edd"
)
V7_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-interaction-law-v7"
    "@e3b1d2230236c67d574f6e89c4fbc01e1d8d4b34"
)

def make_kppppvk(
    wk: int,
    bk: int,
    p0: int,
    p1: int,
    p2: int,
    p3: int,
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
    for pawn in (p0, p1, p2, p3):
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def connected_front(pawns: tuple[int, ...]) -> bool:
    for i in range(len(pawns)):
        for j in range(i + 1, len(pawns)):
            if (
                abs(
                    chess.square_file(pawns[i])
                    - chess.square_file(pawns[j])
                )
                == 1
                and chess.square_rank(pawns[i])
                == chess.square_rank(pawns[j])
            ):
                return True
    return False



def load_guard(path: Path) -> tuple[dict[str, object], set[tuple[object, ...]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line:
            raise ValueError("empty V14 guard artifact")
        header = json.loads(header_line)
        signatures: set[tuple[object, ...]] = set()
        for line in handle:
            row = json.loads(line)
            signatures.add(tuple(row["signature"]))
    if not signatures:
        raise ValueError("V14 guard contains no safe signatures")
    return header, signatures


def pawn_quads() -> list[tuple[int, int, int, int]]:
    return [
        (
            chess.square(1, rb),  # b-file
            chess.square(2, rc),  # c-file
            chess.square(3, rd),  # d-file
            chess.square(4, re),  # e-file
        )
        for rb in range(1, 4)
        for rc in range(1, 4)
        for rd in range(1, 4)
        for re in range(1, 4)
    ]


def target_boundary():
    for p0, p1, p2, p3 in pawn_quads():
        pawns = (p0, p1, p2, p3)
        for wk in chess.SQUARES:
            if wk in pawns:
                continue
            for bk in chess.SQUARES:
                if bk in pawns or bk == wk:
                    continue
                for turn in (False, True):
                    board = make_kppppvk(wk, bk, p0, p1, p2, p3, turn)
                    if board.is_valid():
                        yield pawns, wk, bk, turn, board


def guarded_candidates(
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    role_map: dict[tuple[int, int, int, int], str],
    tier: int,
    safe_signatures: set[tuple[object, ...]],
    *,
    block_connected_front: bool,
) -> list[chess.Move]:
    if block_connected_front and connected_front(pawns):
        return []

    seen: set[chess.Move] = set()
    out: list[chess.Move] = []

    # V14's candidate_bindings accepts two pawns. Here the role is still the
    # same frozen single-pawn constructor. For each anchor, form the concrete
    # move once, then require the V14 pair contract against every other pawn.
    for anchor in pawns:
        role = role_map[(wk, bk, anchor, int(turn))]

        # Recover the same concrete-move semantics as V14/V12 by pairing the
        # anchor with any one other pawn. The "other" affects only the guard
        # signature; the generated move depends on anchor+role.
        other0 = next(other for other in pawns if other != anchor)
        bindings = candidate_bindings(
            board, anchor, other0, wk, bk, turn, role_map
        )
        # candidate_bindings returns both supplied anchors; select the requested
        # anchor binding explicitly.
        binding = None
        for b_anchor, _b_other, b_role, move in bindings:
            if b_anchor == anchor and b_role == role:
                binding = move
                break
        if binding is None:
            continue

        admissible = True
        for other in pawns:
            if other == anchor:
                continue
            sig = signature(board, anchor, other, role, tier)
            if sig not in safe_signatures:
                admissible = False
                break

        if admissible and binding not in seen:
            seen.add(binding)
            out.append(binding)

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    header, safe_signatures = load_guard(args.guard)
    tier = int(header["tier_index"])
    threshold = int(header["minimum_support"])
    tier_name = str(header["tier"])
    if tier_name != TIER_NAMES[tier]:
        raise AssertionError("V14 guard tier metadata mismatch")

    files = sorted(args.tablebase_dir.glob("*.rtbw"))
    names = {p.name for p in files}
    for req in ("KPvK.rtbw", "KPPvK.rtbw", "KPPPPvK.rtbw", "KPPPPvK.rtbw"):
        if req not in names:
            raise SystemExit(f"missing {req}")

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]

    configs = {
        "v14_pair_universal": Counter(),
        "v14_pair_universal_plus_connected_front": Counter(),
    }
    wrong_examples: dict[str, list[dict[str, object]]] = {
        key: [] for key in configs
    }

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, kpvk_enum, kpvk_nonterminal = acquire_policy(
            tb, feature_fns
        )
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        for pawns, wk, bk, turn, board in target_boundary():
            legal_count = board.legal_moves.count()
            for counter in configs.values():
                counter["legal_states"] += 1
                if legal_count == 0:
                    counter["terminal_states"] += 1
                else:
                    counter["nonterminal_states"] += 1
                    counter["baseline_child_expansions"] += legal_count

            if legal_count == 0:
                continue

            root = exact_wdl(tb, board)

            for name, block in (
                ("v14_pair_universal", False),
                ("v14_pair_universal_plus_connected_front", True),
            ):
                counter = configs[name]
                candidates = guarded_candidates(
                    board,
                    pawns,
                    wk,
                    bk,
                    turn,
                    role_map,
                    tier,
                    safe_signatures,
                    block_connected_front=block,
                )
                counter["qualified_states"] += int(bool(candidates))
                counter["qualified_candidate_moves"] += len(candidates)

                all_safe = True
                first_safe = False
                for idx, move in enumerate(candidates):
                    board.push(move)
                    consequence = -exact_wdl(tb, board)
                    board.pop()
                    ok = consequence == root
                    counter["candidate_probes"] += 1
                    counter["safe_candidates"] += int(ok)
                    counter["wrong_candidates"] += int(not ok)
                    if idx == 0:
                        first_safe = ok
                    all_safe = all_safe and ok
                    if not ok and len(wrong_examples[name]) < 50:
                        wrong_examples[name].append(
                            {
                                "fen": board.fen(),
                                "pawns": [chess.square_name(p) for p in pawns],
                                "turn": "white" if turn else "black",
                                "move": move.uci(),
                                "root_wdl": root,
                                "child_consequence": consequence,
                            }
                        )

                if candidates:
                    counter["all_candidates_safe_states"] += int(all_safe)
                    counter["first_candidate_safe_states"] += int(first_safe)
                    # Execution boundary: if the guard is genuinely certified
                    # on the target, hybrid search can expand one child. Until
                    # then we still measure what that pruning would cost.
                    counter["hybrid_child_expansions"] += 1
                    counter["saved_child_expansions"] += legal_count - 1
                else:
                    counter["hybrid_child_expansions"] += legal_count

    result_configs = {}
    for name, counter in configs.items():
        nonterminal = int(counter["nonterminal_states"])
        baseline = int(counter["baseline_child_expansions"])
        hybrid = int(counter["hybrid_child_expansions"])
        qualified = int(counter["qualified_states"])
        wrong = int(counter["wrong_candidates"])
        result_configs[name] = {
            **dict(counter),
            "state_coverage_ratio": qualified / nonterminal if nonterminal else 0.0,
            "candidate_precision": (
                int(counter["safe_candidates"])
                / int(counter["qualified_candidate_moves"])
                if counter["qualified_candidate_moves"]
                else 1.0
            ),
            "zero_false_positive": wrong == 0,
            "child_reduction_ratio_if_admitted": (
                int(counter["saved_child_expansions"]) / baseline
                if baseline else 0.0
            ),
            "expansion_speedup_factor_if_admitted": (
                baseline / hybrid if hybrid else 1.0
            ),
            "wrong_examples": wrong_examples[name],
        }

    interaction = result_configs[
        "v14_pair_universal_plus_connected_front"
    ]
    status = (
        "WARRANTED_PROSPECTIVE_KPPPPVK_VERIFIED_HYBRID_GUARD_TRANSFER"
        if interaction["qualified_states"] > 0
        and interaction["zero_false_positive"]
        else "EXACT_RESIDUAL_KPPPPVK_HYBRID_GUARD_TRANSFER"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "v14_authority": V14_BRANCH_AUTHORITY,
        "v14_run": V14_RUN,
        "v14_guard": {
            "tier": tier_name,
            "tier_index": tier,
            "minimum_support": threshold,
            "safe_signatures": len(safe_signatures),
            "artifact_path": str(args.guard),
        },
        "v7_interaction_authority": V7_AUTHORITY,
        "target": {
            "material": "White K+4P vs Black K",
            "pawn_files": ["b", "c", "d", "e"],
            "pawn_ranks": [2, 3, 4],
            "all_legal_king_placements": True,
            "both_sides_to_move": True,
            "complete_declared_boundary": True,
        },
        "method": {
            "guard_transfer": (
                "an anchor is admitted only when the frozen V14 pair guard "
                "accepts it against every other pawn"
            ),
            "interaction_variant": (
                "also fail closed on the already-qualified V7 connected-front "
                "condition"
            ),
            "fallback": "unchanged full legal-move frontier",
            "target_authority_timing": (
                "KPPPPvK WDL queried only after guard commits candidate moves"
            ),
        },
        "frozen_kpvk": {
            "nonterminal_states": kpvk_nonterminal,
            "role_frequency": frequency,
            "enumeration": kpvk_enum,
        },
        "configs": result_configs,
        "epistemic_boundary": {
            "warranted_if_green": [
                "the V14 guard is loaded unchanged from its source artifact",
                "no KPPPPvK target label changes the guard, threshold, signature vocabulary, or V7 interaction law",
                "every candidate admitted by the promoted interaction configuration preserves exact target WDL",
                "outside admitted states full child search is unchanged",
            ],
            "unknown": [
                "transfer to broader K+4P boundaries and mixed-piece material",
                "production alpha-beta wall-clock speedup",
                "general chess solution",
            ],
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

    print(f"CRYSTAL_CHESS_HYBRID_GUARD_TRANSFER_V16={status}")
    for name, row in result_configs.items():
        print(
            f"{name}: coverage={row['qualified_states']}/{row['nonterminal_states']} "
            f"ratio={row['state_coverage_ratio']:.8f} "
            f"wrong_candidates={row['wrong_candidates']} "
            f"precision={row['candidate_precision']:.8f} "
            f"child_reduction={row['child_reduction_ratio_if_admitted']:.8f}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
