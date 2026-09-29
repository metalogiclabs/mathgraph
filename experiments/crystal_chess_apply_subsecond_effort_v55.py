#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ANCHOR = """            double highBestMoveEffort = std::clamp(
              interpolate(i64(nodesEffort), i64(75800), i64(104510), 0.969, 0.714), 0.693, 0.838);

            double totalTime = mainThread->tm.optimum() * fallingEval * reduction
"""

REPLACEMENT = """            double highBestMoveEffort = std::clamp(
              interpolate(i64(nodesEffort), i64(75800), i64(104510), 0.969, 0.714), 0.693, 0.838);

            // Crystal V55: use Stockfish's existing subsecond regime boundary.
            if (limits.time[rootPos.side_to_move()] < 1000)
                highBestMoveEffort = 1.0;

            double totalTime = mainThread->tm.optimum() * fallingEval * reduction
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-cpp", type=Path, required=True)
    args = ap.parse_args()

    s = args.search_cpp.read_text()
    if s.count(ANCHOR) != 1:
        raise AssertionError(("V55 anchor drift", s.count(ANCHOR)))
    args.search_cpp.write_text(s.replace(ANCHOR, REPLACEMENT, 1))
    print("CRYSTAL_CHESS_SUBSECOND_EFFORT_PATCH_V55=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
