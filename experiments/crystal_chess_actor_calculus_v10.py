#!/usr/bin/env python3
"""Crystal Chess V10: actor-complete capability calculus on all KPvK roots.

V8 qualified the generic least/greatest fixed-point calculus and instantiated it
on White-to-move KPvK decision states.  V10 changes no calculus law.  It applies
the same frozen exact WDL+DTZ policy actor-relatively to BOTH side-to-move
worlds.

For an actor-to-move root:
  actor chooses its compiled exact move;
  if that move enters an already solved external material basin, Syzygy closes it;
  otherwise every legal opponent reply is an adversarial outcome;
  the resulting state returns to the same actor.

The calculus receives only terminal/external win/draw/loss basins.  Internal
Syzygy labels are used solely for post-hoc qualification.  Therefore the gate
is non-tautological: it must reconstruct the complete internal WDL partition as

  forced-goal  = exact actor wins,
  safety       = exact actor wins union exact actor draws,
  residual     = exact actor losses.

This covers all 165,676 canonical KPvK roots, both turns.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from mathgraph.capability_calculus import (
    CapabilityStep,
    compile_strategy_calculus,
    verify_strategy_calculus,
)
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
    tree_summary,
)
from crystal_chess_capability_calculus_v8 import (
    V6_AUTHORITY,
    probe_dtz_safe,
    dtz_optimal_roles,
    material_is_kpvk,
    white_state_key,
    exact_policy_move,
)


SCHEMA = "mathgraph.crystal-chess.actor-complete-capability-calculus.v10"
V8_AUTHORITY = (
    "metalogiclabs/mathgraph@c6f81c20ef165eab0939443f1a8944c522f68bf3"
)
SYZYGY_SUPPORT = "authority:syzygy-wdl-dtz"


def state_key(board: chess.Board) -> tuple[int, int, int, bool]:
    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    pawns = tuple(board.pieces(chess.PAWN, chess.WHITE))
    if wk is None or bk is None or len(pawns) != 1:
        raise ValueError("not KPvK")
    return wk, bk, pawns[0], bool(board.turn)


def actor_external_outcome(
    tablebase: chess.syzygy.Tablebase,
    board: chess.Board,
    actor: bool,
    wdl_cache: dict[tuple[str, bool], int],
    *,
    goal: str,
    draw: str,
    loss: str,
) -> str:
    wdl = probe_wdl(tablebase, board, wdl_cache)
    actor_value = wdl if board.turn == actor else -wdl
    if actor_value > 0:
        return goal
    if actor_value == 0:
        return draw
    return loss


def build_actor_world(
    *,
    actor: bool,
    records,
    X: np.ndarray,
    policy: DecisionTreeClassifier,
    root_dtz_by_index: dict[int, int],
    index_by_key: dict[tuple[int, int, int, bool], int],
    tablebase: chess.syzygy.Tablebase,
    wdl_cache: dict[tuple[str, bool], int],
    dtz_cache: dict[tuple[str, bool], int],
    role_frequency: dict[str, int],
) -> dict[str, object]:
    actor_name = "white" if actor == chess.WHITE else "black"
    turn_tag = "W" if actor == chess.WHITE else "B"
    goal = f"external:{actor_name}:verified-win"
    draw = f"external:{actor_name}:verified-draw"
    loss = f"external:{actor_name}:verified-loss"

    actor_indices = [i for i, rec in enumerate(records) if bool(rec.turn) == actor]
    sid_by_index = {
        i: f"kpvk:{records[i].wk}:{records[i].bk}:{records[i].pawn}:{turn_tag}"
        for i in actor_indices
    }

    expected_wins = {sid_by_index[i] for i in actor_indices if records[i].wdl == 2}
    expected_draws = {sid_by_index[i] for i in actor_indices if records[i].wdl == 0}
    expected_losses = {sid_by_index[i] for i in actor_indices if records[i].wdl == -2}
    unexpected = [
        records[i].wdl
        for i in actor_indices
        if records[i].wdl not in (-2, 0, 2)
    ]
    if unexpected:
        raise AssertionError(f"unexpected cursed/blessed actor roots: {Counter(unexpected)}")

    safe_terminals: set[str] = {draw}
    steps: list[CapabilityStep] = []
    role_use: Counter[str] = Counter()
    external_outcomes: Counter[str] = Counter()

    for i in actor_indices:
        rec = records[i]
        sid = sid_by_index[i]
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        legal = list(board.legal_moves)

        if not legal:
            if rec.wdl == 0:
                safe_terminals.add(sid)
            continue

        predicted_role = str(policy.predict(X[[i]])[0])
        move = exact_policy_move(
            board,
            predicted_role,
            rec.wdl,
            root_dtz_by_index[i],
            tablebase,
            wdl_cache,
            dtz_cache,
        )
        role_use[predicted_role] += 1

        after_actor = board.copy(stack=False)
        after_actor.push(move)
        outcomes: set[str] = set()

        # Completion-by-Reversal: once the selected move leaves KPvK, discharge
        # the state directly to the exact solved external basin.
        if not material_is_kpvk(after_actor):
            out = actor_external_outcome(
                tablebase,
                after_actor,
                actor,
                wdl_cache,
                goal=goal,
                draw=draw,
                loss=loss,
            )
            outcomes.add(out)
            external_outcomes[out] += 1
        else:
            replies = list(after_actor.legal_moves)
            if not replies:
                out = actor_external_outcome(
                    tablebase,
                    after_actor,
                    actor,
                    wdl_cache,
                    goal=goal,
                    draw=draw,
                    loss=loss,
                )
                outcomes.add(out)
                external_outcomes[out] += 1
            else:
                for reply in replies:
                    child = after_actor.copy(stack=False)
                    child.push(reply)
                    if bool(child.turn) != actor:
                        raise AssertionError("two-ply macro did not return actor turn")

                    if material_is_kpvk(child):
                        key = state_key(child)
                        target_i = index_by_key.get(key)
                        if target_i is None:
                            raise AssertionError(
                                f"complete KPvK child missing: {child.fen()}"
                            )
                        target = sid_by_index.get(target_i)
                        if target is None:
                            raise AssertionError(
                                "two-ply internal target belongs to wrong actor world"
                            )
                        outcomes.add(target)
                    else:
                        out = actor_external_outcome(
                            tablebase,
                            child,
                            actor,
                            wdl_cache,
                            goal=goal,
                            draw=draw,
                            loss=loss,
                        )
                        outcomes.add(out)
                        external_outcomes[out] += 1

        steps.append(
            CapabilityStep(
                source=sid,
                capability_id=f"dtz-role:{predicted_role}",
                outcomes=tuple(sorted(outcomes)),
                support_refs=frozenset(
                    {SYZYGY_SUPPORT, f"capability:dtz-role:{predicted_role}"}
                ),
                evidence_refs=(V6_AUTHORITY,),
            )
        )

    states = set(sid_by_index.values()) | {goal, draw, loss}
    live_supports = {SYZYGY_SUPPORT} | {
        f"capability:dtz-role:{role}" for role in role_frequency
    }

    calculus = compile_strategy_calculus(
        states=states,
        goals={goal},
        forbidden={loss},
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=live_supports,
    )
    verify_strategy_calculus(
        calculus,
        states=states,
        goals={goal},
        forbidden={loss},
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=live_supports,
    )

    forced_internal = set(calculus.forced_goal_states) - {goal, draw, loss}
    safe_internal = set(calculus.safety_states) - {goal, draw, loss}
    residual_internal = {
        residual.state
        for residual in calculus.residuals
        if residual.state.startswith("kpvk:")
    }
    expected_safe = expected_wins | expected_draws

    win_missing = expected_wins - forced_internal
    win_extra = forced_internal - expected_wins
    safe_missing = expected_safe - safe_internal
    safe_extra = safe_internal - expected_safe
    loss_missing_residual = expected_losses - residual_internal
    residual_extra = residual_internal - expected_losses

    if win_missing or win_extra:
        raise AssertionError(
            f"{actor_name} forced-goal mismatch "
            f"missing={len(win_missing)} extra={len(win_extra)}"
        )
    if safe_missing or safe_extra:
        raise AssertionError(
            f"{actor_name} safety mismatch "
            f"missing={len(safe_missing)} extra={len(safe_extra)}"
        )
    if loss_missing_residual or residual_extra:
        raise AssertionError(
            f"{actor_name} residual/loss mismatch "
            f"missing={len(loss_missing_residual)} extra={len(residual_extra)}"
        )

    ranks = calculus.rank_map
    forced_ranks = [ranks[s] for s in expected_wins]
    modes = Counter(decision.mode for decision in calculus.decisions)

    return {
        "actor": actor_name,
        "root_states": len(actor_indices),
        "capability_steps": len(steps),
        "distinct_roles_used": len(role_use),
        "role_use": dict(role_use),
        "expected": {
            "wins": len(expected_wins),
            "draws": len(expected_draws),
            "losses": len(expected_losses),
        },
        "calculus": {
            "result_id": calculus.id,
            "forced_goal_internal": len(forced_internal),
            "safety_internal": len(safe_internal),
            "residual_internal": len(residual_internal),
            "max_goal_rank": max(forced_ranks) if forced_ranks else 0,
            "decision_modes": dict(modes),
        },
        "mismatches": {
            "win_missing": len(win_missing),
            "win_extra": len(win_extra),
            "safe_missing": len(safe_missing),
            "safe_extra": len(safe_extra),
            "loss_missing_residual": len(loss_missing_residual),
            "residual_extra": len(residual_extra),
        },
        "external_outcomes": dict(external_outcomes),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtb*"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]
    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    wdl_cache: dict[tuple[str, bool], int] = {}
    dtz_cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tb:
        records, enumeration = enumerate_records(tb, wdl_cache, feature_fns)

        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        root_dtz_by_index: dict[int, int] = {}

        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            legal = list(board.legal_moves)
            if not legal:
                role_sets.append(())
                continue
            root_dtz = probe_dtz_safe(tb, board, dtz_cache)
            root_dtz_by_index[i] = root_dtz
            roles = dtz_optimal_roles(
                board,
                rec.wdl,
                root_dtz,
                tb,
                wdl_cache,
                dtz_cache,
            )
            role_sets.append(roles)
            nonterminal.append(i)

        labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
        X = np.asarray([rec.features for rec in records], dtype=np.int16)
        policy = DecisionTreeClassifier(
            criterion="entropy", splitter="best", random_state=0
        )
        policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
        policy_summary = tree_summary(policy)

        index_by_key = {
            (rec.wk, rec.bk, rec.pawn, bool(rec.turn)): i
            for i, rec in enumerate(records)
        }
        if len(index_by_key) != len(records):
            raise AssertionError("duplicate complete KPvK state key")

        white = build_actor_world(
            actor=chess.WHITE,
            records=records,
            X=X,
            policy=policy,
            root_dtz_by_index=root_dtz_by_index,
            index_by_key=index_by_key,
            tablebase=tb,
            wdl_cache=wdl_cache,
            dtz_cache=dtz_cache,
            role_frequency=role_frequency,
        )
        black = build_actor_world(
            actor=chess.BLACK,
            records=records,
            X=X,
            policy=policy,
            root_dtz_by_index=root_dtz_by_index,
            index_by_key=index_by_key,
            tablebase=tb,
            wdl_cache=wdl_cache,
            dtz_cache=dtz_cache,
            role_frequency=role_frequency,
        )

    total_roots = int(white["root_states"]) + int(black["root_states"])
    if total_roots != len(records):
        raise AssertionError(f"actor worlds do not cover all roots: {total_roots}")

    totals = {
        key: int(white["expected"][key]) + int(black["expected"][key])
        for key in ("wins", "draws", "losses")
    }
    observed = Counter(rec.wdl for rec in records)
    expected_distribution = {
        "wins": observed[2],
        "draws": observed[0],
        "losses": observed[-2],
    }
    if totals != expected_distribution:
        raise AssertionError(
            f"actor partition totals mismatch {totals} != {expected_distribution}"
        )

    evidence = {
        "schema": SCHEMA,
        "status": "WARRANTED_COMPLETE_ACTOR_RELATIVE_KPVK_CALCULUS",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v6_authority": V6_AUTHORITY,
        "v8_authority": V8_AUTHORITY,
        "protected_interfaces": [
            PROTECTED_INTERFACE,
            "chess.syzygy.wdl-dtz.v1",
            "mathgraph.capability-calculus.v1",
        ],
        "authority": {
            "kind": "Syzygy WDL + DTZ",
            "tablebase_files": manifest,
        },
        "compiled_policy": {
            "states": len(records),
            "nonterminal_states": len(nonterminal),
            "tree": policy_summary,
            "role_frequency": role_frequency,
        },
        "actor_worlds": {
            "white": white,
            "black": black,
        },
        "complete_partition": {
            "root_states": total_roots,
            "wins": totals["wins"],
            "draws": totals["draws"],
            "losses": totals["losses"],
            "all_mismatch_counts_zero": all(
                value == 0
                for actor_data in (white, black)
                for value in actor_data["mismatches"].values()
            ),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the unchanged generic calculus reconstructs the exact side-to-move win/draw/loss partition of every state in the complete declared canonical KPvK boundary",
                "internal Syzygy WDL labels are used only after calculus closure for qualification, not as internal goal/safety/forbidden seeds",
                "actor wins are exactly the least forced-goal region; actor non-losses are exactly the greatest safety region; actor losses are exactly the internal residual region",
                "every actor capability is checked against exact WDL+DTZ and every opponent reply is universally included unless an exact solved external basin is reached",
            ],
            "unknown": [
                "complete KPPvK calculus closure without direct tablebase enumeration",
                "finite capability-basis coverage of general chess",
                "game-theoretic value of the standard starting position",
            ],
        },
        "cache": {
            "wdl_positions": len(wdl_cache),
            "dtz_positions": len(dtz_cache),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "enumeration": enumeration,
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")

    print("CRYSTAL_CHESS_ACTOR_CALCULUS_V10=PASS")
    print(
        f"roots={total_roots} wins={totals['wins']} "
        f"draws={totals['draws']} losses={totals['losses']}"
    )
    print(
        f"white roots={white['root_states']} "
        f"W/D/L={white['expected']['wins']}/{white['expected']['draws']}/{white['expected']['losses']} "
        f"rank={white['calculus']['max_goal_rank']}"
    )
    print(
        f"black roots={black['root_states']} "
        f"W/D/L={black['expected']['wins']}/{black['expected']['draws']}/{black['expected']['losses']} "
        f"rank={black['calculus']['max_goal_rank']}"
    )
    print(
        f"all_mismatches_zero={evidence['complete_partition']['all_mismatch_counts_zero']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
