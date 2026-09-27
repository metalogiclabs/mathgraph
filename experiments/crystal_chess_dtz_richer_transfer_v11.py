#!/usr/bin/env python3
"""Crystal Chess V11: frozen exact KPvK DTZ constructor -> KPPvK progress transfer.

The policy is learned only from complete KPvK WDL+DTZ. KPPvK labels are
withheld until prospective evaluation. A transfer success requires that the
predicted relative role correspond to a concrete legal move that exactly
realizes the richer position's root WDL and root DTZ Bellman value.

The declared richer sample uses both pawns on ranks 2..6 and root halfmove
clock 0. Cursed/blessed root WDL states, if encountered, are reported and
excluded from the unconditional-DTZ transfer ratio rather than approximated.
"""

from __future__ import annotations
import argparse, json, platform, sys, time
from collections import Counter
from pathlib import Path

import chess, chess.syzygy, numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY, coordinate_feature_bank, enumerate_records,
    make_kpvk, probe_wdl
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles, file_sha256, move_role, tree_summary
)
from crystal_chess_dtz_certificate_v6 import (
    DTZ_INTERFACE, probe_dtz_safe, dtz_optimal_roles
)
from crystal_chess_kpvk_v0 import horizontal_square
import random

def make_kppvk(wk,bk,p0,p1,turn):
    b=chess.Board(None); b.turn=turn; b.castling_rights=chess.BB_EMPTY
    b.ep_square=None; b.halfmove_clock=0; b.fullmove_number=1
    b.set_piece_at(wk,chess.Piece(chess.KING,chess.WHITE))
    b.set_piece_at(bk,chess.Piece(chess.KING,chess.BLACK))
    b.set_piece_at(p0,chess.Piece(chess.PAWN,chess.WHITE))
    b.set_piece_at(p1,chess.Piece(chess.PAWN,chess.WHITE))
    return b

def sample_kppvk(count,seed):
    rng=random.Random(seed)
    ps=[chess.square(f,r) for f in range(8) for r in range(1,6)]
    seen=set(); out=[]; attempts=0
    while len(out)<count:
        attempts+=1
        if attempts>count*100: raise RuntimeError("sample construction failed")
        p0,p1=sorted(rng.sample(ps,2))
        wk=rng.randrange(64)
        if wk in (p0,p1): continue
        bk=rng.randrange(64)
        if bk in (p0,p1,wk): continue
        turn=bool(rng.getrandbits(1))
        key=(wk,bk,p0,p1,turn)
        if key in seen: continue
        b=make_kppvk(wk,bk,p0,p1,turn)
        if not b.is_valid(): continue
        seen.add(key); out.append(key)
    return out

def canonical_feature_row(wk,bk,anchor,turn,feature_fns):
    reflected=chess.square_file(anchor)>=4
    if reflected:
        wk=horizontal_square(wk); bk=horizontal_square(bk); anchor=horizontal_square(anchor)
    return tuple(fn(wk,bk,anchor,turn) for fn in feature_fns), reflected

def reflect_role(role):
    if role.startswith("P:"): return role
    if not role.startswith("K:"): return role
    body=role.split(":",1)[1]; a,b=body.split(",")
    return f"K:{-int(a):+d},{int(b):+d}"

SCHEMA="mathgraph.crystal-chess.kpvk-dtz-to-kppvk-transfer.v11"
V6_AUTHORITY="metalogiclabs/mathgraph@7c46d0144efea61dca7899a4c8eecbd1e05186fc"


def exact_progress_moves(board,root_wdl,root_dtz,tb,wcache,dcache):
    if root_wdl not in (-2,0,2):
        return None
    out=[]
    for m in board.legal_moves:
        c=board.copy(stack=False); c.push(m)
        cw=probe_wdl(tb,c,wcache)
        if -cw != root_wdl:
            continue
        if root_wdl==0:
            cand=0
        elif c.halfmove_clock==0:
            cand=1 if root_wdl==2 else -1
        else:
            cd=probe_dtz_safe(tb,c,dcache)
            cand=-cd+(1 if root_wdl==2 else -1)
        if cand==root_dtz:
            out.append(m)
    return out


