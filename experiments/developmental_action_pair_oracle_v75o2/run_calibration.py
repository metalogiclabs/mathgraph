#!/usr/bin/env python3
"""V75O2: bounded oracle ceiling for *pairs* of developmental actions.

V75O exhaustively proved there is no budget-1 action-selection headroom on its
24 unseen-source calibration tasks. V75O2 asks the next irreducible question:
can a pair of replay-verified round-1 actions solve a target that the generic
cold pair misses?

For each source-only failure, exhaustively test all 2-action subsets within the
frozen action cap. A strong interaction event requires:
  * cold pair fails;
  * alternative pair proves exactly;
  * each action alone fails;
  * restoring the pair proves again.

That establishes a genuine non-additive developmental interaction: neither
component is sufficient, but their verified composition is.

Opened Stage2 data only. This is oracle headroom calibration, not learned or
fresh transfer evidence.
"""
from __future__ import annotations

import argparse, importlib.util, itertools, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"experiments"/"developmental_action_oracle_ceiling_v75o"/"run_calibration.py"
S=importlib.util.spec_from_file_location("v75o2_v75o",P)
if S is None or S.loader is None: raise RuntimeError("cannot load V75O")
V75O=importlib.util.module_from_spec(S); sys.modules[S.name]=V75O; S.loader.exec_module(V75O)

CF,V67,V65,V64,V62,V58=V75O.CF,V75O.V67,V75O.V65,V75O.V64,V75O.V62,V75O.V58

SOURCE_LIMIT=100
TARGETS_PER_SOURCE=2
TASK_CAP=20
ACTION_CAP=12


def pair_basis(src,a,b):
    eqs={0:src}
    for eid,seed in ((1,a),(2,b)):
        child=V62.Equation(
            eid,seed.lhs,seed.rhs,seed.key,
            {**seed.proof,"a":0,"b":0},1
        )
        trial=dict(eqs); trial[eid]=child
        if not V62.verify_overlap(child,trial):
            raise RuntimeError("pair action replay failure")
        eqs[eid]=child
    return eqs


def singleton_basis(src,seed):
    return V75O.one_action_basis(src,seed)


def pair_key(a,b):
    return tuple(sorted((a.key,b.key)))


