#!/usr/bin/env python3
"""Fast non-claiming V75 depth-3 diagnostic on first 4 V73 sources."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "experiments" / "deep_closure_optimality_audit_v75" / "run.py"
S = importlib.util.spec_from_file_location("v75_diag_core", P)
if S is None or S.loader is None:
    raise RuntimeError("cannot load V75")
V75 = importlib.util.module_from_spec(S)
sys.modules[S.name] = V75
S.loader.exec_module(V75)

V75.ROUND3_POOL = 72
V75.V73.FRESH_SOURCE_COUNT = 4

if __name__ == "__main__":
    V75.main()
