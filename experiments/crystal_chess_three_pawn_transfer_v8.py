#!/usr/bin/env python3
"""Crystal Chess V8: frozen KPvK capability -> exact KPPPvK transfer.

No KPPPvK labels enter acquisition. The KPvK symbolic capability is frozen,
then instantiated independently against each of three pawns in a deterministic
K+3P vs K sample. Every reported success is exact Syzygy WDL checked.
"""

from __future__ import annotations
import argparse, hashlib, json, platform, random, sys, time
from collections import Counter
from pathlib import Path

import chess, chess.syzygy, numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY, PROTECTED_INTERFACE, coordinate_feature_bank,
    enumerate_records, make_kpvk, probe_wdl
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles, file_sha256, optimal_roles, tree_summary
)
from crystal_chess_richer_transfer_v5 import (
    canonical_feature_row, reflect_role, role_is_optimal_for_anchor
)

SCHEMA="mathgraph.crystal-chess.kpvk-to-kpppvk-transfer.v8"
V5_AUTHORITY="metalogiclabs/mathgraph@0b8da1aee8ffecfb351c0211dc8513631fd106cd"


def make_kpppvk(wk,bk,pawns,turn):
    b=chess.Board(None); b.turn=turn; b.castling_rights=chess.BB_EMPTY
    b.ep_square=None; b.halfmove_clock=0; b.fullmove_number=1
    b.set_piece_at(wk,chess.Piece(chess.KING,chess.WHITE))
    b.set_piece_at(bk,chess.Piece(chess.KING,chess.BLACK))
    for p in pawns: b.set_piece_at(p,chess.Piece(chess.PAWN,chess.WHITE))
    return b


def sample_states(count,seed):
    rng=random.Random(seed)
    ps=[chess.square(f,r) for f in range(8) for r in range(1,6)]
    seen=set(); out=[]; attempts=0
    while len(out)<count:
        attempts+=1
        if attempts>count*150: raise RuntimeError("sample construction failed")
        pawns=tuple(sorted(rng.sample(ps,3)))
        occupied=set(pawns)
        wk=rng.randrange(64)
        if wk in occupied: continue
        bk=rng.randrange(64)
        if bk in occupied or bk==wk: continue
        turn=bool(rng.getrandbits(1))
        key=(wk,bk,*pawns,turn)
        if key in seen: continue
        b=make_kpppvk(wk,bk,pawns,turn)
        if not b.is_valid(): continue
        seen.add(key); out.append((wk,bk,pawns,turn))
    return out


