#!/usr/bin/env python3
"""Crystal Chess V44: forced-move consequence audit of the exact V43 residual.

V43 leaves exactly four V42 source positions whose frozen 100k single-PV
authority move is absent even from a clean 100k MultiPV16 list.

V44 does not learn a guard or threshold. For each of those four positions:
* freeze the V42 authority move;
* freeze the V43 100k MultiPV16 rival set;
* force every move in {authority} U rivals;
* independently evaluate the child at 100k and 400k nodes;
* back the score up to the root player;
* also record whether clean root single-PV bestmove changes from 100k to 400k.

This separates two possibilities:
1. search-mode omission: the authority is still consequence-maximal when forced;
2. witness instability: another frozen rival is at least as good under deeper
   forced consequence, so exact bestmove identity is not the right semantic target.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    STOCKFISH_PIN,
    UCIStockfish,
)

SCHEMA = "mathgraph.crystal-chess.forced-consequence-audit.v44"
V43_RUN = 36520938383
BUDGETS = (100000, 400000)


def residuals(v43: dict[str, Any]) -> list[dict[str, Any]]:
    if v43.get("schema") != "mathgraph.crystal-chess.residual-budget-ladder.v43":
        raise AssertionError(("V43 schema drift", v43.get("schema")))
    rows = [
        r for r in v43.get("rows", [])
        if r.get("first_recovered_budget") is None
    ]
    if len(rows) != 4:
        raise AssertionError(("expected four exact V43 residuals", len(rows)))
    return rows


def force_eval(
    engine: UCIStockfish,
    board: chess.Board,
    move_uci: str,
    nodes: int,
) -> dict[str, Any]:
    move = chess.Move.from_uci(move_uci)
    if move not in board.legal_moves:
        raise AssertionError(("illegal frozen move", board.fen(), move_uci))
    child = board.copy(stack=False)
    child.push(move)
    out = engine.search(
        child.fen(),
        nodes,
        multipv=1,
        clear=True,
    )
    child_score = int(out["score1"])
    return {
        "move": move_uci,
        "nodes": nodes,
        "root_backed_score": -child_score,
        "child_score": child_score,
        "child_bestmove": str(out["bestmove"]),
        "depth": int(out["depth"]),
        "seldepth": int(out["seldepth"]),
        "pv1": list(out["pv1"][:10]),
    }


def max_moves(rows: list[dict[str, Any]]) -> tuple[int, list[str]]:
    best = max(int(r["root_backed_score"]) for r in rows)
    moves = [
        str(r["move"])
        for r in rows
        if int(r["root_backed_score"]) == best
    ]
    return best, sorted(moves)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v43-result", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v43 = json.loads(args.v43_result.read_text())
    src = residuals(v43)

    engine = UCIStockfish(args.stockfish)
    out_rows: list[dict[str, Any]] = []
    try:
        for row in src:
            board = chess.Board(str(row["fen"]))
            authority = str(row["authority"])

            # Freeze the final clean 100k MultiPV16 rivals from V43.
            step100 = next(
                s for s in row["ladder"] if int(s["nodes"]) == 100000
            )
            rivals = [
                str(x["move"]) for x in step100["top16"]
            ]
            moves: list[str] = []
            seen: set[str] = set()
            for move in [authority] + rivals:
                if move not in seen:
                    seen.add(move)
                    moves.append(move)

            root_search = {}
            forced = {}
            for budget in BUDGETS:
                root = engine.search(
                    board.fen(),
                    budget,
                    multipv=1,
                    clear=True,
                )
                root_search[str(budget)] = {
                    "bestmove": str(root["bestmove"]),
                    "score1": int(root["score1"]),
                    "depth": int(root["depth"]),
                    "seldepth": int(root["seldepth"]),
                    "pv1": list(root["pv1"][:10]),
                }
                evals = [
                    force_eval(engine, board, move, budget)
                    for move in moves
                ]
                best_score, best_moves = max_moves(evals)
                authority_row = next(
                    e for e in evals if str(e["move"]) == authority
                )
                forced[str(budget)] = {
                    "evaluations": evals,
                    "max_backed_score": best_score,
                    "max_moves": best_moves,
                    "authority_backed_score": int(
                        authority_row["root_backed_score"]
                    ),
                    "authority_is_max": authority in best_moves,
                    "authority_gap_to_max": (
                        int(authority_row["root_backed_score"]) - best_score
                    ),
                }

            authority_is_max_both = all(
                bool(forced[str(b)]["authority_is_max"])
                for b in BUDGETS
            )
            root_witness_changes = (
                root_search["100000"]["bestmove"]
                != root_search["400000"]["bestmove"]
            )

            out_rows.append({
                "generation": row.get("generation"),
                "fen": row["fen"],
                "authority": authority,
                "frozen_rivals_100k_multipv16": rivals,
                "move_count_audited": len(moves),
                "root_search": root_search,
                "forced": forced,
                "authority_is_forced_max_both_budgets": authority_is_max_both,
                "root_witness_changes_100k_to_400k": root_witness_changes,
            })
    finally:
        engine.quit()

    max_both = sum(
        bool(r["authority_is_forced_max_both_budgets"])
        for r in out_rows
    )
    witness_changes = sum(
        bool(r["root_witness_changes_100k_to_400k"])
        for r in out_rows
    )

    if max_both == len(out_rows):
        status = "V43_RESIDUAL_IS_MULTIPV_SEARCH_MODE_OMISSION"
    elif max_both == 0:
        status = "V43_RESIDUAL_IS_WITNESS_IDENTITY_INSTABILITY"
    else:
        status = "V43_RESIDUAL_MIXES_SEARCH_MODE_AND_WITNESS_INSTABILITY"

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v43_run": V43_RUN,
        "budgets": list(BUDGETS),
        "residual_count": len(out_rows),
        "authority_forced_max_both_budgets": max_both,
        "root_witness_change_count": witness_changes,
        "rows": out_rows,
        "epistemic_boundary": {
            "warranted": [
                "only the four exact V43 unrecovered source residuals are audited",
                "authority and rival move identities are frozen before V44 searches",
                "each move is forced and evaluated by an independent clean child search",
                "no score tolerance or fitted threshold is introduced",
            ],
            "unknown": [
                "chess-theoretic move equivalence",
                "a cheap runtime detector for search-mode omissions",
                "fresh transfer of any set-valued consequence rule",
                "self-play Elo gain",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_FORCED_CONSEQUENCE_AUDIT_V44={status}")
    for r in out_rows:
        f100 = r["forced"]["100000"]
        f400 = r["forced"]["400000"]
        print(
            f"authority={r['authority']} "
            f"max100={f100['authority_is_max']} "
            f"gap100={f100['authority_gap_to_max']} "
            f"max400={f400['authority_is_max']} "
            f"gap400={f400['authority_gap_to_max']} "
            f"root_change={r['root_witness_changes_100k_to_400k']} "
            f"fen={r['fen']}"
        )
    print(
        f"summary authority_max_both={max_both}/{len(out_rows)} "
        f"root_witness_changes={witness_changes}/{len(out_rows)}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
