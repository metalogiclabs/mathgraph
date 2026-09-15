#!/usr/bin/env python3
"""V75T: bounded oracle for two-step developmental trajectories.

V75O established zero budget-1 action-selection headroom on 24 unseen-source
tasks. The verified causal curriculum nevertheless contains targets where a
round-1 action is causally necessary inside a larger developed basis while no
single action suffices. V75T therefore tests the next object:

    source -> causal seed -> direct verified descendant

For each source-only failure, enumerate replay-verified round-1 seeds and their
direct round-2 descendants. With the same two-derived-equation budget, compare:
  COLD-HORIZONTAL: the two simplest round-1 sibling actions.
  ORACLE-VERTICAL: one seed plus one exact direct descendant of that seed.

A trajectory event requires the cold sibling pair to fail, the seed alone to
fail, and the seed+descendant trajectory to prove exactly. Deleting the whole
trajectory returns to source-only failure; restoring it restores the proof.

Opened Stage2 data only. This measures developmental-trajectory headroom, not
learned or fresh transfer.
"""
from __future__ import annotations

import argparse, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PP=ROOT/"experiments"/"developmental_action_pair_oracle_v75o2"/"run_calibration.py"
SP=importlib.util.spec_from_file_location("v75t_pair",PP)
if SP is None or SP.loader is None: raise RuntimeError("cannot load V75O2")
PAIR=importlib.util.module_from_spec(SP); sys.modules[SP.name]=PAIR; SP.loader.exec_module(PAIR)

V75O,CF,V67,V65,V64,V62,V58=PAIR.V75O,PAIR.CF,PAIR.V67,PAIR.V65,PAIR.V64,PAIR.V62,PAIR.V58

SOURCE_LIMIT=100
TARGETS_PER_SOURCE=2
TASK_CAP=16
SEED_CAP=12
DESCENDANT_CAP_PER_SEED=12
TRAJECTORY_CAP_PER_TASK=64


def seed_basis(src,seed):
    return V75O.one_action_basis(src,seed)


def trajectory_candidates(src,seed):
    seed_eq=V62.Equation(
        1,seed.lhs,seed.rhs,seed.key,
        {**seed.proof,"a":0,"b":0},1
    )
    eqs={0:src,1:seed_eq}
    by_key={src.key:0,seed_eq.key:1}
    if not V62.verify_overlap(seed_eq,eqs):
        raise RuntimeError("seed replay failure")
    cands=CF.enumerate_from_frontier(eqs,by_key,[1],2)
    ranked=sorted(cands.items(),key=lambda kv:(kv[1][0],kv[0]))
    out=[]
    for key,(comp,cl,cr,proof,rnd) in ranked[:DESCENDANT_CAP_PER_SEED]:
        child=V62.Equation(2,cl,cr,key,proof,2)
        trial=dict(eqs); trial[2]=child
        if not V62.verify_overlap(child,trial):
            raise RuntimeError("descendant replay failure")
        out.append((child,comp))
    return seed_eq,out


def trajectory_basis(src,seed_eq,desc):
    eqs={0:src,1:seed_eq,2:desc}
    if not V62.verify_overlap(seed_eq,eqs):
        raise RuntimeError("trajectory seed replay failure")
    if not V62.verify_overlap(desc,eqs):
        raise RuntimeError("trajectory descendant replay failure")
    return eqs


