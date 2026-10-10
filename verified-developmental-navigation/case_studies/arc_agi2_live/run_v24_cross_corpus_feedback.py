#!/usr/bin/env python3
"""VDN V24 cross-corpus verifier-trained discovery policy.

Historical source: independent, frozen, exact-head V23 CI artifact. This step
learns a signature-dependent generator priority from verified cold successes.
Frozen policy is written BEFORE the independent ConceptARC corpus is fetched.
No ConceptARC group labels, expected outputs, or task identities influence the
generator. All arms get the same candidate grammar, cheap shape guard, source
world, full verifier, and candidate budget. The competitor infers a local
shape-based priority without retaining source-task outcomes.

A positive result warrants only bounded cross-corpus policy transfer; NOT
representation invention, total amortized profitability, or a closed autonomous
recursive loop. A zero/negative result is retained as an exact falsifier.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,random,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v23_generator_feedback as v23
import run_v2,run_v5_retention as v5

ARC1_PIN="399030444e0ab0cc8b4e199870fb20b863846f34"
CONCEPT_PIN="0e67da6af879e4bad3d7cd3c196e8d551b445725"
V23_SHA="c104ecc80db26588f55d92a5078a9731b16fe8df37bc5937789895ede7b13495"
BUDGET=128


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def sig(task):
    return json.dumps(run_v2.v1.signature(task),sort_keys=True)


def freeze(source_path,arc_train,output):
    assert sha(source_path)==V23_SHA,"V23 source bytes drifted"
    src=json.loads(Path(source_path).read_text())
    assert src["schema"]=="vdn.generator-feedback.prospective-arc.v1"
    assert src["authority"]["arc1_train_commit"]==ARC1_PIN
    assert src["freeze"]["protected_count"]==310
    assert src["arm_stats"]["cold"]["solved"]==18
    assert src["claims"]["meta_generator2_feedback_closed"]=="UNKNOWN"
    tasks=run_v2.v1.load_tasks(arc_train)
    assert len(tasks)==400
    per_sig=collections.defaultdict(collections.Counter)
    global_freq=collections.Counter()
    successes=[]
    for r in src["arm_results"]["cold"]:
        if r["protected_solved"]:
            assert r["fit"] and r["name"]
            key=sig(tasks[r["task"]])
            per_sig[key][r["name"]]+=1
            global_freq[r["name"]]+=1
            successes.append({"id":r["task"],"signature":key,"program":r["name"],
                              "source_candidate_checks":r["attempts"]})
    assert len(successes)==18
    def rank(c):
        return [name for name,_ in sorted(c.items(),key=lambda a:(-a[1],a[0]))]
    policy={"schema":"vdn.generator-routing.cross-corpus.v24",
            "historical_run":38040167697,
            "historical_artifact":11664759577,
            "historical_result_sha256":V23_SHA,
            "historical_source_commit":ARC1_PIN,
            "target_source_commit":CONCEPT_PIN,
            "candidate_verifier_budget":BUDGET,
            "global_successful_programs":rank(global_freq),
            "signature_successful_programs":{k:rank(c) for k,c in sorted(per_sig.items())},
            "historical_verified_successes":successes,
            "historical_training_checks":src["arm_stats"]["cold"]["total_candidate_verifications"],
            "target_outputs_seen":False,
            "target_tasks_loaded_before_freeze":False,
            "claim_scope":"reordering an existing DSL based on qualified source outcomes"}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(canonical(policy)+b"\n")
    print(json.dumps({"freeze_sha256":sha(output),"total_successes":len(successes),
                      "learned_programs":len(global_freq),
                      "signature_classes":len(per_sig)},indent=2))


def task_files(root):
    tasks={}
    for p in sorted(Path(root).glob("*/*.json")):
        task=json.loads(p.read_text())
        if not ("train" in task and "test" in task): continue
        assert len(task["test"])==3, (p,len(task["test"]))
        tasks[p.stem]=task
    assert len(tasks)==160,len(tasks)
    return tasks


def universe(task):
    pairs=run_v2.v1.task_pairs(task)
    candidate=list(v23.cold(pairs))
    # Fewer than 512 suffice to expose all previously retained source examples;
    # source learned programs must still be implemented by the same generator.
    return candidate[:512]


def fits_shape(p,pairs):
    for x,y in pairs[:1]:
        z=v23.safe_apply(p,x)
        if z is None or run_v2.v1.shape(z)!=run_v2.v1.shape(y):
            return False
    return True


def candidate_order(pool,task,arm,policy,shuffled):
    key=sig(task)
    learned=policy["signature_successful_programs"].get(key,[])
    global_names=policy["global_successful_programs"]
    local_names=(shuffled.get(key,[]) if arm=="permuted_policy" else learned)
    if arm=="cold":
        order={}
    elif arm=="global_memory":
        order={n:(0,i) for i,n in enumerate(global_names)}
    elif arm=="learned_policy":
        # Parenthesized signature class is a minimal routing context.
        order={n:(0,i) for i,n in enumerate(local_names)}
        for i,n in enumerate(global_names): order.setdefault(n,(1,i))
    elif arm=="permuted_policy":
        order={n:(0,i) for i,n in enumerate(local_names)}
        for i,n in enumerate(global_names):order.setdefault(n,(1,i))
    elif arm=="stateless_shape":
        # The strong stateless arm is allowed the same candidate universe and
        # learned general DSL, but not the source-task success assignments.
        order={}
    else:
        raise ValueError(arm)
    if not order:
        return pool
    # Preserve the same candidate set: a pure generator priority update with
    # no loss of grammar, and no inserted privileged answer programs.
    return sorted(pool,key=lambda p:(order.get(p[0],(2,0)),pool.index(p)))


def attempt(task,arm,policy,shuffled,budget=BUDGET):
    pairs=run_v2.v1.task_pairs(task)
    start=time.perf_counter()
    pool=universe(task)
    ordered=candidate_order(pool,task,arm,policy,shuffled)
    checked=0; cheap=0;selected=None;name=None
    for n,program in ordered:
        if not fits_shape(program,pairs):
            cheap+=1
            continue
        if checked>=budget:break
        checked+=1
        if v5.safe_exact(program,pairs):
            selected=program;name=n;break
    return {"program":selected,"name":name,"fit":selected is not None,
            "full_checks":checked,"cheap_shape_rejections":cheap,
            "generated_candidates":len(pool),
            "wall_seconds":time.perf_counter()-start}


def score(policy_path,target_path,out):
    policy=json.loads(Path(policy_path).read_text())
    assert policy["schema"]=="vdn.generator-routing.cross-corpus.v24"
    assert not policy["target_tasks_loaded_before_freeze"]
    tasks=task_files(target_path)
    keys=list(policy["signature_successful_programs"])
    values=[policy["signature_successful_programs"][k] for k in keys]
    random.Random(0x56444e32).shuffle(values)
    shuffled=dict(zip(keys,values))
    arms=("cold","stateless_shape","global_memory","permuted_policy","learned_policy")
    chosen={}
    for arm in arms:
        chosen[arm]={tid:attempt(task,arm,policy,shuffled)
                     for tid,task in sorted(tasks.items())}
    # Program selections are final BEFORE reading ANY protected test output.
    frozen={a:{t:{"name":r["name"],"fit":r["fit"],"full_checks":r["full_checks"]}
               for t,r in rows.items()} for a,rows in chosen.items()}
    out.mkdir(parents=True,exist_ok=True)
    (out/"choices_frozen_before_test.json").write_bytes(canonical(frozen)+b"\n")
    observed={}
    for arm,rows in chosen.items():
        observed[arm]=[
            {"task_id":tid,
             **{k:v for k,v in r.items() if k!="program"},
             "all_three_tests_exact":bool(r["fit"] and v5.safe_solved(r["program"],tasks[tid]))}
            for tid,r in sorted(rows.items())]
    totals={a:{"solved":sum(r["all_three_tests_exact"] for r in rows),
               "fits":sum(r["fit"] for r in rows),
               "candidate_full_checks":sum(r["full_checks"] for r in rows),
               "shape_only_rejections":sum(r["cheap_shape_rejections"] for r in rows),
               "seconds":round(sum(r["wall_seconds"] for r in rows),3)}
            for a,rows in observed.items()}
    maps={a:{r["task_id"]:r for r in rows} for a,rows in observed.items()}
    incremental=sorted(t for t in tasks if maps["learned_policy"][t]["all_three_tests_exact"]
                       and not maps["stateless_shape"][t]["all_three_tests_exact"]
                       and not maps["cold"][t]["all_three_tests_exact"])
    causal=sorted(t for t in tasks if maps["learned_policy"][t]["all_three_tests_exact"]
                  and not maps["permuted_policy"][t]["all_three_tests_exact"]
                  and not maps["global_memory"][t]["all_three_tests_exact"])
    regressions=sorted(t for t in tasks if maps["cold"][t]["all_three_tests_exact"]
                       and not maps["learned_policy"][t]["all_three_tests_exact"])
    solved_common=[t for t in tasks if all(maps[a][t]["all_three_tests_exact"]
                                           for a in ("learned_policy","cold","stateless_shape"))]
    saved_checks=sum(maps["cold"][t]["full_checks"]-
                     maps["learned_policy"][t]["full_checks"] for t in solved_common)
    positive=bool(incremental and causal and not regressions)
    claims={"qualified_cross_corpus_feedback_gain":
            "WARRANTED_BOUNDED" if positive else "UNKNOWN",
            "strict_gain_vs_both_cold_and_shape_stateless":
            "WARRANTED_BOUNDED" if incremental else "UNKNOWN",
            "causal_signature_policy_vs_permuted_and_memory":
            "WARRANTED_BOUNDED" if causal else "UNKNOWN",
            "strict_no_regressions":not regressions,
            "amortized_total_gain":"UNKNOWN",
            "unbounded_recursive_acceleration":"UNKNOWN"}
    res={"schema":"vdn.verifier-feedback.conceptarc.v24",
         "target":"victorvikram/ConceptARC@"+CONCEPT_PIN,
         "source_v23_sha256":V23_SHA,
         "frozen_policy_sha256":sha(policy_path),
         "frozen_choices_sha256":sha(out/"choices_frozen_before_test.json"),
         "task_count":len(tasks),
         "arms":totals,
         "new_protected_solve_ids":incremental,
         "causal_ablation_ids":causal,
         "regressions":regressions,
         "common_solved_checks_saved_vs_cold":saved_checks,
         "source_training_candidate_verifications":policy["historical_training_checks"],
         "claims":claims,"task_rows":observed}
    (out/"result.json").write_bytes(canonical(res)+b"\n")
    print(json.dumps({k:v for k,v in res.items() if k!="task_rows"},indent=2))
    assert len(tasks)==160
    assert all(v["candidate_full_checks"]<=160*BUDGET for v in totals.values())
    assert claims["unbounded_recursive_acceleration"]=="UNKNOWN"


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("freeze","score"),required=True)
    ap.add_argument("--source-v23",type=Path)
    ap.add_argument("--arc1-train",type=Path)
    ap.add_argument("--policy",type=Path,required=True)
    ap.add_argument("--concept-corpus",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.mode=="freeze":
        assert a.source_v23 and a.arc1_train
        freeze(a.source_v23,a.arc1_train,a.policy)
    else:
        assert a.concept_corpus and a.out
        score(a.policy,a.concept_corpus,a.out)
