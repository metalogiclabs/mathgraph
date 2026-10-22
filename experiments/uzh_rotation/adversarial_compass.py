#!/usr/bin/env python3
"""Causal, one-column synthetic compass stress harness (NOT flight evidence).

All estimators receive ONLY columns, observation-valid flags and gyro deltas.
Truth is held by the trial/grader. The evidence-aware mode shares the robust
baseline's scores, history and thresholds; it adds explicit bounded witness
planning and can only refuse/defer corrections, or accept a newly observed
separating witness. This is a synthetic policy experiment, not formal proof.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
import json
from pathlib import Path
import time

import numpy as np


TAU = 2 * np.pi
DEG = 180 / np.pi
ROWS = 64
BINS = 256
PER_TURN = 360
DT = 0.01
MIN_QUALITY = 0.52
MIN_DISTINCT_PEAK_GAP = 0.09
PEAK_DISTANCE_BINS = 7
HISTORY_FRAMES = 5
HISTORY_MAX_AGE = 20
WITNESS_SEPARATION = 0.32
WITNESS_HORIZON = 180
AUTHORITY_TTL = 90
STRESSES = (
    "clean", "repeat_exact", "repeat_near", "parallax_height",
    "moving_objects", "timing_jitter", "gyro_drift", "speed_changes",
    "blackout_turns", "partial_map", "recovery_confuser", "combined",
)


def wrap(angle: float | np.ndarray) -> float | np.ndarray:
    return (angle + np.pi) % TAU - np.pi


@dataclass(frozen=True)
class Trial:
    stress: str
    seed: int
    turns: int
    truth: np.ndarray
    columns: np.ndarray
    observed: np.ndarray
    gyro_deltas: np.ndarray


@dataclass(frozen=True)
class LearnedMap:
    reference: np.ndarray
    occupied: np.ndarray
    training_end: int


@dataclass(frozen=True)
class WitnessPlan:
    status: str
    step: int | None
    comparisons: int


@dataclass(frozen=True)
class CorrectionGrade:
    incorrect_target: bool
    harmful: bool


@dataclass(frozen=True)
class CorrectionEvent:
    index: int
    before: float
    after: float
    target: float
    via_witness: bool = False


@dataclass
class Estimate:
    heading: np.ndarray
    authority: np.ndarray
    events: list[CorrectionEvent] = field(default_factory=list)
    pixel_multiplications: int = 0
    witness_pair_checks: int = 0
    witness_requests: int = 0
    witness_resolutions: int = 0
    bounded_obstructions: int = 0
    deferred_ambiguous: int = 0
    alias_unresolved_samples: int = 0


def generate_trial(stress: str, seed: int, turns: int = 12) -> Trial:
    """Deterministic synthetic physics and scene. No estimator sees `truth`."""
    if stress not in STRESSES:
        raise ValueError(f"Unknown stress: {stress}")
    if turns < 3:
        raise ValueError("Need at least three revolutions for a held-out interval")
    rng = np.random.default_rng(seed)
    n = turns * PER_TURN
    samples = np.arange(n)
    base = rng.normal(size=(BINS, ROWS))
    for _ in range(3):
        base = (np.roll(base, 1, axis=0) + 2 * base + np.roll(base, -1, axis=0)) / 4
    if stress in ("repeat_exact", "recovery_confuser"):
        base = np.tile(base[:BINS // 4], (4, 1))
    elif stress in ("repeat_near", "combined"):
        base = np.tile(base[:BINS // 4], (4, 1)) + rng.normal(0, 0.025, (BINS, ROWS))
    base -= base.mean(axis=1, keepdims=True)
    base /= np.maximum(np.linalg.norm(base, axis=1, keepdims=True), 1e-12)

    speed_factor = 1 + 0.15 * np.sin(samples * 0.004)
    if stress in ("speed_changes", "combined"):
        speed_factor += 0.48 * np.sin(samples * 0.023) + 0.13 * np.cos(samples * 0.008)
    speed = TAU / (PER_TURN * DT) * np.maximum(speed_factor, 0.25)
    truth = np.cumsum(speed * DT)
    truth -= truth[0]

    # The camera measures a timestamped orientation, not a world-heading label.
    # Jitter and an introduced latency step are unmodelled by the estimators.
    camera_time = samples.astype(float)
    if stress in ("timing_jitter", "combined"):
        affected = samples >= PER_TURN
        camera_time[affected] -= 4.0
        camera_time[affected] += rng.normal(0, 1.3, affected.sum())
    camera_angle = np.interp(np.clip(camera_time, 0, n - 1), samples, truth)
    angular_bin = np.rint(camera_angle / TAU * BINS).astype(int) % BINS
    columns = base[angular_bin].copy() + rng.normal(0, 0.08, size=(n, ROWS))
    if stress in ("parallax_height", "combined"):
        for i in range(PER_TURN, n):
            columns[i] = np.roll(columns[i], int(round(8 * np.sin(i * 0.007))))
    if stress in ("moving_objects", "combined"):
        for i in range(PER_TURN, n):
            # Moving foreground occupies a large varying band of the 64 rows.
            band = int(ROWS * (0.4 + 0.1 * np.sin(i * 0.008)))
            start = int((ROWS - band) * (0.5 + 0.5 * np.sin(i * 0.009)))
            columns[i, start:start + band] = rng.normal(0, 0.20, size=band)

    bias = np.full(n, 0.014)
    if stress in ("gyro_drift", "combined"):
        bias[PER_TURN:] += 0.045 + np.linspace(0, 0.035, n - PER_TURN)
    if stress == "recovery_confuser":
        bias[2 * PER_TURN:5 * PER_TURN] += 0.29
    gyro_deltas = np.diff(truth, prepend=truth[0]) + bias * DT
    gyro_deltas += rng.normal(0, 0.002 * DT, size=n)

    observed = np.ones(n, dtype=bool)
    if stress in ("repeat_exact", "repeat_near"):
        observed[2 * PER_TURN:3 * PER_TURN] = False
    if stress in ("blackout_turns", "recovery_confuser"):
        observed[2 * PER_TURN:5 * PER_TURN] = False
    if stress == "partial_map":
        observed[:165] = False
        observed[250:325] = False
    if stress == "moving_objects":
        observed[3 * PER_TURN:3 * PER_TURN + 140] = False
    if stress == "combined":
        observed[:140] = False
        observed[2 * PER_TURN:5 * PER_TURN] = False
    # Make the absent columns genuinely absent; no hidden image is handed out.
    columns[~observed] = 0
    return Trial(stress, seed, turns, truth, columns, observed, gyro_deltas)


def build_first_turn_map(columns: np.ndarray, observed: np.ndarray,
                         gyro_deltas: np.ndarray, bins: int = BINS) -> LearnedMap:
    """Freeze reference at the FIRST gyro-estimated revolution, never use truth."""
    if columns.ndim != 2 or len(columns) != len(observed) or len(columns) != len(gyro_deltas):
        raise ValueError("Column, mask and gyro dimensions disagree")
    integrated = np.cumsum(gyro_deltas)
    training_end = int(np.searchsorted(integrated, TAU))
    if training_end >= len(columns):
        raise ValueError("No initial gyro-estimated revolution completed")
    rows = columns.shape[1]
    reference = np.zeros((bins, rows))
    counts = np.zeros(bins, dtype=int)
    for i in range(training_end):
        if observed[i]:
            b = int(round(integrated[i] / TAU * bins)) % bins
            reference[b] += columns[i]
            counts[b] += 1
    occupied = counts > 0
    reference[occupied] /= counts[occupied, None]
    reference[occupied] -= reference[occupied].mean(axis=1, keepdims=True)
    reference[occupied] /= np.maximum(np.linalg.norm(reference[occupied], axis=1, keepdims=True), 1e-12)
    return LearnedMap(reference, occupied, training_end)


def plan_separating_witness(reference: np.ndarray, occupied: np.ndarray,
                            hypothesis_bins: tuple[int, ...],
                            angular_step_bins: float, max_steps: int,
                            separation: float) -> WitnessPlan:
    """Find earliest predicted observable whose signatures separate every pair.

    A None result is an obstruction ONLY within the frozen map, candidates,
    constant-rate prediction, and finite step horizon. It is not a theorem
    about all possible observations or true physical navigation.
    """
    checked = 0
    n = len(reference)
    hypotheses = np.asarray(hypothesis_bins, dtype=int)
    if len(hypotheses) < 2:
        return WitnessPlan("INSUFFICIENT_HYPOTHESES", None, checked)
    for step in range(1, max_steps + 1):
        indices = (hypotheses + int(round(step * angular_step_bins))) % n
        if not np.all(occupied[indices]):
            continue
        signatures = reference[indices]
        norms = np.maximum(np.linalg.norm(signatures, axis=1), 1e-12)
        signatures = signatures / norms[:, None]
        distances = 1 - signatures @ signatures.T
        pairs = distances[np.triu_indices(len(hypotheses), 1)]
        checked += len(pairs)
        if np.all(pairs >= separation):
            return WitnessPlan("SEPARATING_OBSERVATION", step, checked)
    return WitnessPlan("BOUNDED_NON_SEPARABILITY", None, checked)


def detect_rotational_alias(learned: LearnedMap) -> int | None:
    """Conservative map-only detector for long-range near-periodic aliases.

    Average correlation across dozens of independent angular positions avoids
    mistaking one noisy map column for a reliable symmetry-breaking witness.
    The threshold defines an operational uncertainty warning, not a proof of
    exact periodicity. Both strong baselines share this detection.
    """
    occupied = learned.occupied
    reference = learned.reference
    bins = len(reference)
    best_lag, best_score = None, 0.48
    for lag in range(12, bins // 2 + 1):
        mask = occupied & np.roll(occupied, -lag)
        if mask.sum() < max(20, bins // 8):
            continue
        other = np.roll(reference, -lag, axis=0)
        correlation = float(np.mean(np.sum(reference[mask] * other[mask], axis=1)))
        if correlation > best_score:
            best_lag, best_score = lag, correlation
    return best_lag


def grade_correction(before: float, after: float, target: float,
                     truth: float) -> CorrectionGrade:
    """External grader only. Estimators must NEVER call this function."""
    incorrect = abs(wrap(target - truth)) > np.deg2rad(10)
    harmful = abs(wrap(after - truth)) > abs(wrap(before - truth)) + np.deg2rad(5)
    return CorrectionGrade(bool(incorrect), bool(harmful))


def _distant_peaks(scores: np.ndarray, max_peaks: int = 5) -> list[int]:
    peaks: list[int] = []
    bins = len(scores)
    for candidate in np.argsort(scores)[::-1]:
        k = int(candidate)
        if scores[k] < -1:
            break
        if all(min(abs(k - j), bins - abs(k - j)) >= PEAK_DISTANCE_BINS for j in peaks):
            peaks.append(k)
            if len(peaks) == max_peaks:
                break
    return peaks


def run_estimators(columns: np.ndarray, observed: np.ndarray,
                   gyro_deltas: np.ndarray) -> dict[str, Estimate]:
    """Four causal estimators. No truth input or truth-derived selection."""
    learned = build_first_turn_map(columns, observed, gyro_deltas)
    alias_period = detect_rotational_alias(learned)
    n, rows = columns.shape
    bins = len(learned.reference)
    cum_gyro = np.cumsum(gyro_deltas)
    methods = ("gyro_only", "matched_filter", "robust", "evidence_aware")
    outputs = {name: Estimate(np.zeros(n), np.zeros(n, dtype=bool)) for name in methods}
    last_accept = {name: -100000 for name in methods}
    history: deque[tuple[int, np.ndarray]] = deque(maxlen=HISTORY_FRAMES)
    pending: dict[str, object] | None = None
    next_plan_allowed = learned.training_end

    for i in range(n):
        before = {name: (out.heading[i - 1] if i else 0.0) + gyro_deltas[i]
                  for name, out in outputs.items()}
        after = before.copy()
        if i >= learned.training_end and observed[i]:
            z = columns[i] - columns[i].mean()
            z /= max(np.linalg.norm(z), 1e-12)
            # Local matched filter intentionally matches the original simple
            # algorithm's limited search and weak peak-margin rule.
            pred = int(round(before["matched_filter"] / TAU * bins))
            local = np.arange(pred - 10, pred + 11) % bins
            local = local[learned.occupied[local]]
            if len(local) >= 2:
                quality = learned.reference[local] @ z
                outputs["matched_filter"].pixel_multiplications += len(local) * rows
                order = np.argsort(quality)
                winner, runner = int(order[-1]), int(order[-2])
                if quality[winner] >= 0.53 and quality[winner] - quality[runner] >= 0.005:
                    innovation = wrap((int(local[winner]) - pred) * TAU / bins)
                    target = before["matched_filter"] + innovation
                    after["matched_filter"] += 0.30 * innovation
                    outputs["matched_filter"].events.append(
                        CorrectionEvent(i, before["matched_filter"], after["matched_filter"], target))
                    last_accept["matched_filter"] = i

            while history and i - history[0][0] > HISTORY_MAX_AGE:
                history.popleft()
            history.append((i, z))
            if len(history) >= 3:
                # A temporal multi-column-in-time correlation, evaluated
                # causally. Robust and evidence-aware use the SAME scores.
                scores = np.zeros(bins)
                valid = np.ones(bins, dtype=bool)
                grid = np.arange(bins)
                multiplies = 0
                for t, past_z in history:
                    shift = int(round((cum_gyro[i] - cum_gyro[t]) / TAU * bins))
                    indices = (grid - shift) % bins
                    valid &= learned.occupied[indices]
                    scores += learned.reference[indices] @ past_z
                    multiplies += bins * rows
                scores /= len(history)
                scores[~valid] = -2
                peaks = _distant_peaks(scores)
                for name in ("robust", "evidence_aware"):
                    outputs[name].pixel_multiplications += multiplies
                if len(peaks) >= 2:
                    top, rival = peaks[0], peaks[1]
                    strong = scores[top] >= MIN_QUALITY
                    unique = strong and scores[top] - scores[rival] >= MIN_DISTINCT_PEAK_GAP
                    for name in ("robust", "evidence_aware"):
                        if alias_period is not None:
                            # Under periodic appearance, a spurious globally
                            # unique peak can arise from one-revolution map
                            # noise or gyro bin quantization. Only use the
                            # local angular neighborhood while a conservative
                            # integrated-bias bound excludes another alias.
                            uncertainty = (0.06 + 0.10 * DT *
                                           (i - max(last_accept[name], learned.training_end)))
                            alias_half_separation = alias_period * TAU / bins / 2
                            if uncertainty >= alias_half_separation - np.deg2rad(5):
                                outputs[name].alias_unresolved_samples += 1
                                continue
                            pred = int(round(before[name] / TAU * bins))
                            local = np.arange(pred - 10, pred + 11) % bins
                            local = local[scores[local] > -1]
                            if len(local):
                                choice = int(local[np.argmax(scores[local])])
                                innovation = float(wrap(choice * TAU / bins - before[name]))
                                if scores[choice] >= MIN_QUALITY and abs(innovation) <= np.deg2rad(20):
                                    target = before[name] + innovation
                                    after[name] += 0.30 * innovation
                                    outputs[name].events.append(CorrectionEvent(i, before[name], after[name], target))
                                    last_accept[name] = i
                            # No long-range global/witness correction may be
                            # warranted solely from an aliased first-turn map.
                            continue
                        if name == "evidence_aware" and pending is not None:
                            # Query the planned future column at the instant
                            # it becomes available, using actual integrated
                            # gyro rather than future true rotation.
                            if i >= int(pending["due"]):
                                origin = int(pending["origin"])
                                hypotheses = np.asarray(pending["hypotheses"], dtype=int)
                                shift = int(round((cum_gyro[i] - cum_gyro[origin]) / TAU * bins))
                                at = (hypotheses + shift) % bins
                                if np.all(learned.occupied[at]):
                                    witness_scores = learned.reference[at] @ z
                                    outputs[name].pixel_multiplications += len(at) * rows
                                    witness_order = np.argsort(witness_scores)
                                    best, other = int(witness_order[-1]), int(witness_order[-2])
                                    if witness_scores[best] >= MIN_QUALITY and witness_scores[best] - witness_scores[other] >= MIN_DISTINCT_PEAK_GAP:
                                        innovation = float(wrap(at[best] * TAU / bins - before[name]))
                                        target = before[name] + innovation
                                        after[name] += 0.30 * innovation
                                        outputs[name].events.append(CorrectionEvent(i, before[name], after[name], target, True))
                                        outputs[name].witness_resolutions += 1
                                        last_accept[name] = i
                                pending = None
                                next_plan_allowed = i + 20
                            else:
                                outputs[name].deferred_ambiguous += 1
                                continue
                        if after[name] != before[name]:
                            continue  # A witnessed correction already applied.
                        if unique:
                            innovation = float(wrap(top * TAU / bins - before[name]))
                            target = before[name] + innovation
                            after[name] += 0.30 * innovation
                            outputs[name].events.append(CorrectionEvent(i, before[name], after[name], target))
                            last_accept[name] = i
                        elif name == "evidence_aware" and strong:
                            outputs[name].deferred_ambiguous += 1
                            if pending is None and i >= next_plan_allowed:
                                near = tuple(p for p in peaks if scores[top] - scores[p] < 0.16)[:4]
                                if len(near) >= 2:
                                    plan = plan_separating_witness(
                                        learned.reference, learned.occupied, near,
                                        gyro_deltas[i] / TAU * bins,
                                        WITNESS_HORIZON, WITNESS_SEPARATION,
                                    )
                                    outputs[name].witness_requests += 1
                                    outputs[name].witness_pair_checks += plan.comparisons
                                    if plan.step is None:
                                        outputs[name].bounded_obstructions += 1
                                        next_plan_allowed = i + WITNESS_HORIZON
                                    else:
                                        pending = {"origin": i, "due": i + plan.step, "hypotheses": near}
                # No unique global visual evidence: robust abstains too.
        else:
            # No image can license a correction; stale temporal history is
            # invalidated across gaps by the age test on next observation.
            if pending is not None and i >= int(pending["due"]):
                pending = None
                next_plan_allowed = i + 20

        for name, out in outputs.items():
            out.heading[i] = after[name]
            # 'Heading available' means a RECENT accepted visual anchor;
            # inertial heading is always emitted but separately untrusted.
            out.authority[i] = (i >= learned.training_end and observed[i]
                                and i - last_accept[name] <= AUTHORITY_TTL
                                and (name != "evidence_aware" or pending is None))
    return outputs


def _longest_post_training_dropout(mask: np.ndarray, start: int) -> tuple[int, int] | None:
    runs = []
    a = None
    for i in range(start, len(mask) + 1):
        bad = i < len(mask) and not mask[i]
        if bad and a is None:
            a = i
        if not bad and a is not None:
            runs.append((a, i))
            a = None
    return max(runs, key=lambda x: x[1] - x[0]) if runs else None


def grade_trial(trial: Trial, estimates: dict[str, Estimate],
                training_end: int) -> dict[str, dict]:
    """Offline scoring: truth is used here, never in run_estimators."""
    scores = {}
    black = _longest_post_training_dropout(trial.observed, training_end)
    for name, estimate in estimates.items():
        diff = wrap(estimate.heading[training_end:] - trial.truth[training_end:])
        unwrapped = estimate.heading[training_end:] - trial.truth[training_end:]
        wrong = harmful = 0
        examples = []
        for event in estimate.events:
            g = grade_correction(event.before, event.after, event.target, trial.truth[event.index])
            wrong += g.incorrect_target
            harmful += g.harmful
            if (g.incorrect_target or g.harmful) and len(examples) < 5:
                examples.append({"index": event.index, "target_error_deg": round(float(wrap(event.target - trial.truth[event.index]) * DEG), 3),
                                 "harmful": g.harmful, "via_witness": event.via_witness})
        recovery = None
        if black:
            # Grader-only: first run of 30 samples with <=5deg heading error
            # AND a live accepted visual anchor, after the largest dropout.
            for i in range(black[1], len(trial.truth) - 29):
                err = np.abs(wrap(estimate.heading[i:i+30] - trial.truth[i:i+30]))
                if estimate.authority[i] and np.all(err <= np.deg2rad(5)):
                    recovery = i - black[1]
                    break
        scores[name] = {
            "heading_rmse_deg": float(np.sqrt(np.mean(diff ** 2)) * DEG),
            "max_heading_error_deg": float(np.max(np.abs(diff)) * DEG),
            "unwrapped_rmse_deg": float(np.sqrt(np.mean(unwrapped ** 2)) * DEG),
            "incorrect_accepted_corrections": int(wrong),
            "harmful_accepted_corrections": int(harmful),
            "accepted_corrections": len(estimate.events),
            "heading_available_fraction": float(np.mean(estimate.authority[training_end:])),
            "recovery_samples": recovery,
            "pixel_multiplications": estimate.pixel_multiplications,
            "witness_pair_checks": estimate.witness_pair_checks,
            "witness_requests": estimate.witness_requests,
            "witness_resolutions": estimate.witness_resolutions,
            "bounded_obstructions": estimate.bounded_obstructions,
            "deferred_ambiguous": estimate.deferred_ambiguous,
            "alias_unresolved_samples": estimate.alias_unresolved_samples,
            "incorrect_examples": examples,
        }
    return scores


def run_benchmark(stress: str, seed: int, turns: int = 12,
                  include_trace: bool = False) -> dict:
    start = time.perf_counter()
    trial = generate_trial(stress, seed, turns)
    learned = build_first_turn_map(trial.columns, trial.observed, trial.gyro_deltas)
    estimates = run_estimators(trial.columns, trial.observed, trial.gyro_deltas)
    alias_period = detect_rotational_alias(learned)
    blackout = _longest_post_training_dropout(trial.observed, learned.training_end)
    result = {
        "evidence_class": "SYNTHETIC_CONTROLLED", "protocol": "adversarial-one-column-v1",
        "stress": stress, "seed": seed, "turns": turns,
        "samples": len(trial.truth), "rows": ROWS, "map_bins": BINS,
        "training_end": learned.training_end, "map_coverage": float(np.mean(learned.occupied)),
        "alias_period_bins": alias_period,
        "blackout": blackout,
        "methods": grade_trial(trial, estimates, learned.training_end),
        "elapsed_seconds_total": time.perf_counter() - start,
        "limitations": [
            "Procedural textured cylinder, not a true line-scan sensor or moving-aircraft recording.",
            "Finite-horizon witness obstruction conditional on frozen map and constant-rate projection.",
            "Visual anchor availability is not authorization to fly; yaw revolution count remains unresolved.",
            "Robust and evidence-aware modes use identical causal temporal scores and thresholds.",
        ],
    }
    if include_trace:
        result["audit_trace"] = {
            "truth": trial.truth.tolist(), "observed": trial.observed.tolist(),
            "gyro_deltas": trial.gyro_deltas.tolist(),
            "methods": {name: {"heading": est.heading.tolist(),
                               "authority": est.authority.tolist(),
                               "events": [vars(e) for e in est.events]}
                        for name, est in estimates.items()},
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stress", choices=STRESSES, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--turns", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-trace", action="store_true")
    args = parser.parse_args()
    result = run_benchmark(args.stress, args.seed, args.turns, args.include_trace)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "audit_trace"}, indent=2))


if __name__ == "__main__":
    main()
