#!/usr/bin/env python3
"""Crystal Chess V7: residual pair-geometry repair with prospective re-test.

Acquisition:
* Freeze the exact KPvK symbolic policy.
* Expose it to one deterministic 50k KPPvK sample (seed A).
* Preserve successful uses as BASE0/BASE1.
* Only where both single-pawn instantiations fail, acquire a repair action.
* Learn one guarded controller from pair geometry + frozen base outputs.

Qualification:
* Exact reclosure on acquisition sample.
* Prospective replay on an independent 100k KPPvK sample (seed B).
* Compare against the unchanged frozen KPvK capability.
* Empty-repair ablation is the base policy itself.

No seed-B KPPvK labels enter acquisition.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    horizontal_square,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    move_role,
    optimal_roles,
    tree_summary,
)
from crystal_chess_richer_transfer_v5 import (
    make_kppvk,
    sample_kppvk,
    exact_optimal_moves,
    canonical_feature_row,
    reflect_role,
    role_is_optimal_for_anchor,
)


SCHEMA = "mathgraph.crystal-chess.kppvk-pair-geometry.v7"
V5_AUTHORITY = (
    "metalogiclabs/mathgraph@0b8da1aee8ffecfb351c0211dc8513631fd106cd"
)
BASE0 = "<BASE0>"
BASE1 = "<BASE1>"


def pair_features(
    wk: int,
    bk: int,
    p0: int,
    p1: int,
    turn: bool,
    base0_role: str,
    base1_role: str,
    role_ids: dict[str, int],
) -> tuple[int, ...]:
    # Canonical unordered pawn pair.
    pawns = sorted((p0, p1), key=lambda s: (chess.square_file(s), chess.square_rank(s)))
    p0, p1 = pawns
    f0, r0 = chess.square_file(p0), chess.square_rank(p0)
    f1, r1 = chess.square_file(p1), chess.square_rank(p1)
    fw, rw = chess.square_file(wk), chess.square_rank(wk)
    fb, rb = chess.square_file(bk), chess.square_rank(bk)

    def cheb(a: int, b: int) -> int:
        return max(
            abs(chess.square_file(a) - chess.square_file(b)),
            abs(chess.square_rank(a) - chess.square_rank(b)),
        )

    def man(a: int, b: int) -> int:
        return abs(chess.square_file(a) - chess.square_file(b)) + abs(
            chess.square_rank(a) - chess.square_rank(b)
        )

    return (
        int(turn),
        fw, rw, fb, rb,
        f0, r0, f1, r1,
        f1 - f0, r1 - r0,
        abs(f1 - f0), abs(r1 - r0),
        int(f0 == f1),
        int(r0 == r1),
        int(abs(f1 - f0) == 1 and abs(r1 - r0) <= 1),
        min(r0, r1), max(r0, r1),
        7 - max(r0, r1), 7 - min(r0, r1),
        cheb(wk, p0), cheb(wk, p1),
        cheb(bk, p0), cheb(bk, p1),
        man(wk, p0), man(wk, p1),
        man(bk, p0), man(bk, p1),
        min(cheb(wk, p0), cheb(wk, p1)),
        max(cheb(wk, p0), cheb(wk, p1)),
        min(cheb(bk, p0), cheb(bk, p1)),
        max(cheb(bk, p0), cheb(bk, p1)),
        fw * 2 - (f0 + f1),
        rw * 2 - (r0 + r1),
        fb * 2 - (f0 + f1),
        rb * 2 - (r0 + r1),
        role_ids[base0_role],
        role_ids[base1_role],
        int(base0_role == base1_role),
    )


def explicit_action_label(
    board: chess.Board,
    move: chess.Move,
    pawns: tuple[int, int],
) -> str:
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("move without source piece")
    role = move_role(board, move)
    if piece.piece_type == chess.KING:
        return role
    if piece.piece_type == chess.PAWN:
        ordered = sorted(pawns, key=lambda s: (chess.square_file(s), chess.square_rank(s)))
        try:
            idx = ordered.index(move.from_square)
        except ValueError as exc:
            raise AssertionError("pawn move source not in pair") from exc
        return f"P{idx}:{role.split(':',1)[1]}"
    raise AssertionError(piece)


def label_is_optimal(
    label: str,
    board: chess.Board,
    pawns: tuple[int, int],
    optimal_moves: list[chess.Move],
    base_roles: tuple[str, str],
) -> bool:
    ordered = sorted(pawns, key=lambda s: (chess.square_file(s), chess.square_rank(s)))
    if label == BASE0:
        return role_is_optimal_for_anchor(base_roles[0], ordered[0], optimal_moves, board)
    if label == BASE1:
        return role_is_optimal_for_anchor(base_roles[1], ordered[1], optimal_moves, board)
    for move in optimal_moves:
        if explicit_action_label(board, move, tuple(ordered)) == label:
            return True
    return False


def frozen_base_roles(
    policy: DecisionTreeClassifier,
    feature_fns,
    wk: int,
    bk: int,
    pawns: tuple[int, int],
    turn: bool,
) -> tuple[str, str]:
    ordered = sorted(pawns, key=lambda s: (chess.square_file(s), chess.square_rank(s)))
    rows = []
    reflected = []
    for anchor in ordered:
        row, refl = canonical_feature_row(wk, bk, anchor, turn, feature_fns)
        rows.append(row)
        reflected.append(refl)
    pred = [str(x) for x in policy.predict(np.asarray(rows, dtype=np.int16))]
    return tuple(
        reflect_role(role) if refl else role
        for role, refl in zip(pred, reflected)
    )


def train_frozen_kpvk_policy(tablebase, feature_fns, wdl_cache):
    records, enumeration = enumerate_records(tablebase, wdl_cache, feature_fns)
    role_sets = []
    nonterminal = []
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        roles = optimal_roles(board, rec.wdl, tablebase, wdl_cache)
        role_sets.append(roles)
        if roles:
            nonterminal.append(i)
    labels, freq = choose_preferred_roles(role_sets, nonterminal)
    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    tree = DecisionTreeClassifier(criterion="entropy", splitter="best", random_state=0)
    tree.fit(X[nonterminal], [labels[i] for i in nonterminal])
    return tree, freq, records, nonterminal, enumeration


def acquire_rows(
    sample,
    tablebase,
    wdl_cache,
    policy,
    feature_fns,
    role_ids,
    learn_labels: bool,
    repair_ranking: dict[str, int] | None = None,
):
    rows = []
    labels = []
    base_success = 0
    residual = 0
    examples = []
    explicit_counter = Counter()

    # First pass when learning: collect explicit repair label frequencies.
    if learn_labels:
        pending = []
        for state in sample:
            wk, bk, p0, p1, turn = state
            board = make_kppvk(wk, bk, p0, p1, turn)
            root = probe_wdl(tablebase, board, wdl_cache)
            optimal = exact_optimal_moves(board, root, tablebase, wdl_cache)
            if not optimal:
                pending.append((state, board, optimal, ("",""), None))
                continue
            base_roles = frozen_base_roles(policy, feature_fns, wk, bk, (p0,p1), turn)
            ordered = tuple(sorted((p0,p1), key=lambda s:(chess.square_file(s),chess.square_rank(s))))
            hit0 = role_is_optimal_for_anchor(base_roles[0], ordered[0], optimal, board)
            hit1 = role_is_optimal_for_anchor(base_roles[1], ordered[1], optimal, board)
            if hit0:
                target = BASE0
            elif hit1:
                target = BASE1
            else:
                target = None
                residual += 1
                for move in optimal:
                    explicit_counter[explicit_action_label(board, move, ordered)] += 1
            pending.append((state, board, optimal, base_roles, target))

        repair_ranking = {
            label: rank
            for rank, (label, _n) in enumerate(
                sorted(explicit_counter.items(), key=lambda kv:(-kv[1],kv[0]))
            )
        }
        for state, board, optimal, base_roles, target in pending:
            wk,bk,p0,p1,turn=state
            if not optimal:
                continue
            ordered=tuple(sorted((p0,p1),key=lambda s:(chess.square_file(s),chess.square_rank(s))))
            if target is None:
                opts=[explicit_action_label(board,m,ordered) for m in optimal]
                target=min(opts,key=lambda x:(repair_ranking.get(x,10**9),x))
            else:
                base_success += 1
            rows.append(pair_features(wk,bk,*ordered,turn,*base_roles,role_ids))
            labels.append(target)
        return rows, labels, repair_ranking, {
            "base_success": base_success,
            "residual": residual,
            "explicit_frequency": dict(explicit_counter),
        }

    # Evaluation rows retain exact board metadata for later audit.
    metadata=[]
    for state in sample:
        wk,bk,p0,p1,turn=state
        board=make_kppvk(wk,bk,p0,p1,turn)
        root=probe_wdl(tablebase,board,wdl_cache)
        optimal=exact_optimal_moves(board,root,tablebase,wdl_cache)
        if not optimal:
            continue
        ordered=tuple(sorted((p0,p1),key=lambda s:(chess.square_file(s),chess.square_rank(s))))
        base_roles=frozen_base_roles(policy,feature_fns,wk,bk,ordered,turn)
        hit=(
            role_is_optimal_for_anchor(base_roles[0],ordered[0],optimal,board)
            or role_is_optimal_for_anchor(base_roles[1],ordered[1],optimal,board)
        )
        base_success += int(hit)
        residual += int(not hit)
        rows.append(pair_features(wk,bk,*ordered,turn,*base_roles,role_ids))
        metadata.append((state,board,ordered,base_roles,optimal,root))
    return rows, metadata, {
        "base_success": base_success,
        "residual": residual,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir",type=Path,required=True)
    ap.add_argument("--acquire-size",type=int,default=50000)
    ap.add_argument("--test-size",type=int,default=100000)
    ap.add_argument("--acquire-seed",type=int,default=20260928)
    ap.add_argument("--test-seed",type=int,default=20260929)
    ap.add_argument("--output",type=Path,default=Path("crystal_chess_pair_geometry_v7.json"))
    args=ap.parse_args()
    started=time.time()

    files=sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest=[{"name":p.name,"size":p.stat().st_size,"sha256":file_sha256(p)} for p in files]
    bank=coordinate_feature_bank()
    feature_fns=[fn for _,fn in bank]
    wdl_cache={}

    with chess.syzygy.open_tablebase(str(args.tablebase_dir),load_wdl=True,load_dtz=False) as tb:
        base_policy,base_freq,kpvk_records,kpvk_nonterm,enum=train_frozen_kpvk_policy(tb,feature_fns,wdl_cache)
        all_roles=sorted(base_freq)
        role_ids={r:i for i,r in enumerate(all_roles)}
        acquire=sample_kppvk(args.acquire_size,args.acquire_seed)
        rows,targets,repair_ranking,acq_stats=acquire_rows(
            acquire,tb,wdl_cache,base_policy,feature_fns,role_ids,True
        )
        X=np.asarray(rows,dtype=np.int16)
        controller=DecisionTreeClassifier(criterion="entropy",splitter="best",random_state=0)
        controller.fit(X,targets)
        pred=[str(x) for x in controller.predict(X)]

        # Exact acquisition reclosure.
        acq_eval_rows,acq_meta,acq_base=acquire_rows(
            acquire,tb,wdl_cache,base_policy,feature_fns,role_ids,False
        )
        assert len(acq_eval_rows)==len(pred)
        acq_good=0
        for label,meta in zip(pred,acq_meta):
            _state,board,ordered,base_roles,optimal,_root=meta
            acq_good += int(label_is_optimal(label,board,ordered,optimal,base_roles))
        if acq_good != len(acq_meta):
            raise AssertionError(f"acquisition controller not exact: {acq_good}/{len(acq_meta)}")

        # Completely independent prospective sample.
        test=sample_kppvk(args.test_size,args.test_seed)
        test_rows,test_meta,test_base=acquire_rows(
            test,tb,wdl_cache,base_policy,feature_fns,role_ids,False
        )
        test_pred=[str(x) for x in controller.predict(np.asarray(test_rows,dtype=np.int16))]
        test_good=0
        repair_used=0
        failures=[]
        for label,meta in zip(test_pred,test_meta):
            state,board,ordered,base_roles,optimal,root=meta
            ok=label_is_optimal(label,board,ordered,optimal,base_roles)
            test_good += int(ok)
            repair_used += int(label not in (BASE0,BASE1))
            if not ok and len(failures)<30:
                failures.append({
                    "fen":board.fen(),
                    "root_wdl":root,
                    "label":label,
                    "base_roles":list(base_roles),
                    "optimal_moves":[m.uci() for m in optimal],
                    "optimal_labels":[explicit_action_label(board,m,ordered) for m in optimal],
                })

    ctrl=tree_summary(controller)
    result={
        "schema":SCHEMA,
        "status":"WARRANTED_BOUNDED_PAIR_GEOMETRY_RESIDUAL_TRANSFER",
        "base_crystal_authority":BASE_CRYSTAL_AUTHORITY,
        "v5_authority":V5_AUTHORITY,
        "protected_interface":PROTECTED_INTERFACE,
        "method":{
            "generation_1":"frozen KPvK symbolic capability",
            "generation_2":"KPPvK pair-geometry guard/repair acquired on seed A only",
            "prospective_test":"independent seed B; no seed-B labels enter acquisition",
        },
        "authority":{"kind":"Syzygy WDL","tablebase_files":manifest},
        "acquisition":{
            "seed":args.acquire_seed,
            "requested_states":args.acquire_size,
            "nonterminal_states":len(acq_meta),
            "base_success":acq_base["base_success"],
            "base_residual":acq_base["residual"],
            "controller_exact":acq_good,
            "controller_tree":ctrl,
            "repair_ranking":repair_ranking,
        },
        "prospective":{
            "seed":args.test_seed,
            "requested_states":args.test_size,
            "nonterminal_states":len(test_meta),
            "base_success":test_base["base_success"],
            "base_ratio":test_base["base_success"]/len(test_meta),
            "base_residual":test_base["residual"],
            "combined_success":test_good,
            "combined_ratio":test_good/len(test_meta),
            "absolute_gain":(test_good-test_base["base_success"])/len(test_meta),
            "remaining_residual":len(test_meta)-test_good,
            "repair_invocations":repair_used,
            "failure_examples":failures,
        },
        "epistemic_boundary":{
            "warranted_if_green":[
                "pair-geometry repair is exact on its acquisition sample",
                "reported prospective gain is measured on an independent deterministic KPPvK sample unseen during acquisition",
                "every success is independently Syzygy WDL checked",
            ],
            "unknown":["complete KPPvK closure","transfer beyond KPPvK","general chess solution"],
        },
        "cache":{"wdl_positions":len(wdl_cache)},
        "environment":{"python":sys.version,"platform":platform.platform(),"numpy":np.__version__},
        "elapsed_seconds":time.time()-started,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CRYSTAL_CHESS_PAIR_GEOMETRY_V7=PASS")
    print(
        f"acquire nonterminal={len(acq_meta)} base={acq_base['base_success']} "
        f"residual={acq_base['residual']} controller={acq_good}"
    )
    print(
        f"test nonterminal={len(test_meta)} base={test_base['base_success']} "
        f"ratio={test_base['base_success']/len(test_meta):.6f} "
        f"combined={test_good} ratio={test_good/len(test_meta):.6f} "
        f"gain={(test_good-test_base['base_success'])/len(test_meta):.6f} "
        f"remaining={len(test_meta)-test_good}"
    )
    print(f"tree leaves={ctrl['leaves']} depth={ctrl['max_depth']} repairs={repair_used}")
    print(f"artifact={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
