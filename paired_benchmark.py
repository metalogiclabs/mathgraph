"""Frozen comparator protocol: same pinned source and three constructed faults.

Not a general agent benchmark. Native replay checks exact upstream blobs and
runs real functions. Rates are deterministic seeds, not population estimates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

from upstream_encoding_transfer import (
    ENCODING_PATH, MUTANTS, NATIVE_COMMAND, call_native_code, copy_package,
    digest, domain, execute, independent_minimum_bound,
    minimum_separator, mutate, oracle, pinned_source, qualify,
)

SEEDS = range(1000)
BUDGETS = (2, 4, 8, 16)
EDGE_TWO = (b"\x00", b"\xff")
EDGE_THREE = EDGE_TWO + (b"\x00\x00\x00",)
RIVALS = tuple(sorted(MUTANTS))


def cover_lookup(inputs: tuple[bytes, ...], observations: dict[str, list[bytes]]):
    assert all(len(observations[n]) == len(inputs) for n in ("reference",) + RIVALS)
    return {
        value: frozenset(n for n in RIVALS
                         if observations[n][i] != observations["reference"][i])
        for i, value in enumerate(inputs)
    }


def report_strategy(selected: tuple[bytes, ...], cover: dict):
    caught = sorted(set().union(*(cover[value] for value in selected))) if selected else []
    return {"inputs_hex": [x.hex() for x in selected],
            "tests": len(selected),
            "synthetic_cost": sum(1 + len(v) for v in selected),
            "mutants_caught": caught,
            "mutants_caught_count": len(caught),
            "fully_separates_declared_pool": len(caught) == len(RIVALS)}


def weighted_greedy(inputs: tuple[bytes, ...], cover: dict) -> tuple[bytes, ...]:
    """A separately authored conventional cost-aware mutant-cover heuristic."""
    from fractions import Fraction
    remain = set(RIVALS)
    available = tuple(inputs)
    selected = []
    while remain:
        candidates = []
        for value in available:
            fresh = len(remain.intersection(cover[value]))
            if fresh:
                price = 1 + len(value)
                candidates.append((Fraction(-fresh, price), price, value))
        if not candidates:
            break
        _, _, chosen = min(candidates)
        selected.append(chosen)
        remain.difference_update(cover[chosen])
        available = tuple(x for x in available if x != chosen)
    return tuple(selected)


def random_baseline(inputs: tuple[bytes, ...], cover: dict) -> dict:
    rows = {}
    for budget in BUDGETS:
        tally = 0
        totals = 0
        costs = 0
        for seed in SEEDS:
            rng = Random(seed)
            chosen = tuple(rng.sample(inputs, budget))
            v = report_strategy(chosen, cover)
            tally += int(v["fully_separates_declared_pool"])
            totals += v["mutants_caught_count"]
            costs += v["synthetic_cost"]
        rows[str(budget)] = {
            "seeds": len(SEEDS), "fully_separating_seeds": tally,
            "full_separation_rate": tally / len(SEEDS),
            "mean_mutants_caught": totals / len(SEEDS),
            "mean_synthetic_cost": costs / len(SEEDS),
        }
    return rows


def withheld_grammar_obstruction(inputs: tuple[bytes, ...], chosen: tuple[bytes, ...]) -> dict:
    # Constructed 4-byte-specific mutant, deliberately OUTSIDE the listed grammar.
    counterexample = b"\xff\xff\xff\xff"
    if counterexample in inputs or counterexample in chosen:
        raise AssertionError("withheld control is not outside frozen input domain")
    def held_out(value):
        if value == counterexample:
            return b"MADE-UP-FAULT"
        return oracle(value)
    assert all(held_out(v) == oracle(v) for v in inputs)
    assert held_out(counterexample) != oracle(counterexample)
    return {"counterexample_hex": counterexample.hex(),
            "caught_within_frozen_domain": False,
            "disposition": "OBSTRUCTION_OUTSIDE_DECLARED_GRAMMAR"}


def benchmark(checkout: Path) -> dict:
    file_evidence = pinned_source(checkout)
    code = (checkout / ENCODING_PATH).read_bytes()
    inputs = domain()
    observations: dict[str, list[bytes]] = {}
    native_receipts = {}
    with TemporaryDirectory(prefix="mathgraph-frozen-baseline-") as tmp:
        root = Path(tmp)
        for name in ("reference",) + RIVALS:
            candidate_root = root / name
            candidate_root.mkdir()
            candidate = code if name == "reference" else mutate(code, name)
            copy_package(checkout, candidate_root, candidate)
            observations[name] = call_native_code(candidate_root, inputs)
            receipt = execute(candidate_root, digest(code), NATIVE_COMMAND)
            native_state = qualify(candidate_root, receipt, digest(code), NATIVE_COMMAND)
            if native_state[0] != "WARRANTED":
                raise AssertionError("frozen native-suite baseline unexpectedly rejects: "+name)
            native_receipts[name] = {"status": native_state[0],
                                     "candidate_sha256": digest(candidate),
                                     "test_envelope_sha256": receipt.after_snapshot,
                                     "output_sha256": receipt.stdout_sha256}
    if observations["reference"] != [oracle(x) for x in inputs]:
        raise AssertionError("upstream reference disagrees with source-distinct oracle")
    cover = cover_lookup(inputs, observations)
    exact = minimum_separator(inputs, observations)
    optimum = independent_minimum_bound(exact["cover_records"])
    if exact["status"] != "MINIMUM_BASIS" or optimum != exact["total_synthetic_cost"]:
        raise AssertionError("finite minimum not independently checked")
    exact_inputs = tuple(bytes.fromhex(x) for x in exact["tests_hex"])
    if any(v not in cover for v in EDGE_TWO + EDGE_THREE):
        raise AssertionError("fixed edge baselines not in finite input domain")
    result = {
        "schema":"mathgraph.frozen-testing-benchmark.v1",
        "scope":"three deliberately injected encoding mutants, one exact pinned external Python library",
        "source": {"repository":"pallets/itsdangerous",
                   "commit":"672971d66a2ef9f85151e53283113f33d642dabd",
                   "file_evidence":file_evidence},
        "mutants":list(RIVALS),
        "frozen_domain_count":len(inputs),
        "price":"synthetic test cost = 1 + input byte length; no wall-clock claim",
        "original_upstream_test_receipts":native_receipts,
        "exact_mathgraph":report_strategy(exact_inputs, cover),
        "independent_brute_force_min_cost":optimum,
        "informed_mutation_greedy":report_strategy(weighted_greedy(inputs, cover),cover),
        "fixed_edge_two":report_strategy(EDGE_TWO, cover),
        "fixed_edge_three":report_strategy(EDGE_THREE, cover),
        "seeded_random_uniform": random_baseline(inputs,cover),
        "known_obstruction":withheld_grammar_obstruction(inputs,exact_inputs),
        "interpretation":"equal mutant knowledge allows conventional greedy to compete; finite optimum is not unique to MathGraph; differentiator is evidence acquisition and source-bound authority",
    }
    assert result["exact_mathgraph"]["fully_separates_declared_pool"]
    assert result["exact_mathgraph"]["synthetic_cost"] == optimum
    assert result["known_obstruction"]["caught_within_frozen_domain"] is False
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--report",type=Path,default=Path("frozen-baseline-report.json"))
    args=p.parse_args()
    result=benchmark(args.upstream_checkout.resolve())
    args.report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("frozen_domain_count","exact_mathgraph",
        "informed_mutation_greedy","fixed_edge_two","fixed_edge_three",
        "seeded_random_uniform","known_obstruction")},indent=2))


if __name__=="__main__":main()
