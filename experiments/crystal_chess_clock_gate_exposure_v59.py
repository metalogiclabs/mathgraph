#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

ENTRY_PAT = r"""(bool Search::Worker::iterative_deepening\(\) \{

    SearchManager\* mainThread = \(is_mainthread\(\) \? main_manager\(\) : nullptr\);
)"""

ENTRY_REPL = r"""\1
    if (mainThread)
        sync_cout << "info string crystal_tm optimum " << mainThread->tm.optimum()
                  << " maximum " << mainThread->tm.maximum()
                  << " active " << int(mainThread->tm.optimum() <= 64) << sync_endl;
"""

GATE_PAT = r"""(            double highBestMoveEffort = std::clamp\(
          \s*interpolate\(i64\(nodesEffort\), i64\(75800\), i64\(104510\), 0\.969, 0\.714\), 0\.693, 0\.838\);)"""

GATE_REPL = r"""\1

            if (mainThread->tm.optimum() <= 64)
                highBestMoveEffort = 1.0;"""

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-cpp", type=Path, required=True)
    a = ap.parse_args()
    s = a.search_cpp.read_text()

    s, n1 = re.subn(ENTRY_PAT, ENTRY_REPL, s, count=1)
    s, n2 = re.subn(GATE_PAT, GATE_REPL, s, count=1)
    if (n1, n2) != (1, 1):
        raise AssertionError(("V59b anchor drift", n1, n2))

    a.search_cpp.write_text(s)
    print("CRYSTAL_CHESS_CLOCK_GATE_EXPOSURE_PATCH_V59B=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
