#!/usr/bin/env python3
"""Crystal Chess V48: uninterrupted iterative-deepening trace on exact V47 residuals.

V47Q leaves 45 source mismatches for last2_move_pv3 and V47's stronger
last3_move_pv3 leaves exactly 11 source mismatches.  Those 11 are the smallest
current late-overturn residual.

V48 does not learn a stopping rule.  It replays only those 11 positions through
one uninterrupted clean Stockfish search to 100k nodes and records the full
completed-depth root trace.

Questions:
* how long can a wrong root move/PV remain stable before the final overturn?
* when does the final authority move first appear and remain to the end?
* would simple "last N completed depths + PV-k stable" rules still fire early?

No new chess feature, threshold, classifier, or authority is introduced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from crystal_chess_search_sufficiency_v25 import STOCKFISH_PIN, UCIStockfish

SCHEMA = "mathgraph.crystal-chess.continuous-trace.v48"
V47_RUN = 36523379587
AUTHORITY_NODES = 100000

RULE_DEPTHS = (2, 3, 4, 5)
RULE_PV = (3, 5, 8)


def exact_residuals(v47: dict[str, Any]) -> list[dict[str, Any]]:
    if v47.get("schema") != "mathgraph.crystal-chess.progressive-stopping.v47":
        raise AssertionError(("V47 schema drift", v47.get("schema")))
    rows = list(
        v47["source"]["rules"]["last3_move_pv3"].get("mismatch_examples", [])
    )
    if len(rows) != 11:
        raise AssertionError(("expected exact V47 residual of 11", len(rows)))
    return rows


def continuous_trace(
    engine: UCIStockfish,
    fen: str,
) -> dict[str, Any]:
    engine.clear_hash()
    engine.send("setoption name MultiPV value 1")
    engine.send("position fen " + fen)
    engine.send(f"go nodes {AUTHORITY_NODES}")
    lines = engine.read_until("bestmove")
    bestmove = lines[-1].split()[1]

    latest_by_depth: dict[int, dict[str, Any]] = {}
    for line in lines[:-1]:
        if not line.startswith("info "):
            continue
        tokens = line.split()
        if "depth" not in tokens or "pv" not in tokens or "score" not in tokens:
            continue
        try:
            depth = int(tokens[tokens.index("depth") + 1])
            pvi = tokens.index("pv")
            pv = tokens[pvi + 1 :]
        except Exception:
            continue
        if not pv:
            continue

        latest_by_depth[depth] = {
            "depth": depth,
            "seldepth": engine._int_after(tokens, "seldepth"),
            "nodes": engine._int_after(tokens, "nodes"),
            "score": engine._score_value(tokens),
            "bestmove": str(pv[0]),
            "pv": list(pv[:12]),
            "lowerbound": "lowerbound" in tokens,
            "upperbound": "upperbound" in tokens,
        }

    trace = [latest_by_depth[d] for d in sorted(latest_by_depth)]
    return {
        "bestmove": bestmove,
        "trace": trace,
    }


def prefix(row: dict[str, Any], k: int) -> tuple[str, ...] | None:
    pv = list(row.get("pv") or [])
    if len(pv) < k:
        return None
    return tuple(str(x) for x in pv[:k])


def rule_fires_at(
    trace: list[dict[str, Any]],
    ndepth: int,
    pvk: int,
) -> dict[str, Any] | None:
    for i in range(ndepth - 1, len(trace)):
        rows = trace[i - ndepth + 1 : i + 1]
        if len({str(r["bestmove"]) for r in rows}) != 1:
            continue
        pfx = [prefix(r, pvk) for r in rows]
        if any(x is None for x in pfx):
            continue
        if len(set(pfx)) != 1:
            continue
        return {
            "depth": int(trace[i]["depth"]),
            "nodes": int(trace[i]["nodes"]),
            "bestmove": str(trace[i]["bestmove"]),
            "pv_prefix": list(pfx[0] or ()),
        }
    return None


def authority_lock(trace: list[dict[str, Any]], authority: str) -> dict[str, Any] | None:
    for i, row in enumerate(trace):
        if str(row["bestmove"]) != authority:
            continue
        if all(str(x["bestmove"]) == authority for x in trace[i:]):
            return {
                "depth": int(row["depth"]),
                "nodes": int(row["nodes"]),
                "score": int(row["score"]),
            }
    return None


def longest_wrong_plateau(trace: list[dict[str, Any]], authority: str) -> dict[str, Any]:
    best = {"length_depths": 0, "move": None, "start_depth": None, "end_depth": None}
    i = 0
    while i < len(trace):
        move = str(trace[i]["bestmove"])
        j = i + 1
        while j < len(trace) and str(trace[j]["bestmove"]) == move:
            j += 1
        if move != authority and j - i > int(best["length_depths"]):
            best = {
                "length_depths": j - i,
                "move": move,
                "start_depth": int(trace[i]["depth"]),
                "end_depth": int(trace[j - 1]["depth"]),
                "start_nodes": int(trace[i]["nodes"]),
                "end_nodes": int(trace[j - 1]["nodes"]),
            }
        i = j
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v47-result", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v47 = json.loads(args.v47_result.read_text())
    residuals = exact_residuals(v47)

    engine = UCIStockfish(args.stockfish)
    rows: list[dict[str, Any]] = []
    try:
        for src in residuals:
            authority = str(src["authority_bestmove"])
            out = continuous_trace(engine, str(src["fen"]))
            trace = list(out["trace"])
            if str(out["bestmove"]) != authority:
                raise AssertionError(
                    ("continuous authority drift", src["fen"], authority, out["bestmove"])
                )

            rules: dict[str, Any] = {}
            for ndepth in RULE_DEPTHS:
                for pvk in RULE_PV:
                    name = f"last{ndepth}_depth_pv{pvk}"
                    fire = rule_fires_at(trace, ndepth, pvk)
                    if fire is None:
                        rules[name] = None
                    else:
                        rules[name] = {
                            **fire,
                            "matches_authority": str(fire["bestmove"]) == authority,
                            "node_fraction": (
                                int(fire["nodes"]) / AUTHORITY_NODES
                                if AUTHORITY_NODES else 1.0
                            ),
                        }

            rows.append({
                "generation": src["generation"],
                "fen": src["fen"],
                "independent_stop_nodes": int(src["stop_nodes"]),
                "independent_wrong_move": str(src["stop_bestmove"]),
                "authority": authority,
                "continuous_trace": trace,
                "authority_lock": authority_lock(trace, authority),
                "longest_wrong_plateau": longest_wrong_plateau(trace, authority),
                "rules": rules,
            })
    finally:
        engine.quit()

    summary: dict[str, Any] = {}
    for ndepth in RULE_DEPTHS:
        for pvk in RULE_PV:
            name = f"last{ndepth}_depth_pv{pvk}"
            fired = [
                r["rules"][name] for r in rows if r["rules"][name] is not None
            ]
            wrong = sum(not bool(x["matches_authority"]) for x in fired)
            summary[name] = {
                "fired": len(fired),
                "wrong": wrong,
                "correct": len(fired) - wrong,
                "mean_node_fraction": (
                    sum(float(x["node_fraction"]) for x in fired) / len(fired)
                    if fired else 1.0
                ),
            }

    max_wrong_plateau = max(
        int(r["longest_wrong_plateau"]["length_depths"]) for r in rows
    )
    lock_nodes = [
        int(r["authority_lock"]["nodes"])
        for r in rows
        if r["authority_lock"] is not None
    ]

    result = {
        "schema": SCHEMA,
        "status": "CONTINUOUS_TRACE_DIAGNOSTIC_COMPLETE",
        "stockfish_pin": STOCKFISH_PIN,
        "v47_run": V47_RUN,
        "authority_nodes": AUTHORITY_NODES,
        "residual_count": len(rows),
        "max_wrong_plateau_completed_depths": max_wrong_plateau,
        "authority_lock_node_distribution": lock_nodes,
        "rule_summary": summary,
        "rows": rows,
        "epistemic_boundary": {
            "warranted": [
                "only the exact 11 V47 last3_move_pv3 source mismatches are replayed",
                "each position is searched once continuously to the frozen 100k authority budget",
                "all stopping-rule diagnostics are computed after the continuous trace is frozen",
            ],
            "unknown": [
                "a globally safe continuous-search stopping certificate",
                "production wall-clock or node savings",
                "self-play Elo gain",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print("CRYSTAL_CHESS_CONTINUOUS_TRACE_V48=CONTINUOUS_TRACE_DIAGNOSTIC_COMPLETE")
    print(
        f"residual={len(rows)} max_wrong_plateau_depths={max_wrong_plateau} "
        f"authority_lock_nodes={lock_nodes}"
    )
    for name, st in summary.items():
        print(
            f"{name}: fired={st['fired']} wrong={st['wrong']} "
            f"mean_node_fraction={st['mean_node_fraction']:.8f}"
        )
    for r in rows:
        p = r["longest_wrong_plateau"]
        lock = r["authority_lock"]
        print(
            f"authority={r['authority']} wrong_plateau={p['move']} "
            f"depths={p['length_depths']} {p['start_depth']}->{p['end_depth']} "
            f"nodes={p.get('start_nodes')}->{p.get('end_nodes')} "
            f"lock={None if lock is None else lock['nodes']} fen={r['fen']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
