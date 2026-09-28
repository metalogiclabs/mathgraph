#!/usr/bin/env python3
"""Crystal Chess V29: second continuation separator from the V28 residual.

Freeze:
* V25 root sufficiency guard.
* V28 first continuation separator: reply_score1_probe2 < 455.

Source pool:
* original V22/V25 source positions;
* already-exposed V28 seed-20260930 positions (after removing source overlap).

Only positions admitted by both frozen layers are eligible. This pool contains
one exact wrong substitution: the V28 residual. It may earn exactly one more
predicate from the existing V28 continuation vocabulary.

The second predicate must retain zero wrong source states and have support in
both source generations. It is frozen before the fresh seed-20261001 target is
searched at 100k nodes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES, PROBE_TOTAL_NODES, STOCKFISH_PIN,
    UCIStockfish, collect_records, extract_positions,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256, base_probes, guard_fires, load_guard, read_epd,
)
from crystal_chess_search_continuation_v28 import (
    CHILD_PROBE_TOTAL_NODES, continuation_features, predicate_eval,
    position_key,
)


SCHEMA = "mathgraph.crystal-chess.search-continuation-margin.v29"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
SEP1 = {
    "feature_name": "reply_score1_probe2",
    "op": "lt",
    "value": 455,
}
FRESH_SEED = 20261001
MIN_V22_SUPPORT = 12
MIN_V28_SUPPORT = 5


def apply_sep1(names: list[str], feats: tuple[int, ...]) -> bool:
    j = names.index(SEP1["feature_name"])
    return predicate_eval({**SEP1, "feature": j}, int(feats[j]))


def candidate_specs(
    failure: dict[str, Any],
    rows: list[dict[str, Any]],
    names: list[str],
) -> list[dict[str, Any]]:
    ff = failure["features"]
    out = []
    for j, name in enumerate(names):
        fv = int(ff[j])
        vals = [int(r["features"][j]) for r in rows]
        out += [
            {"feature": j, "feature_name": name, "op": "lt", "value": fv},
            {"feature": j, "feature_name": name, "op": "gt", "value": fv},
        ]
        if len(set(vals)) <= 8:
            out.append(
                {"feature": j, "feature_name": name, "op": "ne", "value": fv}
            )
    return out


def choose_sep2(rows: list[dict[str, Any]], names: list[str]) -> dict[str, Any] | None:
    bad = [r for r in rows if not r["match"]]
    if len(bad) != 1:
        raise AssertionError(("expected one pooled residual", len(bad)))
    failure = bad[0]
    cands = []
    for spec in candidate_specs(failure, rows, names):
        j = int(spec["feature"])
        kept = [r for r in rows if predicate_eval(spec, int(r["features"][j]))]
        if not kept or any(not r["match"] for r in kept):
            continue
        bygen = {
            g: sum(r["generation"] == g for r in kept)
            for g in ("v22", "v28")
        }
        if bygen["v22"] < MIN_V22_SUPPORT or bygen["v28"] < MIN_V28_SUPPORT:
            continue
        cands.append({
            **spec,
            "support": len(kept),
            "v22_support": bygen["v22"],
            "v28_support": bygen["v28"],
            "retention_ratio": len(kept) / len(rows),
        })
    if not cands:
        return None
    op_rank = {"lt": 0, "gt": 0, "ne": 1}
    cands.sort(key=lambda c: (
        -c["support"], -c["v28_support"], -c["v22_support"],
        op_rank[c["op"]], c["feature_name"], c["value"]
    ))
    return cands[0]


def label_if_admitted(
    engine: UCIStockfish,
    guard: dict[str, Any],
    board: chess.Board,
    *,
    generation: str,
    authority: bool,
) -> tuple[dict[str, Any] | None, list[str] | None]:
    fen = board.fen()
    p1, p2 = base_probes(engine, fen)
    fires, _leaf = guard_fires(guard, board, p1, p2)
    if not fires:
        return None, None
    names, feats, meta = continuation_features(
        engine, board, str(p2["bestmove"])
    )
    if not apply_sep1(names, feats):
        return None, names
    row = {
        "fen": fen,
        "generation": generation,
        "features": feats,
        "candidate": str(p2["bestmove"]),
        "continuation": meta,
    }
    if authority:
        a = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        row["authority"] = str(a["bestmove"])
        row["match"] = row["candidate"] == row["authority"]
    return row, names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--v28-epd", type=Path, required=True)
    ap.add_argument("--fresh-epd", type=Path, required=True)
    ap.add_argument("--fresh-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("guard drift", sha))

    v22_splits = extract_positions(args.v22_pgn, 220)
    v22_boards = [b for split in v22_splits.values() for b in split]
    v22_keys = {position_key(b) for b in v22_boards}

    v28_boards = [
        b for b in read_epd(args.v28_epd)
        if position_key(b) not in v22_keys
    ]
    v28_keys = {position_key(b) for b in v28_boards}

    fresh_manifest = json.loads(args.fresh_manifest.read_text())
    if int(fresh_manifest["seed"]) != FRESH_SEED:
        raise AssertionError(("fresh seed drift", fresh_manifest["seed"]))
    fresh_all = read_epd(args.fresh_epd)
    source_keys = v22_keys | v28_keys
    overlap = {position_key(b) for b in fresh_all} & source_keys
    fresh = [b for b in fresh_all if position_key(b) not in source_keys]
    if len(fresh) < 200:
        raise AssertionError(("fresh too small", len(fresh)))

    engine = UCIStockfish(args.stockfish)
    try:
        rows = []
        names_ref = None

        # V22 source: reproduce full protected labels.
        for split in ("train", "validation", "holdout"):
            records, _ = collect_records(engine, v22_splits[split])
            for rec in records:
                board = chess.Board(rec["fen"])
                fires, _ = guard_fires(guard, board, rec["probe1"], rec["probe2"])
                if not fires:
                    continue
                names, feats, meta = continuation_features(
                    engine, board, str(rec["probe2"]["bestmove"])
                )
                if names_ref is None:
                    names_ref = names
                elif names != names_ref:
                    raise AssertionError("feature drift")
                if not apply_sep1(names, feats):
                    continue
                rows.append({
                    "fen": rec["fen"], "generation": "v22",
                    "features": feats, "candidate": rec["probe2"]["bestmove"],
                    "authority": rec["authority_bestmove"],
                    "match": bool(rec["match"]), "continuation": meta,
                })

        # V28 exposed target becomes source generation 2.
        for board in v28_boards:
            row, names = label_if_admitted(
                engine, guard, board, generation="v28", authority=True
            )
            if names is not None:
                if names_ref is None:
                    names_ref = names
                elif names != names_ref:
                    raise AssertionError("feature drift")
            if row is not None:
                rows.append(row)

        wrong = sum(not r["match"] for r in rows)
        if wrong != 1:
            raise AssertionError(("pooled residual drift", len(rows), wrong))
        sep2 = choose_sep2(rows, names_ref or [])
        if sep2 is None:
            status = "NO_SECOND_CONTINUATION_SEPARATOR"
            result = {
                "schema": SCHEMA, "status": status,
                "pooled_states": len(rows), "pooled_wrong": wrong,
            }
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
            print("CRYSTAL_CHESS_SEARCH_CONTINUATION_MARGIN_V29="+status)
            print(f"artifact={args.output}")
            return 0

        # Frozen here. Fresh authority starts only after both predicates commit.
        j2 = int(sep2["feature"])
        parent = sep1_ok = sep2_ok = accepted_wrong = 0
        examples = []
        for board in fresh:
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            parent += 1
            names, feats, meta = continuation_features(
                engine, board, str(p2["bestmove"])
            )
            if names != names_ref:
                raise AssertionError("fresh feature drift")
            if not apply_sep1(names, feats):
                continue
            sep1_ok += 1
            if not predicate_eval(sep2, int(feats[j2])):
                continue
            sep2_ok += 1

            auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
            ok = str(p2["bestmove"]) == str(auth["bestmove"])
            accepted_wrong += int(not ok)
            if len(examples) < 30:
                examples.append({
                    "fen": fen, "leaf": leaf,
                    "candidate": p2["bestmove"], "authority": auth["bestmove"],
                    "match": ok, "sep2_value": int(feats[j2]),
                    "continuation": meta,
                })
    finally:
        engine.quit()

    n = len(fresh)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * PROBE_TOTAL_NODES
        + parent * CHILD_PROBE_TOTAL_NODES
        + (n - sep2_ok) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline
    green = sep2_ok > 0 and accepted_wrong == 0 and reduction > 0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_TWO_STAGE_CONTINUATION_GUARD"
        if green else
        "FRESH_NORMAL_SEARCH_TWO_STAGE_CONTINUATION_RESIDUAL"
    )
    result = {
        "schema": SCHEMA, "status": status, "stockfish_pin": STOCKFISH_PIN,
        "source": {
            "pooled_states": len(rows), "pooled_wrong": wrong,
            "sep1": SEP1, "sep2": sep2,
        },
        "fresh": {
            "seed": FRESH_SEED, "positions": n,
            "source_overlap_removed": len(overlap),
            "parent_guard_fires": parent, "sep1_accepts": sep1_ok,
            "sep2_accepts": sep2_ok, "wrong": accepted_wrong,
            "coverage_ratio": sep2_ok / n,
            "baseline_nodes": baseline, "hybrid_nodes": hybrid,
            "estimated_node_reduction_ratio": reduction,
            "examples": examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V25 and V28 predicates are frozen",
                "one V28 false positive earns one second predicate only",
                "second predicate has support in both exposed source generations",
                "fresh seed is opened only after separator freeze",
                "all accepted fresh substitutions equal pinned 100k Stockfish",
                "net expected node work is reduced",
            ]
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("CRYSTAL_CHESS_SEARCH_CONTINUATION_MARGIN_V29="+status)
    print(f"source states={len(rows)} wrong={wrong} sep2={sep2}")
    print(
        f"fresh positions={n} parent={parent} sep1={sep1_ok} "
        f"accepted={sep2_ok} wrong={accepted_wrong} "
        f"coverage={sep2_ok/n:.8f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
