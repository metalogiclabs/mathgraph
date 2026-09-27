#!/usr/bin/env python3
"""Crystal Chess V10: exact DTZ certificate compiler across KXvK piece families."""

from __future__ import annotations
import argparse, json, platform, sys, time
from collections import Counter
from pathlib import Path

import chess, chess.syzygy, numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_goal_certificate_v3 import file_sha256, tree_summary
from crystal_chess_dtz_certificate_v6 import probe_dtz_safe
from crystal_chess_kpvk_v0 import BASE_CRYSTAL_AUTHORITY, probe_wdl

SCHEMA="mathgraph.crystal-chess.kxvk-dtz-family.v10"

PIECE_MAP={"Q":chess.QUEEN,"R":chess.ROOK,"B":chess.BISHOP,"N":chess.KNIGHT}

def make_board(wk,bk,x,turn,piece_type):
    b=chess.Board(None); b.turn=turn; b.castling_rights=chess.BB_EMPTY
    b.ep_square=None; b.halfmove_clock=0; b.fullmove_number=1
    b.set_piece_at(wk,chess.Piece(chess.KING,chess.WHITE))
    b.set_piece_at(bk,chess.Piece(chess.KING,chess.BLACK))
    b.set_piece_at(x,chess.Piece(piece_type,chess.WHITE))
    return b

def cheb(a,b):
    return max(abs(chess.square_file(a)-chess.square_file(b)),abs(chess.square_rank(a)-chess.square_rank(b)))
def man(a,b):
    return abs(chess.square_file(a)-chess.square_file(b))+abs(chess.square_rank(a)-chess.square_rank(b))
def edge(s):
    f=chess.square_file(s);r=chess.square_rank(s);return min(f,7-f,r,7-r)

def features(wk,bk,x,turn):
    fw,rw=chess.square_file(wk),chess.square_rank(wk)
    fb,rb=chess.square_file(bk),chess.square_rank(bk)
    fx,rx=chess.square_file(x),chess.square_rank(x)
    return (
        int(turn),fw,rw,fb,rb,fx,rx,
        fw-fx,rw-rx,fb-fx,rb-rx,
        abs(fw-fx),abs(rw-rx),abs(fb-fx),abs(rb-rx),
        fw-fb,rw-rb,abs(fw-fb),abs(rw-rb),
        cheb(wk,x),cheb(bk,x),cheb(wk,bk),
        man(wk,x),man(bk,x),man(wk,bk),
        edge(wk),edge(bk),edge(x),
        int(fw==fx),int(fb==fx),int(rw==rx),int(rb==rx),
        int(fw==fb),int(rw==rb),
    )

def role(board,move,piece_letter):
    p=board.piece_at(move.from_square)
    ff,fr=chess.square_file(move.from_square),chess.square_rank(move.from_square)
    tf,tr=chess.square_file(move.to_square),chess.square_rank(move.to_square)
    tag="K" if p and p.piece_type==chess.KING else piece_letter
    return f"{tag}:{tf-ff:+d},{tr-fr:+d}"

def optimal_roles(board,root_wdl,root_dtz,tb,wdl_cache,dtz_cache,piece_letter):
    roles=set(); legal=0
    if root_wdl not in (-2,0,2):
        raise AssertionError(f"unexpected cursed/blessed K{piece_letter}vK WDL={root_wdl}")
    for m in board.legal_moves:
        legal+=1
        c=board.copy(stack=False);c.push(m)
        cw=probe_wdl(tb,c,wdl_cache)
        if -cw!=root_wdl: continue
        if root_wdl==0:
            cand=0
        elif c.halfmove_clock==0:
            cand=1 if root_wdl==2 else -1
        else:
            cd=probe_dtz_safe(tb,c,dtz_cache)
            cand=-cd+(1 if root_wdl==2 else -1)
        if cand==root_dtz: roles.add(role(board,m,piece_letter))
    if legal==0:return ()
    if not roles: raise AssertionError((root_wdl,root_dtz,board.fen()))
    return tuple(sorted(roles))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--tablebase-dir",type=Path,required=True)
    ap.add_argument("--piece",choices=sorted(PIECE_MAP),required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args();started=time.time()
    letter=args.piece;ptype=PIECE_MAP[letter]
    files=sorted(args.tablebase_dir.glob("*.rtb*"))
    manifest=[{"name":p.name,"size":p.stat().st_size,"sha256":file_sha256(p)} for p in files]
    wcache={};dcache={};rows=[];role_sets=[];wdls=Counter();dtzs=Counter();terminal=0

    with chess.syzygy.open_tablebase(str(args.tablebase_dir),load_wdl=True,load_dtz=True) as tb:
        for x in chess.SQUARES:
            for wk in chess.SQUARES:
                if wk==x:continue
                for bk in chess.SQUARES:
                    if bk in (wk,x):continue
                    for turn in (False,True):
                        b=make_board(wk,bk,x,turn,ptype)
                        if not b.is_valid():continue
                        rw=probe_wdl(tb,b,wcache);rd=probe_dtz_safe(tb,b,dcache)
                        wdls[rw]+=1;dtzs[rd]+=1
                        rs=optimal_roles(b,rw,rd,tb,wcache,dcache,letter)
                        rows.append(features(wk,bk,x,turn));role_sets.append(rs)
                        if not rs:terminal+=1

    nonterm=[i for i,r in enumerate(role_sets) if r]
    freq=Counter()
    for i in nonterm:freq.update(role_sets[i])
    ranking={r:k for k,(r,_n) in enumerate(sorted(freq.items(),key=lambda kv:(-kv[1],kv[0])))}
    labels=[min(role_sets[i],key=lambda r:(ranking[r],r)) for i in nonterm]
    X=np.asarray(rows,dtype=np.int16)
    tree=DecisionTreeClassifier(criterion="entropy",splitter="best",random_state=0)
    tree.fit(X[nonterm],labels)
    pred=[str(x) for x in tree.predict(X[nonterm])]
    bad=[(i,p,role_sets[i]) for i,p in zip(nonterm,pred) if p not in role_sets[i]]
    if bad: raise AssertionError(bad[:20])
    summary=tree_summary(tree)
    result={
      "schema":SCHEMA,"status":"WARRANTED_BOUNDED_KXVK_DTZ_CERTIFICATE",
      "base_crystal_authority":BASE_CRYSTAL_AUTHORITY,"piece":letter,
      "authority":{"kind":"Syzygy WDL+DTZ","tablebase_files":manifest},
      "coverage":{"states":len(rows),"nonterminal":len(nonterm),"terminal":terminal,
                  "wdl_distribution":{str(k):v for k,v in sorted(wdls.items())},
                  "distinct_roles":len({r for rs in role_sets for r in rs})},
      "policy":{"tree":summary,"audit_invalid":len(bad),"compression_vs_state_table":len(nonterm)/int(summary["leaves"]),
                "states_per_leaf":len(nonterm)/int(summary["leaves"])},
      "cache":{"wdl":len(wcache),"dtz":len(dcache)},
      "environment":{"python":sys.version,"platform":platform.platform(),"numpy":np.__version__},
      "elapsed_seconds":time.time()-started
    }
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_PIECE_FAMILY_V10=PASS")
    print(f"piece={letter} states={len(rows)} nonterminal={len(nonterm)} roles={result['coverage']['distinct_roles']}")
    print(f"leaves={summary['leaves']} depth={summary['max_depth']} compression={result['policy']['compression_vs_state_table']:.3f}x")
    print(f"artifact={args.output}")
    return 0

if __name__=="__main__":raise SystemExit(main())
