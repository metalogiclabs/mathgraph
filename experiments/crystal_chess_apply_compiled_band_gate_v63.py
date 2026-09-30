#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PAT = r"""(            double highBestMoveEffort = std::clamp\(
          \s*interpolate\(i64\(nodesEffort\), i64\(75800\), i64\(104510\), 0\.969, 0\.714\), 0\.693, 0\.838\);)"""

REPL = r"""\1

            // Crystal V63: compiled candidate from V56/V58/V60/V62 residual join.
            // Preserve the proven fast-clock region, exclude the candidate harmful
            // 17..32 ms band, and retain the candidate useful 33..64 ms band.
            const auto crystalOptimum = mainThread->tm.optimum();
            if (crystalOptimum <= 16 || (crystalOptimum >= 33 && crystalOptimum <= 64))
                highBestMoveEffort = 1.0;"""

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-cpp", type=Path, required=True)
    a = ap.parse_args()
    s = a.search_cpp.read_text()
    s, n = re.subn(PAT, REPL, s, count=1)
    if n != 1:
        raise AssertionError(("V63 split-gate anchor drift", n))
    a.search_cpp.write_text(s)
    print("CRYSTAL_CHESS_COMPILED_BAND_GATE_V63=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
