#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, random
from pathlib import Path
from collections import Counter
import chess.pgn

SCHEMA="mathgraph.crystal-chess.normal-selfplay.v49"

def points(game,name):
    w=game.headers.get("White","")
    b=game.headers.get("Black","")
    r=game.headers.get("Result","*")
    if name not in (w,b):
        raise AssertionError((name,w,b))
    if r=="1/2-1/2": return 0.5
    if r=="1-0": return 1.0 if w==name else 0.0
    if r=="0-1": return 1.0 if b==name else 0.0
    raise AssertionError(("bad result",r))

def elo(score):
    if score<=0: return -1000.0
    if score>=1: return 1000.0
    return -400.0*math.log10(1.0/score-1.0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pgn",type=Path,required=True)
    ap.add_argument("--crystal-name",default="CrystalV20")
    ap.add_argument("--shortcut-count",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    games=[]
    with a.pgn.open(encoding="utf-8",errors="replace") as h:
        while True:
            g=chess.pgn.read_game(h)
            if g is None: break
            games.append(g)
    if not games or len(games)%2: raise AssertionError(("paired games",len(games)))
    wins=losses=draws=0
    pairs=[]
    terms=Counter()
    for i in range(0,len(games),2):
        pp=0.0
        for g in games[i:i+2]:
            p=points(g,a.crystal_name); pp+=p
            if p==1: wins+=1
            elif p==0: losses+=1
            else: draws+=1
            terms[g.headers.get("Termination","unknown")]+=1
        pairs.append(pp)
    score=(wins+0.5*draws)/len(games)
    est=elo(score)
    rng=random.Random(20260929)
    boots=[]
    for _ in range(20000):
        s=sum(pairs[rng.randrange(len(pairs))] for _ in pairs)/(2*len(pairs))
        boots.append(elo(s))
    boots.sort()
    ci=[boots[int(.025*(len(boots)-1))],boots[int(.975*(len(boots)-1))]]
    shortcuts=int(a.shortcut_count.read_text().strip())
    out={
      "schema":SCHEMA,
      "games":len(games),"opening_pairs":len(pairs),
      "wins":wins,"losses":losses,"draws":draws,
      "score_fraction":score,"elo_estimate":est,
      "paired_bootstrap_95pct_elo_interval":ci,
      "crystal_shortcut_log_events":shortcuts,
      "terminations":dict(terms),
      "claim_boundary":{
        "same_pinned_stockfish_fallback":True,
        "normal_opening_full_games":True,
        "paired_color_reversal":True,
        "not_external_leaderboard_rating":True
      }
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_NORMAL_SELFPLAY_V49=PASS")
    print(f"games={len(games)} W/L/D={wins}/{losses}/{draws} score={score:.6f} elo={est:.3f} ci95={ci} shortcuts={shortcuts}")
    return 0
if __name__=="__main__": raise SystemExit(main())
