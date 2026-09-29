#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

INCLUDE_PAT = '#include <initializer_list>\n'
INCLUDE_REPL = '#include <initializer_list>\n#include <cstdlib>\n#include <fstream>\n'

GATE_PAT = r"""(            double highBestMoveEffort = std::clamp\(
          \s*interpolate\(i64\(nodesEffort\), i64\(75800\), i64\(104510\), 0\.969, 0\.714\), 0\.693, 0\.838\);)"""

GATE_REPL = r"""\1

            // Crystal V60 diagnostic: observe the frozen 64 ms gate exactly where it is used.
            // Log once per search (rootDepth == 1), after time management has been initialized.
            if (rootDepth == 1)
            {
                if (const char* crystalLog = std::getenv("CRYSTAL_TM_LOG"))
                {
                    std::ofstream out(crystalLog, std::ios::app);
                    out << "crystal_tm optimum " << mainThread->tm.optimum()
                        << " maximum " << mainThread->tm.maximum()
                        << " active " << int(mainThread->tm.optimum() <= 64) << '\\n';
                }
            }

            if (mainThread->tm.optimum() <= 64)
                highBestMoveEffort = 1.0;"""

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-cpp", type=Path, required=True)
    a = ap.parse_args()
    s = a.search_cpp.read_text()

    if INCLUDE_PAT not in s:
        raise AssertionError("V60 include anchor drift")
    s = s.replace(INCLUDE_PAT, INCLUDE_REPL, 1)

    s, n = re.subn(GATE_PAT, GATE_REPL, s, count=1)
    if n != 1:
        raise AssertionError(("V60 gate anchor drift", n))

    a.search_cpp.write_text(s)
    print("CRYSTAL_CHESS_CLOCK_GATE_EXPOSURE_PATCH_V60=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
