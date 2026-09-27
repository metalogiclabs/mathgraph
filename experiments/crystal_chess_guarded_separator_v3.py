#!/usr/bin/env python3
"""Crystal Chess V3: guarded separator census on exact KPvK.

The V1 global equality schema was safe but overfragmented ~4.8x relative to the
oracle. This experiment asks a narrower question: when a state has exactly two
protected WDL move classes, can one simple binary predicate on one observable
separate those classes exactly?

Rules are parameter-free at deployment time:
  feature == integer
  feature <= integer

Exact WDL is used only to discover/verify which rules are separators. A small
separator vocabulary is a CANDIDATE until a label-free applicability guard is
qualified.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import chess
import chess.syzygy

from experiments.crystal_chess_action_congruence_v1 import (
    ActionRecord,
    collect_actions,
)

SCHEMA="mathgraph.crystal-chess.guarded-separator.v3"
BASE_AUTHORITY="metalogiclabs/mathgraph@e8ab96412c88b8175e7116081c4cae8276a890d1"
THRESHOLD_UNIVERSE=tuple(range(-2,10))+(98,99)

Rule=tuple[str,str,int]


def group_states(records:list[ActionRecord]) -> dict[int,list[ActionRecord]]:
    out:dict[int,list[ActionRecord]]=defaultdict(list)
    for r in records:
        out[r.state_id].append(r)
    return out


def exact_binary_rules(
    actions:list[ActionRecord], feature_names:list[str]
) -> set[Rule]:
    labels=sorted({a.consequence for a in actions})
    if len(labels)!=2:
        return set()
    la,lb=labels
    rules:set[Rule]=set()
    for idx,name in enumerate(feature_names):
        va={a.features[idx] for a in actions if a.consequence==la}
        vb={a.features[idx] for a in actions if a.consequence==lb}

        # Equality predicate: one consequence class is exactly one value and
        # the other class never takes that value.
        if len(va)==1:
            v=next(iter(va))
            if v not in vb:
                rules.add((name,"eq",int(v)))
        if len(vb)==1:
            v=next(iter(vb))
            if v not in va:
                rules.add((name,"eq",int(v)))

        # Threshold predicate: the two value ranges are strictly ordered.
        maxa,mina=max(va),min(va)
        maxb,minb=max(vb),min(vb)
        if maxa<minb:
            lo,hi=maxa,minb-1
            for t in THRESHOLD_UNIVERSE:
                if lo<=t<=hi:
                    rules.add((name,"le",int(t)))
        if maxb<mina:
            lo,hi=maxb,mina-1
            for t in THRESHOLD_UNIVERSE:
                if lo<=t<=hi:
                    rules.add((name,"le",int(t)))
    return rules


def build_coverage(
    states:dict[int,list[ActionRecord]],
    feature_names:list[str],
) -> tuple[set[int],dict[Rule,set[int]],int]:
    ambiguous:set[int]=set()
    coverage:dict[Rule,set[int]]=defaultdict(set)
    no_rule=0
    for sid,actions in states.items():
        if len({a.consequence for a in actions})!=2:
            continue
        ambiguous.add(sid)
        rules=exact_binary_rules(actions,feature_names)
        if not rules:
            no_rule+=1
        for rule in rules:
            coverage[rule].add(sid)
    return ambiguous,coverage,no_rule


def greedy_cover(
    universe:set[int], coverage:dict[Rule,set[int]], limit:int
) -> tuple[list[dict[str,object]],set[int]]:
    uncovered=set(universe)
    selected=[]
    used:set[Rule]=set()
    for _ in range(limit):
        best=None
        best_gain=0
        for rule,covered in coverage.items():
            if rule in used:
                continue
            gain=len(covered & uncovered)
            if gain>best_gain or (gain==best_gain and gain>0 and (best is None or rule<best)):
                best=rule; best_gain=gain
        if best is None or best_gain==0:
            break
        used.add(best)
        uncovered-=coverage[best]
        selected.append({
            "rule":{"feature":best[0],"op":best[1],"value":best[2]},
            "gain":best_gain,
            "remaining":len(uncovered),
            "cumulative_coverage":len(universe)-len(uncovered),
        })
    return selected,uncovered


def predicate(rule:Rule,value:int) -> bool:
    _,op,param=rule
    if op=="eq":
        return value==param
    if op=="le":
        return value<=param
    raise ValueError(op)


def rule_safety(
    states:dict[int,list[ActionRecord]],
    feature_index:dict[str,int],
    rule:Rule,
) -> dict[str,int]:
    idx=feature_index[rule[0]]
    out=Counter()
    for actions in states.values():
        groups={False:[],True:[]}
        for a in actions:
            groups[predicate(rule,a.features[idx])].append(a.consequence)
        if not groups[False] or not groups[True]:
            continue
        out["applicable"]+=1
        if len(set(groups[False]))==1 and len(set(groups[True]))==1:
            out["safe"]+=1
        else:
            out["unsafe"]+=1
    return dict(out)


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--cover-limit",type=int,default=12)
    args=ap.parse_args()
    started=time.time()

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir),load_wdl=True,load_dtz=False
    ) as tb:
        records,feature_names,collection=collect_actions(tb)

    train_records=[r for r in records if r.pawn_file<3]
    test_records=[r for r in records if r.pawn_file==3]
    train_states=group_states(train_records)
    test_states=group_states(test_records)

    train_ambig,train_cov,train_no=build_coverage(train_states,feature_names)
    test_ambig,test_cov,test_no=build_coverage(test_states,feature_names)

    selected,train_uncovered=greedy_cover(
        train_ambig,train_cov,args.cover_limit
    )
    selected_rules=[
        (row["rule"]["feature"],row["rule"]["op"],int(row["rule"]["value"]))
        for row in selected
    ]
    test_covered:set[int]=set()
    for rule in selected_rules:
        test_covered |= test_cov.get(rule,set())

    feature_index={name:i for i,name in enumerate(feature_names)}
    selected_safety=[]
    for rule in selected_rules:
        selected_safety.append({
            "rule":{"feature":rule[0],"op":rule[1],"value":rule[2]},
            "train":rule_safety(train_states,feature_index,rule),
            "test":rule_safety(test_states,feature_index,rule),
        })

    single_feature_counts=Counter()
    for rule,states in train_cov.items():
        single_feature_counts[rule[0]]+=len(states)
    test_feature_counts=Counter()
    for rule,states in test_cov.items():
        test_feature_counts[rule[0]]+=len(states)

    train_union=set().union(*train_cov.values()) if train_cov else set()
    test_union=set().union(*test_cov.values()) if test_cov else set()

    train_ratio=(len(train_ambig)-len(train_uncovered))/len(train_ambig) if train_ambig else 1.0
    test_ratio=len(test_covered)/len(test_ambig) if test_ambig else 1.0

    status=(
        "CANDIDATE_TRANSFERABLE_GUARDED_SEPARATOR_VOCABULARY"
        if test_ratio>=0.80 and len(selected_rules)<=args.cover_limit
        else "UNKNOWN_GUARDED_SEPARATOR_VOCABULARY"
    )

    result={
        "schema":SCHEMA,
        "status":status,
        "base_authority":BASE_AUTHORITY,
        "collection":collection,
        "candidate_features":feature_names,
        "rule_language":{
            "forms":["feature == integer","feature <= integer"],
            "threshold_universe":list(THRESHOLD_UNIVERSE),
        },
        "train":{
            "files":"a,b,c",
            "states":len(train_states),
            "two_consequence_states":len(train_ambig),
            "states_with_any_simple_separator":len(train_union),
            "no_simple_separator":train_no,
            "any_separator_ratio":len(train_union)/len(train_ambig) if train_ambig else 1.0,
        },
        "test":{
            "file":"d",
            "states":len(test_states),
            "two_consequence_states":len(test_ambig),
            "states_with_any_simple_separator":len(test_union),
            "no_simple_separator":test_no,
            "any_separator_ratio":len(test_union)/len(test_ambig) if test_ambig else 1.0,
        },
        "greedy_train_cover":{
            "limit":args.cover_limit,
            "selected":selected,
            "uncovered":len(train_uncovered),
            "coverage_ratio":train_ratio,
        },
        "heldout_same_vocabulary":{
            "covered_test_states":len(test_covered),
            "coverage_ratio":test_ratio,
        },
        "selected_rule_safety":selected_safety,
        "top_train_features":single_feature_counts.most_common(15),
        "top_test_features":test_feature_counts.most_common(15),
        "epistemic_boundary":{
            "candidate_only":(
                "selected fixed predicate vocabulary transfers as an available "
                "exact separator family; a label-free applicability/selector "
                "guard is not yet qualified"
            ),
            "not_claimed":[
                "safe blind application of selected rules",
                "cross-material transfer",
                "general chess solution",
            ],
        },
        "elapsed_seconds":time.time()-started,
    }

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")

    print(f"CRYSTAL_CHESS_GUARDED_SEPARATOR_V3={status}")
    print(
        f"train_two={len(train_ambig)} any={len(train_union)} "
        f"greedy={len(train_ambig)-len(train_uncovered)} "
        f"ratio={train_ratio:.4f}"
    )
    print(
        f"test_two={len(test_ambig)} any={len(test_union)} "
        f"selected_vocab={len(test_covered)} ratio={test_ratio:.4f}"
    )
    print("selected_rules="+json.dumps([row["rule"] for row in selected],sort_keys=True))
    print("top_train_features="+json.dumps(single_feature_counts.most_common(10)))
    print(f"artifact={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