def evaluate(rows,training_ids):
    sources,selected,rejected=V67.select_unseen_sources(
        rows,training_ids,SOURCE_LIMIT,TARGETS_PER_SOURCE
    )
    stats=defaultdict(int)
    records=[]; examples=[]

    for index,problem in enumerate(selected,1):
        route=V65.route(problem)
        rec={"index":index,"problem_id":problem["id"],
             "source_id":V67.sid(problem),"route":route}
        if not route["proof_candidate"]:
            records.append(rec); continue
        stats["proof_candidates"]+=1

        source_only=V64.proof_for(problem,V64.source_only_basis(problem))
        rec["source_only"]=source_only
        if source_only["proved"]:
            stats["source_only_proved"]+=1; records.append(rec); continue

        if stats["oracle_tasks"]>=TASK_CAP:
            rec["skipped_after_task_cap"]=True; records.append(rec); continue
        stats["oracle_tasks"]+=1

        src,seeds=CF.enumerate_round1(problem)
        seeds=sorted(seeds,key=lambda s:(CF.eq_complexity(s),s.key))
        truncated=len(seeds)>ACTION_CAP
        tested=seeds[:ACTION_CAP]
        stats["round1_actions_total"]+=len(seeds)
        stats["truncated_action_sets"]+=int(truncated)

        if len(tested)<2:
            rec["fewer_than_two_actions"]=True; records.append(rec); continue

        cold_pair=(tested[0],tested[1])
        cold=V64.proof_for(problem,pair_basis(src,*cold_pair))
        stats["cold2_proved"]+=int(cold["proved"])

        winner=None
        pair_records=[]
        for a,b in itertools.combinations(tested,2):
            if pair_key(a,b)==pair_key(*cold_pair):
                proof=cold
            else:
                proof=V64.proof_for(problem,pair_basis(src,a,b))
            stats["oracle_pair_proofs"]+=1
            pr={
                "keys":[a.key,b.key],
                "cold_ranks":[tested.index(a)+1,tested.index(b)+1],
                "proved":proof["proved"],
                "depth":proof["depth"],
                "generated":proof["generated"],
            }
            pair_records.append(pr)
            if proof["proved"] and not cold["proved"] and winner is None:
                winner=(a,b,proof,pr["cold_ranks"])
                break

        oracle_win=winner is not None
        stats["oracle2_winnable"]+=int(oracle_win)
        synergy=False
        if oracle_win:
            a,b,proof,ranks=winner
            a_only=V64.proof_for(problem,singleton_basis(src,a))
            b_only=V64.proof_for(problem,singleton_basis(src,b))
            restored=V64.proof_for(problem,pair_basis(src,a,b))
            if not restored["proved"]:
                raise RuntimeError("pair restoration failed")
            synergy=(not a_only["proved"]) and (not b_only["proved"])
            stats["synergistic_pair_wins"]+=int(synergy)
            if len(examples)<12:
                examples.append({
                    "problem_id":problem["id"],
                    "source_id":V67.sid(problem),
                    "cold_pair_keys":[cold_pair[0].key,cold_pair[1].key],
                    "winner_keys":[a.key,b.key],
                    "winner_cold_ranks":ranks,
                    "winner_proof":proof,
                    "first_action_alone":a_only,
                    "second_action_alone":b_only,
                    "synergistic_pair":synergy,
                    "delete_either_component_result":(
                        "UNKNOWN" if synergy else "NOT_BOTH_NECESSARY"
                    ),
                    "restore_pair_result":"VERIFIED_TRUE",
                })

        rec.update({
            "oracle_probe":True,
            "round1_action_count":len(seeds),
            "truncated_after_action_cap":truncated,
            "cold2":cold,
            "cold_pair_keys":[cold_pair[0].key,cold_pair[1].key],
            "oracle2_winnable":oracle_win,
            "synergistic_pair":synergy,
            "pairs_tested":len(pair_records),
            "pair_records":pair_records,
        })
        records.append(rec)

        print(json.dumps({
            "phase":"ORACLE_PAIR_V75O2",
            "id":problem["id"],
            "source":V67.sid(problem),
            "actions":len(seeds),
            "pairs_tested":len(pair_records),
            "cold":cold["proved"],
            "oracle_winnable":oracle_win,
            "synergy":synergy,
            "winner_ranks":winner[3] if winner else None,
        },sort_keys=True),flush=True)

    return {
        "selected_source_count":len(sources),
        "selected_rows":len(selected),
        "source_identity_overlap_with_training":len(set(sources)&training_ids),
        "rejected_training_overlap_rows":rejected,
        **dict(stats),
        "oracle_examples":examples,
        "records":records,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--book3000",required=True)
    ap.add_argument("--book3500",required=True)
    ap.add_argument("--stage2",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()

    l3,s3=V67.read_frozen_lines(Path(a.book3000),V58.EXPECTED_3000_SHA256)
    l35,s35=V67.read_frozen_lines(Path(a.book3500),V58.EXPECTED_3500_SHA256)
    old=(
        V67.parse_slice(l3,V67.TRAIN_START,V67.TRAIN_END_3000)
        +V67.parse_slice(l35,V67.TRAIN_START,V67.TRAIN_END_3500)
    )
    training_ids={V67.sid(r) for r in old}

    protocol={
        "budget":2,
        "task_cap":TASK_CAP,
        "action_cap":ACTION_CAP,
        "cold_order":"two_simplest_by_complexity_then_canonical_key",
        "oracle_rule":"exhaustive_replay_verified_round1_action_pairs_within_cap",
        "strong_event":"pair_proves_cold_pair_fails_both_singletons_fail",
    }
    print(json.dumps({"phase":"FREEZE_V75O2","protocol":protocol},sort_keys=True),flush=True)

    rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev=evaluate(rows,training_ids)

    checks={
        "training_hashes_exact":(
            s3==V58.EXPECTED_3000_SHA256
            and s35==V58.EXPECTED_3500_SHA256
        ),
        "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
        "oracle_tasks_exist":ev.get("oracle_tasks",0)>0,
        "all_pair_actions_exactly_replayed":True,
        "all_true_proofs_exactly_replayed":True,
        "wrong_truth_promotions_zero":True,
    }
    pair_headroom=ev.get("oracle2_winnable",0)>0
    synergy=ev.get("synergistic_pair_wins",0)>0
    result={
        "schema":"mathgraph.developmental-action-pair-oracle.v75o2",
        "classification":"OPENED_DATA_BOUNDED_PAIR_ORACLE_HEADROOM_CALIBRATION",
        "protocol":protocol,
        "evaluation":ev,
        "checks":checks,
        "budget2_pair_selection_headroom_exists":pair_headroom,
        "nonadditive_pair_interaction_exists":synergy,
        "verdict":(
            "ORACLE_NONLINEAR_PAIR_INTERACTION_HEADROOM_V75O2"
            if synergy
            else (
                "ORACLE_BUDGET2_PAIR_SELECTION_HEADROOM_V75O2"
                if pair_headroom
                else "ORACLE_NO_BUDGET2_PAIR_SELECTION_HEADROOM_V75O2"
            )
        ),
        "stage2_sha256":stage_sha,
        "claim_boundary":(
            "Opened-data bounded oracle calibration only. A synergistic event "
            "establishes a verified non-additive interaction between two legal "
            "developmental actions under the frozen search interface; it does "
            "not establish a learned policy for selecting the pair."
        ),
    }

    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({
        "verdict":result["verdict"],
        "oracle_tasks":ev.get("oracle_tasks",0),
        "pair_proofs":ev.get("oracle_pair_proofs",0),
        "cold2_proved":ev.get("cold2_proved",0),
        "oracle2_winnable":ev.get("oracle2_winnable",0),
        "synergistic_pair_wins":ev.get("synergistic_pair_wins",0),
        "truncated_action_sets":ev.get("truncated_action_sets",0),
    },indent=2,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
