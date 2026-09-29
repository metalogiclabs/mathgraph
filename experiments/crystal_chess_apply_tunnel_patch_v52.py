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

            // Crystal V52: residual-earned tunnel guard.
            if (nodesEffort >= 75800 && rootDepth - lastBestMoveDepth >= 5)
            {
                timeReduction      = 1.0;
                highBestMoveEffort = 1.0;
                reduction =
                  (1.468 + mainThread->previousTimeReduction) / (2.284 * timeReduction);
            }

            double totalTime = mainThread->tm.optimum() * fallingEval * reduction
"""

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--search-cpp",type=Path,required=True)
    args=ap.parse_args()
    s=args.search_cpp.read_text()
    if s.count(ANCHOR)!=1:
        raise AssertionError(("V52 anchor drift",s.count(ANCHOR)))
    args.search_cpp.write_text(s.replace(ANCHOR,REPLACEMENT,1))
    print("CRYSTAL_CHESS_TUNNEL_PATCH_V52=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