def exact_optimal_moves(board,root_wdl,tb,cache):
    scored=[]; best=-99
    for m in board.legal_moves:
        c=board.copy(stack=False); c.push(m)
        val=-probe_wdl(tb,c,cache)
        scored.append((m,val)); best=max(best,val)
    if not scored: return []
    if best!=root_wdl:
        raise AssertionError((root_wdl,best,board.fen()))
    return [m for m,v in scored if v==root_wdl]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir",type=Path,required=True)
    ap.add_argument("--sample-size",type=int,default=100000)
    ap.add_argument("--seed",type=int,default=20260930)
    ap.add_argument("--output",type=Path,default=Path("crystal_chess_three_pawn_v8.json"))
    args=ap.parse_args(); started=time.time()

    files=sorted(args.tablebase_dir.glob("*.rtbw"))
    names={p.name for p in files}
    if "KPPPvK.rtbw" not in names or "KPPvK.rtbw" not in names:
        raise SystemExit(f"required tablebase missing: {sorted(names)}")
    manifest=[{"name":p.name,"size":p.stat().st_size,"sha256":file_sha256(p)} for p in files]

    bank=coordinate_feature_bank(); feature_fns=[fn for _,fn in bank]
    cache={}
    with chess.syzygy.open_tablebase(str(args.tablebase_dir),load_wdl=True,load_dtz=False) as tb:
        recs,enum=enumerate_records(tb,cache,feature_fns)
        role_sets=[]; nonterm=[]
        for i,r in enumerate(recs):
            b=make_kpvk(r.wk,r.bk,r.pawn,r.turn)
            roles=optimal_roles(b,r.wdl,tb,cache); role_sets.append(roles)
            if roles: nonterm.append(i)
        labels,freq=choose_preferred_roles(role_sets,nonterm)
        X=np.asarray([r.features for r in recs],dtype=np.int16)
        policy=DecisionTreeClassifier(criterion="entropy",splitter="best",random_state=0)
        policy.fit(X[nonterm],[labels[i] for i in nonterm])
        summary=tree_summary(policy)
        default_role=sorted(freq.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]

        sample=sample_states(args.sample_size,args.seed)
        states_with_moves=terminal=any_success=first_success=default_success=0
        by_turn={"white":[0,0],"black":[0,0]}; failures=[]; wdl=Counter()
        for wk,bk,pawns,turn in sample:
            board=make_kpppvk(wk,bk,pawns,turn)
            root=probe_wdl(tb,board,cache); wdl[root]+=1
            optimal=exact_optimal_moves(board,root,tb,cache)
            if not optimal: terminal+=1; continue
            states_with_moves+=1
            roles=[]; defaults=[]
            for anchor in pawns:
                row,refl=canonical_feature_row(wk,bk,anchor,turn,feature_fns)
                pr=str(policy.predict(np.asarray([row],dtype=np.int16))[0])
                roles.append(reflect_role(pr) if refl else pr)
                defaults.append(reflect_role(default_role) if refl else default_role)
            hits=[role_is_optimal_for_anchor(role,anchor,optimal,board) for role,anchor in zip(roles,pawns)]
            dhits=[role_is_optimal_for_anchor(role,anchor,optimal,board) for role,anchor in zip(defaults,pawns)]
            ok=any(hits); any_success+=int(ok); first_success+=int(hits[0]); default_success+=int(any(dhits))
            bucket="white" if turn else "black"; by_turn[bucket][1]+=1; by_turn[bucket][0]+=int(ok)
            if not ok and len(failures)<30:
                failures.append({"fen":board.fen(),"root_wdl":root,"anchors":[chess.square_name(p) for p in pawns],
                    "predicted_roles":roles,"optimal_moves":[m.uci() for m in optimal]})

    ratio=any_success/states_with_moves; first=first_success/states_with_moves; base=default_success/states_with_moves
    result={
        "schema":SCHEMA,"status":"WARRANTED_BOUNDED_PROSPECTIVE_KPVK_TO_KPPPVK_TRANSFER",
        "base_crystal_authority":BASE_CRYSTAL_AUTHORITY,"v5_authority":V5_AUTHORITY,
        "protected_interface":PROTECTED_INTERFACE,
        "method":{"acquisition_material":"KPvK only","evaluation_material":"KPPPvK only","evaluation_labels_used_in_acquisition":0,
                  "adapter":"instantiate frozen single-pawn capability independently against each of three pawns"},
        "authority":{"kind":"Syzygy WDL","tablebase_files":manifest},
        "frozen_capability":{"tree":summary,"default_role":default_role},
        "sample":{"seed":args.seed,"requested":args.sample_size,"nonterminal":states_with_moves,"terminal":terminal,
                  "wdl_distribution":{str(k):v for k,v in sorted(wdl.items())}},
        "transfer":{"any_anchor_success":any_success,"any_anchor_ratio":ratio,"first_anchor_success":first_success,
                    "first_anchor_ratio":first,"default_any_success":default_success,"default_any_ratio":base,
                    "absolute_gain_over_default":ratio-base,
                    "success_by_turn":{k:{"success":v[0],"states":v[1],"ratio":v[0]/v[1] if v[1] else 1.0} for k,v in by_turn.items()},
                    "failure_examples":failures},
        "epistemic_boundary":{"warranted_if_green":["KPvK policy frozen before KPPPvK evaluation","every success exact Syzygy WDL checked",
                                                   "ratio applies only to deterministic declared sample"],
                              "unknown":["complete KPPPvK coverage","further richer material","general chess solution"]},
        "cache":{"wdl_positions":len(cache)},"environment":{"python":sys.version,"platform":platform.platform(),"numpy":np.__version__},
        "elapsed_seconds":time.time()-started
    }
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_THREE_PAWN_TRANSFER_V8=PASS")
    print(f"nonterminal={states_with_moves} any={any_success} ratio={ratio:.6f}")
    print(f"first={first_success} ratio={first:.6f} default={default_success} ratio={base:.6f} gain={ratio-base:.6f}")
    print(f"artifact={args.output}")
    return 0

if __name__=="__main__": raise SystemExit(main())
