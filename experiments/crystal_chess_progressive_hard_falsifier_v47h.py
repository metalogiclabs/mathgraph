#!/usr/bin/env python3
"""V47H: hard-only falsifier for progressive stopping.

Runs V47's exact predeclared trajectory-stability rules on only the 19 frozen
V42/V43 hard candidate-generation residuals. If every rule has >=1 mismatch
against the frozen 100k authority, the full V47 rule family is already
falsified and no full-corpus rule can qualify.
"""

from __future__ import annotations
import argparse, json
from pathlib import Path
import chess

from crystal_chess_search_sufficiency_v25 import UCIStockfish
from crystal_chess_progressive_stopping_v47 import (
    RULES, trajectory, evaluate_rule,
)

SCHEMA = "mathgraph.crystal-chess.progressive-hard-falsifier.v47h"


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--stockfish",type=Path,required=True)
    ap.add_argument("--v43-result",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    v43=json.loads(args.v43_result.read_text())
    rows=list(v43.get("rows",[]))
    if len(rows)!=19:
        raise AssertionError(("expected 19 V43 rows",len(rows)))

    engine=UCIStockfish(args.stockfish)
    source=[]
    try:
        for r in rows:
            source.append({
                "generation":"v42_hard",
                "fen":str(r["fen"]),
                "trajectory":trajectory(engine,str(r["fen"])),
            })
    finally:
        engine.quit()

    stats={rule:evaluate_rule(rule,source) for rule in RULES}
    surviving=[rule for rule,st in stats.items() if int(st["mismatches"])==0]
    status=(
        "HARD_RESIDUAL_LEAVES_PROGRESSIVE_RULES"
        if surviving else
        "HARD_RESIDUAL_FALSIFIES_ALL_PROGRESSIVE_RULES"
    )

    result={
        "schema":SCHEMA,
        "status":status,
        "hard_positions":len(source),
        "surviving_zero_mismatch_rules":surviving,
        "rules":stats,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

    print(f"CRYSTAL_CHESS_PROGRESSIVE_HARD_FALSIFIER_V47H={status}")
    for rule,st in stats.items():
        print(
            f"{rule}: mismatches={st['mismatches']} "
            f"early={st['early_stop_ratio']:.8f} "
            f"mean_nodes={st['mean_nodes']:.2f} "
            f"reduction={st['node_reduction_ratio']:.8f}"
        )
    print(f"surviving={surviving}")
    print(f"artifact={args.output}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
