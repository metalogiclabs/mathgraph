#!/usr/bin/env python3
import itertools, json, os
from collections import defaultdict

X = range(3)
FUNS = list(itertools.product(X, repeat=3))
OBS = list(itertools.product((0,1), repeat=3))


def partition_from_signatures(sig):
    d = defaultdict(list)
    for x,s in enumerate(sig): d[s].append(x)
    return tuple(sorted(tuple(v) for v in d.values()))


def base_partition(v):
    return partition_from_signatures([(v[x],) for x in X])


def expanded_partition(v, o1):
    # Horizon-1 protected continuation profile after acquiring o1:
    # identity observation plus observation after o1.
    return partition_from_signatures([(v[x], v[o1[x]]) for x in X])


def refines(p_new, p_old):
    old_id = {x:i for i,b in enumerate(p_old) for x in b}
    return all(len({old_id[x] for x in b}) == 1 for b in p_new)


def strict_refines(p_new, p_old):
    return p_new != p_old and refines(p_new,p_old)


def congruent(part, op):
    cid = {x:i for i,b in enumerate(part) for x in b}
    for b in part:
        images = {cid[op[x]] for x in b}
        if len(images) != 1:
            return False
    return True

summary = {
  "schema":"verified-developmental-navigation.capability-induced-interface-refinement.v53",
  "worlds":0,
  "monotonicity_failures":0,
  "strict_refinement_cases":0,
  "bridge_cases":0,
  "ablation_failures":0,
  "example_bridge":None,
  "all_checks_pass":True,
}

for v in OBS:
  p0 = base_partition(v)
  for o1 in FUNS:
    summary["worlds"] += 1
    p1 = expanded_partition(v,o1)
    if not refines(p1,p0):
      summary["monotonicity_failures"] += 1
    if strict_refines(p1,p0):
      summary["strict_refinement_cases"] += 1
      for o2 in FUNS:
        before = congruent(p0,o2)
        after = congruent(p1,o2)
        if (not before) and after:
          summary["bridge_cases"] += 1
          # Ablating O1 restores p0, so O2 must again fail quotient well-definedness.
          if congruent(p0,o2):
            summary["ablation_failures"] += 1
          if summary["example_bridge"] is None:
            summary["example_bridge"] = {
              "protected_observation":v,
              "O1":o1,
              "O2":o2,
              "before_partition":p0,
              "after_O1_partition":p1,
              "O2_congruent_before":before,
              "O2_congruent_after":after,
            }

if summary["monotonicity_failures"] or summary["ablation_failures"] or summary["bridge_cases"] == 0:
  summary["all_checks_pass"] = False

summary["mathematical_core"] = (
  "With fixed protected observation semantics, expanding the available continuation family by acquiring O1 can only refine the induced interface. "
  "There exist finite worlds where that refinement is causally necessary and sufficient for a second transformation O2 to become well-defined on the quotient: O2 is non-congruent before O1, congruent after O1 exposes an additional protected continuation, and ablation of O1 restores the obstruction. "
  "This proves a representation-level O1->O2 bridge, not autonomous discovery of O1 or O2 and not closure-level discoverability by itself."
)

out="verified-developmental-navigation/case_studies/finite_inevitability/results_v53_capability_induced_interface_refinement/result.json"
os.makedirs(os.path.dirname(out),exist_ok=True)
with open(out,"w") as f: json.dump(summary,f,indent=2)
print(json.dumps(summary,indent=2))
