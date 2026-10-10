#!/usr/bin/env python3
"""VDN prospective generator-feedback experiment.

Source learning: exact V4 source result, pinned GitHub Actions run 33038153009.
Development cohort: hash-frozen 1/5 of ARC-AGI-1 training, for meta update only.
Protected cohort: disjoint 4/5 of ARC-AGI-1 training; its test outputs are not
observed before the generator policy and all per-task choices are frozen.

This is a bounded empirical test of L0 residual -> L1 operator -> L2 discovery
policy -> L1 generated candidates -> protected L0 solve; no generic ARC or
unbounded recursion claim. Distinguish cost under declared search ordering from
old-language impossibility. In particular, all public data is public.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v4_composition as v4
import run_v5_retention as v5

SOURCE_ARC="399030444e0ab0cc8b4e199870fb20b863846f34"
SOURCE_V4_RUN=33038153009
SOURCE_V4_ARTIFACT=9632884567
BASE_BUDGET=128
# Source-derived stored macro executables are the ONLY retained programs.
MACROS=tuple(v5.MACROS)
VALID_FAMILIES=tuple(run_v2.NEW_BASE)


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def h(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def safe_apply(p,g):
    try:
        return p(g)
    except Exception:
        return None


def source_policy(path):
    """Induce shared *first stage* from independently verified V4 winners.

    No prefix name, task ID or output is encoded in the generator choice. The
    source V4 artifact is a historical training source and is never called
    prospective evidence for its own four winning tasks.
    """
    report=json.loads(Path(path).read_text())
    assert report["schema"]=="verified-developmental-navigation.arc-depth2-composition.v4"
    body=report["arc_agi1"]
    assert body["source_commit"]==SOURCE_ARC
    assert body["evaluation_tasks"]==400
    assert body["truncated_tasks"]==[]
    wins=[r for r in body["rows"]
          if r["depth2_solved"] and not r["base_solved"]]
    assert len(wins)>=3
    # Derive stage-1 code shared by different verified programs.
    groups=collections.defaultdict(list)
    for r in wins:
        if " THEN " not in r["depth2_program"]:
            continue
        left,right=r["depth2_program"].split(" THEN ",1)
        groups[left].append((r["task"],right,r["depth2_family"].split("->")[-1]))
    choices=[(p,x) for p,x in groups.items()
             if len({tid for tid,_,_ in x})>=2
             and len({suffix_family for _,_,suffix_family in x})>=2]
    assert choices,"no cross-family reusable prefix in source"
    prefix,records=sorted(choices,key=lambda x:(-len(x[1]),x[0]))[0]
    suffix_count=collections.Counter(f for _,_,f in records)
    suffixes=[f for f,_ in sorted(suffix_count.items(),
                                 key=lambda kv:(-kv[1],kv[0]))]
    assert len(suffixes)>=2
    return {"schema":"vdn.learned_generator.v1",
            "source_run":SOURCE_V4_RUN,
            "source_artifact":SOURCE_V4_ARTIFACT,
            "source_witness_tasks":sorted(tid for tid,_,_ in records),
            "learned_prefixes":[prefix],
            "learned_suffix_families":suffixes,
            "preferred_exact_suffixes":[],
            "evidence":"at least two source-distinct successes and two suffix families",
            "claim":"search-policy bias only, not a new primitive or universal closure"}


def candidate_from_name(pairs,name):
    for fam in VALID_FAMILIES:
        for candidate_name,p in run_v2.programs(fam,pairs):
            if candidate_name==name:
                return p
    return None


def proposed(prefixes,pairs,suffixes,prioritized_suffixes=()):
    """Generate *new composite candidates*, not merely look up old answers."""
    for prefix in prefixes:
        p1=candidate_from_name(pairs,prefix)
        if p1 is None: continue
        transformed=[]
        for x,y in pairs:
            z=safe_apply(p1,x)
            if z is None:
                break
            transformed.append((z,y))
        if len(transformed)!=len(pairs): continue
        collected=[]
        for fam in suffixes:
            for name,p2 in run_v2.programs(fam,transformed):
                def comp(g,p1=p1,p2=p2):
                    z=safe_apply(p1,g)
                    return None if z is None else safe_apply(p2,z)
                collected.append((prefix+" THEN "+name,comp))
        priorities={n:i for i,n in enumerate(prioritized_suffixes)}
        collected.sort(key=lambda item:(0,priorities[item[0].split(" THEN ",1)[1]])
                       if item[0].split(" THEN ",1)[1] in priorities else (1,0))
        yield from collected


def cold(pairs):
    # Exact original bounded V4 generator: primitives then all lawful depth2.
    firsts=list(v4.all_programs(pairs))
    for _,name,p in firsts:
        yield "BASE:"+name,p
    for _,n1,p1 in firsts:
        trans=[]
        for x,y in pairs:
            z=safe_apply(p1,x)
            if z is None:break
            trans.append((z,y))
        if len(trans)!=len(pairs):continue
        for _,n2,p2 in v4.all_programs(trans):
            def comp(g,p1=p1,p2=p2):
                z=safe_apply(p1,g)
                return None if z is None else safe_apply(p2,z)
            yield n1+" THEN "+n2,comp


def strong_stateless(pairs):
    """Strong structural stateless search, no learned prefix.

    It knows the *same DSL* and both composition suffix families, uses dimension
    mismatch to prioritize composition, but searches all concat prefixes
    without consulting source success traces.
    """
    # Same public operator primitives and family options available to everybody.
    concat=list(run_v2.concat_programs(pairs))
    target_is_larger=all(run_v2.v1.shape(y)[0]>=run_v2.v1.shape(x)[0]
                         and run_v2.v1.shape(y)[1]>=run_v2.v1.shape(x)[1]
                         for x,y in pairs)
    if target_is_larger:
        for prefix,_ in concat:
            yield from proposed([prefix],pairs,("concat_symmetry","tile_grid"))
    else:
        for prefix,_ in concat:
            yield from proposed([prefix],pairs,VALID_FAMILIES)
    yield from cold(pairs)


def stream(pairs,arm,policy):
    if arm in ("macro_only","full_v1","full_v2"):
        for name,p in MACROS:
            yield "MACRO:"+name,p
    if arm in ("generator_v1","full_v1","full_v2"):
        yield from proposed(policy["learned_prefixes"],pairs,
                            policy["learned_suffix_families"],
                            policy["preferred_exact_suffixes"])
    if arm=="stateless_schema":
        yield from strong_stateless(pairs)
    else:
        yield from cold(pairs)


def attempt(task,arm,policy,budget=BASE_BUDGET):
    pairs=run_v2.v1.task_pairs(task)
    seen=set()
    tried=0
    generated=0
    start=time.perf_counter()
    for name,p in stream(pairs,arm,policy):
        generated+=1
        # Same generated candidate repeated under multiple authorities does not
        # require paying a second official demonstration check.
        if name in seen:continue
        seen.add(name)
        if tried>=budget:break
        tried+=1
        if v5.safe_exact(p,pairs):
            return {"fit":True,"attempts":tried,"generated":generated,
                    "name":name,"program":p,"wall_seconds":time.perf_counter()-start}
    return {"fit":False,"attempts":tried,"generated":generated,
            "name":None,"program":None,"wall_seconds":time.perf_counter()-start}


def record_selection(x):
    return {k:v for k,v in x.items() if k!="program"}


def split_tasks(tasks):
    dev,protected={},{}
    for tid,task in sorted(tasks.items()):
        # Predeclared deterministic split, not chosen from scores.
        (dev if int(hashlib.sha256(tid.encode()).hexdigest(),16)%5==0
         else protected)[tid]=task
    assert len(tasks)==400 and 50<len(dev)<120 and 270<len(protected)<350
    assert not(set(dev)&set(protected))
    return dev,protected


def learn_second_policy(policy,dev,budget=BASE_BUDGET):
    """A true second-level update is admitted only from development witnesses.

    For dev tasks, demonstration fit chooses a program; the dev test output is
    consulted *only here* to admit successful discovery updates. Frozen
    protection starts afterwards on a disjoint set.
    """
    extra_prefixes=collections.Counter()
    suffix_names=collections.Counter()
    dev_counts=collections.Counter()
    causal=[]
    t0=time.perf_counter()
    for tid,task in dev.items():
        r1=attempt(task,"generator_v1",policy,budget)
        memory=attempt(task,"macro_only",policy,budget)
        dev_counts["generator_candidate_checks"]+=r1["attempts"]
        dev_counts["memory_candidate_checks"]+=memory["attempts"]
        if r1["fit"] and v5.safe_solved(r1["program"],task):
            dev_counts["generator_verified_solved"]+=1
            # Extract candidate *generator* update, not the literal task answer.
            if " THEN " in r1["name"]:
                pref,suff=r1["name"].split(" THEN ",1)
                if not (memory["fit"] and v5.safe_solved(memory["program"],task)):
                    extra_prefixes[pref]+=1
                    suffix_names[suff]+=1
                    causal.append({"dev_task":tid,"new_generator_program":r1["name"],
                                   "memory_fit":bool(memory["fit"]),
                                   "source_train_fit":True,
                                   "dev_heldout_solved":True})
        if memory["fit"] and v5.safe_solved(memory["program"],task):
            dev_counts["memory_verified_solved"]+=1
    # Meta-policy uses only dev data and original V4 source. Prefer newly
    # successful suffixes; no independently designed per-target condition.
    v2=dict(policy)
    # Only a non-source-solved dev success licenses a policy update.
    old=set(policy["preferred_exact_suffixes"])
    ranked=[s for s,_ in suffix_names.most_common(8) if s not in old]
    v2["preferred_exact_suffixes"]=ranked
    v2["dev_new_witnesses"]=causal
    v2["policy_changed"]=bool(ranked)
    v2["parent_policy_sha256"]=h(policy)
    return v2,dict(dev_counts),time.perf_counter()-t0


def measure(protected,policies,budget):
    # Freeze ALL policy bytes prior to accessing any public protected test output.
    chosen={}
    for arm in ("cold","macro_only","generator_v1","full_v1","full_v2","stateless_schema"):
        p=policies["v2"] if arm=="full_v2" else policies["v1"]
        rows={}
        for tid,task in protected.items():
            r=attempt(task,arm,p,budget)
            rows[tid]=r
        chosen[arm]=rows
    # Only from this point on are protected 'test' fields allowed to influence
    # scores. Task selection programs are never modified after this boundary.
    outcomes={}
    for arm,rows in chosen.items():
        records=[]
        for tid,r in rows.items():
            solved=bool(r["fit"] and v5.safe_solved(r["program"],protected[tid]))
            records.append({**record_selection(r),"task":tid,
                            "protected_solved":solved})
        outcomes[arm]=records
    return outcomes


def stats(rows):
    return {"tasks":len(rows),"solved":sum(x["protected_solved"] for x in rows),
            "fits":sum(x["fit"] for x in rows),
            "total_candidate_verifications":sum(x["attempts"] for x in rows),
            "wall_seconds":round(sum(x["wall_seconds"] for x in rows),3)}


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--arc1-train",type=Path)
    ap.add_argument("--v4-result",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--budget",type=int,default=BASE_BUDGET)
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args(argv)
    if args.selftest:
        x=[{"train":[{"input":[[1,2]],"output":[[2,1,1,2]]}],
            "test":[{"input":[[3,4]],"output":[[4,3,3,4]]}]}]
        p=source_policy.__name__
        assert p=="source_policy"
        assert run_v2.v1.exact_on_pairs(v5.macro_quad_sym,
             [(((1,2),),(((2,1,1,2)),))]) is False
        print("VDN_GENERATOR_POLICY_SELFTEST_OK")
        return

    assert args.budget>0 and args.budget<=1000
    args.out.mkdir(parents=True,exist_ok=True)
    tasks=run_v2.v1.load_tasks(args.arc1_train)
    dev,protected=split_tasks(tasks)
    policy1=source_policy(args.v4_result)
    policy1["budget"]=args.budget
    policy1["source_result_sha256"]=hashlib.sha256(args.v4_result.read_bytes()).hexdigest()
    (args.out/"policy_v1_frozen.json").write_bytes(canonical(policy1)+b"\n")
    policy2,dev_stats,dev_seconds=learn_second_policy(policy1,dev,args.budget)
    (args.out/"policy_v2_frozen.json").write_bytes(canonical(policy2)+b"\n")
    frozen={"schema":"vdn.generator-feedback.freeze.v1",
            "arc_source":SOURCE_ARC,"source_v4_run":SOURCE_V4_RUN,
            "source_v4_artifact":SOURCE_V4_ARTIFACT,
            "source_result_sha256":policy1["source_result_sha256"],
            "dev_ids_sha256":h(sorted(dev)),
            "protected_ids_sha256":h(sorted(protected)),
            "dev_count":len(dev),"protected_count":len(protected),
            "policy1_sha256":h(policy1),"policy2_sha256":h(policy2),
            "budget_per_task_per_arm":args.budget,
            "dev_stats":dev_stats,"dev_cost_wall_seconds":dev_seconds,
            "dev_evidence":policy2["dev_new_witnesses"],
            "protected_outputs_inspected_pre_freeze":False}
    (args.out/"freeze.json").write_bytes(canonical(frozen)+b"\n")

    # Do not read protected held-out scores until after the policy and candidate
    # selection boundaries have been frozen. Frozen script/commit is stronger
    # than simply freezing a JSON file.
    result=measure(protected,{"v1":policy1,"v2":policy2},args.budget)
    summary={k:stats(v) for k,v in result.items()}
    index={arm:{v["task"]:v for v in rows} for arm,rows in result.items()}
    wins1=sorted(tid for tid in protected
                 if index["full_v1"][tid]["protected_solved"]
                 and not index["macro_only"][tid]["protected_solved"])
    wins2=sorted(tid for tid in protected
                 if index["full_v2"][tid]["protected_solved"]
                 and not index["full_v1"][tid]["protected_solved"])
    independent=sorted(tid for tid in protected
                       if index["full_v2"][tid]["protected_solved"]
                       and not index["stateless_schema"][tid]["protected_solved"])
    regression=sorted(tid for tid in protected
                      if index["full_v1"][tid]["protected_solved"]
                      and not index["full_v2"][tid]["protected_solved"])
    claim={
        "source_v4_to_generator1":"WARRANTED_BOUNDED_SOURCE_DERIVATION",
        "generator1_protected_gain_vs_memory":
            "WARRANTED_BOUNDED" if wins1 else "UNKNOWN",
        "meta_generator2_feedback_closed":
            "WARRANTED_BOUNDED" if policy2["policy_changed"] and wins2 and not regression
            else "UNKNOWN",
        "generator2_strict_gain_vs_strong_stateless":
            "WARRANTED_BOUNDED" if independent else "UNKNOWN",
        "unbounded_recursive_acceleration":"UNKNOWN",
        "real_ARC_generalization":"UNKNOWN"
    }
    output={"schema":"vdn.generator-feedback.prospective-arc.v1",
            "authority":{"arc1_train_commit":SOURCE_ARC,
                         "v4_run":SOURCE_V4_RUN,
                         "v4_artifact":SOURCE_V4_ARTIFACT},
            "freeze":frozen,
            "policy1":policy1,"policy2":policy2,
            "arm_stats":summary,
            "new_generator1_solves_over_memory":wins1,
            "new_generator2_solves_over_generator1":wins2,
            "generator2_solves_beyond_strong_stateless":independent,
            "generator2_regressions":regression,
            "claims":claim,
            "arm_results":result}
    (args.out/"result.json").write_bytes(canonical(output)+b"\n")
    print(json.dumps({"source":output["authority"],"freeze":frozen,
                      "summary":summary,"wins1":wins1,"wins2":wins2,
                      "independent":independent,"regressions":regression,
                      "claims":claim},indent=2))
    assert len(protected)+len(dev)==400
    assert all(z["total_candidate_verifications"]<=args.budget*len(protected)
               for z in summary.values())
    assert claim["unbounded_recursive_acceleration"]=="UNKNOWN"


if __name__=="__main__":
    main()
