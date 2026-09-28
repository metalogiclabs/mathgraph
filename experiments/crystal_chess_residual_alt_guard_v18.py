#!/usr/bin/env python3
"""Crystal Chess V18: residual-only alternate-witness applicability guard.

V17 diagnostic showed that replacing one preferred witness by the whole local
certificate set under the *same* V14 pair guard is unsafe on the K+3P source:
some alternate witnesses need a different applicability contract.

V18 therefore preserves V14 unchanged and learns a second guard only where V14
abstains.

Acquisition:
* Source = complete V15 K+3P b-c-d ranks-2..4 boundary.
* Preferred V14 guard is frozen and remains authoritative where it fires.
* Only source states where that guard abstains may contribute evidence.
* On those states, enumerate every exact local KPvK WDL-preserving relative
  role for every pawn projection.
* Audit each concrete richer-material move against exact K+3P WDL.
* A pair-interface signature enters the alternate-witness bank iff support is
  at least the frozen V14 threshold and it has zero failures over every
  acquisition occurrence.
* An alternate candidate is executable only when EVERY one of its pair
  signatures belongs to this separate alternate bank.

Prospective target:
* Complete V16 K+4P b-c-d-e ranks-2..4 boundary.
* Preferred V14 guard executes first, unchanged.
* Only its abstentions may use the frozen alternate-witness bank.
* K+4P truth is queried only after candidate commitment.
* Outside both guards the full legal-move frontier is unchanged.

This directly implements the Go/Crystal lesson:
same protected move consequence can require a different applicability
interface depending on which capability/witness produced it.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from crystal_chess_residual_certificate_set_v17 import (
    load_guard,
    source_pawn_tuples,
    target_pawn_tuples,
    iter_boundary,
    preferred_candidates,
    all_local_candidates,
)


SCHEMA = "mathgraph.crystal-chess.residual-alt-guard.v18"
V14_RUN = 36357299241
V15_RUN = 36359645338
V16_RUN = 36359934616
V17_DIAGNOSTIC_RUN = 36360359244
V14_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-verified-hybrid-search-v14"
    "@55be612bbf8cf3bd26ef10d5474873443f0f7edd"
)
V15_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v15"
    "@7f258e22057e8ffe1bb51c72ddca5d1ca3316949"
)
V16_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v16"
    "@80599fe6c9dd509a18119bcee6f52f91290d7b33"
)


def audit_move(
    tb: chess.syzygy.Tablebase,
    board: chess.Board,
    move: chess.Move,
    root: int,
) -> bool:
    child = board.copy(stack=False)
    child.push(move)
    return -exact_wdl(tb, child) == root


def admitted_alternates(
    *,
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    tb: chess.syzygy.Tablebase,
    cache,
    role_cache,
    tier: int,
    alt_bank: set[tuple[object, ...]],
):
    rows = all_local_candidates(
        board=board,
        pawns=pawns,
        wk=wk,
        bk=bk,
        turn=turn,
        tb=tb,
        cache=cache,
        role_cache=role_cache,
        tier=tier,
    )
    out = []
    seen: set[chess.Move] = set()
    for move, anchor, role, sigs in rows:
        if move in seen:
            continue
        if all(sig in alt_bank for sig in sigs):
            seen.add(move)
            out.append((move, anchor, role, sigs))
    return out


def acquire_alt_bank(
    *,
    tb: chess.syzygy.Tablebase,
    cache,
    role_cache,
    role_map,
    tier: int,
    base_bank: set[tuple[object, ...]],
    threshold: int,
):
    stats: dict[tuple[object, ...], list[int]] = defaultdict(
        lambda: [0, 0]
    )
    counts = Counter()

    for pawns, wk, bk, turn, board in iter_boundary(source_pawn_tuples()):
        legal_count = board.legal_moves.count()
        if legal_count == 0:
            continue
        counts["nonterminal_states"] += 1

        base = preferred_candidates(
            board, pawns, wk, bk, turn, role_map, tier, base_bank
        )
        if base:
            counts["preferred_covered"] += 1
            continue

        counts["preferred_residual"] += 1
        root = exact_wdl(tb, board)

        for move, _anchor, _role, sigs in all_local_candidates(
            board=board,
            pawns=pawns,
            wk=wk,
            bk=bk,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            tier=tier,
        ):
            ok = audit_move(tb, board, move, root)
            counts["candidate_moves"] += 1
            counts["safe_candidate_moves"] += int(ok)
            counts["wrong_candidate_moves"] += int(not ok)
            for sig in sigs:
                cell = stats[sig]
                cell[0] += 1
                cell[1] += int(not ok)

    alt_bank = {
        sig
        for sig, (support, failures) in stats.items()
        if support >= threshold and failures == 0
    }
    counts["pair_signatures_seen"] = len(stats)
    counts["alternate_safe_signatures"] = len(alt_bank)
    return alt_bank, counts, stats


def evaluate(
    *,
    name: str,
    pawn_sets,
    tb: chess.syzygy.Tablebase,
    cache,
    role_cache,
    role_map,
    tier: int,
    base_bank: set[tuple[object, ...]],
    alt_bank: set[tuple[object, ...]],
):
    counter = Counter()
    wrong_examples = []

    for pawns, wk, bk, turn, board in iter_boundary(pawn_sets):
        legal_count = board.legal_moves.count()
        counter["legal_states"] += 1
        if legal_count == 0:
            counter["terminal_states"] += 1
            continue

        counter["nonterminal_states"] += 1
        counter["baseline_children"] += legal_count

        base = preferred_candidates(
            board, pawns, wk, bk, turn, role_map, tier, base_bank
        )
        if base:
            # V14/V15/V16 already qualify these states. Keep their execution
            # exactly unchanged and do not let alternate candidates interfere.
            counter["preferred_states"] += 1
            counter["preferred_candidate_moves"] += len(base)
            counter["combined_states"] += 1
            counter["hybrid_children"] += 1
            counter["saved_children"] += legal_count - 1
            continue

        counter["preferred_residual"] += 1
        alt = admitted_alternates(
            board=board,
            pawns=pawns,
            wk=wk,
            bk=bk,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            tier=tier,
            alt_bank=alt_bank,
        )

        if not alt:
            counter["hybrid_children"] += legal_count
            continue

        counter["alternate_states"] += 1
        counter["alternate_candidate_moves"] += len(alt)
        root = exact_wdl(tb, board)
        wrong = 0
        safe = 0
        for move, _anchor, _role, _sigs in alt:
            ok = audit_move(tb, board, move, root)
            safe += int(ok)
            wrong += int(not ok)
            if not ok and len(wrong_examples) < 40:
                wrong_examples.append(
                    {
                        "fen": board.fen(),
                        "pawns": [chess.square_name(p) for p in pawns],
                        "turn": "white" if turn else "black",
                        "move": move.uci(),
                        "root_wdl": root,
                    }
                )
        counter["alternate_safe_moves"] += safe
        counter["alternate_wrong_moves"] += wrong
        counter["alternate_all_safe_states"] += int(wrong == 0)
        counter["combined_states"] += 1
        counter["hybrid_children"] += 1
        counter["saved_children"] += legal_count - 1

    n = int(counter["nonterminal_states"])
    baseline = int(counter["baseline_children"])
    hybrid = int(counter["hybrid_children"])
    preferred = int(counter["preferred_states"])
    alternate = int(counter["alternate_states"])
    wrong = int(counter["alternate_wrong_moves"])

    return {
        "name": name,
        **dict(counter),
        "preferred_coverage_ratio": preferred / n if n else 0.0,
        "alternate_incremental_ratio": alternate / n if n else 0.0,
        "combined_coverage_ratio": (
            int(counter["combined_states"]) / n if n else 0.0
        ),
        "alternate_candidate_precision": (
            int(counter["alternate_safe_moves"])
            / int(counter["alternate_candidate_moves"])
            if counter["alternate_candidate_moves"]
            else 1.0
        ),
        "zero_false_positive_alternate": wrong == 0,
        "child_reduction_ratio": (
            int(counter["saved_children"]) / baseline if baseline else 0.0
        ),
        "expansion_speedup": baseline / hybrid if hybrid else 1.0,
        "wrong_examples": wrong_examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    header, base_bank = load_guard(args.guard)
    tier = int(header["tier_index"])
    threshold = int(header["minimum_support"])

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]
    cache: dict[tuple[str, bool], int] = {}
    role_cache: dict[tuple[int, int, int, int], tuple[str, ...]] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, kpvk_enum, kpvk_nonterminal = acquire_policy(
            tb, feature_fns
        )
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        alt_bank, acquisition, _stats = acquire_alt_bank(
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            role_map=role_map,
            tier=tier,
            base_bank=base_bank,
            threshold=threshold,
        )

        source = evaluate(
            name="complete_K+3P_bcd_ranks2_4",
            pawn_sets=source_pawn_tuples(),
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            role_map=role_map,
            tier=tier,
            base_bank=base_bank,
            alt_bank=alt_bank,
        )
        if not source["zero_false_positive_alternate"]:
            raise AssertionError(
                "alternate-witness guard regresses its acquisition boundary"
            )

        target = evaluate(
            name="complete_K+4P_bcde_ranks2_4",
            pawn_sets=target_pawn_tuples(),
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            role_map=role_map,
            tier=tier,
            base_bank=base_bank,
            alt_bank=alt_bank,
        )

    status = (
        "WARRANTED_PROSPECTIVE_RESIDUAL_ALT_GUARD_TRANSFER"
        if int(target["alternate_states"]) > 0
        and bool(target["zero_false_positive_alternate"])
        else "EXACT_RESIDUAL_ALT_GUARD_TRANSFER"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "lineage": {
            "v14": V14_AUTHORITY,
            "v14_run": V14_RUN,
            "v15": V15_AUTHORITY,
            "v15_run": V15_RUN,
            "v16": V16_AUTHORITY,
            "v16_run": V16_RUN,
            "v17_diagnostic_run": V17_DIAGNOSTIC_RUN,
        },
        "frozen_preferred_guard": {
            "tier": str(header["tier"]),
            "tier_index": tier,
            "minimum_support": threshold,
            "safe_signatures": len(base_bank),
        },
        "residual_only_acquisition": {
            "source": "only V14-preferred K+3P abstentions",
            "counts": dict(acquisition),
            "alternate_safe_signatures": len(alt_bank),
            "contract": (
                "separate alternate-witness pair-interface bank; preferred "
                "V14 guard is never modified"
            ),
        },
        "source_reclosure": source,
        "prospective_target": target,
        "epistemic_boundary": {
            "warranted_if_green": [
                "preferred V14 execution is unchanged wherever it fires",
                "alternate guard is learned only from preferred-guard abstentions",
                "alternate guard has zero errors on complete source reclosure",
                "target K+4P labels do not alter the frozen alternate bank",
                "every admitted target alternate has zero exact Syzygy WDL error",
                "outside both guards full legal-child fallback is unchanged",
            ],
            "unknown": [
                "mixed-piece material transfer",
                "deep alpha-beta wall-clock gain",
                "general chess solution",
            ],
        },
        "cache": {
            "local_projection_role_sets": len(role_cache),
            "wdl_cache": len(cache),
        },
        "frozen_kpvk": {
            "nonterminal_states": kpvk_nonterminal,
            "role_frequency": frequency,
            "enumeration": kpvk_enum,
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

    print(f"CRYSTAL_CHESS_RESIDUAL_ALT_GUARD_V18={status}")
    print(
        f"source preferred={source['preferred_states']} "
        f"alternate={source['alternate_states']} "
        f"combined={source['combined_states']} "
        f"wrong={source['alternate_wrong_moves']} "
        f"prune={source['child_reduction_ratio']:.8f}"
    )
    print(
        f"target preferred={target['preferred_states']} "
        f"alternate={target['alternate_states']} "
        f"combined={target['combined_states']} "
        f"wrong={target['alternate_wrong_moves']} "
        f"prune={target['child_reduction_ratio']:.8f}"
    )
    print(
        f"alt_signatures={len(alt_bank)} "
        f"source_residual={acquisition['preferred_residual']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
