"""Native comparison for qualified SCC-local closure; exact semantic parity required."""
import csv
import random
import statistics
import time
import tracemalloc
from mathgraph_check.warrant_resolution import resolve_graph
from mathgraph_check.qualified_consequence_closure import QualifiedConsequenceClosure
from experiments.capability_lineage_region_baseline import RegionBaseline
from experiments.capability_lineage_paired_benchmark import fixture


def trial(n, seed, scenario, count=60):
    claims, receipts, routes, relations = fixture(n, seed, scenario)
    rng = random.Random(seed + 932)
    ids = [r.id for r in receipts]
    changes = [ids[rng.randrange(len(ids))] for _ in range(count)]
    if scenario == "qualification":
        changes[:4] = ["bridge_verifier", "bridge_qualification",
                       "bridge_verifier", "bridge_qualification"]
    if scenario == "shared":
        changes[::4] = ["e0"] * len(changes[::4])
    engines, memory = {}, {}
    for name, cls in (("compiled", QualifiedConsequenceClosure),
                      ("region", RegionBaseline)):
        tracemalloc.start()
        engines[name] = cls(claims, routes, receipts, relations=relations)
        memory[name] = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    timing = {"compiled": [], "region": [], "canonical": []}
    withdrawn = set()
    for i, rid in enumerate(changes):
        live = rid in withdrawn
        if live:
            withdrawn.remove(rid)
        else:
            withdrawn.add(rid)
        names = ("compiled", "region") if i % 2 == 0 else ("region", "compiled")
        for name in names:
            t0 = time.perf_counter_ns()
            engines[name].update(rid, live)
            timing[name].append((time.perf_counter_ns() - t0) / 1000)
        t0 = time.perf_counter_ns()
        oracle = resolve_graph(claims, routes, receipts,
                               withdrawn=frozenset(withdrawn), relations=relations)
        timing["canonical"].append((time.perf_counter_ns() - t0) / 1000)
        for name in names:
            assert engines[name].states() == dict(oracle.states), (name, scenario, i, "states")
            assert engines[name].active_routes() == oracle.active_routes, (name, scenario, i, "routes")
    return [{
        "scenario": scenario, "claims": n, "seed": seed, "method": name,
        "mean_us": round(statistics.mean(timing[name]), 3),
        "worst_observed_us": round(max(timing[name]), 3),
        "p95_us": round(sorted(timing[name])[int(.95*(count - 1))], 3),
        "constructor_peak_bytes": memory.get(name, ""),
        "updates": count
    } for name in timing]


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    a = p.parse_args()
    rows = [row for scenario in ("dag", "shared", "cycle", "qualification")
            for n in (80, 240) for seed in (0, 1)
            for row in trial(n, seed, scenario)]
    with open(a.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
