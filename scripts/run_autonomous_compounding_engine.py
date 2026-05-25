#!/usr/bin/env python
"""Run the autonomous finite-core MathGraph compounding façade."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mathgraph.autonomous_compounding_engine import AutonomousCompoundingConfig, run_autonomous_compounding


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equations")
    parser.add_argument("--matrix")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--episodes", type=int, default=4)
    parser.add_argument("--sample-pairs", type=int, default=4000)
    parser.add_argument("--repair-budget", type=int, default=40)
    parser.add_argument("--max-n", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument("--tiny-demo", action="store_true")
    parser.add_argument("--finite-core-mode", choices=("facade", "native_v2"), default="facade")
    parser.add_argument("--constructor-limit", type=int)
    parser.add_argument("--include-random-constructors", action="store_true")
    parser.add_argument("--random-constructor-count", type=int, default=0)
    parser.add_argument("--lawbook-path")
    parser.add_argument("--reuse-lawbook", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    summary = run_autonomous_compounding(
        AutonomousCompoundingConfig(
            equations=args.equations,
            matrix=args.matrix,
            out_dir=args.out_dir,
            episodes=args.episodes,
            sample_pairs=args.sample_pairs,
            repair_budget=args.repair_budget,
            max_n=args.max_n,
            seed=args.seed,
            tiny_demo=args.tiny_demo,
            finite_core_mode=args.finite_core_mode,
            constructor_limit=args.constructor_limit,
            include_random_constructors=args.include_random_constructors,
            random_constructor_count=args.random_constructor_count,
            lawbook_path=args.lawbook_path,
            reuse_lawbook=args.reuse_lawbook,
            write_report=args.write_report,
        )
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
