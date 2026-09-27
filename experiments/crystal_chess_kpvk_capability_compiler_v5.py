#!/usr/bin/env python3
"""Crystal Chess V5: compile a complete exact KPvK capability bank.

KPvK is now treated as a solved finite source world, not a generalization test.
The compiler may use complete Syzygy truth during qualification. The emitted
runtime capability bank contains only ordinary chess observables:

  * guarded collapse-all capabilities for regions where every legal move has
    the same protected WDL consequence;
  * guarded two-way move separators from the V3 vocabulary.

Every admitted guard is required to have zero unsafe support over the complete
legal KPvK source world. The frozen runtime policy is then exhaustively replayed
over that same complete world. WDL is never a runtime input.

This creates a verified reusable lower-material capability for subsequent
material-class growth; it is not a claim about general chess.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.syzygy

from experiments.crystal_chess_action_congruence_v1 import (
    ActionRecord,
    collect_actions,
)
from experiments.crystal_chess_guarded_pruning_v4 import (
    SELECTED_RULES,
    Clause,
    Rule,
    clause_holds,
    choose_representatives,
    enumerate_roots,
    mine_guard_clauses,
    rule_status,
)

SCHEMA = "mathgraph.crystal-chess.kpvk-capability-bank.v5"
BASE_AUTHORITY = (
    "metalogiclabs/mathgraph@200fb37f38b4fec072f49aead42306f39f8c0c9b"
)


def group_states(records: list[ActionRecord]) -> dict[int, list[ActionRecord]]:
    out: dict[int, list[ActionRecord]] = defaultdict(list)
    for record in records:
        out[record.state_id].append(record)
    return out


def mine_global_guards(
    states: dict[int, list[ActionRecord]],
    roots,
    root_names: list[str],
    action_index: dict[str, int],
    *,
    promising_limit: int,
    clauses_per_rule: int,
    collapse_clauses: int,
    min_safe: int,
) -> tuple[tuple[Clause, ...], dict[Rule, tuple[Clause, ...]], list[dict[str, object]]]:
    root_index = {name: i for i, name in enumerate(root_names)}
    all_sids = set(states)

    one_class = {
        sid for sid, actions in states.items()
        if len({a.consequence for a in actions}) == 1
    }
    multi_class = all_sids - one_class

    collapse_mined = mine_guard_clauses(
        all_sids,
        one_class,
        multi_class,
        roots,
        root_names,
        root_index,
        promising_limit=promising_limit,
        clause_limit=collapse_clauses,
        min_safe=min_safe,
    )
    collapse = tuple(clause for clause, _ in collapse_mined)

    compiled: dict[Rule, tuple[Clause, ...]] = {}
    diagnostics: list[dict[str, object]] = []
    for rule in SELECTED_RULES:
        applicable: set[int] = set()
        safe: set[int] = set()
        unsafe: set[int] = set()
        for sid, actions in states.items():
            app, ok = rule_status(actions, rule, action_index)
            if not app:
                continue
            applicable.add(sid)
            (safe if ok else unsafe).add(sid)

        mined = mine_guard_clauses(
            applicable,
            safe,
            unsafe,
            roots,
            root_names,
            root_index,
            promising_limit=promising_limit,
            clause_limit=clauses_per_rule,
            min_safe=min_safe,
        )
        clauses = tuple(clause for clause, _ in mined)
        if clauses:
            compiled[rule] = clauses
        diagnostics.append(
            {
                "rule": list(rule),
                "applicable_states": len(applicable),
                "safe_states": len(safe),
                "unsafe_states": len(unsafe),
                "admitted_guards": len(clauses),
                "guards": [
                    {
                        "clause": [list(lit) for lit in clause],
                        "complete_world_safe_support": len(cover),
                    }
                    for clause, cover in mined
                ],
            }
        )

    return collapse, compiled, diagnostics


def evaluate_complete_policy(
    states: dict[int, list[ActionRecord]],
    roots,
    root_names: list[str],
    collapse: tuple[Clause, ...],
    compiled: dict[Rule, tuple[Clause, ...]],
    action_index: dict[str, int],
) -> dict[str, object]:
    root_index = {name: i for i, name in enumerate(root_names)}

    raw_moves = 0
    kept_moves = 0
    oracle_classes = 0
    collapse_states = 0
    separator_states = 0
    abstain_states = 0
    unsafe_applications = 0
    minimax_mismatches = 0
    collapse_false_positives = 0
    rule_use: dict[str, int] = defaultdict(int)
    examples: list[dict[str, object]] = []

    for sid, actions in states.items():
        raw_moves += len(actions)
        actual_classes = len({a.consequence for a in actions})
        oracle_classes += actual_classes
        root_values = roots[sid].features

        if collapse and any(
            clause_holds(clause, root_values, root_index)
            for clause in collapse
        ):
            collapse_states += 1
            if actual_classes != 1:
                collapse_false_positives += 1
                unsafe_applications += 1
            reps = [min(actions, key=lambda a: a.move_uci)]
        else:
            selected: Rule | None = None
            for rule in SELECTED_RULES:
                clauses = compiled.get(rule, ())
                if not clauses:
                    continue
                applicable, safe = rule_status(actions, rule, action_index)
                if not applicable:
                    continue
                if any(
                    clause_holds(clause, root_values, root_index)
                    for clause in clauses
                ):
                    selected = rule
                    if not safe:
                        unsafe_applications += 1
                    break

            if selected is None:
                abstain_states += 1
                reps = actions
            else:
                separator_states += 1
                rule_use[str(selected)] += 1
                reps = choose_representatives(actions, selected, action_index)

        kept_moves += len(reps)
        root_wdl = actions[0].root_wdl
        pruned_value = max(a.consequence for a in reps)
        if pruned_value != root_wdl:
            minimax_mismatches += 1
            if len(examples) < 20:
                examples.append(
                    {
                        "state_id": sid,
                        "root_wdl": root_wdl,
                        "actual_classes": sorted({a.consequence for a in actions}),
                        "kept": [a.consequence for a in reps],
                    }
                )

    return {
        "states": len(states),
        "raw_moves": raw_moves,
        "kept_moves": kept_moves,
        "oracle_action_classes": oracle_classes,
        "policy_compression": raw_moves / kept_moves,
        "oracle_compression": raw_moves / oracle_classes,
        "overfragmentation_vs_oracle": kept_moves / oracle_classes,
        "collapse_states": collapse_states,
        "separator_states": separator_states,
        "abstain_states": abstain_states,
        "active_capability_ratio": (
            (collapse_states + separator_states) / len(states)
        ),
        "collapse_false_positives": collapse_false_positives,
        "unsafe_applications": unsafe_applications,
        "minimax_mismatches": minimax_mismatches,
        "rule_use": dict(rule_use),
        "error_examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--promising-limit", type=int, default=100)
    ap.add_argument("--clauses-per-rule", type=int, default=12)
    ap.add_argument("--collapse-clauses", type=int, default=24)
    ap.add_argument("--min-safe", type=int, default=30)
    args = ap.parse_args()
    started = time.time()

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, action_names, collection = collect_actions(tablebase)

    roots, root_names = enumerate_roots()
    states = group_states(records)
    action_index = {name: i for i, name in enumerate(action_names)}

    collapse, compiled, diagnostics = mine_global_guards(
        states,
        roots,
        root_names,
        action_index,
        promising_limit=args.promising_limit,
        clauses_per_rule=args.clauses_per_rule,
        collapse_clauses=args.collapse_clauses,
        min_safe=args.min_safe,
    )

    evaluation = evaluate_complete_policy(
        states,
        roots,
        root_names,
        collapse,
        compiled,
        action_index,
    )

    exact = (
        evaluation["collapse_false_positives"] == 0
        and evaluation["unsafe_applications"] == 0
        and evaluation["minimax_mismatches"] == 0
    )
    status = (
        "WARRANTED_EXACT_KPVK_CAPABILITY_BANK"
        if exact
        else "REJECTED_NONEXACT_KPVK_CAPABILITY_BANK"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_authority": BASE_AUTHORITY,
        "qualification_boundary": (
            "complete legal canonical KPvK world, pawn files a-d; horizontal "
            "reflection authority from V0 covers e-h"
        ),
        "runtime_uses_wdl": False,
        "root_guard_features": root_names,
        "collapse_all": {
            "guard_count": len(collapse),
            "guards": [[list(lit) for lit in clause] for clause in collapse],
        },
        "separator_capabilities": [
            {
                "rule": list(rule),
                "guards": [[list(lit) for lit in clause] for clause in clauses],
            }
            for rule, clauses in compiled.items()
        ],
        "compiled_rule_count": len(compiled),
        "compiled_separator_guard_count": sum(len(v) for v in compiled.values()),
        "diagnostics": diagnostics,
        "evaluation": evaluation,
        "collection": collection,
        "epistemic_boundary": {
            "warranted_if_green": (
                "the frozen observable-only capability bank preserves exact "
                "Syzygy WDL minimax over the complete qualified KPvK world"
            ),
            "not_claimed": [
                "minimal capability bank",
                "transfer to richer material without requalification",
                "general chess solution",
            ],
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_KPVK_CAPABILITY_V5={status}")
    print(
        f"collapse_guards={len(collapse)} "
        f"separator_rules={len(compiled)} "
        f"separator_guards={sum(len(v) for v in compiled.values())}"
    )
    print(
        f"states={evaluation['states']} "
        f"active={evaluation['collapse_states'] + evaluation['separator_states']} "
        f"raw={evaluation['raw_moves']} kept={evaluation['kept_moves']} "
        f"oracle={evaluation['oracle_action_classes']} "
        f"compression={evaluation['policy_compression']:.3f}x "
        f"oracle_compression={evaluation['oracle_compression']:.3f}x "
        f"over={evaluation['overfragmentation_vs_oracle']:.3f} "
        f"unsafe={evaluation['unsafe_applications']} "
        f"collapse_fp={evaluation['collapse_false_positives']} "
        f"mm={evaluation['minimax_mismatches']}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
