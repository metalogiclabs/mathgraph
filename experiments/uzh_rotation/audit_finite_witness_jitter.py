#!/usr/bin/env python3
"""Independent exhaustive certificate checker for finite timing-jitter model.

Neither compiler nor estimator is imported. The auditor recomputes geometric
prediction sets, exact minimum permitted witness subsets, every candidate
update and both source-bound premises from independently retained raw traces.
"""

import argparse
from itertools import combinations
import json
from types import SimpleNamespace


def brute_force_jitter_plan(reference, hypotheses, permitted_steps,
                            noise_budget, jitter_bins):
    possibilities = sorted(set(hypotheses))
    pairs = list(combinations(possibilities,2))
    if not pairs:
        return ()
    eligible=[]
    for step in sorted(set(permitted_steps)):
        separated=set()
        for a,b in pairs:
            alternatives_a={reference[(a+step+d)%len(reference)]
                            for d in range(-jitter_bins,jitter_bins+1)}
            alternatives_b={reference[(b+step+d)%len(reference)]
                            for d in range(-jitter_bins,jitter_bins+1)}
            disjoint=all(bin(x^y).count("1")>2*noise_budget
                         for x in alternatives_a for y in alternatives_b)
            if disjoint:
                separated.add((a,b))
        if separated:
            eligible.append((step,separated))
    if set().union(*(s for _,s in eligible)) != set(pairs):
        return None
    for n in range(1, min(len(eligible),len(pairs))+1):
        winners=[]
        for subset in combinations(eligible,n):
            if set().union(*(s for _,s in subset)) == set(pairs):
                winners.append(tuple(step for step,_ in subset))
        if winners:
            return min(winners,key=lambda s:(s[-1],s))
    raise AssertionError("Failed independent minimum-cover enumeration")


def independent_filter(reference, candidates, step, column, error=2, jitter=1):
    survivors=[]
    for candidate in candidates:
        for delta in range(-jitter,jitter+1):
            expected=reference[(candidate+step+delta)%len(reference)]
            if bin(expected^column).count("1")<=error:
                survivors.append(candidate)
                break
    return tuple(survivors)


def audit_jitter_trial(trial, acquired, continuous):
    first=tuple(trial.reference)
    actual=tuple(trial.physical_source)
    columns=tuple(trial.columns)
    offsets=tuple(trial.timing_offsets)
    candidates=(0,16,32,48)
    assert len(first)==len(actual)==64
    assert len(columns)==len(offsets)>=17
    assert trial.true_bin in candidates
    for template, learned in zip(actual,first):
        assert (template^learned).bit_count()<=1,"FIRST_TURN_ERROR_BOUND_BROKEN"
    for i,(obs,jitter) in enumerate(zip(columns,offsets)):
        assert -1<=jitter<=1,"TIMING_BOUND_BROKEN"
        if obs is not None:
            physical=actual[(trial.true_bin+i+jitter)%64]
            assert (physical^obs).bit_count()<=1,"RUNTIME_ERROR_BOUND_BROKEN"
    for outcome,scheduled in ((acquired,True),(continuous,False)):
        live=candidates
        observed=[]
        if scheduled:
            next_step=1
            for step in outcome.attempted_steps:
                oracle=brute_force_jitter_plan(first,live,
                                               tuple(range(next_step,len(columns))),2,1)
                assert oracle is not None and len(oracle)>0
                assert step==oracle[0],"NOT_A_MINIMUM_FUTURE_WITNESS"
                if columns[step] is not None:
                    observed.append(step)
                    live=independent_filter(first,live,step,columns[step])
                    assert trial.true_bin in live,"TRUE_CANDIDATE_DISCARDED"
                next_step=step+1
                if len(live)==1:
                    assert outcome.decision_step==step
                    break
            if len(live)>1:
                assert brute_force_jitter_plan(first,live,
                   tuple(range(next_step,len(columns))),2,1) is None
                assert outcome.status=="UNKNOWN_OBSTRUCTION"
        else:
            for step in range(1,len(columns)):
                if columns[step] is None:
                    continue
                observed.append(step)
                live=independent_filter(first,live,step,columns[step])
                assert trial.true_bin in live
                if len(live)==1:
                    assert outcome.decision_step==step
                    break
        assert tuple(observed)==tuple(outcome.acquired_steps)
        assert outcome.observations_processed==len(observed)
        assert outcome.candidates==live
        assert (outcome.status=="AUTHORIZED")== (len(live)==1)
        assert outcome.accepted_bin==(live[0] if len(live)==1 else None)
        if outcome.accepted_bin is not None:
            assert outcome.accepted_bin==trial.true_bin,"FALSE_AUTHORIZED_HEADING"
    if acquired.status=="AUTHORIZED":
        assert continuous.status=="AUTHORIZED"
        assert continuous.decision_step<=acquired.decision_step
    return True


def exhaust_jitter_observations(reference, hypotheses=(0,16,32,48),
                                 times=(7,13), error=2, timing_jitter=1,
                                 bits=16):
    """All 4 * 3^2 * (1+16+120)^2 input combinations, no random sampling."""
    if error!=2 or timing_jitter!=1:
        raise ValueError("Exhaustive radius-two verifier has fixed assumptions")
    patterns=[0]
    patterns.extend(1<<b for b in range(bits))
    patterns.extend((1<<a)|(1<<b) for a in range(bits) for b in range(a+1,bits))
    count=0
    for true_bin in hypotheses:
        for first_offset in range(-1,2):
            pred1=reference[(true_bin+times[0]+first_offset)%len(reference)]
            for second_offset in range(-1,2):
                pred2=reference[(true_bin+times[1]+second_offset)%len(reference)]
                for error1 in patterns:
                    obs1=pred1^error1
                    survivors=independent_filter(reference,hypotheses,times[0],obs1)
                    assert true_bin in survivors
                    for error2 in patterns:
                        last=independent_filter(reference,survivors,times[1],pred2^error2)
                        assert last==(true_bin,), (true_bin,first_offset,second_offset,error1,error2,last)
                        count+=1
    return count


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("traces",nargs="+")
    args=parser.parse_args()
    for path in args.traces:
        r=json.load(open(path,encoding="utf-8"))
        t=SimpleNamespace(reference=r["reference"],physical_source=r["physical_source_grader_only"],
            true_bin=r["true_bin"],columns=r["columns"],timing_offsets=r["timing_offsets_grader_only"])
        outcomes=[]
        for name in ("acquired","continuous"):
            d=dict(r[name])
            for key in ("candidates","attempted_steps","acquired_steps"):
                d[key]=tuple(d[key])
            outcomes.append(SimpleNamespace(**d))
        audit_jitter_trial(t,*outcomes)
        print("AUDIT PASS",path,"bounded jitter, source error and exact minimum plan")


if __name__=="__main__":
    main()
