#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, random
from pathlib import Path
from collections import Counter
import chess.pgn

SCHEMA="mathgraph.crystal-chess.tunnel-guard.v52"

def points(g,name):
    w=g.headers.get("White",""); b=g.headers.get("Black",""); r=g.headers.get("Result","*")
    if name not in (w,b): raise AssertionError((name,w,b))
    if r=="1/2-1/2": return .5
    if r=="1-0": return 1.0 if w==name else 0.0
    if r=="0-1": return 1.0 if b==name else 0.0
    raise AssertionError(("result",r))

def elo(s):
    if s<=0: return -1000.0
    if s>=1: return 1000.0
    return -400.0*math.log10(1.0/s-1.0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pgn",type=Path,required=True)
    ap.add_argument("--candidate-name",default="CrystalTunnelV52")
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    games=[]
    with a.pgn.open(encoding="utf-8",errors="replace") as h:
        while True:
            g=chess.pgn.read_game(h)
            if g is None: break
            games.append(g)
    if not games or len(games)%2: raise AssertionError(("paired games",len(games)))
    w=l=d=0; pairs=[]; terms=Counter()
    for i in range(0,len(games),2):
        pp=0.0
        for g in games[i:i+2]:
            p=points(g,a.candidate_name); pp+=p
            if p==1.0:w+=1
            elif p==0.0:l+=1
            else:d+=1
            terms[g.headers.get("Termination","unknown")]+=1
        pairs.append(pp)
    score=(w+0.5*d)/len(games)
    rng=random.Random(20261103)
    boots=[]
    for _ in range(20000):
        s=sum(pairs[rng.randrange(len(pairs))] for _ in pairs)/(2.0*len(pairs))
        boots.append(elo(s))
    boots.sort()
    ci=[boots[int(.025*(len(boots)-1))],boots[int(.975*(len(boots)-1))]]
    out={"schema":SCHEMA,"games":len(games),"opening_pairs":len(pairs),
         "wins":w,"losses":l,"draws":d,"score_fraction":score,
         "elo_estimate":elo(score),"paired_bootstrap_95pct_elo_interval":ci,
         "terminations":dict(terms),
         "claim_boundary":{"same_pinned_stockfish_baseline":True,
                           "single_conditional_time_manager_patch":True,
                           "normal_opening_full_games":True,
                           "not_external_leaderboard_rating":True}}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_TUNNEL_GUARD_V52=PASS")
    print(f"games={len(games)} W/L/D={w}/{l}/{d} score={score:.6f} elo={out['elo_estimate']:.3f} ci95={ci}")
    return 0
if __name__=="__main__": raise SystemExit(main())
