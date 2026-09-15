#!/usr/bin/env python3
"""Fast non-claiming V71 diagnostic: same graph/budget, 4 train + 4 eval sources."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "experiments" / "capability_graph_frontier_transfer_v71" / "run_calibration.py"
S = importlib.util.spec_from_file_location("v71_diag_core", P)
if S is None or S.loader is None:
    raise RuntimeError("cannot load V71")
V71 = importlib.util.module_from_spec(S)
sys.modules[S.name] = V71
S.loader.exec_module(V71)

V71.TRAIN_SOURCE_COUNT = 4
V71.EVAL_SOURCE_COUNT = 4
V71.MAX_SOURCE_ATTEMPTS = 180

if __name__ == "__main__":
    V71.main()
