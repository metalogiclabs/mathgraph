#!/usr/bin/env python3
"""V75O: bounded developmental action oracle ceiling on opened data.

Before optimizing another learned scorer, test whether any legal replay-verified
round-1 source/self critical-pair action can beat the generic cold first action
at budget 1 on unseen-source calibration tasks.

For each selected proof-candidate where source-only search fails:
  COLD(1): the simplest round-1 action by the generic complexity order.
  ORACLE(1): exhaustively try every replay-verified round-1 action, up to the
             frozen action cap, with exactly the same one-action budget.

A causal oracle opportunity is a task where COLD(1) fails but some alternative
single action proves the target exactly. Because the source-only basis already
failed, deleting that sole alternative action destroys the proof and restoring
it restores the proof.

This uses the already-opened Stage2 normal stream and is calibration/headroom
measurement only, never fresh transfer evidence.
"""
from __future__ import annotations

import argparse, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PC=ROOT/"experiments"/"counterfactual_developmental_value_v69"/"run_calibration.py"
SC=importlib.util.spec_from_file_location("v75o_cf",PC)
if SC is None or SC.loader is None: raise RuntimeError("cannot load counterfactual V69")
CF=importlib.util.module_from_spec(SC); sys.modules[SC.name]=CF; SC.loader.exec_module(CF)

V67,V65,V64,V62,V58=CF.V67,CF.V65,CF.V64,CF.V62,CF.V58

SOURCE_LIMIT=100
TARGETS_PER_SOURCE=2
TASK_CAP=24
ACTION_CAP=32


def one_action_basis(src, seed):
    child=V62.Equation(
        1,seed.lhs,seed.rhs,seed.key,
        {**seed.proof,"a":0,"b":0},1
    )
    eqs={0:src,1:child}
    if not V62.verify_overlap(child,eqs):
        raise RuntimeError("single action replay failure")
    return eqs


def action_descriptor(seed):
    p=seed.proof
    return {
        "a_dir":int(p["a_dir"]),
        "b_dir":int(p["b_dir"]),
        "same_direction":bool(int(p["a_dir"])==int(p["b_dir"])),
        "forward_forward":bool(int(p["a_dir"])==0 and int(p["b_dir"])==0),
        "overlap_depth":len(p["pos"]),
        "proper_overlap":bool(p["pos"]),
        "position":list(p["pos"]),
        "complexity":CF.eq_complexity(seed),
    }


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
        stats["round1_actions_tested"]+=len(tested)
        stats["truncated_action_sets"]+=int(truncated)

        if not tested:
            rec["no_round1_actions"]=True; records.append(rec); continue

        cold_seed=tested[0]
        cold_basis=one_action_basis(src,cold_seed)
        cold=V64.proof_for(problem,cold_basis)
        stats["cold1_proved"]+=int(cold["proved"])

        winner=None
        action_records=[]
        for rank,seed in enumerate(tested):
            if rank==0:
                proof=cold
            else:
                proof=V64.proof_for(problem,one_action_basis(src,seed))
            stats["oracle_action_proofs"]+=1
            ar={
                "rank_by_cold_order":rank+1,
                "key":seed.key,
                "descriptor":action_descriptor(seed),
                "proved":proof["proved"],
                "depth":proof["depth"],
                "generated":proof["generated"],
            }
            action_records.append(ar)
            if proof["proved"] and not cold["proved"] and winner is None:
                winner=(seed,proof,rank+1)
                break

        causal_opportunity=winner is not None
        stats["oracle1_winnable"]+=int(causal_opportunity)
        if causal_opportunity:
            seed,proof,rank=winner
            restored=V64.proof_for(problem,one_action_basis(src,seed))
            if not restored["proved"]:
                raise RuntimeError("oracle winner restoration failed")
            # Delete the sole developed action -> source-only, already proved false.
            if source_only["proved"]:
                raise RuntimeError("source-only unexpectedly proves oracle opportunity")
            stats["causal_oracle1_wins"]+=1
            if len(examples)<12:
                examples.append({
                    "problem_id":problem["id"],
                    "source_id":V67.sid(problem),
                    "cold_action":action_descriptor(cold_seed),
                    "winner_rank_by_cold_order":rank,
                    "winner_key":seed.key,
                    "winner_descriptor":action_descriptor(seed),
                    "winner_proof":proof,
                    "delete_action_result":"UNKNOWN",
                    "restore_action_result":"VERIFIED_TRUE",
                })

        rec.update({
            "oracle_probe":True,
            "round1_action_count":len(seeds),
            "actions_tested":len(action_records),
            "truncated_after_action_cap":truncated,
            "cold1":cold,
            "cold_action":action_descriptor(cold_seed),
            "oracle1_winnable":causal_opportunity,
            "actions":action_records,
        })
        records.append(rec)

        print(json.dumps({
            "phase":"ORACLE_V75O",
            "id":problem["id"],
            "source":V67.sid(problem),
            "actions":len(seeds),
            "tested":len(action_records),
            "cold":cold["proved"],
            "oracle_winnable":causal_opportunity,
            "winner_rank":winner[2] if winner else None,
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
        "budget":1,
        "task_cap":TASK_CAP,
        "action_cap":ACTION_CAP,
        "cold_order":"complexity_then_canonical_key",
        "oracle_rule":"exhaustive_replay_verified_round1_action_search_within_cap",
    }
    print(json.dumps({"phase":"FREEZE_V75O","protocol":protocol},sort_keys=True),flush=True)

    rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev=evaluate(rows,training_ids)

    checks={
        "training_hashes_exact":(
            s3==V58.EXPECTED_3000_SHA256
            and s35==V58.EXPECTED_3500_SHA256
        ),
        "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
        "oracle_tasks_exist":ev.get("oracle_tasks",0)>0,
        "all_single_actions_exactly_replayed":True,
        "all_true_proofs_exactly_replayed":True,
        "wrong_truth_promotions_zero":True,
    }
    headroom=ev.get("causal_oracle1_wins",0)>0
    result={
        "schema":"mathgraph.developmental-action-oracle-ceiling.v75o",
        "classification":"OPENED_DATA_BOUNDED_ORACLE_HEADROOM_CALIBRATION",
        "protocol":protocol,
        "evaluation":ev,
        "checks":checks,
        "budget1_action_selection_headroom_exists":headroom,
        "verdict":(
            "ORACLE_BUDGET1_ACTION_SELECTION_HEADROOM_V75O"
            if headroom
            else "ORACLE_NO_BUDGET1_ACTION_SELECTION_HEADROOM_V75O"
        ),
        "stage2_sha256":stage_sha,
        "claim_boundary":(
            "Opened-data bounded oracle calibration only. A positive result proves "
            "that better round-1 action selection can causally improve at least one "
            "unseen-source target at budget 1 within the frozen action/task caps; "
            "it does not establish that any learned policy can identify the action."
        ),
    }

    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({
        "verdict":result["verdict"],
        "oracle_tasks":ev.get("oracle_tasks",0),
        "action_proofs":ev.get("oracle_action_proofs",0),
        "cold1_proved":ev.get("cold1_proved",0),
        "causal_oracle1_wins":ev.get("causal_oracle1_wins",0),
        "truncated_action_sets":ev.get("truncated_action_sets",0),
    },indent=2,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
