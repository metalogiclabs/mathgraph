"""Bounded native benchmark: canonical reclosure vs experimental DAG update.

Reports sample statistics, not a worst-case or real-time guarantee.
"""
import argparse
import csv
import random
import statistics
import time
from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph
from mathgraph_check.incremental_closure import IncrementalClosure


def graph(size, seed):
    rng = random.Random(seed)
    claims = [Claim(f"c{i}", "formal", "synthetic:benchmark") for i in range(size)]
    receipts = [Receipt(f"e{i}", "formal", "synthetic:benchmark")
                for i in range(max(8, size // 8))]
    routes = []
    for i in range(size):
        for _ in range(2):
            parents = tuple(f"c{j}" for j in rng.sample(range(i), min(i, 2)))
            evidence = tuple(dict.fromkeys(
                (f"e{rng.randrange(len(receipts))}", "e0")))
            routes.append(Route(f"c{i}", evidence, parents))
    return claims, receipts, list(dict.fromkeys(routes))


def measure(size, seed, updates):
    claims, receipts, routes = graph(size, seed)
    rng = random.Random(1000 + seed + size)
    toggles = [f"e{rng.randrange(len(receipts))}" for _ in range(updates)]
    candidate = IncrementalClosure(claims, routes, receipts)
    withdrawn = set()
    full_times, incremental_times = [], []
    for rid in toggles:
        live = rid in withdrawn
        t0 = time.perf_counter_ns()
        candidate.update(rid, live)
        incremental_times.append((time.perf_counter_ns() - t0) / 1000)
        if live:
            withdrawn.remove(rid)
        else:
            withdrawn.add(rid)
        t0 = time.perf_counter_ns()
        reference = resolve_graph(claims, routes, receipts,
                                  withdrawn=frozenset(withdrawn))
        full_times.append((time.perf_counter_ns() - t0) / 1000)
        assert candidate.states() == dict(reference.states)
        assert candidate.active_routes() == reference.active_routes
    return {
        "claims": size, "seed": seed, "updates": updates,
        "full_mean_us": round(statistics.mean(full_times), 3),
        "incremental_mean_us": round(statistics.mean(incremental_times), 3),
        "full_p95_us": round(sorted(full_times)[int(.95 * (updates - 1))], 3),
        "incremental_p95_us": round(sorted(incremental_times)[int(.95 * (updates - 1))], 3),
        "speedup": round(statistics.mean(full_times) / statistics.mean(incremental_times), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--updates", type=int, default=80)
    args = parser.parse_args()
    rows = [measure(n, seed, args.updates)
            for n in (80, 240, 640) for seed in (0, 1)]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
