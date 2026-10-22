#!/usr/bin/env python3
"""Finite, first-turn-trained one-column witness acquisition (synthetic only).

This is a deliberately stronger *finite assumption* than the noisy grey-level
camera model. Training signatures and later observations are binary columns.
The physical signature differs from the training column by <=1 bit and the
runtime column differs from physical by <=1 bit, hence a total Hamming error
<=2. The estimator knows that bound, but cannot see physical source or truth.
The model assumes supplied gyro-consistent candidate heading bins include the
actual bin and exact relative angular steps. Neither assumption is certified
for the real drone. All results are modulo 64, NOT absolute revolution count.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random


BITS = 16
MAP_BINS = 64
SECTOR_BINS = 16
HYPOTHESES = (0, 16, 32, 48)
NOISE_BUDGET = 2
HORIZON = 32
BIT_MASK = (1 << BITS) - 1


@dataclass(frozen=True)
class Plan:
    status: str
    steps: tuple[int, ...]
    cost: int
    pair_coverage: int
    total_pairs: int
    pair_checks: int


@dataclass(frozen=True)
class Outcome:
    status: str
    accepted_bin: int | None
    candidates: tuple[int, ...]
    attempted_steps: tuple[int, ...]
    acquired_steps: tuple[int, ...]
    observations_processed: int
    pair_checks: int
    decision_step: int | None


@dataclass(frozen=True)
class FiniteTrial:
    seed: int
    kind: str
    true_bin: int  # External grader ONLY; never passed into tracker.
    physical_source: tuple[int, ...]  # External validation ONLY.
    reference: tuple[int, ...]  # Observed on the FIRST revolution, frozen.
    columns: tuple[int | None, ...]  # Subsequent revolution, with outages.
    occluded_steps: tuple[int, ...]


def compile_minimum_witnesses(reference: tuple[int, ...],
                              hypotheses: tuple[int, ...],
                              permitted_steps: tuple[int, ...],
                              noise_budget: int) -> Plan:
    """Exact minimum-cardinality set covering all hypothesis pairs.

    Each pair is provably disjoint at a step if Hamming signatures exceed
    twice the *total* allowed reference-observation error. Returns an explicit
    obstruction relative to this map, motion, permission set and finite horizon.
    No truth or future acquired measurements are read.
    """
    hypotheses = tuple(sorted(set(hypotheses)))
    steps = tuple(sorted(set(permitted_steps)))
    if len(reference) == 0 or noise_budget < 0 or any(s < 1 for s in steps):
        raise ValueError("Empty map, negative noise bound, or invalid future step")
    if not hypotheses:
        return Plan("NO_CANDIDATES", (), 0, 0, 0, 0)
    if len(hypotheses) == 1:
        return Plan("ALREADY_UNIQUE", (), 0, 0, 0, 0)
    pairs = [(a, b) for i, a in enumerate(hypotheses) for b in hypotheses[i+1:]]
    target = (1 << len(pairs)) - 1
    checks = 0
    # State indexes pair coverage, NOT candidate subsets. Objective:
    # minimum acquired columns; then earliest final observation; then order.
    optimum: dict[int, tuple[int, ...]] = {0: ()}
    for s in steps:
        covered = 0
        for bit, (a, b) in enumerate(pairs):
            distance = (reference[(a + s) % len(reference)] ^
                        reference[(b + s) % len(reference)]).bit_count()
            checks += 1
            if distance > 2 * noise_budget:
                covered |= 1 << bit
        if not covered:
            continue
        previous = optimum.copy()
        for mask, selected in previous.items():
            new_mask = mask | covered
            candidate = selected + (s,)
            old = optimum.get(new_mask)
            if old is None or (len(candidate), candidate[-1], candidate) < (len(old), old[-1], old):
                optimum[new_mask] = candidate
    if target not in optimum:
        return Plan("BOUNDED_OBSTRUCTION", (), 0,
                    max(optimum, key=int.bit_count), len(pairs), checks)
    selected = optimum[target]
    return Plan("SEPARATING_SET", selected, len(selected), target,
                len(pairs), checks)


def filter_hypotheses(reference: tuple[int, ...], hypotheses: tuple[int, ...],
                      step: int, actual_column: int, noise_budget: int) -> tuple[int, ...]:
    """Keep only headings consistent with what the camera ACTUALLY observed."""
    return tuple(h for h in hypotheses if
                 (reference[(h + step) % len(reference)] ^ actual_column).bit_count()
                 <= noise_budget)


def check_retained_authority(reference: tuple[int, ...], accepted_bin: int,
                             step: int, column: int | None,
                             noise_budget: int = NOISE_BUDGET) -> str:
    """New observations may WITHDRAW a formerly supported correction.

    If a changed scene also mimics the old heading, this check is unable to
    detect it. Absent observations cannot refresh or revalidate authority.
    """
    if column is None:
        return "UNKNOWN_NO_OBSERVATION"
    if filter_hypotheses(reference, (accepted_bin,), step, column, noise_budget):
        return "RETAINED"
    return "WITHDRAWN"


def _result(status: str, headings: tuple[int, ...], attempted: list[int],
            acquired: list[int], pair_checks: int, step: int | None) -> Outcome:
    accepted = headings[0] if status == "AUTHORIZED" else None
    return Outcome(status, accepted, headings, tuple(attempted), tuple(acquired),
                   len(acquired), pair_checks, step)


def run_acquired(reference: tuple[int, ...], hypotheses: tuple[int, ...],
                 columns: tuple[int | None, ...],
                 noise_budget: int = NOISE_BUDGET) -> Outcome:
    """Observe only proposed separating instants; replan after an occlusion."""
    candidates = tuple(sorted(set(hypotheses)))
    attempted: list[int] = []
    acquired: list[int] = []
    checks = 0
    if len(candidates) == 1:
        return _result("AUTHORIZED", candidates, attempted, acquired, checks, 0)
    step = 1
    while step < len(columns):
        # Occlusions are NOT known in advance and cannot be removed from plan.
        plan = compile_minimum_witnesses(reference, candidates,
                                         tuple(range(step, len(columns))), noise_budget)
        checks += plan.pair_checks
        if plan.status != "SEPARATING_SET":
            return _result("UNKNOWN_OBSTRUCTION", candidates, attempted,
                           acquired, checks, None)
        next_step = plan.steps[0]
        attempted.append(next_step)
        column = columns[next_step]
        if column is not None:
            acquired.append(next_step)
            candidates = filter_hypotheses(reference, candidates, next_step,
                                           column, noise_budget)
            if len(candidates) == 0:
                return _result("CONFLICT", candidates, attempted, acquired, checks, next_step)
            if len(candidates) == 1:
                return _result("AUTHORIZED", candidates, attempted, acquired, checks, next_step)
        step = next_step + 1
    return _result("UNKNOWN_OBSTRUCTION", candidates, attempted, acquired, checks, None)


def run_continuous(reference: tuple[int, ...], hypotheses: tuple[int, ...],
                   columns: tuple[int | None, ...],
                   noise_budget: int = NOISE_BUDGET) -> Outcome:
    """Equally informed conventional set-valued tracker, processes EVERY sample.

    It uses the same learned map, candidate hypotheses and total error budget;
    it can resolve no later than the planned policy in this finite model.
    """
    candidates = tuple(sorted(set(hypotheses)))
    acquired = []
    for step in range(1, len(columns)):
        column = columns[step]
        if column is None:
            continue
        acquired.append(step)
        candidates = filter_hypotheses(reference, candidates, step, column, noise_budget)
        if not candidates:
            return _result("CONFLICT", candidates, acquired, acquired, 0, step)
        if len(candidates) == 1:
            return _result("AUTHORIZED", candidates, acquired, acquired, 0, step)
    return _result("UNKNOWN_AMBIGUOUS", candidates, acquired, acquired, 0, None)


def generate_finite_trial(seed: int, true_bin: int | None = None,
                          kind: str = "breakable",
                          occluded_steps: tuple[int, ...] = (),
                          horizon: int = HORIZON) -> FiniteTrial:
    """Procedural first revolution and second encounter; no oracle reference.

    A physical 64-bin scene has four similar 16-bin sectors. Distinctive
    landmarks at future step 7 separate one binary partition of sectors; those
    at step 13 separate the other. No single observation divides all four.
    For the obstruction control no distinguishing landmarks are present.
    """
    if kind not in ("breakable", "unbreakable"):
        raise ValueError(kind)
    rng = random.Random(seed)
    base = [rng.getrandbits(BITS) for _ in range(SECTOR_BINS)]
    physical = base * 4
    if kind == "breakable":
        for sector in (2, 3):
            physical[sector * SECTOR_BINS + 7] = base[7] ^ BIT_MASK
        for sector in (1, 3):
            physical[sector * SECTOR_BINS + 13] = base[13] ^ BIT_MASK
    # FIRST revolution: one bounded corrupt bit per observed bin, then freeze.
    reference = tuple(value ^ (1 << rng.randrange(BITS)) for value in physical)
    heading = rng.choice(HYPOTHESES) if true_bin is None else true_bin
    if heading not in HYPOTHESES:
        raise ValueError("True heading must be among declared gyro candidates")
    absent = set(occluded_steps)
    columns: list[int | None] = []
    for step in range(horizon + 1):
        observed = physical[(heading + step) % MAP_BINS] ^ (1 << rng.randrange(BITS))
        columns.append(None if step in absent else observed)
    return FiniteTrial(seed, kind, heading, tuple(physical), reference,
                       tuple(columns), tuple(sorted(absent)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--true-bin", type=int, choices=HYPOTHESES, required=True)
    parser.add_argument("--kind", choices=("breakable", "unbreakable"), default="breakable")
    parser.add_argument("--occlude", type=int, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    t = generate_finite_trial(args.seed, args.true_bin, args.kind, tuple(args.occlude))
    acquired = run_acquired(t.reference, HYPOTHESES, t.columns)
    continuous = run_continuous(t.reference, HYPOTHESES, t.columns)
    result = {
        "boundary": "FINITE_BINARY_SYNTHETIC_ASSUMED_NOISE_2_NO_PHYSICAL_SENSOR",
        "seed": args.seed, "kind": args.kind, "true_bin": t.true_bin,
        "occluded_steps": t.occluded_steps, "reference": t.reference,
        "physical_source_grader_only": t.physical_source,
        "columns": t.columns, "hypotheses": HYPOTHESES,
        "acquired": vars(acquired), "continuous": vars(continuous),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in
                      ("reference", "physical_source_grader_only", "columns")}, indent=2))


if __name__ == "__main__":
    main()
