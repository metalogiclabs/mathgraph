#!/usr/bin/env python3
"""Robust finite witness acquisition with bounded camera/gyro timing slip.

Separate v3 experiment. Each future column's true angular bin may be +/-1
around the gyro prediction. A separating witness must disambiguate ALL allowed
offset combinations, not just an optimistic point prediction. This assumes
the jitter bound and finite binary image-error bound are known and valid.
It is not an implementation of real camera/gyro synchronization.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random

from finite_witness_compass import (
    BITS, MAP_BINS, SECTOR_BINS, HYPOTHESES,
    NOISE_BUDGET, HORIZON, BIT_MASK, Plan, Outcome,
)


@dataclass(frozen=True)
class JitterTrial:
    seed: int
    kind: str
    true_bin: int  # external grader only
    physical_source: tuple[int, ...]  # external bound audit only
    reference: tuple[int, ...]  # first-turn observed map
    columns: tuple[int | None, ...]  # actual future measurements
    timing_offsets: tuple[int, ...]  # external auditor only
    occluded_steps: tuple[int, ...]


def compile_jitter_witnesses(reference: tuple[int, ...],
                             hypotheses: tuple[int, ...],
                             permitted_steps: tuple[int, ...],
                             noise_budget: int = NOISE_BUDGET,
                             timing_jitter_bins: int = 1) -> Plan:
    """Exact minimum probe set, worst-case over every admissible timing slip."""
    if not reference or noise_budget < 0 or timing_jitter_bins < 0:
        raise ValueError("Invalid map or uncertainty envelope")
    candidates = tuple(sorted(set(hypotheses)))
    steps = tuple(sorted(set(permitted_steps)))
    if any(s < 1 for s in steps):
        raise ValueError("Only future positive observation times are permitted")
    if len(candidates) < 2:
        return Plan("ALREADY_UNIQUE" if candidates else "NO_CANDIDATES",
                    (), 0, 0, 0, 0)
    pairs = [(a, b) for i, a in enumerate(candidates) for b in candidates[i+1:]]
    all_pairs = (1 << len(pairs)) - 1
    checks = 0
    selected_by_mask: dict[int, tuple[int, ...]] = {0: ()}
    for step in steps:
        separated = 0
        for pair_index, (a, b) in enumerate(pairs):
            left = [reference[(a + step + delta) % len(reference)]
                    for delta in range(-timing_jitter_bins, timing_jitter_bins+1)]
            right = [reference[(b + step + delta) % len(reference)]
                     for delta in range(-timing_jitter_bins, timing_jitter_bins+1)]
            disjoint = True
            for x in left:
                for y in right:
                    checks += 1
                    if (x ^ y).bit_count() <= 2 * noise_budget:
                        disjoint = False
            if disjoint:
                separated |= 1 << pair_index
        if not separated:
            continue
        for old_mask, old_steps in list(selected_by_mask.items()):
            new_mask = old_mask | separated
            proposed = old_steps + (step,)
            incumbent = selected_by_mask.get(new_mask)
            if incumbent is None or (len(proposed), proposed[-1], proposed) < (len(incumbent), incumbent[-1], incumbent):
                selected_by_mask[new_mask] = proposed
    if all_pairs not in selected_by_mask:
        return Plan("BOUNDED_NO_GUARANTEED_SEPARATION", (), 0,
                    max(selected_by_mask, key=int.bit_count), len(pairs), checks)
    steps = selected_by_mask[all_pairs]
    return Plan("SEPARATING_SET", steps, len(steps), all_pairs, len(pairs), checks)


def filter_jitter_hypotheses(reference: tuple[int, ...],
                             hypotheses: tuple[int, ...], step: int,
                             column: int, noise_budget: int = NOISE_BUDGET,
                             timing_jitter_bins: int = 1) -> tuple[int, ...]:
    """A candidate survives if ANY allowed true timing offset fits the reading."""
    return tuple(h for h in hypotheses if any(
        (column ^ reference[(h + step + delta) % len(reference)]).bit_count() <= noise_budget
        for delta in range(-timing_jitter_bins, timing_jitter_bins+1)))


def _result(status, candidates, attempted, acquired, pair_checks, step):
    return Outcome(status, candidates[0] if status=="AUTHORIZED" else None,
                   candidates, tuple(attempted), tuple(acquired), len(acquired),
                   pair_checks, step)


def run_jitter_acquired(reference: tuple[int, ...],
                        hypotheses: tuple[int, ...],
                        columns: tuple[int | None, ...],
                        noise_budget: int = NOISE_BUDGET,
                        timing_jitter_bins: int = 1) -> Outcome:
    """Plan, acquire, replan after blackout; no future reading enters a plan."""
    candidates = tuple(sorted(set(hypotheses)))
    attempted: list[int] = []
    acquired: list[int] = []
    checks = 0
    if len(candidates)==1:
        return _result("AUTHORIZED", candidates, attempted, acquired, checks, 0)
    step = 1
    while step < len(columns):
        plan = compile_jitter_witnesses(reference, candidates,
                                       tuple(range(step, len(columns))),
                                       noise_budget, timing_jitter_bins)
        checks += plan.pair_checks
        if plan.status != "SEPARATING_SET":
            return _result("UNKNOWN_OBSTRUCTION", candidates, attempted, acquired, checks, None)
        step = plan.steps[0]
        attempted.append(step)
        observed = columns[step]
        if observed is not None:
            acquired.append(step)
            candidates = filter_jitter_hypotheses(reference, candidates, step,
                                                   observed, noise_budget,
                                                   timing_jitter_bins)
            if not candidates:
                return _result("CONFLICT", candidates, attempted, acquired, checks, step)
            if len(candidates)==1:
                return _result("AUTHORIZED", candidates, attempted, acquired, checks, step)
        step += 1
    return _result("UNKNOWN_OBSTRUCTION", candidates, attempted, acquired, checks, None)


def run_jitter_continuous(reference: tuple[int, ...],
                          hypotheses: tuple[int, ...],
                          columns: tuple[int | None, ...],
                          noise_budget: int = NOISE_BUDGET,
                          timing_jitter_bins: int = 1) -> Outcome:
    """Fair conventional filter sees each available column and same jitter set."""
    candidates = tuple(sorted(set(hypotheses)))
    inspected=[]
    for step in range(1,len(columns)):
        if columns[step] is None:
            continue
        inspected.append(step)
        candidates = filter_jitter_hypotheses(reference, candidates, step,
                                              columns[step], noise_budget,
                                              timing_jitter_bins)
        if len(candidates)==0:
            return _result("CONFLICT", candidates, inspected, inspected, 0, step)
        if len(candidates)==1:
            return _result("AUTHORIZED", candidates, inspected, inspected, 0, step)
    return _result("UNKNOWN_AMBIGUOUS", candidates, inspected, inspected, 0, None)


def generate_jitter_trial(seed: int, true_bin: int | None = None,
                          kind: str = "wide", occluded_steps: tuple[int, ...] = (),
                          horizon: int = HORIZON) -> JitterTrial:
    """64 first-turn binary columns; independent +/-1 later angular slips."""
    if kind not in ("wide", "narrow", "unbreakable"):
        raise ValueError(kind)
    rng = random.Random(seed)
    base = [rng.getrandbits(BITS) for _ in range(SECTOR_BINS)]
    physical = base * 4
    if kind in ("wide", "narrow"):
        first = (6,7,8) if kind=="wide" else (7,)
        second = (12,13,14) if kind=="wide" else (13,)
        for offset in first:
            for sector in range(4):
                physical[sector*SECTOR_BINS+offset] = base[7] ^ (BIT_MASK if sector>=2 else 0)
        for offset in second:
            for sector in range(4):
                physical[sector*SECTOR_BINS+offset] = base[13] ^ (BIT_MASK if sector%2 else 0)
    reference = tuple(v ^ (1 << rng.randrange(BITS)) for v in physical)
    heading = rng.choice(HYPOTHESES) if true_bin is None else true_bin
    if heading not in HYPOTHESES:
        raise ValueError("Real heading must be in declared prior support")
    absent = set(occluded_steps)
    columns: list[int | None] = []
    slips=[]
    for step in range(horizon+1):
        timing_slip = rng.randrange(-1,2)
        slips.append(timing_slip)
        measured = physical[(heading + step + timing_slip) % MAP_BINS] ^ (1 << rng.randrange(BITS))
        columns.append(None if step in absent else measured)
    return JitterTrial(seed, kind, heading, tuple(physical), reference,
                       tuple(columns), tuple(slips), tuple(sorted(absent)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--true-bin", type=int, choices=HYPOTHESES, required=True)
    parser.add_argument("--kind", choices=("wide", "narrow", "unbreakable"), default="wide")
    parser.add_argument("--occlude", type=int, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    trial=generate_jitter_trial(args.seed,args.true_bin,args.kind,tuple(args.occlude))
    a=run_jitter_acquired(trial.reference,HYPOTHESES,trial.columns)
    c=run_jitter_continuous(trial.reference,HYPOTHESES,trial.columns)
    record={
        "boundary":"SYNTHETIC_BINARY_16_ROWS_GYRO_TIMING_SLIP_PLUS_MINUS_1_ASSUMED",
        "seed":trial.seed,"kind":trial.kind,"true_bin":trial.true_bin,
        "physical_source_grader_only":trial.physical_source,
        "reference":trial.reference,"columns":trial.columns,
        "timing_offsets_grader_only":trial.timing_offsets,
        "occluded_steps":trial.occluded_steps,
        "hypotheses":HYPOTHESES,"acquired":vars(a),"continuous":vars(c),
    }
    args.output.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in
        ("physical_source_grader_only","reference","columns","timing_offsets_grader_only")},indent=2))


if __name__=="__main__":
    main()
