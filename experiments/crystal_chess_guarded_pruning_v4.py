#!/usr/bin/env python3
"""Crystal Chess V4: compile guarded, consequence-pure pruning capabilities.

A capability is:
    root-state applicability guard  +  move separator

Runtime inputs are ordinary chess observables only. Syzygy WDL is never used as
a feature or applicability signal; it is qualification authority only.

Lineage:
* V0: oracle action quotient is ~5x smaller than raw legal branching.
* V1: one global local-move schema is safe but only ~1.024x compression.
* V2: shallow continuation has nearly the right class count but wrong members;
      deeper monotone refinement repairs errors while destroying compression.
* V3: simple separators exist widely, but blind application is unsafe.
* V4: learn conservative root-state guards for those separators.

Guard synthesis:
* mine on pawn files a,b;
* use pawn file c only to reject guards with unsafe applicability;
* never alter guards after seeing pawn file d;
* qualify the compiled policy on the complete d-file KPvK cover.

No general-chess claim is made.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.syzygy

from experiments.crystal_chess_action_congruence_v1 import (
    ActionRecord,
    collect_actions,
)
from experiments.crystal_chess_guarded_separator_v3 import Rule, predicate
from experiments.crystal_chess_kpvk_v0 import (
    cheb,
    coordinate_feature_bank,
    make_kpvk,
)

SCHEMA = "mathgraph.crystal-chess.guarded-pruning.v4"
BASE_AUTHORITY = (
    "metalogiclabs/mathgraph@a2f31ec1a811373515d7d38d83e5993a6ff5ca51"
)

SELECTED_RULES: tuple[Rule, ...] = (
    ("child_terminal", "le", 1),
    ("to_pawn_rank_side", "eq", -1),
    ("mover_toward_promo", "eq", -1),
    ("mover_toward_promo", "eq", 1),
    ("to_pawn_cheb", "le", 1),
    ("mover_toward_pawn", "eq", 1),
    ("mover_edge_change", "eq", 1),
    ("promotion_type", "le", 3),
    ("after_pawn_rank", "eq", 3),
    ("after_opposition_gap", "eq", 0),
    ("to_pawn_file_distance", "le", 1),
    ("king_distance_change", "eq", -1),
)

Literal = tuple[str, str, int]
Clause = tuple[Literal, ...]


@dataclass(frozen=True)
class RootInfo:
    state_id: int
    pawn_file: int
    features: tuple[int, ...]


def root_feature_bank() -> list[tuple[str, object]]:
    base = coordinate_feature_bank()

    def pawn_edge(wk: int, bk: int, p: int, turn: bool) -> int:
        f = chess.square_file(p)
        return min(f, 7 - f)

    def opposition(wk: int, bk: int, p: int, turn: bool) -> int:
        aligned = (
            chess.square_file(wk) == chess.square_file(bk)
            or chess.square_rank(wk) == chess.square_rank(bk)
        )
        return int(aligned and cheb(wk, bk) == 2)

    def color_parity(square: int) -> int:
        return (chess.square_file(square) + chess.square_rank(square)) & 1

    extra = [
        ("pawn_edge_distance", pawn_edge),
        ("root_opposition_gap", opposition),
        ("wk_square_parity", lambda wk, bk, p, t: color_parity(wk)),
        ("bk_square_parity", lambda wk, bk, p, t: color_parity(bk)),
        ("pawn_square_parity", lambda wk, bk, p, t: color_parity(p)),
        (
            "kings_same_color",
            lambda wk, bk, p, t: int(color_parity(wk) == color_parity(bk)),
        ),
    ]

    # Raw absolute file coordinates are deliberately excluded from guard
    # synthesis. The final test is an unseen pawn file, so a successful guard
    # must be relational/role-like rather than a file lookup.
    excluded = {"pawn_file", "wk_file", "bk_file"}
    return [(n, f) for n, f in base if n not in excluded] + extra


def enumerate_roots() -> tuple[dict[int, RootInfo], list[str]]:
    bank = root_feature_bank()
    names = [n for n, _ in bank]
    fns = [f for _, f in bank]
    roots: dict[int, RootInfo] = {}
    state_id = 0
    for pawn_file in range(4):
        for pawn_rank in range(1, 7):
            pawn = chess.square(pawn_file, pawn_rank)
            for wk in chess.SQUARES:
                if wk == pawn:
                    continue
                for bk in chess.SQUARES:
                    if bk in (pawn, wk):
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        board = make_kpvk(wk, bk, pawn, turn)
                        if not board.is_valid():
                            continue
                        vals = tuple(int(fn(wk, bk, pawn, turn)) for fn in fns)
                        # Label-free root observables not present in the
                        # coordinate bank.
                        vals += (int(board.is_check()), board.legal_moves.count())
                        roots[state_id] = RootInfo(state_id, pawn_file, vals)
                        state_id += 1
    names += ["root_in_check", "root_legal_move_count"]
    return roots, names


def group_states(records: Iterable[ActionRecord]) -> dict[int, list[ActionRecord]]:
    out: dict[int, list[ActionRecord]] = defaultdict(list)
    for record in records:
        out[record.state_id].append(record)
    return out


def rule_status(
    actions: list[ActionRecord],
    rule: Rule,
    action_index: dict[str, int],
) -> tuple[bool, bool]:
    idx = action_index[rule[0]]
    bins: dict[bool, list[int]] = {False: [], True: []}
    for action in actions:
        bins[predicate(rule, action.features[idx])].append(action.consequence)
    applicable = bool(bins[False]) and bool(bins[True])
    if not applicable:
        return False, False
    safe = len(set(bins[False])) == 1 and len(set(bins[True])) == 1
    return True, safe


def literal_holds(lit: Literal, values: tuple[int, ...], root_index: dict[str, int]) -> bool:
    name, op, param = lit
    value = values[root_index[name]]
    if op == "eq":
        return value == param
    if op == "le":
        return value <= param
    if op == "ge":
        return value >= param
    raise ValueError(op)


def clause_holds(clause: Clause, values: tuple[int, ...], root_index: dict[str, int]) -> bool:
    return all(literal_holds(lit, values, root_index) for lit in clause)


def candidate_literals(
    sids: set[int],
    roots: dict[int, RootInfo],
    root_names: list[str],
    root_index: dict[str, int],
) -> list[tuple[Literal, set[int]]]:
    out: list[tuple[Literal, set[int]]] = []
    for name in root_names:
        idx = root_index[name]
        by_value: dict[int, set[int]] = defaultdict(set)
        for sid in sids:
            by_value[roots[sid].features[idx]].add(sid)
        values = sorted(by_value)
        for value in values:
            out.append(((name, "eq", int(value)), set(by_value[value])))
        running: set[int] = set()
        for value in values[:-1]:
            running |= by_value[value]
            out.append(((name, "le", int(value)), set(running)))
        running = set()
        for value in reversed(values[1:]):
            running |= by_value[value]
            out.append(((name, "ge", int(value)), set(running)))
    # Deduplicate semantically identical state subsets while retaining a stable
    # smallest textual literal.
    best: dict[frozenset[int], Literal] = {}
    for lit, matched in out:
        key = frozenset(matched)
        old = best.get(key)
        if old is None or lit < old:
            best[key] = lit
    return [(lit, set(key)) for key, lit in best.items()]


def mine_guard_clauses(
    applicable: set[int],
    safe: set[int],
    unsafe: set[int],
    roots: dict[int, RootInfo],
    root_names: list[str],
    root_index: dict[str, int],
    *,
    promising_limit: int,
    clause_limit: int,
    min_safe: int,
) -> list[tuple[Clause, set[int]]]:
    literals = candidate_literals(applicable, roots, root_names, root_index)
    scored = []
    pure: dict[Clause, set[int]] = {}

    for lit, matched in literals:
        safe_n = len(matched & safe)
        unsafe_n = len(matched & unsafe)
        if safe_n < min_safe:
            continue
        if unsafe_n == 0:
            pure[(lit,)] = matched & safe
        precision = safe_n / (safe_n + unsafe_n)
        # Prefer precision first because the eventual capability must be
        # conservative, then broad support.
        scored.append((-precision, -safe_n, unsafe_n, lit, matched))

    scored.sort()
    promising = scored[:promising_limit]

    # Pair conjunctions give state-relative scope without introducing an
    # open-ended grammar. Only promising literals participate.
    for i in range(len(promising)):
        lit_a, set_a = promising[i][3], promising[i][4]
        for j in range(i + 1, len(promising)):
            lit_b, set_b = promising[j][3], promising[j][4]
            if lit_a[0] == lit_b[0] and lit_a[1] == lit_b[1] and lit_a[2] != lit_b[2]:
                # Most same-feature duplicate constraints are either
                # contradictory or needlessly redundant.
                continue
            matched = set_a & set_b
            if not matched:
                continue
            safe_part = matched & safe
            if len(safe_part) < min_safe:
                continue
            if matched & unsafe:
                continue
            clause = tuple(sorted((lit_a, lit_b)))
            pure[clause] = safe_part

    # Greedy cover over train-safe applicable states. Every admitted clause is
    # zero-false-positive on train by construction.
    uncovered = set(safe)
    selected: list[tuple[Clause, set[int]]] = []
    candidates = list(pure.items())
    for _ in range(clause_limit):
        best_clause = None
        best_cover: set[int] = set()
        for clause, covered in candidates:
            gain = covered & uncovered
            if len(gain) > len(best_cover) or (
                len(gain) == len(best_cover)
                and gain
                and (best_clause is None or clause < best_clause)
            ):
                best_clause = clause
                best_cover = gain
        if best_clause is None or not best_cover:
            break
        selected.append((best_clause, pure[best_clause]))
        uncovered -= best_cover
        candidates = [(c, s) for c, s in candidates if c != best_clause]
    return selected


def validate_clause_on_split(
    clause: Clause,
    rule: Rule,
    states: dict[int, list[ActionRecord]],
    roots: dict[int, RootInfo],
    root_index: dict[str, int],
    action_index: dict[str, int],
) -> tuple[int, int, int]:
    matched_safe = 0
    matched_unsafe = 0
    matched_applicable = 0
    for sid, actions in states.items():
        applicable, safe = rule_status(actions, rule, action_index)
        if not applicable:
            continue
        if not clause_holds(clause, roots[sid].features, root_index):
            continue
        matched_applicable += 1
        if safe:
            matched_safe += 1
        else:
            matched_unsafe += 1
    return matched_applicable, matched_safe, matched_unsafe


def compile_guards(
    train_states: dict[int, list[ActionRecord]],
    dev_states: dict[int, list[ActionRecord]],
    roots: dict[int, RootInfo],
    root_names: list[str],
    action_index: dict[str, int],
    *,
    promising_limit: int,
    clauses_per_rule: int,
    min_safe: int,
    min_dev_safe: int,
) -> tuple[dict[Rule, tuple[Clause, ...]], list[dict[str, object]]]:
    root_index = {name: i for i, name in enumerate(root_names)}
    compiled: dict[Rule, tuple[Clause, ...]] = {}
    diagnostics: list[dict[str, object]] = []

    for rule in SELECTED_RULES:
        applicable: set[int] = set()
        safe: set[int] = set()
        unsafe: set[int] = set()
        for sid, actions in train_states.items():
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
            clause_limit=clauses_per_rule * 3,
            min_safe=min_safe,
        )

        kept: list[Clause] = []
        clause_rows = []
        for clause, train_cover in mined:
            app_n, safe_n, unsafe_n = validate_clause_on_split(
                clause,
                rule,
                dev_states,
                roots,
                root_index,
                action_index,
            )
            admit = unsafe_n == 0 and safe_n >= min_dev_safe
            clause_rows.append(
                {
                    "clause": [list(lit) for lit in clause],
                    "train_safe_support": len(train_cover),
                    "dev_applicable": app_n,
                    "dev_safe": safe_n,
                    "dev_unsafe": unsafe_n,
                    "admitted": admit,
                }
            )
            if admit:
                kept.append(clause)
            if len(kept) >= clauses_per_rule:
                break

        if kept:
            compiled[rule] = tuple(kept)
        diagnostics.append(
            {
                "rule": list(rule),
                "train_applicable": len(applicable),
                "train_safe": len(safe),
                "train_unsafe": len(unsafe),
                "mined_clauses": len(mined),
                "admitted_clauses": len(kept),
                "clauses": clause_rows,
            }
        )
    return compiled, diagnostics


def choose_representatives(
    actions: list[ActionRecord],
    rule: Rule,
    action_index: dict[str, int],
) -> list[ActionRecord]:
    idx = action_index[rule[0]]
    bins: dict[bool, list[ActionRecord]] = {False: [], True: []}
    for action in actions:
        bins[predicate(rule, action.features[idx])].append(action)
    if not bins[False] or not bins[True]:
        return actions
    return [
        min(bins[False], key=lambda a: a.move_uci),
        min(bins[True], key=lambda a: a.move_uci),
    ]


def evaluate_policy(
    states: dict[int, list[ActionRecord]],
    roots: dict[int, RootInfo],
    root_names: list[str],
    compiled: dict[Rule, tuple[Clause, ...]],
    action_index: dict[str, int],
) -> dict[str, object]:
    root_index = {name: i for i, name in enumerate(root_names)}
    raw = 0
    kept = 0
    oracle = 0
    applied_states = 0
    unsafe_applications = 0
    minimax_mismatches = 0
    one_class = 0
    two_class = 0
    three_plus = 0
    rule_use: Counter[str] = Counter()
    error_examples: list[dict[str, object]] = []

    for sid, actions in states.items():
        raw += len(actions)
        oracle_n = len({a.consequence for a in actions})
        oracle += oracle_n
        if oracle_n == 1:
            one_class += 1
        elif oracle_n == 2:
            two_class += 1
        else:
            three_plus += 1

        selected_rule: Rule | None = None
        for rule in SELECTED_RULES:
            clauses = compiled.get(rule, ())
            if not clauses:
                continue
            app, _ = rule_status(actions, rule, action_index)
            if not app:
                continue
            if any(
                clause_holds(clause, roots[sid].features, root_index)
                for clause in clauses
            ):
                selected_rule = rule
                break

        if selected_rule is None:
            reps = actions
        else:
            applied_states += 1
            _, safe = rule_status(actions, selected_rule, action_index)
            if not safe:
                unsafe_applications += 1
            reps = choose_representatives(actions, selected_rule, action_index)
            rule_use[str(selected_rule)] += 1

        kept += len(reps)
        pruned_value = max(a.consequence for a in reps)
        root_wdl = actions[0].root_wdl
        if pruned_value != root_wdl:
            minimax_mismatches += 1
            if len(error_examples) < 20:
                error_examples.append(
                    {
                        "state_id": sid,
                        "rule": list(selected_rule) if selected_rule else None,
                        "root_wdl": root_wdl,
                        "kept_consequences": [a.consequence for a in reps],
                        "all_consequences": sorted({a.consequence for a in actions}),
                    }
                )

    return {
        "states": len(states),
        "raw_moves": raw,
        "kept_moves": kept,
        "oracle_action_classes": oracle,
        "policy_compression": raw / kept if kept else 1.0,
        "oracle_compression": raw / oracle if oracle else 1.0,
        "overfragmentation_vs_oracle": kept / oracle if oracle else 1.0,
        "applied_states": applied_states,
        "application_ratio": applied_states / len(states) if states else 0.0,
        "unsafe_applications": unsafe_applications,
        "minimax_mismatches": minimax_mismatches,
        "oracle_class_histogram": {
            "one": one_class,
            "two": two_class,
            "three_plus": three_plus,
        },
        "rule_use": dict(rule_use),
        "error_examples": error_examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--promising-limit", type=int, default=60)
    ap.add_argument("--clauses-per-rule", type=int, default=6)
    ap.add_argument("--min-train-safe", type=int, default=40)
    ap.add_argument("--min-dev-safe", type=int, default=10)
    args = ap.parse_args()
    started = time.time()

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, action_names, collection = collect_actions(tablebase)

    roots, root_names = enumerate_roots()
    action_index = {name: i for i, name in enumerate(action_names)}
    all_states = group_states(records)
    train_states = {
        sid: actions for sid, actions in all_states.items()
        if roots[sid].pawn_file in (0, 1)
    }
    dev_states = {
        sid: actions for sid, actions in all_states.items()
        if roots[sid].pawn_file == 2
    }
    test_states = {
        sid: actions for sid, actions in all_states.items()
        if roots[sid].pawn_file == 3
    }

    compiled, diagnostics = compile_guards(
        train_states,
        dev_states,
        roots,
        root_names,
        action_index,
        promising_limit=args.promising_limit,
        clauses_per_rule=args.clauses_per_rule,
        min_safe=args.min_train_safe,
        min_dev_safe=args.min_dev_safe,
    )

    train_eval = evaluate_policy(
        train_states, roots, root_names, compiled, action_index
    )
    dev_eval = evaluate_policy(
        dev_states, roots, root_names, compiled, action_index
    )
    test_eval = evaluate_policy(
        test_states, roots, root_names, compiled, action_index
    )

    exact_test = (
        int(test_eval["unsafe_applications"]) == 0
        and int(test_eval["minimax_mismatches"]) == 0
    )
    useful_test = float(test_eval["policy_compression"]) >= 1.10
    if exact_test and useful_test:
        status = "WARRANTED_HELDOUT_GUARDED_ACTION_PRUNING"
    elif exact_test:
        status = "WARRANTED_SAFE_BUT_LOW_GAIN_GUARDED_PRUNING"
    else:
        status = "CANDIDATE_WITH_HELDOUT_GUARD_RESIDUAL"

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_authority": BASE_AUTHORITY,
        "split": {
            "guard_mining": "pawn files a,b",
            "guard_rejection_only": "pawn file c",
            "final_untouched_test": "complete pawn file d",
        },
        "selected_separator_rules": [list(rule) for rule in SELECTED_RULES],
        "root_guard_features": root_names,
        "guard_language": {
            "clause": "one or two root literals",
            "literals": ["feature == integer", "feature <= integer", "feature >= integer"],
            "raw_absolute_file_features_excluded": [
                "pawn_file", "wk_file", "bk_file"
            ],
        },
        "compile_parameters": {
            "promising_limit": args.promising_limit,
            "clauses_per_rule": args.clauses_per_rule,
            "min_train_safe": args.min_train_safe,
            "min_dev_safe": args.min_dev_safe,
        },
        "compiled_guard_count": sum(len(v) for v in compiled.values()),
        "compiled_rule_count": len(compiled),
        "compiled": [
            {
                "rule": list(rule),
                "clauses": [[list(lit) for lit in clause] for clause in clauses],
            }
            for rule, clauses in compiled.items()
        ],
        "diagnostics": diagnostics,
        "evaluation": {
            "train_ab": train_eval,
            "development_c": dev_eval,
            "test_d": test_eval,
        },
        "collection": collection,
        "epistemic_boundary": {
            "warranted_if_green": (
                "the frozen guard+separator policy compiled without d-file labels "
                "preserves exact Syzygy minimax on the complete d-file KPvK cover"
            ),
            "not_claimed": [
                "minimum guard language",
                "cross-material transfer",
                "unbounded future equivalence",
                "general chess solution",
            ],
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    print(f"CRYSTAL_CHESS_GUARDED_PRUNING_V4={status}")
    print(
        f"compiled_rules={len(compiled)} "
        f"compiled_guards={sum(len(v) for v in compiled.values())}"
    )
    for name, ev in (
        ("train", train_eval),
        ("dev", dev_eval),
        ("test", test_eval),
    ):
        print(
            f"{name}: states={ev['states']} applied={ev['applied_states']} "
            f"raw={ev['raw_moves']} kept={ev['kept_moves']} "
            f"oracle={ev['oracle_action_classes']} "
            f"compression={ev['policy_compression']:.3f}x "
            f"over={ev['overfragmentation_vs_oracle']:.3f} "
            f"unsafe={ev['unsafe_applications']} "
            f"mm={ev['minimax_mismatches']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
