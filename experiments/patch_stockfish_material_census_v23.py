#!/usr/bin/env python3
"""Deterministically instrument pinned Stockfish search.cpp for V23."""

from __future__ import annotations

import argparse
from pathlib import Path


INSERT_BLOCK = r'''
// Diagnostic-only material census for Crystal Chess V23. The qualification
// workflow pins Threads=1, so only the main search worker records nodes.
// This code does not alter search decisions or values.
std::map<std::uint64_t, std::uint64_t> crystalMaterialCounts;

std::uint64_t crystal_material_code(const Position& pos) {
    constexpr std::array<PieceType, 5> pts = {PAWN, KNIGHT, BISHOP, ROOK, QUEEN};
    std::uint64_t code = 0;
    int shift = 0;
    for (Color c : {WHITE, BLACK})
        for (PieceType pt : pts)
        {
            const std::uint64_t n = std::uint64_t(popcount(pos.pieces(c, pt)));
            code |= (n & 0xFULL) << shift;
            shift += 4;
        }
    return code;
}

void crystal_record_material(const Position& pos) {
    if (pos.count<ALL_PIECES>() <= 8)
        ++crystalMaterialCounts[crystal_material_code(pos)];
}

void crystal_dump_material() {
    for (const auto& [code, count] : crystalMaterialCounts)
        std::cout << "info string CRYSTAL_SEARCH_MATERIAL " << code << " " << count << std::endl;
}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {n}")
    return text.replace(old, new, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("search_cpp", type=Path)
    args = ap.parse_args()
    path = args.search_cpp
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "#include <list>\n#include <ratio>",
        "#include <list>\n#include <map>\n#include <ratio>",
        "include map",
    )
    text = replace_once(
        text,
        "constexpr u64 NODES_LIMIT_OUTPUT = 10'000'000;\n\n"
        "constexpr int SEARCHEDLIST_CAPACITY = 32;",
        "constexpr u64 NODES_LIMIT_OUTPUT = 10'000'000;\n"
        + INSERT_BLOCK
        + "\nconstexpr int SEARCHEDLIST_CAPACITY = 32;",
        "diagnostic block",
    )
    text = replace_once(
        text,
        "    accumulatorStack.reset();\n\n"
        "    // Non-main threads go directly to iterative_deepening()",
        "    accumulatorStack.reset();\n\n"
        "    if (is_mainthread())\n"
        "        crystalMaterialCounts.clear();\n\n"
        "    // Non-main threads go directly to iterative_deepening()",
        "reset census",
    )
    text = replace_once(
        text,
        "    auto bestmove = UCIEngine::move(bestThread->rootMoves[0].pv[0], rootPos.is_chess960());\n"
        "    main_manager()->updates.onBestmove(bestmove, ponder);",
        "    if (is_mainthread())\n"
        "        crystal_dump_material();\n\n"
        "    auto bestmove = UCIEngine::move(bestThread->rootMoves[0].pv[0], rootPos.is_chess960());\n"
        "    main_manager()->updates.onBestmove(bestmove, ponder);",
        "dump census",
    )
    text = replace_once(
        text,
        "    if (depth <= 0)\n"
        "        return qsearch<PvNode ? PV : NonPV>(pos, ss, alpha, beta);\n\n"
        "    // Limit the depth if extensions made it too large",
        "    if (depth <= 0)\n"
        "        return qsearch<PvNode ? PV : NonPV>(pos, ss, alpha, beta);\n\n"
        "    if (is_mainthread())\n"
        "        crystal_record_material(pos);\n\n"
        "    // Limit the depth if extensions made it too large",
        "record search",
    )
    text = replace_once(
        text,
        "    assert(alpha >= -VALUE_INFINITE && alpha < beta && beta <= VALUE_INFINITE);\n"
        "    assert(PvNode || (alpha == beta - 1));\n\n"
        "    // Check if we have an upcoming move that draws by repetition",
        "    assert(alpha >= -VALUE_INFINITE && alpha < beta && beta <= VALUE_INFINITE);\n"
        "    assert(PvNode || (alpha == beta - 1));\n\n"
        "    if (is_mainthread())\n"
        "        crystal_record_material(pos);\n\n"
        "    // Check if we have an upcoming move that draws by repetition",
        "record qsearch",
    )

    path.write_text(text, encoding="utf-8")
    print("CRYSTAL_STOCKFISH_MATERIAL_CENSUS_PATCH_V23=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
