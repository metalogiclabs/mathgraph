"""Paired timing and tracemalloc benchmark; correctness checked after every update."""
import argparse
import csv
import random
import statistics
import time
import tracemalloc

from mathgraph_check.warrant_resolution import Claim, Receipt, Route, QualifiedRelation, resolve_graph
from mathgraph_check.incremental_closure import IncrementalClosure
from experiments.capability_lineage_agenda_baseline import AgendaBaseline


def fixture(n, seed, scenario):
    rng = random.Random(seed)
    scope = "synthetic:paired"
    claims = [Claim(f"c{i}", "formal", scope) for i in range(n)]
    receipts = [Receipt(f"e{i}", "formal", scope) for i in range(max(8, n // 8))]
    routes = []
    for i in range(n):
        parents = tuple(f"c{k}" for k in rng.sample(range(i), min(i, 2)))
        for j in range(2):
            evidence = tuple(dict.fromkeys((f"e{rng.randrange(len(receipts))}", "e0")))
            routes.append(Route(f"c{i}", evidence, parents if j == 0 else ()))
    if scenario in ("cycle", "qualification"):
        routes.append(Route("c0", ("e0",), (f"c{n-1}",)))
    relations = ()
    if scenario == "qualification":
        receipts += [Receipt("bridge_verifier", "formal", scope),
                     Receipt("bridge_qualification", "formal", scope),
                     Receipt("external", "documentary", "other")]
        claims += [Claim("source", "documentary", "other")]
        routes.append(Route("source", ("external",)))
        bridge = Route("c0", ("external",), ("source",), "verified_bridge")
        routes.append(bridge)
        relations = (QualifiedRelation("verified_bridge", "documentary", "other",
                      "formal", scope, "bridge_verifier", ("bridge_qualification",), bridge),)
    return claims, receipts, list(dict.fromkeys(routes)), relations


def bench(n, seed, scenario, updates):
    claims, receipts, routes, relations = fixture(n, seed, scenario)
    ids = [r.id for r in receipts]
    rng = random.Random(seed + 991)
    changes = [ids[rng.randrange(len(ids))] for _ in range(updates)]
    if scenario == "qualification":
        changes[:4] = ["bridge_verifier", "bridge_qualification", "bridge_verifier", "bridge_qualification"]
    if scenario == "shared":
        changes[::4] = ["e0"] * len(changes[::4])
    candidates = [("hybrid", IncrementalClosure), ("agenda", AgendaBaseline)]
    engines = {}
    memory = {}
    for name, typ in candidates:
        tracemalloc.start()
        obj = typ(claims, routes, receipts, relations=relations)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        engines[name] = obj
        memory[name] = peak
    times = {name: [] for name, _ in candidates}
    times["canonical"] = []
    withdrawn = set()
    for rid in changes:
        live = rid in withdrawn
        if live:
            withdrawn.remove(rid)
        else:
            withdrawn.add(rid)
        order = candidates if len(times["canonical"]) % 2 == 0 else list(reversed(candidates))
        for name, _ in order:
            t0 = time.perf_counter_ns()
            engines[name].update(rid, live)
            times[name].append((time.perf_counter_ns() - t0) / 1000)
        t0 = time.perf_counter_ns()
        expected = resolve_graph(claims, routes, receipts, withdrawn=frozenset(withdrawn),
                                 relations=relations)
        times["canonical"].append((time.perf_counter_ns() - t0) / 1000)
        for name, _ in candidates:
            assert engines[name].states() == dict(expected.states), (name, scenario, rid, "states")
            assert engines[name].active_routes() == expected.active_routes, (name, scenario, rid, "routes")
    rows = []
    for name in ("hybrid", "agenda", "canonical"):
        samples = times[name]
        rows.append(dict(scenario=scenario, claims=n, seed=seed, method=name,
                         updates=updates, mean_us=round(statistics.mean(samples), 3),
                         p95_us=round(sorted(samples)[int(.95*(len(samples)-1))], 3),
                         worst_us=round(max(samples), 3),
                         constructor_peak_bytes=memory.get(name, 0),
                         memory_boundary="constructor tracemalloc; excludes graph inputs and updates"))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--updates", type=int, default=80)
    args = parser.parse_args()
    rows = []
    for scenario in ("dag", "shared", "cycle", "qualification"):
        for n in (80, 240):
            for seed in (0, 1):
                rows.extend(bench(n, seed, scenario, args.updates))
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
