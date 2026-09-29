#!/usr/bin/env python3
"""Crystal Chess V50: Stockfish-internal root-state trace on the exact V47 residual.

The Stockfish binary is patched diagnostically to emit one "crystal_root" line
after each completed iterative-deepening iteration. Search remains node-limited,
single-PV, Threads=1; the patch does not alter move selection or pruning.

V50 replays only the exact 11 V47 last3_move_pv3 source mismatches and records:
root best move, score/average/previous score, effort share, best-move age,
cumulative best-move changes, search-again count, fail-high recovery and
inexactness.

This is diagnostic-only. No stopping rule is learned or deployed here.
"""

from __future__ import annotations
import argparse, json
from pathlib import Path
from statistics import median
from typing import Any
from crystal_chess_search_sufficiency_v25 import STOCKFISH_PIN, UCIStockfish

SCHEMA="mathgraph.crystal-chess.root-internal-trace.v50"
V47_RUN=36523379587
AUTHORITY_NODES=100000

def residuals(d):
    if d.get("schema")!="mathgraph.crystal-chess.progressive-stopping.v47":
        raise AssertionError(("schema",d.get("schema")))
    rows=list(d["source"]["rules"]["last3_move_pv3"]["mismatch_examples"])
    if len(rows)!=11: raise AssertionError(("residual",len(rows)))
    return rows

def trace(engine: UCIStockfish, fen: str):
    engine.clear_hash()
    engine.send("setoption name MultiPV value 1")
    engine.send("position fen "+fen)
    engine.send(f"go nodes {AUTHORITY_NODES}")
    lines=engine.read_until("bestmove")
    best=lines[-1].split()[1]
    out=[]
    for line in lines[:-1]:
        if not line.startswith("info string crystal_root "): continue
        t=line.split()[3:]  # after info string crystal_root
        row={}
        for i in range(0,len(t)-1,2):
            k=t[i]; v=t[i+1]
            if k=="best": row[k]=v
            elif k=="changes": row[k]=float(v)
            else:
                try: row[k]=int(v)
                except ValueError: row[k]=v
        out.append(row)
    return best,out

def authority_lock(rows,authority):
    for i,r in enumerate(rows):
        if r.get("best")!=authority: continue
        if all(x.get("best")==authority for x in rows[i:]):
            return i
    return None

def longest_wrong(rows,authority):
    best=(0,None,None,None)
    i=0
    while i<len(rows):
        m=rows[i].get("best")
        j=i+1
        while j<len(rows) and rows[j].get("best")==m: j+=1
        if m!=authority and j-i>best[0]:
            best=(j-i,m,i,j-1)
        i=j
    return best

def metrics(row):
    score=int(row.get("score",0)); avg=int(row.get("avg",0)); prev=int(row.get("prev",0))
    mss=int(row.get("mss",0))
    return {
      "nodes":int(row.get("nodes",0)),
      "depth":int(row.get("depth",0)),
      "best":row.get("best"),
      "score":score,"avg":avg,"prev":prev,
      "score_minus_avg":score-avg,
      "score_minus_prev":score-prev,
      "mss":mss,
      "effort":int(row.get("effort",0)),
      "effortpct":int(row.get("effortpct",0)),
      "best_age":int(row.get("bestAge",0)),
      "changes":float(row.get("changes",0.0)),
      "search_again":int(row.get("searchAgain",0)),
      "fail_high_recovery":int(row.get("failHighRec",0)),
      "inexact":int(row.get("inexact",0)),
    }

def summarize(rows,key):
    vals=[float(r[key]) for r in rows if key in r]
    if not vals: return None
    return {"min":min(vals),"median":median(vals),"max":max(vals)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stockfish",type=Path,required=True)
    ap.add_argument("--v47-result",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    src=residuals(json.loads(a.v47_result.read_text()))
    eng=UCIStockfish(a.stockfish)
    rows=[]
    try:
        for s in src:
            authority=str(s["authority_bestmove"])
            best,tr=trace(eng,str(s["fen"]))
            if best!=authority: raise AssertionError(("patched behavior drift",s["fen"],authority,best))
            if not tr: raise AssertionError(("missing crystal trace",s["fen"]))
            li=authority_lock(tr,authority)
            plat=longest_wrong(tr,authority)
            wrong_end=metrics(tr[plat[3]]) if plat[3] is not None else None
            locked=metrics(tr[li]) if li is not None else None
            rows.append({
              "generation":s["generation"],"fen":s["fen"],"authority":authority,
              "trace":tr,
              "authority_lock_index":li,
              "authority_lock":locked,
              "longest_wrong_plateau":{
                "length_depths":plat[0],"move":plat[1],
                "start":None if plat[2] is None else metrics(tr[plat[2]]),
                "end":wrong_end
              }
            })
    finally:
        eng.quit()

    wrong=[r["longest_wrong_plateau"]["end"] for r in rows if r["longest_wrong_plateau"]["end"]]
    locked=[r["authority_lock"] for r in rows if r["authority_lock"]]
    keys=["nodes","depth","score_minus_avg","score_minus_prev","effortpct","best_age","changes","search_again","fail_high_recovery","inexact"]
    result={
      "schema":SCHEMA,"status":"ROOT_INTERNAL_TRACE_COMPLETE","stockfish_pin":STOCKFISH_PIN,
      "v47_run":V47_RUN,"authority_nodes":AUTHORITY_NODES,"residual_count":len(rows),
      "wrong_plateau_end_summary":{k:summarize(wrong,k) for k in keys},
      "authority_lock_summary":{k:summarize(locked,k) for k in keys},
      "rows":rows,
      "epistemic_boundary":{
        "warranted":[
          "diagnostic patch is required to preserve final bestmove identity on all 11 frozen residuals",
          "only exact V47 source mismatches are inspected",
          "no internal-state threshold or stopping rule is selected"
        ],
        "unknown":["globally safe internal stopping rule","node or Elo gain from internal control"]
      }
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_ROOT_INTERNAL_TRACE_V50=ROOT_INTERNAL_TRACE_COMPLETE")
    print("wrong_end",result["wrong_plateau_end_summary"])
    print("authority_lock",result["authority_lock_summary"])
    for r in rows:
        w=r["longest_wrong_plateau"]["end"]; q=r["authority_lock"]
        print(f"authority={r['authority']} wrong={r['longest_wrong_plateau']['move']} wrong_end={None if w is None else (w['depth'],w['nodes'],w['effortpct'],w['best_age'],w['changes'])} lock={None if q is None else (q['depth'],q['nodes'],q['effortpct'],q['best_age'],q['changes'])} fen={r['fen']}")
    print(f"artifact={a.output}")
    return 0
if __name__=="__main__": raise SystemExit(main())
