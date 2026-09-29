#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PAT = r"""(            double highBestMoveEffort = std::clamp\(
          \s*interpolate\(i64\(nodesEffort\), i64\(75800\), i64\(104510\), 0\.969, 0\.714\), 0\.693, 0\.838\);)"""

REPL = r"""\1

            // Crystal V59 diagnostic: expose the frozen V55/V56 gate coordinate.
            if (rootDepth == 1)
                sync_cout << "info string crystal_tm optimum " << mainThread->tm.optimum()
                          << " maximum " << mainThread->tm.maximum()
                          << " active " << int(mainThread->tm.optimum() <= 64) << sync_endl;

            if (mainThread->tm.optimum() <= 64)
                highBestMoveEffort = 1.0;"""

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-cpp", type=Path, required=True)
    a = ap.parse_args()
    s = a.search_cpp.read_text()
    s, n = re.subn(PAT, REPL, s, count=1)
    if n != 1:
        raise AssertionError(("V59 anchor drift", n))
    a.search_cpp.write_text(s)
    print("CRYSTAL_CHESS_CLOCK_GATE_EXPOSURE_PATCH_V59=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