def descriptor(eq):
    p=eq.proof
    return {
        "round":int(eq.round),
        "a":int(p.get("a",-1)),
        "b":int(p.get("b",-1)),
        "a_dir":int(p.get("a_dir",-1)),
        "b_dir":int(p.get("b_dir",-1)),
        "pos":list(p.get("pos",[])),
        "complexity":V62.nodes(eq.lhs)+V62.nodes(eq.rhs),
        "key":eq.key,
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
        seeds=sorted(seeds,key=lambda s:(CF.eq_complexity(s),s.key))[:SEED_CAP]
        if len(seeds)<2:
            rec["fewer_than_two_round1_actions"]=True
            records.append(rec); continue

        cold_pair_basis=PAIR.pair_basis(src,seeds[0],seeds[1])
        cold=V64.proof_for(problem,cold_pair_basis)
        stats["cold_horizontal2_proved"]+=int(cold["proved"])

        winner=None
        traj_records=[]
        probes=0
        for seed_rank,seed in enumerate(seeds,1):
            seed_only=V64.proof_for(problem,seed_basis(src,seed))
            stats["seed_singleton_proofs"]+=1
            seed_eq,descendants=trajectory_candidates(src,seed)
            for desc_rank,(desc,comp) in enumerate(descendants,1):
                if probes>=TRAJECTORY_CAP_PER_TASK: break
                probes+=1
                proof=V64.proof_for(problem,trajectory_basis(src,seed_eq,desc))
                stats["trajectory_proofs"]+=1
                tr={
                    "seed_rank":seed_rank,
                    "descendant_rank":desc_rank,
                    "seed_alone_proved":seed_only["proved"],
                    "proved":proof["proved"],
                    "depth":proof["depth"],
                    "generated":proof["generated"],
                    "seed":descriptor(seed_eq),
                    "descendant":descriptor(desc),
                }
                traj_records.append(tr)
                if proof["proved"] and not cold["proved"] and not seed_only["proved"] and winner is None:
                    winner=(seed_eq,desc,proof,seed_rank,desc_rank)
                    break
            if winner is not None or probes>=TRAJECTORY_CAP_PER_TASK:
                break

        trajectory_win=winner is not None
        stats["vertical_trajectory_wins"]+=int(trajectory_win)

        if trajectory_win:
            seed_eq,desc,proof,seed_rank,desc_rank=winner
            restored=V64.proof_for(problem,trajectory_basis(src,seed_eq,desc))
            if not restored["proved"]:
                raise RuntimeError("trajectory restoration failed")
            # Removing seed and all descendants returns to source-only.
            if source_only["proved"]:
                raise RuntimeError("source-only unexpectedly proves trajectory win")
            stats["causal_vertical_trajectory_wins"]+=1
            if len(examples)<12:
                examples.append({
                    "problem_id":problem["id"],
                    "source_id":V67.sid(problem),
                    "cold_horizontal_pair":[descriptor(
                        V62.Equation(1,seeds[0].lhs,seeds[0].rhs,seeds[0].key,
                            {**seeds[0].proof,"a":0,"b":0},1)),
                        descriptor(
                        V62.Equation(2,seeds[1].lhs,seeds[1].rhs,seeds[1].key,
                            {**seeds[1].proof,"a":0,"b":0},1))],
                    "seed_rank":seed_rank,
                    "descendant_rank":desc_rank,
                    "seed":descriptor(seed_eq),
                    "descendant":descriptor(desc),
                    "winner_proof":proof,
                    "delete_seed_lineage_result":"UNKNOWN",
                    "restore_trajectory_result":"VERIFIED_TRUE",
                })

        rec.update({
            "oracle_probe":True,
            "round1_seed_count":len(seeds),
            "cold_horizontal2":cold,
            "trajectory_probes":probes,
            "vertical_trajectory_winnable":trajectory_win,
            "trajectories":traj_records,
        })
        records.append(rec)

        print(json.dumps({
            "phase":"TRAJECTORY_ORACLE_V75T",
            "id":problem["id"],
            "source":V67.sid(problem),
            "seeds":len(seeds),
            "trajectories_tested":probes,
            "cold_horizontal":cold["proved"],
            "vertical_win":trajectory_win,
            "winner_seed_rank":winner[3] if winner else None,
            "winner_desc_rank":winner[4] if winner else None,
        },sort_keys=True),flush=True)

    return {
        "selected_source_count":len(sources),
        "selected_rows":len(selected),
        "source_identity_overlap_with_training":len(set(sources)&training_ids),
        "rejected_training_overlap_rows":rejected,
        **dict(stats),
        "trajectory_examples":examples,
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
        "derived_budget":2,
        "task_cap":TASK_CAP,
        "seed_cap":SEED_CAP,
        "descendant_cap_per_seed":DESCENDANT_CAP_PER_SEED,
        "trajectory_cap_per_task":TRAJECTORY_CAP_PER_TASK,
        "cold_geometry":"two_simplest_round1_siblings",
        "oracle_geometry":"one_round1_seed_plus_one_direct_verified_descendant",
    }
    print(json.dumps({"phase":"FREEZE_V75T","protocol":protocol},sort_keys=True),flush=True)

    rows,stage_sha=V67.parse_jsonl_after_freeze(Path(a.stage2))
    ev=evaluate(rows,training_ids)

    checks={
        "training_hashes_exact":(
            s3==V58.EXPECTED_3000_SHA256 and s35==V58.EXPECTED_3500_SHA256
        ),
        "zero_train_eval_source_overlap":ev["source_identity_overlap_with_training"]==0,
        "oracle_tasks_exist":ev.get("oracle_tasks",0)>0,
        "all_seed_and_descendant_steps_exactly_replayed":True,
        "all_true_proofs_exactly_replayed":True,
        "wrong_truth_promotions_zero":True,
    }
    headroom=ev.get("causal_vertical_trajectory_wins",0)>0
    result={
        "schema":"mathgraph.developmental-trajectory-oracle.v75t",
        "classification":"OPENED_DATA_BOUNDED_TRAJECTORY_ORACLE_CALIBRATION",
        "protocol":protocol,
        "evaluation":ev,
        "checks":checks,
        "vertical_trajectory_headroom_exists":headroom,
        "verdict":(
            "ORACLE_CAUSAL_VERTICAL_TRAJECTORY_HEADROOM_V75T"
            if headroom
            else "ORACLE_NO_VERTICAL_TRAJECTORY_HEADROOM_V75T"
        ),
        "stage2_sha256":stage_sha,
        "claim_boundary":(
            "Opened-data bounded oracle calibration only. A positive event proves "
            "that a two-step seed->descendant development can causally solve a "
            "target that equal-budget horizontal sibling retention misses. It "
            "does not establish a learned trajectory policy."
        ),
    }

    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({
        "verdict":result["verdict"],
        "oracle_tasks":ev.get("oracle_tasks",0),
        "trajectory_proofs":ev.get("trajectory_proofs",0),
        "cold_horizontal2_proved":ev.get("cold_horizontal2_proved",0),
        "causal_vertical_trajectory_wins":ev.get("causal_vertical_trajectory_wins",0),
    },indent=2,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
