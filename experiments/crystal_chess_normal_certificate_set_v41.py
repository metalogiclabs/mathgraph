#!/usr/bin/env python3
"""Crystal Chess V41: normal-game root certificate sets.

The V34-V40 lineage shows that exact root-witness substitution is correct only
on a sparse normal-game slice.  V13 already taught the programme that strategy
semantics should be sets of admissible certificates rather than arbitrary
witness identity.

V41 therefore asks a denser question:

    Does a small frozen set of cheap MultiPV root moves contain the
    pinned 100k Stockfish move?

No learned threshold or classifier is used.  Six set constructors are declared
before source evaluation.  The smallest source-zero-miss constructor is frozen
before untouched seeds 20261021/20261022.

If green, this certifies root *move elimination* relative to pinned Stockfish.
It does not yet claim node or Elo gain; a later systems gate must run Stockfish
inside the certified set.
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
    extract_positions,
)
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key

SCHEMA = "mathgraph.crystal-chess.normal-certificate-set.v41"
FRESH_SEEDS = (20261021, 20261022)
MULTIPV = 4

VARIANTS = (
    "p2_top2",
    "p2_top3",
    "p2_top4",
    "union_p1p2_top2",
    "union_p1p2_top3",
    "union_p1p2_top4",
)


def search_multi(
    engine: UCIStockfish,
    fen: str,
    nodes: int,
    *,
    multipv: int,
    clear: bool,
) -> dict[str, Any]:
    if clear:
        engine.clear_hash()
    engine.send(f"setoption name MultiPV value {multipv}")
    engine.send("position fen " + fen)
    engine.send(f"go nodes {nodes}")
    lines = engine.read_until("bestmove")
    bestmove = lines[-1].split()[1]
    pv_info: dict[int, dict[str, Any]] = {}

    for line in lines[:-1]:
        if not line.startswith("info "):
            continue
        tokens = line.split()
        if "pv" not in tokens or "score" not in tokens:
            continue
        mpv = engine._int_after(tokens, "multipv", 1)
        try:
            pvi = tokens.index("pv")
            pv = tokens[pvi + 1 :]
        except ValueError:
            pv = []
        pv_info[mpv] = {
            "score": engine._score_value(tokens),
            "depth": engine._int_after(tokens, "depth"),
            "seldepth": engine._int_after(tokens, "seldepth"),
            "nodes": engine._int_after(tokens, "nodes"),
            "pv": pv,
        }

    ranked = []
    for rank in range(1, multipv + 1):
        row = pv_info.get(rank)
        if not row or not row["pv"]:
            continue
        ranked.append({
            "rank": rank,
            "move": str(row["pv"][0]),
            "score": int(row["score"]),
            "depth": int(row["depth"]),
            "seldepth": int(row["seldepth"]),
            "pv": list(row["pv"]),
        })
    return {
        "bestmove": bestmove,
        "ranked": ranked,
    }


def top_moves(probe: dict[str, Any], k: int) -> list[str]:
    out = []
    seen = set()
    for row in probe["ranked"][:k]:
        move = str(row["move"])
        if move and move not in seen:
            seen.add(move)
            out.append(move)
    return out


def candidate_set(
    variant: str,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> list[str]:
    if variant.startswith("p2_top"):
        k = int(variant[-1])
        return top_moves(p2, k)
    if variant.startswith("union_p1p2_top"):
        k = int(variant[-1])
        out = []
        seen = set()
        for move in top_moves(p2, k) + top_moves(p1, k):
            if move not in seen:
                seen.add(move)
                out.append(move)
        return out
    raise ValueError(variant)


def collect_boards(
    v22_pgn: Path,
    generations: list[tuple[str, Path]],
) -> list[tuple[str, chess.Board]]:
    out: list[tuple[str, chess.Board]] = []
    seen: set[tuple[str, bool, str, int | None]] = set()

    splits = extract_positions(v22_pgn, 120)
    for split in ("train", "validation", "holdout"):
        for board in splits[split]:
            key = position_key(board)
            if key in seen:
                continue
            seen.add(key)
            out.append(("v22_" + split, board))

    for generation, path in generations:
        for board in read_epd(path):
            key = position_key(board)
            if key in seen:
                continue
            seen.add(key)
            out.append((generation, board))
    return out


def evaluate_corpus(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stats = {
        variant: {
            "positions": 0,
            "misses": 0,
            "set_size_sum": 0,
            "legal_moves_sum": 0,
            "support": Counter(),
            "miss_examples": [],
        }
        for variant in VARIANTS
    }
    records: list[dict[str, Any]] = []

    for generation, board in items:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES,
            multipv=MULTIPV, clear=True,
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES,
            multipv=MULTIPV, clear=False,
        )
        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        authority = str(auth["bestmove"])
        legal_count = board.legal_moves.count()

        row_sets = {}
        for variant in VARIANTS:
            cset = candidate_set(variant, p1, p2)
            row_sets[variant] = cset
            st = stats[variant]
            st["positions"] += 1
            st["set_size_sum"] += len(cset)
            st["legal_moves_sum"] += legal_count
            st["support"][generation] += 1
            if authority not in cset:
                st["misses"] += 1
                if len(st["miss_examples"]) < 30:
                    st["miss_examples"].append({
                        "generation": generation,
                        "fen": fen,
                        "authority": authority,
                        "candidate_set": cset,
                        "p1": p1,
                        "p2": p2,
                    })

        records.append({
            "generation": generation,
            "fen": fen,
            "authority": authority,
            "legal_moves": legal_count,
            "sets": row_sets,
        })

    finalized = {}
    for variant, st in stats.items():
        n = int(st["positions"])
        size_sum = int(st["set_size_sum"])
        legal_sum = int(st["legal_moves_sum"])
        finalized[variant] = {
            "positions": n,
            "misses": int(st["misses"]),
            "hit_ratio": (
                (n - int(st["misses"])) / n if n else 1.0
            ),
            "mean_set_size": size_sum / n if n else 0.0,
            "mean_legal_moves": legal_sum / n if n else 0.0,
            "root_move_elimination_ratio": (
                1.0 - size_sum / legal_sum if legal_sum else 0.0
            ),
            "support": dict(st["support"]),
            "miss_examples": st["miss_examples"],
        }
    return finalized, records


def choose_variant(stats: dict[str, Any]) -> str | None:
    candidates = []
    order = {v: i for i, v in enumerate(VARIANTS)}
    for variant, st in stats.items():
        if int(st["misses"]) != 0:
            continue
        candidates.append((
            float(st["mean_set_size"]),
            -float(st["root_move_elimination_ratio"]),
            order[variant],
            variant,
        ))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][3]


def evaluate_fresh(
    engine: UCIStockfish,
    boards: list[chess.Board],
    variant: str,
) -> dict[str, Any]:
    misses = 0
    set_size_sum = 0
    legal_sum = 0
    examples = []

    for board in boards:
        fen = board.fen()
        p1 = search_multi(
            engine, fen, PROBE1_NODES,
            multipv=MULTIPV, clear=True,
        )
        p2 = search_multi(
            engine, fen, PROBE2_NODES,
            multipv=MULTIPV, clear=False,
        )
        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        authority = str(auth["bestmove"])
        cset = candidate_set(variant, p1, p2)
        legal_count = board.legal_moves.count()

        set_size_sum += len(cset)
        legal_sum += legal_count
        ok = authority in cset
        misses += int(not ok)
        if len(examples) < 30:
            examples.append({
                "fen": fen,
                "authority": authority,
                "candidate_set": cset,
                "contains_authority": ok,
                "legal_moves": legal_count,
            })

    n = len(boards)
    return {
        "positions": n,
        "misses": misses,
        "hit_ratio": (n - misses) / n if n else 1.0,
        "mean_set_size": set_size_sum / n if n else 0.0,
        "mean_legal_moves": legal_sum / n if n else 0.0,
        "root_move_elimination_ratio": (
            1.0 - set_size_sum / legal_sum if legal_sum else 0.0
        ),
        "examples": examples,
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
        source_stats, _ = evaluate_corpus(engine, source_items)
        variant = choose_variant(source_stats)

        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ZERO_MISS_NORMAL_CERTIFICATE_SET",
                "stockfish_pin": STOCKFISH_PIN,
                "source": {
                    "positions": len(source_items),
                    "generation_counts": dict(Counter(g for g, _ in source_items)),
                    "variants": source_stats,
                },
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_NORMAL_CERTIFICATE_SET_V41="
                "NO_ZERO_MISS_NORMAL_CERTIFICATE_SET"
            )
            for name, st in source_stats.items():
                print(
                    f"{name}: misses={st['misses']} "
                    f"mean_set={st['mean_set_size']:.4f} "
                    f"elimination={st['root_move_elimination_ratio']:.8f}"
                )
            print(f"artifact={args.output}")
            return 0

        # Freeze here before fresh 100k authority queries.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = {position_key(b) for _, b in source_items}
        target_sets = []
        source_overlaps = []
        cross_overlaps = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            source_overlaps.append(len(overlap))
            cross_overlaps.append(len(cross))

        fresh = [
            evaluate_fresh(engine, boards, variant)
            for boards in target_sets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in fresh)
    combined_misses = sum(r["misses"] for r in fresh)
    combined_set = sum(r["mean_set_size"] * r["positions"] for r in fresh)
    combined_legal = sum(r["mean_legal_moves"] * r["positions"] for r in fresh)
    combined_elim = 1.0 - combined_set / combined_legal

    green = (
        all(r["misses"] == 0 for r in fresh)
        and combined_elim > 0
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_CERTIFICATE_SET"
        if green else
        "FRESH_NORMAL_CERTIFICATE_SET_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "probe_protocol": {
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "probe2_reuses_probe1_tt": True,
            "multipv": MULTIPV,
            "authority_nodes": AUTHORITY_NODES,
        },
        "source": {
            "positions": len(source_items),
            "generation_counts": dict(Counter(g for g, _ in source_items)),
            "variants": source_stats,
            "selected_variant": variant,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": source_overlaps[i],
                "earlier_target_overlap_removed_before_search": cross_overlaps[i],
                **fresh[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": combined_positions,
            "misses": combined_misses,
            "hit_ratio": (
                (combined_positions - combined_misses) / combined_positions
            ),
            "mean_set_size": combined_set / combined_positions,
            "mean_legal_moves": combined_legal / combined_positions,
            "root_move_elimination_ratio": combined_elim,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the set constructor is selected only from six predeclared MultiPV set constructions",
                "selected set contains the pinned 100k Stockfish move on every exposed source position",
                "constructor is frozen before fresh 100k authority search",
                "selected set contains the authority move on both untouched fresh seeds",
                "reported move elimination counts only legal root moves outside the certified set",
            ],
            "unknown": [
                "node reduction when Stockfish is actually restricted to the set",
                "wall-clock gain",
                "self-play Elo gain",
                "chess-theoretic optimality of the 100k authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_NORMAL_CERTIFICATE_SET_V41={status}")
    print(
        f"source positions={len(source_items)} selected={variant} "
        f"mean_set={source_stats[variant]['mean_set_size']:.6f} "
        f"elimination={source_stats[variant]['root_move_elimination_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, fresh):
        print(
            f"seed={seed} positions={row['positions']} misses={row['misses']} "
            f"mean_set={row['mean_set_size']:.6f} "
            f"mean_legal={row['mean_legal_moves']:.6f} "
            f"elimination={row['root_move_elimination_ratio']:.8f}"
        )
    print(
        f"combined misses={combined_misses}/{combined_positions} "
        f"mean_set={result['combined']['mean_set_size']:.6f} "
        f"elimination={combined_elim:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
