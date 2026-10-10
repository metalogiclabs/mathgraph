#!/usr/bin/env python3
import itertools, json
from collections import defaultdict

X = range(3)
C = range(3)


def profile(table, x, B):
    return tuple(table[x][c] for c in B)


def classes(table, B):
    buckets = defaultdict(list)
    for x in X:
        buckets[profile(table, x, B)].append(x)
    return tuple(sorted(tuple(v) for v in buckets.values()))


def class_id(cls):
    out = {}
    for i, block in enumerate(cls):
        for x in block:
            out[x] = i
    return out


def congruent(table, B, f):
    cls = classes(table, B)
    cid = class_id(cls)
    for block in cls:
        for x in block:
            for y in block:
                if cid[f[x]] != cid[f[y]]:
                    return False
    return True


def orbit_raw(seed, ops):
    seen = {seed}
    frontier = [seed]
    while frontier:
        x = frontier.pop()
        for f in ops:
            y = f[x]
            if y not in seen:
                seen.add(y)
                frontier.append(y)
    return seen


def induced_op(cls, f):
    cid = class_id(cls)
    out = {}
    for i, block in enumerate(cls):
        images = {cid[f[x]] for x in block}
        if len(images) != 1:
            return None
        out[i] = next(iter(images))
    return out


def orbit_quotient(seed_class, qops):
    seen = {seed_class}
    frontier = [seed_class]
    while frontier:
        q = frontier.pop()
        for f in qops:
            r = f[q]
            if r not in seen:
                seen.add(r)
                frontier.append(r)
    return seen

all_functions = list(itertools.product(X, repeat=len(X)))

def all_tables():
    for bits in itertools.product((0,1), repeat=len(X)*len(C)):
        yield [list(bits[i*len(C):(i+1)*len(C)]) for i in X]

summary = {
    "schema": "verified-developmental-navigation.quotient-capability-compatibility.v52",
    "tables": 0,
    "contexts": 0,
    "operator_checks": 0,
    "congruent_operator_checks": 0,
    "noncongruent_operator_checks": 0,
    "descent_failures": 0,
    "closure_commutation_checks": 0,
    "closure_commutation_failures": 0,
    "counterexample_noncongruent": None,
    "all_checks_pass": True,
}

# Exhaust every protected table, every retained continuation subset, every deterministic operator.
for table in all_tables():
    summary["tables"] += 1
    for mask in range(1 << len(C)):
        B = tuple(c for c in C if mask & (1 << c))
        cls = classes(table, B)
        cid = class_id(cls)
        summary["contexts"] += 1
        for f in all_functions:
            summary["operator_checks"] += 1
            is_cong = congruent(table, B, f)
            qf = induced_op(cls, f)
            if is_cong:
                summary["congruent_operator_checks"] += 1
                if qf is None:
                    summary["descent_failures"] += 1
            else:
                summary["noncongruent_operator_checks"] += 1
                if qf is not None:
                    summary["descent_failures"] += 1
                if summary["counterexample_noncongruent"] is None and len(cls) < len(X):
                    summary["counterexample_noncongruent"] = {
                        "table": table,
                        "B": B,
                        "classes": cls,
                        "operator": f,
                    }

# Test closure/quotient commutation for all ordered pairs of quotient-safe operators.
# Q(Reach_raw(x;F)) must equal Reach_quotient([x];Fbar) when each f respects ~_B.
for table in all_tables():
    for mask in range(1 << len(C)):
        B = tuple(c for c in C if mask & (1 << c))
        cls = classes(table, B)
        cid = class_id(cls)
        safe = []
        for f in all_functions:
            qf = induced_op(cls, f)
            if qf is not None:
                safe.append((f, qf))
        for (f1,q1),(f2,q2) in itertools.product(safe, repeat=2):
            for seed in X:
                summary["closure_commutation_checks"] += 1
                raw = orbit_raw(seed, (f1,f2))
                raw_q = {cid[x] for x in raw}
                qq = orbit_quotient(cid[seed], (q1,q2))
                if raw_q != qq:
                    summary["closure_commutation_failures"] += 1
                    summary["all_checks_pass"] = False
                    raise AssertionError((table,B,cls,f1,f2,seed,raw_q,qq))

if summary["descent_failures"]:
    summary["all_checks_pass"] = False

summary["mathematical_core"] = (
    "An operator acts well-definedly on the continuation-induced quotient exactly when it preserves observational equivalence (is a congruence for ~_B). "
    "Under that condition, raw reachability followed by quotienting equals reachability computed directly on the quotient. "
    "Without congruence, 'act on the quotient' is not well-defined: a single merged class can be sent to multiple quotient classes."
)

out = "verified-developmental-navigation/case_studies/finite_inevitability/results_v52_quotient_capability_compatibility/result.json"
import os
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