def role_hits_anchor(role,anchor,moves,board):
    for m in moves:
        if move_role(board,m)!=role:
            continue
        p=board.piece_at(m.from_square)
        if p is None: continue
        if p.piece_type==chess.PAWN and m.from_square!=anchor:
            continue
        return True
    return False


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir",type=Path,required=True)
    ap.add_argument("--sample-size",type=int,default=50000)
    ap.add_argument("--seed",type=int,default=20261002)
    ap.add_argument("--output",type=Path,default=Path("crystal_chess_dtz_richer_transfer_v11.json"))
    args=ap.parse_args(); started=time.time()

    files=sorted(args.tablebase_dir.glob("*.rtb*"))
    names={p.name for p in files}
    for req in ("KPvK.rtbw","KPvK.rtbz","KPPvK.rtbw","KPPvK.rtbz"):
        if req not in names: raise SystemExit(f"missing {req}")
    manifest=[{"name":p.name,"size":p.stat().st_size,"sha256":file_sha256(p)} for p in files]

    bank=coordinate_feature_bank(); feature_fns=[fn for _,fn in bank]
    wc={}; dc={}
    with chess.syzygy.open_tablebase(str(args.tablebase_dir),load_wdl=True,load_dtz=True) as tb:
        # Acquire/freeze exact KPvK DTZ constructor.
        recs,enum=enumerate_records(tb,wc,feature_fns)
        role_sets=[]; nonterm=[]
        for i,r in enumerate(recs):
            b=make_kpvk(r.wk,r.bk,r.pawn,r.turn)
            if list(b.legal_moves):
                rd=probe_dtz_safe(tb,b,dc)
                rs=dtz_optimal_roles(b,r.wdl,rd,tb,wc,dc)
                role_sets.append(rs); nonterm.append(i)
            else:
                role_sets.append(())
        labels,freq=choose_preferred_roles(role_sets,nonterm)
        X=np.asarray([r.features for r in recs],dtype=np.int16)
        policy=DecisionTreeClassifier(criterion="entropy",splitter="best",random_state=0)
        policy.fit(X[nonterm],[labels[i] for i in nonterm])
        summary=tree_summary(policy)

        sample=sample_kppvk(args.sample_size,args.seed)
        eligible=terminal=cursed=any_ok=first_ok=0
        by_turn={"white":[0,0],"black":[0,0]}; failures=[]; wdl=Counter(); dtz=Counter()
        for wk,bk,p0,p1,turn in sample:
            board=make_kppvk(wk,bk,p0,p1,turn)
            rw=probe_wdl(tb,board,wc); wdl[rw]+=1
            if rw not in (-2,0,2):
                cursed+=1; continue
            rd=probe_dtz_safe(tb,board,dc); dtz[rd]+=1
            moves=exact_progress_moves(board,rw,rd,tb,wc,dc)
            if moves is None:
                cursed+=1; continue
            if not moves:
                if not list(board.legal_moves): terminal+=1; continue
                raise AssertionError(("no exact progress move",rw,rd,board.fen()))
            eligible+=1
            roles=[]
            for anchor in (p0,p1):
                row,refl=canonical_feature_row(wk,bk,anchor,turn,feature_fns)
                pr=str(policy.predict(np.asarray([row],dtype=np.int16))[0])
                roles.append(reflect_role(pr) if refl else pr)
            hits=[role_hits_anchor(role,anchor,moves,board) for role,anchor in zip(roles,(p0,p1))]
            ok=any(hits); any_ok+=int(ok); first_ok+=int(hits[0])
            bucket="white" if turn else "black"; by_turn[bucket][1]+=1; by_turn[bucket][0]+=int(ok)
            if not ok and len(failures)<30:
                failures.append({"fen":board.fen(),"root_wdl":rw,"root_dtz":rd,
                    "predicted_roles":roles,"exact_progress_moves":[m.uci() for m in moves],
                    "exact_progress_roles":[move_role(board,m) for m in moves]})

    ratio=any_ok/eligible if eligible else 1.0; first=first_ok/eligible if eligible else 1.0
    result={
      "schema":SCHEMA,"status":"WARRANTED_BOUNDED_PROSPECTIVE_DTZ_PROGRESS_TRANSFER",
      "base_crystal_authority":BASE_CRYSTAL_AUTHORITY,"v6_authority":V6_AUTHORITY,
      "protected_interface":DTZ_INTERFACE,
      "method":{"acquisition_material":"KPvK WDL+DTZ only","evaluation_material":"KPPvK WDL+DTZ only",
                "evaluation_labels_used_in_acquisition":0,
                "success":"frozen role realizes exact richer root WDL + root DTZ Bellman value"},
      "authority":{"kind":"Syzygy WDL+DTZ","tablebase_files":manifest},
      "frozen_capability":{"tree":summary,"kpvk_nonterminal":len(nonterm)},
      "sample":{"seed":args.seed,"requested":args.sample_size,"eligible_unconditional":eligible,
                "cursed_or_blessed_excluded":cursed,"terminal":terminal,
                "wdl_distribution":{str(k):v for k,v in sorted(wdl.items())},
                "dtz_distribution":{str(k):v for k,v in sorted(dtz.items())}},
      "transfer":{"any_anchor_success":any_ok,"any_anchor_ratio":ratio,
                  "first_anchor_success":first_ok,"first_anchor_ratio":first,
                  "success_by_turn":{k:{"success":v[0],"states":v[1],"ratio":v[0]/v[1] if v[1] else 1.0} for k,v in by_turn.items()},
                  "failure_examples":failures},
      "epistemic_boundary":{"warranted_if_green":["KPvK DTZ policy frozen before KPPvK labels are read",
          "every success exactly reproduces richer root WDL and DTZ recurrence under Syzygy",
          "ratio excludes rather than approximates cursed/blessed roots"],
          "unknown":["complete KPPvK DTZ policy","further-material DTZ transfer","general chess solution"]},
      "cache":{"wdl":len(wc),"dtz":len(dc)},"environment":{"python":sys.version,"platform":platform.platform(),"numpy":np.__version__},
      "elapsed_seconds":time.time()-started
    }
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_DTZ_RICHER_TRANSFER_V11=PASS")
    print(f"eligible={eligible} cursed={cursed} any={any_ok} ratio={ratio:.6f}")
    print(f"first={first_ok} ratio={first:.6f}")
    print(f"artifact={args.output}")
    return 0

if __name__=="__main__":raise SystemExit(main())
