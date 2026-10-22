#!/usr/bin/env python3
"""Independent exact audit for finite single-column witness acquisition.

Does not import the planner, filter, estimators or generator. It reconstructs
the observation bounds, brute-force minimum probe set, transitions and
authorization using primitive integer operations.
"""

import argparse
from itertools import combinations
import json


def brute_force_minimum(reference, hypotheses, permitted_steps, noise_budget):
    """Independent subset enumerator, lexicographic earliest minimum witness."""
    candidates = sorted(set(hypotheses))
    steps = sorted(set(permitted_steps))
    pairs = [(a, b) for i, a in enumerate(candidates) for b in candidates[i+1:]]
    if not pairs:
        return ()
    distinguishing = []
    for s in steps:
        split = set()
        for pair in pairs:
            a, b = pair
            if bin(reference[(a+s) % len(reference)] ^
                   reference[(b+s) % len(reference)]).count("1") > 2 * noise_budget:
                split.add(pair)
        if split:
            distinguishing.append((s, split))
    if set().union(*(split for _, split in distinguishing)) != set(pairs):
        return None
    # A minimum pair-cover solution needs no more than number-of-pairs steps.
    for count in range(1, min(len(pairs), len(distinguishing)) + 1):
        winners = []
        for choice in combinations(distinguishing, count):
            covered = set().union(*(x[1] for x in choice))
            if covered == set(pairs):
                winners.append(tuple(x[0] for x in choice))
        if winners:
            # Same declared objective: fewest samples, earliest completion,
            # then lexicographic tie-break. Unlike the compiler, this oracle
            # actually enumerates subsets of steps.
            return min(winners, key=lambda s: (s[-1], s))
    raise AssertionError("Unexpected oracle completeness failure")


def _audited_filter(reference, candidates, step, observation, noise_budget=2):
    return tuple(h for h in candidates if
                 bin(reference[(h + step) % len(reference)] ^ observation).count("1")
                 <= noise_budget)


def exhaust_all_bounded_two_probe_observations(reference, hypotheses=(0, 16, 32, 48),
                                               steps=(7, 13), bits=16,
                                               noise_budget=2):
    """Enumerate every <=2-bit corruption at both decisive observations.

    This validates ALL finite observation tuples in the declared independent
    2-bit Hamming balls, a superset of the generated 1+1-bit perturbations.
    The enumeration is not evidence the real camera obeys these assumptions.
    """
    if noise_budget != 2:
        raise ValueError("This exhaustive audit is specialized to radius two")
    changes = [0]
    changes.extend(1 << i for i in range(bits))
    changes.extend((1 << i) | (1 << j) for i in range(bits) for j in range(i+1, bits))
    total = 0
    for true_bin in hypotheses:
        first_expected = reference[(true_bin + steps[0]) % len(reference)]
        second_expected = reference[(true_bin + steps[1]) % len(reference)]
        for flip1 in changes:
            candidates = _audited_filter(reference, hypotheses, steps[0],
                                         first_expected ^ flip1, noise_budget)
            assert true_bin in candidates
            for flip2 in changes:
                remaining = _audited_filter(reference, candidates, steps[1],
                                            second_expected ^ flip2, noise_budget)
                assert remaining == (true_bin,), (true_bin, flip1, flip2, remaining)
                total += 1
    return total


def audit_finite_trial(trial, acquired, continuous):
    """Fail on spoofed output or false confidence within the declared bounds."""
    reference = tuple(trial.reference)
    physical = tuple(trial.physical_source)
    columns = tuple(trial.columns)
    true_bin = trial.true_bin
    hypotheses = (0, 16, 32, 48)
    assert len(reference) == len(physical) == 64
    assert len(columns) >= 17
    assert true_bin in hypotheses
    for observed, source in zip(reference, physical):
        assert (observed ^ source).bit_count() <= 1, "TRAINING_NOISE_BOUND_BROKEN"
    for step, observation in enumerate(columns):
        if observation is not None:
            assert (observation ^ physical[(true_bin + step) % 64]).bit_count() <= 1, "RUNTIME_NOISE_BOUND_BROKEN"

    # Independently replay every actual correction opportunity for each method.
    for outcome, scheduled in ((acquired, True), (continuous, False)):
        candidates = hypotheses
        observed_steps = []
        inspected = []
        if scheduled:
            next_permission = 1
            for step in outcome.attempted_steps:
                oracle = brute_force_minimum(reference, candidates,
                                             tuple(range(next_permission, len(columns))), 2)
                assert oracle is not None and len(oracle)>0
                assert step == oracle[0], "NONMINIMAL_OR_PRECOGNITIVE_PLAN"
                assert step >= next_permission
                inspected.append(step)
                if columns[step] is not None:
                    observed_steps.append(step)
                    candidates = _audited_filter(reference, candidates, step, columns[step])
                    assert true_bin in candidates, "INCORRECT_POST_OBSERVATION_SUPPORT"
                next_permission = step + 1
                if len(candidates) <= 1:
                    assert step == outcome.decision_step
                    break
            assert tuple(inspected) == tuple(outcome.attempted_steps)
            if len(candidates) > 1:
                assert brute_force_minimum(reference, candidates,
                                           tuple(range(next_permission, len(columns))), 2) is None
                assert outcome.status == "UNKNOWN_OBSTRUCTION"
        else:
            for step in range(1, len(columns)):
                if columns[step] is None:
                    continue
                inspected.append(step)
                observed_steps.append(step)
                candidates = _audited_filter(reference, candidates, step, columns[step])
                assert true_bin in candidates
                if len(candidates) == 1:
                    assert outcome.decision_step == step
                    break
        assert tuple(observed_steps) == tuple(outcome.acquired_steps)
        assert outcome.observations_processed == len(observed_steps)
        assert outcome.candidates == candidates, "SPOOFED_FINAL_SUPPORT"
        assert (outcome.status == "AUTHORIZED") == (len(candidates) == 1)
        assert outcome.accepted_bin == (candidates[0] if len(candidates) == 1 else None)
        if outcome.accepted_bin is not None:
            assert outcome.accepted_bin == true_bin, "FALSE_AUTHORIZED_HEADING"
    if acquired.status == "AUTHORIZED":
        assert continuous.status == "AUTHORIZED", "ACQUISITION_BEAT_FULL_INFORMATION"
        assert continuous.decision_step <= acquired.decision_step
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_files", nargs="+")
    args = parser.parse_args()
    from types import SimpleNamespace
    for path in args.trace_files:
        trace = json.loads(open(path, encoding="utf-8").read())
        trial = SimpleNamespace(reference=trace["reference"],
                                physical_source=trace["physical_source_grader_only"],
                                columns=trace["columns"], true_bin=trace["true_bin"])
        outcomes = []
        for name in ("acquired", "continuous"):
            o = dict(trace[name])
            for key in ("candidates", "attempted_steps", "acquired_steps"):
                o[key] = tuple(o[key])
            outcomes.append(SimpleNamespace(**o))
        audit_finite_trial(trial, *outcomes)
        print(f"AUDIT PASS {path}: independent exact subset oracle and both trackers")


if __name__ == "__main__":
    main()
