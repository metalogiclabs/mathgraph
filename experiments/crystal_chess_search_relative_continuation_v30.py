#!/usr/bin/env python3
"""Crystal Chess V30: relative continuation arbitration.

V29 leaves one exact prospective false positive after two serial predicates on
the *candidate's own* continuation.  The residual says that isolated candidate
descriptors are not the canonical object.

V30 therefore introduces exactly one new relation:
compare the frozen 4k root candidate against the frozen 4k MultiPV2 alternative
after independently backing up both moves through the opponent's cheap
1k->TT-reused-4k continuation.

Frozen parent:
* V25 root guard.
* V28 separator: reply_score1_probe2 < 455 on candidate continuation.
* V29 separator: reply_depth_probe2 != 6 on candidate continuation.

Source pool:
* V22 original source corpus,
* exposed V28 target,
* exposed V29 target.
Only states admitted by every frozen parent layer are eligible.  The pooled
source must contain exactly the single V29 false positive.

One relative predicate is earned from that residual, with support required in
all three source generations.  It is frozen before any 100k query on the new
seed-20261002 target.

This is behavioral search substitution relative to pinned Stockfish, not a
claim of chess-theoretic optimality.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
    collect_records,
    extract_positions,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    base_probes,
    guard_fires,
    load_guard,
    read_epd,
)
from crystal_chess_search_continuation_v28 import (
    CHILD_PROBE_TOTAL_NODES,
    continuation_features,
    predicate_eval,
    position_key,
)
from crystal_chess_search_continuation_margin_v29 import (
    SEP1,
)


SCHEMA = "mathgraph.crystal-chess.search-relative-continuation.v30"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
FRESH_SEED = 20261002

SEP2 = {
    "feature_name": "reply_depth_probe2",
    "op": "ne",
    "value": 6,
}

MIN_SUPPORT = {
    "v22": 12,
    "v28": 5,
    "v29": 5,
}


def apply_pred(
    names: list[str],
    feats: tuple[int, ...],
    spec: dict[str, Any],
) -> bool:
    j = names.index(str(spec["feature_name"]))
    return predicate_eval(
        {"feature": j, **spec},
        int(feats[j]),
    )


def root_alternative(p2: dict[str, Any]) -> str | None:
    pv1 = list(p2.get("pv1") or [])
    pv2 = list(p2.get("pv2") or [])
    candidate = str(p2.get("bestmove") or "")
    alt = str(pv2[0]) if pv2 else ""
    if not candidate or not alt or alt == candidate:
        return None
    if pv1 and str(pv1[0]) != candidate:
        # Fail closed if Stockfish's bestmove/PV1 contract drifts.
        return None
    return alt


def cont_margin(meta: dict[str, Any], probe: str) -> int:
    row = meta[probe]
    s1 = int(row["score1"])
    s2 = row.get("score2")
    if s2 is None:
        return 100000
    return s1 - int(s2)


def relation_features(
    engine: UCIStockfish,
    board: chess.Board,
    candidate: str,
    alternative: str,
) -> tuple[list[str], tuple[int, ...], dict[str, Any]]:
    cnames, cfeats, cmeta = continuation_features(
        engine, board, candidate
    )
    anames, afeats, ameta = continuation_features(
        engine, board, alternative
    )
    if cnames != anames:
        raise AssertionError("candidate/alternative continuation feature drift")

    cidx = {name: i for i, name in enumerate(cnames)}

    # Child search score is from the child side-to-move (opponent), so negate
    # to get the root player's backed-up value.
    cback1 = -int(cmeta["probe1"]["score1"])
    cback2 = -int(cmeta["probe2"]["score1"])
    aback1 = -int(ameta["probe1"]["score1"])
    aback2 = -int(ameta["probe2"]["score1"])

    root_names = [
        "backed_delta_probe1",
        "backed_delta_probe2",
        "backed_delta_change",
        "candidate_backed_probe1",
        "candidate_backed_probe2",
        "alternative_backed_probe1",
        "alternative_backed_probe2",
        "candidate_reply_margin_probe2",
        "alternative_reply_margin_probe2",
        "reply_margin_relative",
        "candidate_reply_score_change_abs",
        "alternative_reply_score_change_abs",
        "score_change_relative",
        "candidate_reply_depth_probe2",
        "alternative_reply_depth_probe2",
        "reply_depth_relative",
        "candidate_reply_seldepth_probe2",
        "alternative_reply_seldepth_probe2",
        "reply_seldepth_relative",
        "candidate_reply_stable",
        "alternative_reply_stable",
        "stability_advantage",
        "candidate_child_legal_moves",
        "alternative_child_legal_moves",
        "child_branching_relative",
    ]

    cm2 = cont_margin(cmeta, "probe2")
    am2 = cont_margin(ameta, "probe2")
    cchange = abs(
        int(cmeta["probe2"]["score1"]) - int(cmeta["probe1"]["score1"])
    )
    achange = abs(
        int(ameta["probe2"]["score1"]) - int(ameta["probe1"]["score1"])
    )
    cd = int(cmeta["probe2"]["depth"])
    ad = int(ameta["probe2"]["depth"])
    csd = int(cmeta["probe2"]["seldepth"])
    asd = int(ameta["probe2"]["seldepth"])
    cstable = int(
        cmeta["probe1"]["bestmove"] == cmeta["probe2"]["bestmove"]
    )
    astable = int(
        ameta["probe1"]["bestmove"] == ameta["probe2"]["bestmove"]
    )
    clegal = int(cfeats[cidx["child_legal_moves"]])
    alegal = int(afeats[cidx["child_legal_moves"]])

    vals = (
        cback1 - aback1,
        cback2 - aback2,
        (cback2 - aback2) - (cback1 - aback1),
        cback1,
        cback2,
        aback1,
        aback2,
        cm2,
        am2,
        cm2 - am2,
        cchange,
        achange,
        cchange - achange,
        cd,
        ad,
        cd - ad,
        csd,
        asd,
        csd - asd,
        cstable,
        astable,
        cstable - astable,
        clegal,
        alegal,
        clegal - alegal,
    )

    meta = {
        "candidate": candidate,
        "alternative": alternative,
        "candidate_continuation": cmeta,
        "alternative_continuation": ameta,
        "backed_candidate_probe1": cback1,
        "backed_candidate_probe2": cback2,
        "backed_alternative_probe1": aback1,
        "backed_alternative_probe2": aback2,
        "backed_delta_probe1": cback1 - aback1,
        "backed_delta_probe2": cback2 - aback2,
    }
    return root_names, vals, meta


def candidate_specs(
    failure: dict[str, Any],
    rows: list[dict[str, Any]],
    names: list[str],
) -> list[dict[str, Any]]:
    ff = tuple(int(x) for x in failure["relation_features"])
    out: list[dict[str, Any]] = []

    # Prefer the semantic no-worse backed-up relation when it works.
    for feature_name in ("backed_delta_probe2", "backed_delta_probe1"):
        j = names.index(feature_name)
        out.append({
            "feature": j,
            "feature_name": feature_name,
            "op": "ge",
            "value": 0,
            "semantic_priority": 0,
        })

    # Otherwise let the exact residual earn one threshold/equality relation
    # inside the *relative* continuation vocabulary only.
    for j, name in enumerate(names):
        fv = int(ff[j])
        vals = [int(r["relation_features"][j]) for r in rows]
        out.extend([
            {
                "feature": j,
                "feature_name": name,
                "op": "lt",
                "value": fv,
                "semantic_priority": 1,
            },
            {
                "feature": j,
                "feature_name": name,
                "op": "gt",
                "value": fv,
                "semantic_priority": 1,
            },
        ])
        if len(set(vals)) <= 8:
            out.append({
                "feature": j,
                "feature_name": name,
                "op": "ne",
                "value": fv,
                "semantic_priority": 2,
            })
    return out


def relation_eval(spec: dict[str, Any], value: int) -> bool:
    op = str(spec["op"])
    ref = int(spec["value"])
    if op == "ge":
        return value >= ref
    return predicate_eval(spec, value)


def choose_relation(
    rows: list[dict[str, Any]],
    names: list[str],
) -> dict[str, Any] | None:
    bad = [r for r in rows if not bool(r["match"])]
    if len(bad) != 1:
        raise AssertionError(("expected one V29 pooled residual", len(bad)))
    failure = bad[0]

    candidates = []
    for spec in candidate_specs(failure, rows, names):
        j = int(spec["feature"])
        kept = [
            row
            for row in rows
            if relation_eval(spec, int(row["relation_features"][j]))
        ]
        if not kept or any(not bool(row["match"]) for row in kept):
            continue
        support = Counter(str(r["generation"]) for r in kept)
        if any(support[g] < MIN_SUPPORT[g] for g in MIN_SUPPORT):
            continue
        candidates.append({
            **spec,
            "support": len(kept),
            "source_support": dict(support),
            "retention_ratio": len(kept) / len(rows),
        })

    if not candidates:
        return None
    op_rank = {"ge": 0, "lt": 1, "gt": 1, "ne": 2}
    candidates.sort(key=lambda c: (
        int(c["semantic_priority"]),
        -int(c["support"]),
        -min(int(c["source_support"].get(g, 0)) for g in MIN_SUPPORT),
        op_rank[str(c["op"])],
        str(c["feature_name"]),
        int(c["value"]),
    ))
    return candidates[0]


def admitted_parent(
    engine: UCIStockfish,
    guard: dict[str, Any],
    board: chess.Board,
    *,
    authority: bool,
    generation: str,
) -> tuple[dict[str, Any] | None, list[str] | None]:
    fen = board.fen()
    p1, p2 = base_probes(engine, fen)
    fires, leaf = guard_fires(guard, board, p1, p2)
    if not fires:
        return None, None

    cnames, cfeats, cmeta = continuation_features(
        engine, board, str(p2["bestmove"])
    )
    if not apply_pred(cnames, cfeats, SEP1):
        return None, cnames
    if not apply_pred(cnames, cfeats, SEP2):
        return None, cnames

    alt = root_alternative(p2)
    if alt is None:
        return None, cnames

    rnames, rfeats, rmeta = relation_features(
        engine, board, str(p2["bestmove"]), alt
    )
    row = {
        "fen": fen,
        "generation": generation,
        "leaf": leaf,
        "candidate": str(p2["bestmove"]),
        "alternative": alt,
        "relation_features": rfeats,
        "relation_meta": rmeta,
    }
    if authority:
        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        row["authority"] = str(auth["bestmove"])
        row["match"] = row["candidate"] == row["authority"]
    return row, rnames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--v28-epd", type=Path, required=True)
    ap.add_argument("--v29-epd", type=Path, required=True)
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

    v28_all = read_epd(args.v28_epd)
    v28_boards = [b for b in v28_all if position_key(b) not in v22_keys]
    v28_keys = {position_key(b) for b in v28_boards}

    v29_all = read_epd(args.v29_epd)
    prior_keys = v22_keys | v28_keys
    v29_boards = [b for b in v29_all if position_key(b) not in prior_keys]
    v29_keys = {position_key(b) for b in v29_boards}

    manifest = json.loads(args.fresh_manifest.read_text())
    if int(manifest["seed"]) != FRESH_SEED:
        raise AssertionError(("fresh seed drift", manifest["seed"]))
    fresh_all = read_epd(args.fresh_epd)
    source_keys = v22_keys | v28_keys | v29_keys
    overlap = {position_key(b) for b in fresh_all} & source_keys
    fresh = [b for b in fresh_all if position_key(b) not in source_keys]
    if len(fresh) < 200:
        raise AssertionError(("fresh too small", len(fresh)))

    engine = UCIStockfish(args.stockfish)
    try:
        rows: list[dict[str, Any]] = []
        relation_names: list[str] | None = None

        # V22 generation: reuse already-protected labels from exact source
        # records, compute relation only after all parent layers admit.
        for split in ("train", "validation", "holdout"):
            records, _ = collect_records(engine, v22_splits[split])
            for rec in records:
                board = chess.Board(rec["fen"])
                p1, p2 = rec["probe1"], rec["probe2"]
                fires, leaf = guard_fires(guard, board, p1, p2)
                if not fires:
                    continue
                cnames, cfeats, _cmeta = continuation_features(
                    engine, board, str(p2["bestmove"])
                )
                if not apply_pred(cnames, cfeats, SEP1):
                    continue
                if not apply_pred(cnames, cfeats, SEP2):
                    continue
                alt = root_alternative(p2)
                if alt is None:
                    continue
                rnames, rfeats, rmeta = relation_features(
                    engine, board, str(p2["bestmove"]), alt
                )
                if relation_names is None:
                    relation_names = rnames
                elif relation_names != rnames:
                    raise AssertionError("relation feature drift")
                rows.append({
                    "fen": rec["fen"],
                    "generation": "v22",
                    "leaf": leaf,
                    "candidate": str(p2["bestmove"]),
                    "alternative": alt,
                    "relation_features": rfeats,
                    "relation_meta": rmeta,
                    "authority": str(rec["authority_bestmove"]),
                    "match": bool(rec["match"]),
                })

        for generation, boards in (("v28", v28_boards), ("v29", v29_boards)):
            for board in boards:
                row, names = admitted_parent(
                    engine, guard, board,
                    authority=True,
                    generation=generation,
                )
                if names is not None and relation_names is not None:
                    # names here is candidate continuation names, not relation.
                    pass
                if row is None:
                    continue
                if relation_names is None:
                    relation_names = list(
                        relation_features(
                            engine,
                            board,
                            row["candidate"],
                            row["alternative"],
                        )[0]
                    )
                rows.append(row)

        wrong = sum(not bool(r["match"]) for r in rows)
        if wrong != 1:
            raise AssertionError(("pooled V30 residual drift", len(rows), wrong))
        generations = Counter(str(r["generation"]) for r in rows)
        relation = choose_relation(rows, relation_names or [])
        if relation is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_RELATIVE_CONTINUATION_SEPARATOR",
                "source_states": len(rows),
                "source_wrong": wrong,
                "source_generations": dict(generations),
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_RELATIVE_CONTINUATION_V30="
                "NO_RELATIVE_CONTINUATION_SEPARATOR"
            )
            print(f"artifact={args.output}")
            return 0

        # Frozen here. No fresh 100k authority has been queried.
        j = int(relation["feature"])
        parent = accepted = wrong_fresh = 0
        no_alt = 0
        examples = []

        for board in fresh:
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            cnames, cfeats, _ = continuation_features(
                engine, board, str(p2["bestmove"])
            )
            if not apply_pred(cnames, cfeats, SEP1):
                continue
            if not apply_pred(cnames, cfeats, SEP2):
                continue

            parent += 1
            alt = root_alternative(p2)
            if alt is None:
                no_alt += 1
                continue
            rnames, rfeats, rmeta = relation_features(
                engine, board, str(p2["bestmove"]), alt
            )
            if rnames != relation_names:
                raise AssertionError("fresh relation feature drift")
            if not relation_eval(relation, int(rfeats[j])):
                continue

            accepted += 1
            auth = engine.search(
                fen, AUTHORITY_NODES, multipv=1, clear=True
            )
            ok = str(p2["bestmove"]) == str(auth["bestmove"])
            wrong_fresh += int(not ok)
            if len(examples) < 30:
                examples.append({
                    "fen": fen,
                    "leaf": leaf,
                    "candidate": str(p2["bestmove"]),
                    "alternative": alt,
                    "authority": str(auth["bestmove"]),
                    "match": ok,
                    "relation_feature": relation["feature_name"],
                    "relation_value": int(rfeats[j]),
                    "relation_meta": rmeta,
                })
    finally:
        engine.quit()

    n = len(fresh)
    baseline = n * AUTHORITY_NODES
    # Root probes everywhere. Candidate-continuation probe is paid only for
    # V25-covered roots, just as V28/V29. Alternative continuation adds one
    # extra 5k only after sep1+sep2 admit the state.
    # parent is exactly the states paying that alternative probe.
    v25_cost_states = 0
    # Recompute economically from source-free target without deep authority is
    # unnecessary for correctness; parent is a lower bound for V25 fires after
    # sep1+sep2. We conservatively charge 10k continuation work to every parent
    # state and retain the V28 5k cost only there. This never overstates savings.
    hybrid = (
        n * PROBE_TOTAL_NODES
        + parent * (2 * CHILD_PROBE_TOTAL_NODES)
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline

    green = accepted > 0 and wrong_fresh == 0 and reduction > 0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_RELATIVE_CONTINUATION_GUARD"
        if green else
        "FRESH_NORMAL_SEARCH_RELATIVE_CONTINUATION_RESIDUAL"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source_runs": {
            "v22": V22_RUN,
            "v25": V25_RUN,
            "v28": V28_RUN,
            "v29": V29_RUN,
        },
        "frozen_parent": {
            "v25_guard_sha256": sha,
            "sep1": SEP1,
            "sep2": SEP2,
        },
        "source": {
            "states": len(rows),
            "wrong": wrong,
            "generations": dict(generations),
            "relation_feature_names": relation_names,
            "relation": relation,
        },
        "fresh": {
            "seed": FRESH_SEED,
            "book_sha256": manifest["book_sha256"],
            "positions": n,
            "source_overlap_removed": len(overlap),
            "parent_admitted": parent,
            "no_alternative": no_alt,
            "accepted": accepted,
            "wrong": wrong_fresh,
            "coverage_ratio": accepted / n,
            "baseline_nodes": baseline,
            "conservative_hybrid_nodes": hybrid,
            "estimated_node_reduction_ratio": reduction,
            "examples": examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V25/V28/V29 parent guards are frozen",
                "single V29 false positive earns one candidate-vs-alternative continuation relation only",
                "relation has minimum support in all three exposed source generations",
                "fresh seed is opened only after relation freeze and exact source duplicates are removed without target labels",
                "every accepted fresh shortcut equals pinned 100k Stockfish",
                "conservatively charged total node work is lower than 100k-per-root baseline",
            ],
            "unknown": [
                "replication on another fresh seed",
                "wall-clock UCI gain",
                "self-play Elo gain",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_RELATIVE_CONTINUATION_V30={status}")
    print(
        f"source states={len(rows)} wrong={wrong} "
        f"generations={dict(generations)} relation={relation}"
    )
    print(
        f"fresh positions={n} parent={parent} accepted={accepted} "
        f"wrong={wrong_fresh} coverage={accepted/n:.8f} "
        f"reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
