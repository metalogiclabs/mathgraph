#!/usr/bin/env python3
"""Crystal Chess V42: residual-earned certificate-set width.

V41 showed that union(top-4 at 1k, top-4 at TT-reused 4k) contains the
pinned 100k Stockfish move on 94.675% of 2,385 exposed normal positions,
while eliminating 85.95% of legal root moves.

V42 changes exactly one thing: certificate-set width.  No classifier,
threshold, board feature, or continuation feature is introduced.

Protocol:
* one 1k MultiPV16 root probe;
* one TT-reused 4k MultiPV16 root probe;
* evaluate predeclared widths K in {4,6,8,12,16};
* candidate set is either p2 top-K or union(p1 top-K,p2 top-K);
* choose the smallest source-zero-miss set that still eliminates >=50% of
  legal root moves;
* freeze before fresh 100k authority queries on seeds 20261023/20261024.

If no nontrivial zero-miss set exists, report the exact residual, including
how many authorities are absent from both shallow top-16 lists.
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
    PROBE1_NODES,
    PROBE2_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key
from crystal_chess_normal_certificate_set_v41 import (
    collect_boards,
    search_multi,
    top_moves,
)

SCHEMA = "mathgraph.crystal-chess.normal-certificate-width.v42"
FRESH_SEEDS = (20261023, 20261024)
MAX_MULTIPV = 16
WIDTHS = (4, 6, 8, 12, 16)
MIN_ELIMINATION = 0.50


def cset(kind: str, k: int, p1: dict[str, Any], p2: dict[str, Any]) -> list[str]:
    if kind == "p2":
        return top_moves(p2, k)
    if kind == "union":
        out: list[str] = []
        seen: set[str] = set()
        for move in top_moves(p2, k) + top_moves(p1, k):
            if move not in seen:
                seen.add(move)
                out.append(move)
        return out
    raise ValueError(kind)


def rank_of(move: str, probe: dict[str, Any]) -> int | None:
    for row in probe["ranked"]:
        if str(row["move"]) == move:
            return int(row["rank"])
    return None


def eval_items(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
    *,
    keep_examples: int = 40,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    keys = [(kind, k) for kind in ("p2", "union") for k in WIDTHS]
    stats = {
        key: {
            "positions": 0,
            "misses": 0,
            "set_size_sum": 0,
            "legal_sum": 0,
            "support": Counter(),
        }
        for key in keys
    }
    records: list[dict[str, Any]] = []

    for generation, board in items:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES, multipv=MAX_MULTIPV, clear=True
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES, multipv=MAX_MULTIPV, clear=False
        )
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        authority = str(auth["bestmove"])
        legal = board.legal_moves.count()
        r1 = rank_of(authority, p1)
        r2 = rank_of(authority, p2)

        sets = {}
        for key in keys:
            kind, k = key
            moves = cset(kind, k, p1, p2)
            sets[f"{kind}_top{k}"] = moves
            st = stats[key]
            st["positions"] += 1
            st["set_size_sum"] += len(moves)
            st["legal_sum"] += legal
            st["support"][generation] += 1
            st["misses"] += int(authority not in moves)

        records.append({
            "generation": generation,
            "fen": fen,
            "authority": authority,
            "legal_moves": legal,
            "authority_rank_p1": r1,
            "authority_rank_p2": r2,
            "authority_absent_both_top16": r1 is None and r2 is None,
            "sets": sets,
        })

    final: dict[str, Any] = {}
    for (kind, k), st in stats.items():
        n = int(st["positions"])
        size = int(st["set_size_sum"])
        legal = int(st["legal_sum"])
        name = f"{kind}_top{k}"
        misses = int(st["misses"])
        final[name] = {
            "positions": n,
            "misses": misses,
            "hit_ratio": (n - misses) / n if n else 1.0,
            "mean_set_size": size / n if n else 0.0,
            "mean_legal_moves": legal / n if n else 0.0,
            "root_move_elimination_ratio": 1.0 - size / legal if legal else 0.0,
            "support": dict(st["support"]),
        }

    # Attach examples only for the strongest predeclared set.
    strongest = "union_top16"
    examples = []
    for row in records:
        if row["authority"] not in row["sets"][strongest]:
            if len(examples) < keep_examples:
                examples.append({
                    "generation": row["generation"],
                    "fen": row["fen"],
                    "authority": row["authority"],
                    "authority_rank_p1": row["authority_rank_p1"],
                    "authority_rank_p2": row["authority_rank_p2"],
                    "authority_absent_both_top16": row["authority_absent_both_top16"],
                    "candidate_set": row["sets"][strongest],
                })
    final[strongest]["miss_examples"] = examples
    return final, records


def choose(stats: dict[str, Any]) -> str | None:
    candidates = []
    for name, st in stats.items():
        if int(st["misses"]) != 0:
            continue
        if float(st["root_move_elimination_ratio"]) < MIN_ELIMINATION:
            continue
        candidates.append((
            float(st["mean_set_size"]),
            -float(st["root_move_elimination_ratio"]),
            name,
        ))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def fresh_eval(
    engine: UCIStockfish,
    boards: list[chess.Board],
    variant: str,
) -> dict[str, Any]:
    kind, width_txt = variant.split("_top")
    k = int(width_txt)
    misses = 0
    set_sum = 0
    legal_sum = 0
    examples = []

    for board in boards:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES, multipv=MAX_MULTIPV, clear=True
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES, multipv=MAX_MULTIPV, clear=False
        )
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        authority = str(auth["bestmove"])
        moves = cset(kind, k, p1, p2)
        legal = board.legal_moves.count()
        ok = authority in moves
        misses += int(not ok)
        set_sum += len(moves)
        legal_sum += legal
        if not ok and len(examples) < 30:
            examples.append({
                "fen": fen,
                "authority": authority,
                "authority_rank_p1": rank_of(authority, p1),
                "authority_rank_p2": rank_of(authority, p2),
                "candidate_set": moves,
            })

    n = len(boards)
    return {
        "positions": n,
        "misses": misses,
        "hit_ratio": (n - misses) / n if n else 1.0,
        "mean_set_size": set_sum / n if n else 0.0,
        "mean_legal_moves": legal_sum / n if n else 0.0,
        "root_move_elimination_ratio": 1.0 - set_sum / legal_sum if legal_sum else 0.0,
        "miss_examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation mismatch")

    source_items = collect_boards(
        args.v22_pgn,
        list(zip(args.source_generation, args.source_epd)),
    )

    engine = UCIStockfish(args.stockfish)
    try:
        source_stats, records = eval_items(engine, source_items)
        selected = choose(source_stats)

        absent_both = sum(bool(r["authority_absent_both_top16"]) for r in records)
        if selected is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_NONTRIVIAL_ZERO_MISS_WIDTH",
                "stockfish_pin": STOCKFISH_PIN,
                "probe_protocol": {
                    "probe1_nodes": PROBE1_NODES,
                    "probe2_nodes": PROBE2_NODES,
                    "probe2_reuses_probe1_tt": True,
                    "multipv": MAX_MULTIPV,
                    "authority_nodes": AUTHORITY_NODES,
                },
                "source": {
                    "positions": len(source_items),
                    "generation_counts": dict(Counter(g for g, _ in source_items)),
                    "variants": source_stats,
                    "authority_absent_both_top16": absent_both,
                },
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print("CRYSTAL_CHESS_NORMAL_CERTIFICATE_WIDTH_V42=NO_NONTRIVIAL_ZERO_MISS_WIDTH")
            for name, st in source_stats.items():
                print(
                    f"{name}: misses={st['misses']} hit={st['hit_ratio']:.8f} "
                    f"mean_set={st['mean_set_size']:.4f} "
                    f"elimination={st['root_move_elimination_ratio']:.8f}"
                )
            print(f"authority_absent_both_top16={absent_both}/{len(records)}")
            print(f"artifact={args.output}")
            return 0

        # Freeze selected width before any fresh 100k authority search.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = {position_key(b) for _, b in source_items}
        targets = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        overlap_info = []
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            source_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            targets.append(fresh_eval(engine, boards, selected))
            overlap_info.append((len(source_overlap), len(cross)))
    finally:
        engine.quit()

    total_n = sum(x["positions"] for x in targets)
    total_miss = sum(x["misses"] for x in targets)
    set_sum = sum(x["mean_set_size"] * x["positions"] for x in targets)
    legal_sum = sum(x["mean_legal_moves"] * x["positions"] for x in targets)
    elim = 1.0 - set_sum / legal_sum

    green = total_miss == 0 and elim >= MIN_ELIMINATION
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_WIDE_CERTIFICATE_SET"
        if green else
        "FRESH_NORMAL_WIDE_CERTIFICATE_SET_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source": {
            "positions": len(source_items),
            "generation_counts": dict(Counter(g for g, _ in source_items)),
            "variants": source_stats,
            "selected_variant": selected,
            "authority_absent_both_top16": absent_both,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlap_info[i][0],
                "earlier_target_overlap_removed_before_search": overlap_info[i][1],
                **targets[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_n,
            "misses": total_miss,
            "hit_ratio": (total_n - total_miss) / total_n,
            "mean_set_size": set_sum / total_n,
            "mean_legal_moves": legal_sum / total_n,
            "root_move_elimination_ratio": elim,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "only certificate-set width changes relative to V41",
                "selected width has zero source misses and >=50% legal root-move elimination",
                "width is frozen before fresh authority queries",
                "same frozen set contains pinned 100k authority on both fresh seeds",
            ],
            "unknown": [
                "node reduction when search is restricted to the set",
                "wall-clock gain",
                "self-play Elo gain",
                "chess-theoretic optimality of 100k Stockfish",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_NORMAL_CERTIFICATE_WIDTH_V42={status}")
    print(
        f"source positions={len(source_items)} selected={selected} "
        f"mean_set={source_stats[selected]['mean_set_size']:.6f} "
        f"elimination={source_stats[selected]['root_move_elimination_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} misses={row['misses']} "
            f"mean_set={row['mean_set_size']:.6f} "
            f"elimination={row['root_move_elimination_ratio']:.8f}"
        )
    print(
        f"combined misses={total_miss}/{total_n} "
        f"mean_set={result['combined']['mean_set_size']:.6f} "
        f"elimination={elim:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
