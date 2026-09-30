"""Prospective TaskSAT shadow-carrier experiment selected by Crystal controller.

This is deliberately a shadow model, not an upstream patch.  It tests the exact
missing distinction from the frozen ROS residual: zones are the sorted unique
set {0,H} union boundaries of INCLUDED tasks only.

The oracle is direct event semantics, independent of zone construction.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path

@dataclass(frozen=True)
class Task:
    name: str
    start: int
    end: int
    included: bool
    state_end: int = 0
    cumulative_end: int = 0
    rate_start: int = 0
    rate_end: int = 0

def shadow_carrier(tasks, horizon):
    return sorted({0, horizon} | {
        x for t in tasks if t.included for x in (t.start, t.end)
    })

def legacy_carrier_requires(tasks, horizon):
    # Current TaskSAT _encode_zones allocates 2*all_tasks+2 strictly increasing
    # zones and requires every task start/end to align, regardless of inclusion.
    return sorted({0, horizon} | {x for t in tasks for x in (t.start, t.end)})

def direct_semantics(tasks, horizon):
    active=[t for t in tasks if t.included]
    state=0
    cumulative=0
    rate=0
    value=0
    temporal_ok=True
    events={}
    for t in active:
        events.setdefault(t.start,[]).append(("start",t))
        events.setdefault(t.end,[]).append(("end",t))
    last=0
    for time in sorted(set([0,horizon]+list(events))):
        value += rate*(time-last)
        for kind,t in sorted(events.get(time,[]), key=lambda p:(p[0]!="end",p[1].name)):
            if kind=="end":
                state=t.state_end or state
                cumulative += t.cumulative_end
                rate += t.rate_end
            else:
                rate += t.rate_start
        temporal_ok &= cumulative >= 0 and value >= -100
        last=time
    return (state,cumulative,value,rate,temporal_ok)

def zone_semantics(tasks,horizon,carrier):
    active=[t for t in tasks if t.included]
    state=0; cumulative=0; rate=0; value=0; temporal_ok=True
    last=carrier[0]
    for time in carrier:
        value += rate*(time-last)
        ending=[t for t in active if t.end==time]
        starting=[t for t in active if t.start==time]
        for t in sorted(ending,key=lambda x:x.name):
            state=t.state_end or state
            cumulative += t.cumulative_end
            rate += t.rate_end
        for t in sorted(starting,key=lambda x:x.name):
            rate += t.rate_start
        temporal_ok &= cumulative >= 0 and value >= -100
        last=time
    return (state,cumulative,value,rate,temporal_ok)

def run():
    H=8
    templates=[
        Task("state",1,2,True,state_end=2),
        Task("cumulative",2,4,True,cumulative_end=3),
        Task("rate",3,6,True,rate_start=2,rate_end=-2),
        Task("optional",4,7,True,state_end=5,cumulative_end=1,rate_start=-1,rate_end=1),
    ]
    rows=[]
    for mask in product([False,True], repeat=4):
        tasks=[Task(**{**t.__dict__,"included":inc}) for t,inc in zip(templates,mask)]
        carrier=shadow_carrier(tasks,H)
        oracle=direct_semantics(tasks,H)
        got=zone_semantics(tasks,H,carrier)
        rows.append({
            "mask":mask,
            "carrier":carrier,
            "legacy_carrier":legacy_carrier_requires(tasks,H),
            "oracle":oracle,
            "shadow":got,
            "match":got==oracle,
        })
    assert all(r["match"] for r in rows), rows

    # Four explicit separators: excluding each task removes both of its
    # boundaries.  This is the exact distinction the current unconditional
    # carrier cannot express.
    separators=[]
    for idx,t in enumerate(templates):
        tasks=[Task(**{**x.__dict__,"included": i!=idx}) for i,x in enumerate(templates)]
        shadow=shadow_carrier(tasks,H)
        legacy=legacy_carrier_requires(tasks,H)
        sep=t.start in legacy and t.end in legacy and t.start not in shadow and t.end not in shadow
        separators.append({"task":t.name,"shadow":shadow,"legacy":legacy,"separates":sep})
    assert all(x["separates"] for x in separators), separators

    # Representative consequence classes are all exercised by the full case.
    full=templates
    oracle=direct_semantics(full,H)
    shadow=zone_semantics(full,H,shadow_carrier(full,H))
    assert oracle==shadow
    result={
      "schema":"mathgraph.tasksat-shadow-inclusion-carrier-v1",
      "upstream":"nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0",
      "declared_boundary":"bounded shadow semantics; not an upstream TaskNetSMT patch",
      "enumerated_inclusion_worlds":len(rows),
      "exact_matches":sum(r["match"] for r in rows),
      "separators_closed":sum(x["separates"] for x in separators),
      "separators_total":len(separators),
      "consequence_classes":["state","cumulative","rate/value","temporal"],
      "status":"WARRANTED_BOUNDED_SHADOW_CARRIER" if all(r["match"] for r in rows) else "REJECTED",
      "next_residual":"integrate conditional/quotiented carrier into real TaskNetSMT encoding and differential-test public tasknets"
    }
    out=Path(__file__).with_name("RESULT.json")
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    run()
